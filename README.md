# Gmail Newsletter Summarizer

This project is an AI-powered system that summarizes your weekly newsletters from Gmail and sends you a well-formatted, engaging summary email.

## Features
- Fetches up to 500 emails from your Gmail (Primary and Updates categories)
- Uses OpenAI GPT models to summarize and synthesize newsletter content
- Automated agentic QA: checks and corrects all "Read more here" hyperlinks to ensure they point to the correct source email
- Provides quality feedback on the newsletter's tone, structure, and engagement
- Outputs a beautiful, easy-to-read HTML summary email

## How It Works
1. Fetches recent emails from Gmail using the Gmail API
2. Classifies and summarizes relevant newsletters using OpenAI
3. Synthesizes a narrative summary and enhances it for readability
4. Runs an agentic QA step to verify and correct hyperlinks
5. Sends the final summary as an HTML email

## Usage
1. Clone the repo and install dependencies
2. Set up your `.env` file with your OpenAI API key and Gmail API credentials
3. Run the script:
   ```bash
   python3 fetch_updates.py
   ```
4. Check your email for the summary and review the QA report in your terminal

## Configuration
- Change the `maxResults` parameter in `fetch_updates.py` to adjust how many emails are processed
- Edit the OpenAI model in the script for cost/quality trade-offs

## Customization
- You can further personalize the summary style, add more agentic steps, or automate quality improvements as needed

---

Enjoy your AI-powered, self-correcting newsletter summaries! 