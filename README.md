# 🔬 Multi-Agent Research Pipeline

> **AI-Powered Research with Intelligent Search & Email Integration**

A production-ready multi-agent system that combines AI-optimized search capabilities with automated email drafting. Built with Pydantic AI, featuring Tavily search, SerpAPI fallback, and Gmail integration.

## ✨ Features

### 🔍 **Intelligent Multi-Search**
- **Primary**: Tavily API (AI-optimized search results)
- **Fallback**: SerpAPI (Google search integration)
- **Smart routing** with automatic provider selection

### 🤖 **Advanced LLM Integration**
- **Gemini** (recommended for research analysis)
- **OpenAI** (GPT-4o/4o-mini support)
- **Automatic fallback** between providers

### 📧 **Email Automation**
- **Gmail API** integration for draft creation
- **Context-aware** email generation
- **Source attribution** and professional formatting

### 🖥️ **Rich CLI Interface**
- **Interactive mode** for research sessions
- **Batch processing** for automated workflows
- **Rich formatting** with progress indicators

## 🚀 Quick Start

### 1. **Installation**

```bash
# Clone the repository
git clone <repository-url>
cd multi-agent-research-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Configuration**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Required API Keys:**
- **Tavily API**: Get from [tavily.com](https://tavily.com) (1000 searches/month free)
- **SerpAPI**: Get from [serpapi.com](https://serpapi.com) (100 searches/month free)
- **Gemini API**: Get from [Google AI Studio](https://aistudio.google.com)
- **Gmail OAuth**: Download `credentials.json` from [Google Cloud Console](https://console.cloud.google.com)

### 3. **Gmail Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download `credentials.json` to `./credentials/`

### 4. **Usage**

```bash
# Display system info
python cli.py info

# Perform research
python cli.py research "latest AI safety developments"

# Research + Email in one command
python cli.py research-and-email "AI safety research" "colleague@company.com"

# Interactive mode
python cli.py interactive
```

## 📖 Detailed Usage

### **Command Line Interface**

#### **Research Command**
```bash
python cli.py research "your research query" \
    --max-results 10 \
    --no-sources    # Hide source URLs \
    --no-summary    # Skip AI summary
```

#### **Research + Email Command**
```bash
python cli.py research-and-email \
    "quantum computing advances" \
    "recipient@email.com" \
    --context "Monthly tech update" \
    --subject "Quantum Computing Update" \
    --tone "professional" \
    --max-results 15
```

#### **Interactive Mode**
```bash
python cli.py interactive

# Interactive commands:
research latest AI developments
email colleague@company.com
history
help
quit
```

### **Programmatic Usage**

#### **Research Agent**
```python
from agents.research_agent import run_research_agent

# Perform research
response = await run_research_agent(
    query="artificial intelligence trends 2024",
    max_results=10,
    create_summary=True
)

if response.success:
    print(f"Summary: {response.data['summary']}")
    print(f"Sources: {response.data['sources']}")
```

#### **Email Agent**
```python
from agents.email_agent import run_email_agent
from agents.models import ResearchEmailRequest

# Create email from research
request = ResearchEmailRequest(
    research_query="AI trends research",
    email_context="Quarterly technology update",
    recipient_email="team@company.com",
    tone="professional",
    include_sources=True
)

response = await run_email_agent(request, research_content, sources)
```

## 🏗️ Architecture

### **System Overview**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Research Agent  │    │   Email Agent   │
│                 │───▶│                  │───▶│                 │
│ • Interactive   │    │ • Multi-search   │    │ • Gmail API     │
│ • Commands      │    │ • AI synthesis   │    │ • Draft creation│
│ • Rich output   │    │ • Source linking │    │ • Formatting    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Search Tools  │    │   LLM Providers  │    │   Gmail Tool    │
│                 │    │                  │    │                 │
│ • Tavily API    │    │ • Gemini Pro     │    │ • OAuth2 Flow   │
│ • SerpAPI       │    │ • OpenAI GPT-4   │    │ • Draft Mgmt    │
│ • Auto-fallback │    │ • Auto-selection │    │ • Send Support  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Multi-Agent Pattern**
- **Research Agent**: Primary orchestrator with search capabilities
- **Email Agent**: Specialized sub-agent for email composition
- **Tool Integration**: Each agent has access to specific tools
- **Context Passing**: Seamless data flow between agents

### **Search Strategy**
```python
# Intelligent search routing
if strategy == "intelligent":
    try:
        # 1. Try Tavily (AI-optimized)
        results = await tavily_search(query)
    except TavilyAPIError:
        # 2. Fallback to SerpAPI (Google)
        results = await serp_search(query)
```

## 🔧 Configuration

### **Environment Variables**

```bash
# LLM Configuration
LLM_PROVIDER=gemini                    # Options: openai, gemini
GEMINI_API_KEY=AIza...                 # Google AI Studio
OPENAI_API_KEY=sk-proj-...             # OpenAI API

# Search APIs
TAVILY_API_KEY=tvly-...                # AI-optimized search
SERP_API_KEY=...                       # Google search fallback

# Gmail Integration
GMAIL_CREDENTIALS_PATH=./credentials/credentials.json

