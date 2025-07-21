#!/usr/bin/env python3
"""
Count messages in Updates & Promotions from the past 7 days.
"""

import os
from dotenv import load_dotenv
import openai
import google.generativeai as genai
from datetime import datetime, timedelta
from gmail_service import get_service
import base64
from email.mime.text import MIMEText
import re
from collections import defaultdict
import urllib.parse
from bs4 import BeautifulSoup

# Configuration - easily change the model here
MODEL_CONFIG = {
    "fast": "gpt-3.5-turbo",  # Cheaper, faster
    "balanced": "gpt-4o",     # Good balance of cost/quality
    "best": "gpt-4",          # Best quality, most expensive
    "gemini-fast": "gemini-1.5-flash",  # Gemini's fastest model
    "gemini-balanced": "gemini-1.5-pro",  # Gemini's balanced model
    "gemini-best": "gemini-2.0-flash-exp"  # Gemini's best model
}

# Current model setting - change this to switch models
CURRENT_MODEL = "gemini-fast"  # Options: "fast", "balanced", "best", "gemini-fast", "gemini-balanced", "gemini-best"

def get_openai_api_key():
    """Load the OpenAI API key from the .env file."""
    load_dotenv()
    return os.getenv("OPENAI_API_KEY")

def get_gemini_api_key():
    """Load the Gemini API key from the .env file."""
    load_dotenv()
    # Try both possible environment variable names
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return api_key


def get_model_name():
    """Get the current model name based on configuration."""
    return MODEL_CONFIG.get(CURRENT_MODEL, "gpt-4o")

def is_gemini_model():
    """Check if the current model is a Gemini model."""
    return CURRENT_MODEL.startswith("gemini-")


def estimate_cost(input_tokens, output_tokens, model_name):
    """Estimate the cost of an API call based on token usage."""
    # OpenAI pricing per 1K tokens (as of 2024)
    openai_pricing = {
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},  # $0.0005/$0.0015 per 1K tokens
        "gpt-4o": {"input": 0.005, "output": 0.015},           # $0.005/$0.015 per 1K tokens
        "gpt-4": {"input": 0.03, "output": 0.06}               # $0.03/$0.06 per 1K tokens
    }
    
    # Gemini pricing per 1M characters (as of 2024)
    gemini_pricing = {
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},      # $0.075/$0.30 per 1M chars
        "gemini-1.5-pro": {"input": 3.50, "output": 10.50},        # $3.50/$10.50 per 1M chars
        "gemini-2.0-flash-exp": {"input": 0.15, "output": 0.60}    # $0.15/$0.60 per 1M chars
    }
    
    if model_name in openai_pricing:
        model_pricing = openai_pricing[model_name]
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
    elif model_name in gemini_pricing:
        model_pricing = gemini_pricing[model_name]
        # Convert tokens to characters (rough approximation: 1 token ≈ 4 characters)
        input_chars = input_tokens * 4
        output_chars = output_tokens * 4
        input_cost = (input_chars / 1000000) * model_pricing["input"]
        output_cost = (output_chars / 1000000) * model_pricing["output"]
    else:
        # Default to GPT-4o pricing
        model_pricing = openai_pricing["gpt-4o"]
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
    
    total_cost = input_cost + output_cost
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "model": model_name
    }


def get_email_body(msg_detail):
    """Extract the plain text body from the email if available, else fallback to snippet."""
    payload = msg_detail.get("payload", {})
    # Try to find the plain text part
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                import base64
                import quopri
                data = part["body"]["data"]
                # Gmail API returns base64url encoded data
                decoded = base64.urlsafe_b64decode(data).decode(errors="ignore")
                # Sometimes it's quoted-printable encoded
                try:
                    decoded = quopri.decodestring(decoded).decode(errors="ignore")
                except Exception:
                    pass
                return decoded.strip()
    # Fallback to snippet
    return msg_detail.get("snippet", "")


def make_ai_call(prompt, max_tokens=1000, temperature=0.5):
    """Make an API call to either OpenAI or Gemini based on current model setting."""
    if is_gemini_model():
        return make_gemini_call(prompt, max_tokens, temperature)
    else:
        return make_openai_call(prompt, max_tokens, temperature)

