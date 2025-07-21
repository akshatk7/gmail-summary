#!/usr/bin/env python3
"""
Quick test script to debug Gemini API classification
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def get_gemini_api_key():
    """Load the Gemini API key from the .env file."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return api_key

def test_gemini_classification():
    """Test Gemini API with sample emails"""
    
    # Configure Gemini
    genai.configure(api_key=get_gemini_api_key())
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Sample emails to test
    test_emails = [
        {
            "subject": "The Information: Tech Briefing",
            "sender": "The Information <noreply@theinformation.com>",
            "body": "Latest tech news and analysis from The Information..."
        },
        {
            "subject": "Lenny's Newsletter: Product Management Insights",
            "sender": "Lenny Rachitsky <lenny@substack.com>",
            "body": "This week's product management insights and case studies..."
        },
        {
            "subject": "Your Uber receipt",
            "sender": "Uber <receipts@uber.com>",
            "body": "Thank you for your ride. Here's your receipt..."
        },
        {
            "subject": "a16z Newsletter: Venture Capital Updates",
            "sender": "Andreessen Horowitz <newsletter@a16z.com>",
            "body": "Latest insights from the venture capital world..."
        }
    ]
    
    prompt_template = (
        "You are an expert email assistant helping curate a weekly newsletter summary for a tech/product/VC leader.\n"
        "Given the following email, answer these two questions:\n"
        "1. Should this email be included in a weekly newsletter post about technology, AI, product management, growth, stock market, politics, or venture capital?\n"
        "   - Include if it is a thought leadership, analysis, or curated content newsletter (e.g., Stratechery, Lenny's, a16z, Adam Grant, Chartr, AI Secret, Defiant, Cointracker, The Information, The Block, Keychain, Guy Raz, Snacks, Newcomer, Sequoia, Y Combinator, etc.).\n"
        "   - Exclude if it is a transactional alert (e.g., Google Pay, Coinbase price alerts, Robinhood), job alert, product update (e.g., Replit updates), LinkedIn InMail or event invite, generic news digest (e.g., NYT daily news unless deep tech/VC/PM/AI analysis), job/interview prep community (e.g., Exponent, Glassdoor), or notification/alert.\n"
        "2. Explain your reasoning in 1-2 sentences.\n\n"
        "Email details:\nSubject: {subject}\nSender: {sender}\nBody: {body}\n\n"
        "Respond in this format:\nReason: [your reasoning]\nInclude: [yes/no]"
    )
    
    print("🧪 Testing Gemini API Classification...\n")
    
    for i, email in enumerate(test_emails, 1):
        print(f"📧 Test Email {i}:")
        print(f"   Subject: {email['subject']}")
        print(f"   Sender: {email['sender']}")
        
        prompt = prompt_template.format(**email)
        
        try:
            response = model.generate_content(prompt)
            content = response.text.strip()
            
            print(f"   Gemini Response: {content}")
            
            # Parse the response
            if "include:" in content.lower():
                include_line = next((line for line in content.splitlines() if "include:" in line.lower()), "")
                result = "yes" in include_line.lower()
                print(f"   ✅ Classification: {'INCLUDE' if result else 'EXCLUDE'}")
                print(f"   🔍 Debug: include_line='{include_line}', result={result}")
            else:
                print(f"   ❌ No 'include:' line found in response")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_gemini_classification() 