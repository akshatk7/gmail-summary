# Gmail Newsletter Summarizer

An intelligent email processing system that automatically summarizes your newsletters using AI. Supports both OpenAI and Google Gemini APIs.

## Features

- 🤖 **Dual AI Support**: Choose between OpenAI (GPT-3.5-turbo, GPT-4o, GPT-4) or Google Gemini (1.5-flash, 1.5-pro, 2.0-flash-exp)
- 📧 **Smart Email Filtering**: Automatically identifies relevant newsletters and excludes transactional emails
- 📊 **Cost Tracking**: Real-time cost estimation for all API calls
- 🔗 **Source Links**: Each summary includes "Read more here" links back to original emails
- 📝 **Comprehensive Summaries**: Generates detailed, educational newsletter posts
- ⚡ **Fast Processing**: Handles hundreds of emails efficiently

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create credentials (OAuth 2.0 Client ID)
5. Download `credentials.json` and place it in the project root

### 3. AI API Keys

Create a `.env` file in the project root:

```env
# OpenAI API Key (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-openai-key-here

# Google Gemini API Key (get from https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY=AIza-your-gemini-key-here
```

### 4. First Run Authentication

Run the script once to authenticate with Gmail:

```bash
python fetch_updates.py
```

This will open a browser window for Gmail authentication. The token will be saved for future use.

## Usage

### Basic Usage

```bash
python fetch_updates.py
```

The script will:
1. Fetch emails from the past 7 days
2. Filter out your own emails and non-newsletters
3. Classify relevant newsletters using AI
4. Generate detailed summaries
5. Send a comprehensive newsletter digest to your email

### Model Selection

Edit `fetch_updates.py` and change the `CURRENT_MODEL` setting:

```python
# OpenAI Models
CURRENT_MODEL = "fast"        # GPT-3.5-turbo (cheapest)
CURRENT_MODEL = "balanced"    # GPT-4o (good balance)
CURRENT_MODEL = "best"        # GPT-4 (best quality)

# Gemini Models
CURRENT_MODEL = "gemini-fast"     # Gemini 1.5-flash (fastest)
CURRENT_MODEL = "gemini-balanced" # Gemini 1.5-pro (balanced)
CURRENT_MODEL = "gemini-best"     # Gemini 2.0-flash-exp (best)
```

## Cost Comparison

### OpenAI Pricing (per 1K tokens)
- **GPT-3.5-turbo**: $0.0005 input, $0.0015 output
- **GPT-4o**: $0.005 input, $0.015 output
- **GPT-4**: $0.03 input, $0.06 output

### Gemini Pricing (per 1M characters)
- **Gemini 1.5-flash**: $0.075 input, $0.30 output
- **Gemini 1.5-pro**: $3.50 input, $10.50 output
- **Gemini 2.0-flash-exp**: $0.15 input, $0.60 output

### Typical Costs
- **100 emails processed**: ~$0.10-0.20 (Gemini) vs $0.50-1.00 (OpenAI)
- **Weekly newsletter**: ~$0.05-0.15 (Gemini) vs $0.20-0.50 (OpenAI)

## Newsletter Sources

The script automatically identifies and includes newsletters from:
- **Tech/Product**: Stratechery, Lenny's, a16z, Adam Grant
- **AI/ML**: AI Secret, OpenAI updates
- **Finance**: Chartr, CoinTracker, The Block
- **VC/Startups**: The Information, Newcomer, Sequoia, Y Combinator
- **News**: Guy Raz, Snacks, Defiant

## Configuration

### Email Filtering
- Automatically excludes emails from your own address
- Filters out transactional emails (receipts, alerts, etc.)
- Focuses on thought leadership and analysis content

### Output Format
- **HTML email** with proper formatting
- **Bullet points** with key insights
- **Source links** for each bullet point
- **Date range** in subject line
- **Cost summary** in console output

## Testing

Run the test script to verify Gemini API integration:

```bash
python test_gemini.py
```

This tests the classification logic with sample emails.

## Troubleshooting

### Gmail Authentication Issues
- Delete `token.json` and re-run the script
- Ensure `credentials.json` is in the project root

### API Key Issues
- Verify API keys are correctly set in `.env`
- Check billing is enabled for Gemini API
- Ensure API quotas haven't been exceeded

### No Newsletters Found
- Check the date range (default: past 7 days)
- Verify emails are in Primary/Updates categories
- Review the classification logic in the script

## File Structure

```
gmail-summary/
├── fetch_updates.py      # Main script
├── gmail_service.py      # Gmail API integration
├── test_gemini.py        # Gemini API test script
├── requirements.txt       # Python dependencies
├── credentials.json      # Gmail API credentials
├── .env                  # API keys (not in git)
└── README.md            # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `python test_gemini.py`
5. Submit a pull request

## License

MIT License - feel free to use and modify as needed. 