def make_openai_call(prompt, max_tokens=1000, temperature=0.5):
    """Make an API call to OpenAI."""
    openai.api_key = get_openai_api_key()
    try:
        response = openai.chat.completions.create(
            model=get_model_name(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response and response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip(), response.usage
        else:
            return "[No response]", None
    except Exception as e:
        return f"[Error: {e}]", None

def make_gemini_call(prompt, max_tokens=1000, temperature=0.5):
    """Make an API call to Gemini."""
    try:
        genai.configure(api_key=get_gemini_api_key())
        model = genai.GenerativeModel(get_model_name())
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        if response and response.text:
            # Create a mock usage object similar to OpenAI's
            class MockUsage:
                def __init__(self, prompt_tokens, completion_tokens):
                    self.prompt_tokens = prompt_tokens
                    self.completion_tokens = completion_tokens
            
            # Rough token estimation (1 token ≈ 4 characters)
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(response.text) // 4
            usage = MockUsage(prompt_tokens, completion_tokens)
            
            return response.text.strip(), usage
        else:
            return "[No response]", None
    except Exception as e:
        return f"[Error: {e}]", None

def is_relevant_newsletter(subject, sender, body):
    """Use AI to classify if an email is a relevant newsletter, with reasoning and improved exclusion/inclusion logic."""
    prompt = (
        "You are an expert email assistant helping curate a weekly newsletter summary for a tech/product/VC leader.\n"
        "Given the following email, answer these two questions:\n"
        "1. Should this email be included in a weekly newsletter post about technology, AI, product management, growth, stock market, politics, or venture capital?\n"
        "   - Include if it is a thought leadership, analysis, or curated content newsletter (e.g., Stratechery, Lenny's, a16z, Adam Grant, Chartr, AI Secret, Defiant, Cointracker, The Information, The Block, Keychain, Guy Raz, Snacks, Newcomer, Sequoia, Y Combinator, etc.).\n"
        "   - Exclude if it is a transactional alert (e.g., Google Pay, Coinbase price alerts, Robinhood), job alert, product update (e.g., Replit updates), LinkedIn InMail or event invite, generic news digest (e.g., NYT daily news unless deep tech/VC/PM/AI analysis), job/interview prep community (e.g., Exponent, Glassdoor), or notification/alert.\n"
        "2. Explain your reasoning in 1-2 sentences.\n\n"
        f"Email details:\nSubject: {subject}\nSender: {sender}\nBody: {body[:1000]}\n\n"
        "Respond in this format:\nReason: [your reasoning]\nInclude: [yes/no]"
    )
    
    content, usage = make_ai_call(prompt, max_tokens=100, temperature=0)
    if content and "include:" in content.lower():
        include_line = next((line for line in content.splitlines() if "include:" in line.lower()), "")
        result = "yes" in include_line.lower()  # Convert to lowercase for comparison
        return result, usage
    else:
        return False, usage


def summarize_single_email(subject, sender, body):
    """Use AI to generate a detailed summary of a single email."""
    prompt = (
        "You are an expert newsletter summarizer. Read the following email and write a detailed, insightful summary (not just a sentence or two). "
        "Capture the main ideas, arguments, and any actionable insights.\n"
        f"Subject: {subject}\nSender: {sender}\nBody: {body}\n"
        "Summary: "
    )
    return make_ai_call(prompt, max_tokens=1000, temperature=0.5)


def merge_batch_summaries(batch_summaries_with_meta):
    """Use AI to merge a batch of email summaries into a section summary."""
    email_summaries = "\n\n".join([
        f"{i+1}. Subject: {meta['subject']} | From: {meta['sender']}\nSummary: {meta['summary']}"
        for i, meta in enumerate(batch_summaries_with_meta)
    ])
    prompt = (
        "You are an expert newsletter editor. Merge the following email summaries into a single, cohesive, engaging, and insightful section of a newsletter post for a tech/product leader.\n"
        "- Group similar topics together.\n"
        "- Synthesize key insights, trends, and actionable takeaways.\n"
        "- Write in a clear, engaging, and professional style.\n"
        "- For each insight or fact, cite the original email's subject and sender.\n"
        "- Do NOT just list the summaries; weave them into a narrative as a real newsletter would.\n\n"
        f"Here are the email summaries:\n{email_summaries}\n\n"
        "Write the section."
    )
    return make_ai_call(prompt, max_tokens=2000, temperature=0.5)


def merge_sections_to_newsletter(section_summaries):
    """Use AI to merge section summaries into the final newsletter post."""
    sections_text = "\n\n".join(section_summaries)
    prompt = (
        "You are an expert newsletter editor. Merge the following newsletter sections into a single, cohesive, engaging, and insightful newsletter post for a tech/product leader.\n"
        "- Group similar topics together if possible.\n"
        "- Synthesize key insights, trends, and actionable takeaways.\n"
        "- Write in a clear, engaging, and professional style.\n"
        "- For each insight or fact, cite the original email's subject and sender if possible.\n"
        "- Do NOT just list the sections; weave them into a narrative as a real newsletter would.\n"
        "- The post should take 10-15 minutes to read.\n\n"
        f"Here are the newsletter sections:\n{sections_text}\n\n"
        "Write the final newsletter post. At the end, include a section titled 'Sources' listing all the newsletters (subject and sender) you used."
    )
    return make_ai_call(prompt, max_tokens=4000, temperature=0.5)


def fetch_and_print(service, label, label_name, read_status):
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y/%m/%d")
    query = f"after:{cutoff} label:{label} {'is:read' if read_status == 'read' else 'is:unread'}"
    print(f"\n--- {label_name} ({read_status.title()}) ---")
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=5)
        .execute()
    )
    messages = resp.get("messages", [])
    print(f"Found {len(messages)} message(s) in {label_name} ({read_status}) in the last week.")
    emails = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["Subject", "From"]).execute()
        headers = {h["name"]: h["value"] for h in msg_detail["payload"]["headers"]}
        subject = headers.get("Subject", "(No Subject)")
        sender = headers.get("From", "(No Sender)")
        snippet = msg_detail.get("snippet", "")
        emails.append({"subject": subject, "sender": sender, "snippet": snippet})
    # Generate a combined summary for the section
    # This section is no longer needed as we are not summarizing newsletters here.
    # The new workflow uses summarize_single_email and merge_summaries_to_newsletter.
    # print(f"Summary for {label_name} ({read_status.title()}):\n{section_summary}\n")