# Search Strategy
SEARCH_STRATEGY=intelligent             # Options: intelligent, tavily_only, serp_only
MAX_SEARCH_RESULTS=10                  # Default result limit
SEARCH_TIMEOUT=30                      # Request timeout (seconds)

# Logging
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR
```

### **Search Strategies**

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `intelligent` | Tavily first, SerpAPI fallback | **Recommended** - Best results with reliability |
| `tavily_only` | Only use Tavily API | When you need AI-optimized results |
| `serp_only` | Only use SerpAPI | When you prefer Google search results |

### **Model Selection**

| Provider | Model | Best For |
|----------|-------|----------|
| **Gemini** | `gemini-1.5-pro` | Research analysis, contextual understanding |
| **Gemini** | `gemini-1.5-flash` | Faster processing, cost optimization |
| **OpenAI** | `gpt-4o` | General purpose, reliable performance |
| **OpenAI** | `gpt-4o-mini` | Cost-effective, lighter tasks |

## 🧪 Testing

### **Run Tests**
```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=agents --cov=tools --cov-report=html

# Integration tests (requires API keys)
pytest tests/ --integration
```

### **Test Structure**
```
tests/
├── test_tavily_search.py      # Tavily API integration
├── test_serp_search.py        # SerpAPI integration  
├── test_research_agent.py     # Research agent logic
├── test_email_agent.py        # Email agent functionality
├── test_gmail_tool.py         # Gmail API integration
└── test_cli.py               # CLI interface
```

## 📊 Performance & Limits

### **API Rate Limits**

| Provider | Free Tier | Rate Limits |
|----------|-----------|-------------|
| **Tavily** | 1,000 searches/month | 5 req/sec |
| **SerpAPI** | 100 searches/month | 1 req/sec |
| **Gemini** | 15 RPM, 1M TPM | 1.5M requests/day |
| **OpenAI** | Varies by tier | Model-dependent |

### **Performance Metrics**
- **Average Search Time**: 1-3 seconds
- **Research Analysis**: 5-15 seconds (depending on LLM)
- **Email Generation**: 3-8 seconds
- **Gmail Draft Creation**: 1-2 seconds

### **Cost Optimization**
- Use `gemini-1.5-flash` for faster, cheaper processing
- Set appropriate `MAX_SEARCH_RESULTS` limits
- Monitor token usage with built-in tracking
- Use `serp_only` strategy to conserve Tavily quota

## 🛠️ Development

### **Project Structure**
```
multi-agent-research-pipeline/
├── agents/                    # Agent implementations
│   ├── __init__.py
│   ├── models.py             # Data models
│   ├── providers.py          # LLM provider config
│   ├── research_agent.py     # Main research agent
│   └── email_agent.py        # Email composition agent
├── tools/                     # External API integrations
│   ├── __init__.py
│   ├── tavily_search.py      # Tavily API client
│   ├── serp_search.py        # SerpAPI client
│   └── gmail_tool.py         # Gmail API integration
├── config/                    # Configuration management
│   ├── __init__.py
│   └── settings.py           # Settings and validation
├── tests/                     # Comprehensive test suite
├── credentials/               # OAuth credentials (gitignored)
├── cli.py                     # Command-line interface
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

### **Adding New Search Providers**
1. Create new tool in `tools/` directory
2. Implement `SearchResult` model variant
3. Add provider to `SearchProvider` enum
4. Update `intelligent_search` logic
5. Add configuration options

### **Adding New LLM Providers**
1. Update `providers.py` with new provider
2. Add configuration in `settings.py`
3. Update environment template
4. Add tests for new provider

## 🔒 Security & Privacy

### **API Key Management**
- Store keys in `.env` file (never commit)
- Use environment variables in production
- Rotate keys regularly
- Monitor usage for unusual activity

### **Gmail Security**
- OAuth2 flow for secure authentication
- Minimal required scopes
- Token stored securely in `credentials/`
- Automatic token refresh

### **Data Handling**
- No sensitive data stored permanently
- Search results cached temporarily
- Email drafts created in user's Gmail
- All processing happens locally

## 🐛 Troubleshooting

### **Common Issues**

#### **"No search providers configured"**
```bash
# Check your API keys
python cli.py info

# Verify .env file exists and has correct keys
cat .env
```

#### **Gmail OAuth Issues**
```bash
# Ensure credentials.json exists
ls -la credentials/

# Delete token.json to re-authenticate
rm credentials/token.json
```

#### **Import Errors**
```bash
# Ensure you're in the project directory
pwd

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### **Search Provider Errors**
- **Tavily**: Check API key format (starts with `tvly-`)
- **SerpAPI**: Verify monthly quota not exceeded
- **Rate Limits**: Implement delays between requests

### **Debug Mode**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python cli.py research "test query" --verbose
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** Pull Request

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest tests/

# Code formatting
black .
ruff check . --fix

# Type checking
mypy .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Pydantic AI** - Excellent agent framework
- **Tavily** - AI-optimized search capabilities
- **SerpAPI** - Reliable Google search integration
- **Google AI Studio** - Gemini API access
- **Rich** - Beautiful terminal formatting

---

**Built with ❤️ for the AI research community**

For questions, issues, or suggestions, please open an issue on GitHub.