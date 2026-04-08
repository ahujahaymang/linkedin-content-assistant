# LinkedIn Content Assistant

An AI-powered content generation system that helps create engaging, professional LinkedIn posts tailored to your personal brand and expertise.

## Features

- **Profile Management**: Define multiple professional profiles with unique voice, expertise, and target audience
- **AI-Powered Content Strategy**: Generate 3 post options based on your profile and recent trends
- **Smart Drafting**: Convert content ideas into LinkedIn-ready posts with proper formatting
- **Memory System**: Track post history to avoid repetition and maintain content diversity
- **Multi-LLM Support**: Works with OpenAI GPT models and AWS Bedrock Claude models
- **LinkedIn-Friendly Formatting**: Generates copy-paste ready posts without markdown

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ahujahaymang/linkedin-content-assistant.git
cd linkedin-content-assistant
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

## Configuration

### API Keys

Add your API keys to `.env`:
```
OPENAI_API_KEY=your_openai_key_here
AWS_ACCESS_KEY_ID=your_aws_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_here
```

### Profile Setup

Create your profile in `profiles/active/your-profile.yaml`:
```yaml
profile_id: "your-profile"
version: 1

identity:
  headline: "Your Professional Title"
  seniority: "Senior/Mid/Junior"
  primary_domains:
    - "Your Domain 1"
    - "Your Domain 2"
  target_audience: "Your target audience"
  positioning: "How you want to be positioned"
  
behavior:
  vocabulary_bias: "technical/professional/casual"
  emoji_frequency: "rare/moderate/frequent"
  comment_depth: "brief/detailed/comprehensive"
```

## Usage

### Generate a Single Post

```bash
python3 -m linkedin_content_assistant.main generate-once --profile your-profile
```

### Start Scheduled Generation

```bash
python3 -m linkedin_content_assistant.main start --profile your-profile
```

### Health Check

```bash
python3 -m linkedin_content_assistant.main health-check
```

## Project Structure

```
linkedin-content-assistant/
├── src/linkedin_content_assistant/
│   ├── agents/           # Content strategy and drafting agents
│   ├── config/           # Configuration management
│   ├── llm/              # LLM integration layer
│   ├── memory/           # Post history and memory store
│   ├── orchestration/    # Workflow orchestration
│   └── profiles/         # Profile management
├── profiles/active/      # Active profile configurations
├── config/               # System configuration
├── data/memory/          # Generated posts and history
└── tests/                # Test suite

```

## Generated Posts

Posts are stored in `data/memory/events.json` with full metadata including:
- Post content (LinkedIn-ready, no markdown)
- Hashtags
- Call-to-action
- Theme and tone analysis
- Generation timestamp

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/linkedin_content_assistant

# Run specific test file
pytest tests/unit/test_main.py
```

### Code Style

The project follows PEP 8 style guidelines. Format code with:
```bash
black src/
```

## Safety Features

- **No Auto-Posting**: System only generates drafts, never posts automatically
- **Manual Review Required**: All posts require manual review before posting
- **Rate Limiting**: Built-in rate limiting to respect API quotas
- **No Credential Storage**: Never stores LinkedIn credentials

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues or questions, please open a GitHub issue.