def build_summary_email_body(section_summaries):
    """Build the email body from the section summaries."""
    body = [
        "Hi Akshat,",
        "\nHere's your weekly summary for Promotions and Updates:\n"
    ]
    for section, summary in section_summaries.items():
        body.append(f"--- {section} ---\n{summary}\n")
    body.append("\nHave a great week!\n")
    return "\n".join(body)


def send_email(service, to, subject, body):
    """Send an email using the Gmail API."""
    message = MIMEText(body)
    message["to"] = to
    message["from"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_body = {"raw": raw}
    service.users().messages().send(userId="me", body=message_body).execute()


def get_gmail_link(msg_id):
    """Generate a Gmail web link to the email by its message ID."""
    # Properly encode the message ID for URL safety
    encoded_msg_id = urllib.parse.quote(msg_id, safe='')
    # Use Gmail search format which is more reliable for finding specific messages
    return f"https://mail.google.com/mail/u/0/#search/{encoded_msg_id}"


def summarize_email_bullets(subject, sender, body, msg_id):
    """Use AI to generate 2-3 bullet point key takeaways for an email with hyperlinks."""
    gmail_link = get_gmail_link(msg_id)
    prompt = (
        "You are an expert newsletter summarizer. Read the following email and write 2-3 bullet points with the key takeaways.\n"
        f"Subject: {subject}\nSender: {sender}\nBody: {body}\n"
        "For each bullet point, start with a bolded phrase (the key insight), followed by a colon and the explanation. Do NOT include any emoji, symbol, numbering, 'Point N:', or bullet symbols at the start of the bullet. Just write the summary text for each point, starting with <b>Key Insight:</b> or a similar bolded phrase.\n"
        "Example:\n<b>AI as a Catalyst:</b> AI is transforming industries by enabling more personalized and efficient solutions.\n"
        "Bullet points:"
    )
    content, usage = make_ai_call(prompt, max_tokens=300, temperature=0.5)
    if content:
        bullets = content.strip()
        lines = []
        for bullet in bullets.split('\n'):
            lines.append(bullet)
        return '\n'.join(lines), usage
    else:
        return "- [Summary unavailable]", usage


def extract_sender_name(sender):
    """Extract the sender's name from the sender string."""
    match = re.match(r'"?([^"<]*)"?\s*<.*>', sender)
    if match:
        return match.group(1).strip()
    return sender


def clean_html_output(html):
    """Remove code block markers and generic summary lines from AI output."""
    # Remove triple backticks and language tags
    html = re.sub(r'```[a-zA-Z]*', '', html)
    html = html.replace('```', '')
    # Remove the generic summary line if present
    html = re.sub(r'This enhanced newsletter provides a more comprehensive and educational overview of the key topics, offering readers valuable insights and context to better understand the trends and developments in technology, investment, and market dynamics\.', '', html, flags=re.IGNORECASE)
    html = html.strip()
    return html


def get_date_range_str(messages):
    """Get the date range string for the subject line based on the emails."""
    if not messages:
        return ""
    from datetime import datetime
    # Gmail message IDs are not timestamps, so get internalDate from the first and last message
    timestamps = []
    for msg in messages:
        if 'internalDate' in msg:
            timestamps.append(int(msg['internalDate']) // 1000)
    if not timestamps:
        return ""
    start = min(timestamps)
    end = max(timestamps)
    start_dt = datetime.utcfromtimestamp(start)
    end_dt = datetime.utcfromtimestamp(end)
    # Format as 'July 7–13, 2025'
    if start_dt.month == end_dt.month:
        date_range = f"{start_dt.strftime('%B')} {start_dt.day}–{end_dt.day}, {end_dt.year}"
    else:
        date_range = f"{start_dt.strftime('%b %d')} – {end_dt.strftime('%b %d, %Y')}"
    return date_range


def synthesize_newsletter_post(bullet_points_html):
    """Use AI to synthesize a cohesive, newsletter-style post from the bullet-pointed HTML summary, with proper HTML formatting and more emojis."""
    prompt = (
        "You are an expert newsletter editor. Here is a list of key takeaways from various newsletters, grouped by source. "
        "Please synthesize this into a single, engaging, newsletter-style post for a tech/product/VC leader. "
        "Group similar topics, highlight trends, and write in a clear, professional style. "
        "Output the result as HTML with the following formatting: "
        "- Use <h2> for the main title, <h3> for each section/topic, and <ul><li> for bullet points. "
        "- Add spacing between sections for clarity. "
        "- Do NOT include any sign-off, closing, or 'Best regards' lines. "
        "- Do NOT just list the points—create a narrative digest, but keep the structure clear and scannable.\n\n"
        "- Use relevant emojis in section headers and bullet points to make the newsletter lively and engaging.\n\n"
        "- The main title should be: 'Your weekly insights in the world of AI, technology, stock markets, and politics.'\n\n"
        f"Here are the takeaways (in HTML):\n{bullet_points_html}\n\n"
        "Write the newsletter post as HTML."
    )
    return make_ai_call(prompt, max_tokens=3000, temperature=0.5)


def enhance_newsletter_with_review_agent(newsletter_html, original_bullets):
    """Use a second AI agent to review and enhance the newsletter, making it more detailed and educational."""
    prompt = (
        "You are an expert newsletter reviewer and enhancer. Your job is to take a newsletter post and make it more detailed, educational, and insightful.\n\n"
        "The current newsletter post is:\n"
        f"{newsletter_html}\n\n"
        "The original bullet points that were synthesized were:\n"
        f"{original_bullets}\n\n"
        "Please enhance this newsletter by:\n"
        "1. Adding more context and background information where relevant\n"
        "2. Explaining concepts more thoroughly so readers feel like they're learning something\n"
        "3. Connecting related insights across different sources\n"
        "4. Adding more detailed explanations for key trends or developments\n"
        "5. Making sure hyperlinks are preserved and meaningful\n"
        "6. Ensuring the tone is educational but engaging\n"
        "7. Adding more depth to each section while maintaining readability\n\n"
        "The goal is to make this feel like a comprehensive, educational newsletter that provides real value and learning.\n"
        "Output the enhanced newsletter as HTML, maintaining the same structure but with more detail and educational content."
    )
    try:
        content, usage = make_ai_call(prompt, max_tokens=5000, temperature=0.3)
        if content and content != "[Error:":
            return content, usage
        else:
            return newsletter_html, usage  # Fallback to original if enhancement fails
    except Exception as e:
        print(f"Enhancement failed: {e}")
        return newsletter_html, None  # Fallback to original


def append_read_more_links(html, bullet_to_links):
    """Append 'Read more here' hyperlinks to each bullet point in the HTML newsletter."""
    soup = BeautifulSoup(html, 'html.parser')
    from bs4 import Tag
    bullet_idx = 0
    for ul in soup.find_all('ul'):
        if not isinstance(ul, Tag):
            continue
        for li in ul.find_all('li'):
            if not isinstance(li, Tag):
                continue
            if bullet_idx < len(bullet_to_links):
                links = bullet_to_links[bullet_idx]
                if links:
                    if len(links) == 1:
                        read_more = soup.new_tag('a', href=links[0], target="_blank", style="color: #1a73e8; text-decoration: underline;")
                        read_more.string = 'here'
                        li.append(' ')  # space before
                        li.append('Read more ')
                        li.append(read_more)
                    else:
                        li.append(' ')
                        li.append('Read more ')
                        for i, link in enumerate(links):
                            read_more = soup.new_tag('a', href=link, target="_blank", style="color: #1a73e8; text-decoration: underline;")
                            read_more.string = 'here'
                            li.append(read_more)
                            if i < len(links) - 2:
                                li.append(', ')
                            elif i == len(links) - 2:
                                li.append(' and ')
                bullet_idx += 1
    return str(soup)


def remove_all_links(html):
    """Remove all <a> tags from the HTML output, regardless of destination."""
    soup = BeautifulSoup(html, 'html.parser')
    from bs4 import Tag
    for a in soup.find_all('a'):
        if isinstance(a, Tag):
            a.unwrap()  # Remove the <a> tag but keep the text
    return str(soup)


def print_cost_summary(total_costs):
    """Print a summary of all costs incurred."""
    print("\n" + "="*50)
    print("💰 COST SUMMARY")
    print("="*50)
    
    total_spent = 0
    for i, cost in enumerate(total_costs, 1):
        print(f"\nCall {i} ({cost['model']}):")
        print(f"  Input:  {cost['input_tokens']:,} tokens (${cost['input_cost']:.4f})")
        print(f"  Output: {cost['output_tokens']:,} tokens (${cost['output_cost']:.4f})")
        print(f"  Total:  ${cost['total_cost']:.4f}")
        total_spent += cost['total_cost']
    
    print(f"\n🎯 TOTAL COST: ${total_spent:.4f}")
    print(f"📊 Average per call: ${total_spent/len(total_costs):.4f}")
    print("="*50)


def format_bullets_with_titles(html, bullet_to_links):
    """Format each bullet as: bullet text with 'Read more here' appended, no numbering or 'Point N:'."""
    from bs4 import Tag
    from bs4.element import NavigableString
    import re
    soup = BeautifulSoup(html, 'html.parser')
    bullet_idx = 0
    for ul in soup.find_all('ul'):
        if not isinstance(ul, Tag):
            continue
        for li in ul.find_all('li'):
            if not isinstance(li, Tag):
                continue
            # Remove all children that are <b> or <strong> at the start (no longer needed, but keep for safety)
            while li.contents and isinstance(li.contents[0], Tag) and hasattr(li.contents[0], 'name') and li.contents[0].name in ['b', 'strong']:
                li.contents[0].decompose()
            # Remove leading whitespace
            if li.contents and isinstance(li.contents[0], NavigableString):
                li.contents[0].replace_with(NavigableString(li.contents[0].lstrip()))
            # Remove any previous 'Read more' text
            li_text = li.get_text()
            li.clear()
            # Remove any previous 'Read more' text
            main_text = re.sub(r'Read more.*$', '', li_text).strip()
            li.append(NavigableString(main_text))
            # Append 'Read more here.' with only 'here' hyperlinked
            if bullet_idx < len(bullet_to_links):
                links = bullet_to_links[bullet_idx]
                if links:
                    li.append(NavigableString(' Read more '))
                    for i, link in enumerate(links):
                        read_more = soup.new_tag('a', href=link, target="_blank", style="color: #1a73e8; text-decoration: underline;")
                        read_more.string = 'here'
                        li.append(read_more)
                        if i < len(links) - 2:
                            li.append(NavigableString(', '))
                        elif i == len(links) - 2:
                            li.append(NavigableString(' and '))
                    li.append(NavigableString('.'))
            bullet_idx += 1
    return str(soup)


def bold_first_phrase(bullet):
    # Remove any HTML tags (if present)
    bullet = re.sub(r'<.*?>', '', bullet)
    # Remove leading bullet symbols, whitespace, and emojis
    bullet = re.sub(r'^[\s\-•🔍🌟💡🚀🤖🛫🛬🛒📈📉📊📰]+', '', bullet)
    # Bold up to the first colon (and keep the colon)
    match = re.match(r'([^:]+:)(.*)', bullet)
    if match:
        return f'<b>{match.group(1).strip()}</b>{match.group(2)}'
    return bullet


def agentic_verify_links(emails, final_html):
    # Build the list of source emails for the prompt
    email_list = "\n".join([
        f"{i+1}. Subject: {email['subject']} | Snippet: {email['body'][:200]} | Link: {get_gmail_link(email['msg_id'])}"
        for i, email in enumerate(emails)
    ])
    prompt = (
        "You are an expert newsletter QA agent.\n"
        "Here is a list of source emails (with subject, snippet, and link):\n"
        f"{email_list}\n\n"
        "First, for each bullet in the summary, check if the 'Read more here' hyperlink points to the correct source email, based on the bullet content and the email subject/snippet.\n"
        "For any mismatches, list the bullet and the correct link. If all are correct, say 'All links are correct.'\n\n"
        "Second, review the overall quality of the summary as a newsletter. Does it feel like a well-written, engaging, and enjoyable newsletter that someone would look forward to reading with their morning coffee on Mondays?\n"
        "If not, provide specific, constructive feedback on how to improve the tone, structure, or content to make it more appealing and engaging."
    )
    print("\nRunning agentic verification of summary links and quality...\n")
    qa_report, usage = make_ai_call(prompt, max_tokens=1500, temperature=0.0)
    if qa_report and qa_report != "[Error:":
        print("Agentic QA Report:\n" + qa_report)
        return qa_report
    else:
        print("Agentic QA failed or returned no output.")
        return None

# Parse the QA agent's output for link corrections
import re

def parse_link_corrections(qa_report):
    # Returns a dict: {bullet_summary: correct_link}
    corrections = {}
    if not qa_report:
        return corrections
    # Look for lines like: The correct link should be from the email with the subject "..."
    pattern = re.compile(r'\*\*(.*?)\*\*:.*?The correct link should be from the email with the subject "([^"]+)"', re.DOTALL)
    for match in pattern.finditer(qa_report):
        bullet_summary = match.group(1).strip()
        subject = match.group(2).strip()
        corrections[bullet_summary] = subject
    return corrections

def update_links_in_html(final_html, corrections, emails):
    from bs4 import BeautifulSoup, Tag
    soup = BeautifulSoup(final_html, 'html.parser')
    # Build subject->link mapping
    subject_to_link = {email['subject']: get_gmail_link(email['msg_id']) for email in emails}
    for li in soup.find_all('li'):
        if not isinstance(li, Tag):
            continue
        text = li.get_text()
        for bullet_summary, subject in corrections.items():
            if bullet_summary in text and subject in subject_to_link:
                # Find the 'here' link and update its href
                for a in li.find_all('a'):
                    if isinstance(a, Tag) and a.string == 'here':
                        a['href'] = subject_to_link[subject]
    return str(soup)


def main():
    print(f"🤖 Using model: {get_model_name()} ({CURRENT_MODEL} setting)")
    print(f"💡 To change models, edit CURRENT_MODEL in the script: 'fast', 'balanced', or 'best'")
    
    service = get_service()
    total_costs = []  # Track all API costs
    
    # Fetch all emails from the past 7 days in Primary and Updates categories only
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y/%m/%d")
    query = f"after:{cutoff} (category:primary OR category:updates)"
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=500)
        .execute()
    )
    messages = resp.get("messages", [])
    qualifying_emails = []
    
    print(f"\n📧 Processing {len(messages)} emails...")
    
    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="full", metadataHeaders=["Subject", "From"]).execute()
        headers = {h["name"]: h["value"] for h in msg_detail["payload"]["headers"]}
        subject = headers.get("Subject", "(No Subject)")
        sender = headers.get("From", "(No Sender)")
        sender_name = extract_sender_name(sender)
        body = get_email_body(msg_detail)
        
        # Skip emails from self
        if "akshatk7@gmail.com" in sender.lower():
            continue
            
        # Track cost for classification
        is_relevant, usage = is_relevant_newsletter(subject, sender, body)
        if usage:
            cost = estimate_cost(usage.prompt_tokens, usage.completion_tokens, get_model_name())
            total_costs.append(cost)
        
        if is_relevant:
            qualifying_emails.append({
                "subject": subject, 
                "sender": sender, 
                "sender_name": sender_name, 
                "body": body,
                "msg_id": msg["id"],
                "internalDate": msg_detail.get("internalDate")
            })
    
    print(f"✅ Found {len(qualifying_emails)} relevant newsletters")
    
    # Group by sender_name
    grouped = defaultdict(list)
    for email in qualifying_emails:
        grouped[email["sender_name"]].append(email)
    
    # Build the bullet-pointed HTML summary with hyperlinks
    lines = ["Hey Akshat, here is a summary of all the newsletters you received last week.<br><br>"]
    bullet_to_links = []
    for idx, (newsletter, emails) in enumerate(grouped.items(), 1):
        lines.append(f"<b>{idx}. {newsletter}</b>:<br>")
        for email in emails:
            bullets, usage = summarize_email_bullets(email["subject"], email["sender"], email["body"], email["msg_id"])
            if usage:
                cost = estimate_cost(usage.prompt_tokens, usage.completion_tokens, get_model_name())
                total_costs.append(cost)
            for bullet in filter(None, bullets.split("\n")):
                bullet_html = bold_first_phrase(bullet.strip())
                lines.append(f"&nbsp;&nbsp;• {bullet_html}<br>")
                bullet_to_links.append([get_gmail_link(email["msg_id"])])
        lines.append("<br>")
    
    bullet_points_html = "".join(lines)
    
    # Synthesize the initial newsletter post
    print("Generating initial newsletter post...")
    newsletter_post, usage = synthesize_newsletter_post(bullet_points_html)
    if usage:
        cost = estimate_cost(usage.prompt_tokens, usage.completion_tokens, get_model_name())
        total_costs.append(cost)
    
    # Enhance with the review agent
    print("Enhancing with review agent...")
    enhanced_newsletter, usage = enhance_newsletter_with_review_agent(newsletter_post, bullet_points_html)
    if usage:
        cost = estimate_cost(usage.prompt_tokens, usage.completion_tokens, get_model_name())
        total_costs.append(cost)
    
    # Clean up the HTML output
    cleaned_html = clean_html_output(enhanced_newsletter)
    
    # Remove all links from the AI output
    cleaned_html = remove_all_links(cleaned_html)
    
    # Format bullets with bolded Point N and 'Read more here.'
    final_html = format_bullets_with_titles(cleaned_html, bullet_to_links)
    
    # Get the date range for the subject line
    date_range = get_date_range_str(qualifying_emails)
    subject_line = f"Weekly Digest: {date_range}" if date_range else "Your Weekly Newsletter Summaries"
    
    # After final_html is built, but before sending the email, run agentic verification
    qa_report = agentic_verify_links(qualifying_emails, final_html)
    corrections = parse_link_corrections(qa_report)
    if corrections:
        print("\nApplying hyperlink corrections from QA agent...\n")
        final_html = update_links_in_html(final_html, corrections, qualifying_emails)

    # Send as HTML
    message = MIMEText(final_html, "html")
    message["to"] = "akshatk7@gmail.com"
    message["from"] = "akshatk7@gmail.com"
    message["subject"] = subject_line
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_body = {"raw": raw}
    service.users().messages().send(userId="me", body=message_body).execute()
    print("\nEnhanced summary email sent!")
    
    # Print actual cost summary
    if total_costs:
        print_cost_summary(total_costs)
    else:
        print("\n💡 No cost data available (API calls may have failed)")

if __name__ == "__main__":
    main()
