# 🔗 N8N Integration Guide
## Multi-Agent Research Pipeline

This guide shows you how to integrate the Multi-Agent Research Pipeline with your N8N workflows.

## 📁 **Code Location**

The complete research pipeline is located at:
```
/Users/daletaylor/Library/CloudStorage/OneDrive-Personal/All Coding Work/multi-agent-research-pipeline/
```

## 🚀 **Quick Integration Options**

### **Option 1: Direct Python Code Node**

Use the `n8n_integration.py` module directly in N8N Code nodes:

```javascript
// N8N Code Node Example
const { execSync } = require('child_process');

// Get input data
const query = $input.first().json.query || 'Python programming';
const maxResults = $input.first().json.max_results || 5;

// Path to your research pipeline
const projectPath = '/Users/daletaylor/Library/CloudStorage/OneDrive-Personal/All Coding Work/multi-agent-research-pipeline';

// Execute Python search
const pythonScript = `
import sys
sys.path.insert(0, '${projectPath}')
from n8n_integration import sync_intelligent_search
import json

result = sync_intelligent_search("${query}", ${maxResults})
print(json.dumps(result))
`;

try {
  const result = execSync(`cd ${projectPath} && python3 -c "${pythonScript}"`, { encoding: 'utf8' });
  const searchResults = JSON.parse(result);
  
  return [{ json: searchResults }];
  
} catch (error) {
  return [{ 
    json: { 
      success: false, 
      error: error.message,
      query: query 
    } 
  }];
}
```

### **Option 2: FastAPI Server** 

Run the research pipeline as a service:

1. **Start the FastAPI server:**
```bash
cd /path/to/multi-agent-research-pipeline
python3 fastapi_server.py
```

2. **Use HTTP Request Node in N8N:**
```json
{
  "method": "POST",
  "url": "http://localhost:8000/search",
  "body": {
    "query": "{{ $json.query }}",
    "max_results": 5,
    "search_strategy": "intelligent"
  }
}
```

### **Option 3: Import N8N Workflow**

Import the pre-built workflow:

1. Copy `n8n_workflow_template.json`
2. Import into your N8N instance
3. Update the project path in the Code node
4. Activate the workflow

## 📊 **Available Functions**

### **🔍 Core Search Functions**

```python
# Intelligent search (Tavily + SerpAPI fallback)
sync_intelligent_search(query, max_results=5)

# Tavily-only search (AI-optimized)
sync_tavily_search(query, max_results=5)

# SerpAPI-only search (Google results)
sync_serp_search(query, max_results=5)
```

### **🎯 Response Format**

All functions return this standardized format:

```json
{
  "success": true,
  "query": "your search query",
  "total_results": 3,
  "search_time": 2.45,
  "providers_used": ["tavily"],
  "ai_summary": "AI-generated summary from Tavily",
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com",
      "content": "Full content or snippet",
      "score": 0.95,
      "provider": "tavily",
      "published_date": "2024-01-01"
    }
  ],
  "timestamp": "2024-07-25T18:30:00.000Z"
}
```

## ⚙️ **Configuration**

### **Environment Variables**

Ensure these are set in your `.env` file:

```bash
# Search APIs
TAVILY_API_KEY=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
SERP_API_KEY=9aa5eca11968de410bd7b5dbe623e849750ff9f5a89ce64b5ad27d45dbd6b2c6

# Search Strategy
SEARCH_STRATEGY=intelligent  # Options: intelligent, tavily_only, serp_only
MAX_SEARCH_RESULTS=10
SEARCH_TIMEOUT=30
```

### **Dependencies**

Install required packages:

```bash
cd /path/to/research-pipeline
pip install -r requirements.txt
```

## 🔧 **N8N Workflow Examples**

### **Example 1: Simple Search Trigger**

1. **Webhook Trigger** → **Code Node** → **Response**

```javascript
// Code Node
const projectPath = '/Users/daletaylor/Library/CloudStorage/OneDrive-Personal/All Coding Work/multi-agent-research-pipeline';
const query = $input.first().json.body.query;

const { execSync } = require('child_process');

const result = execSync(`cd ${projectPath} && python3 -c "
from n8n_integration import sync_intelligent_search
import json
result = sync_intelligent_search('${query}', 5)
print(json.dumps(result))
"`, { encoding: 'utf8' });

return [{ json: JSON.parse(result) }];
```

### **Example 2: Slack Research Bot**

1. **Slack Trigger** → **Code Node** → **Slack Message**

```javascript
// Extract query from Slack message
const slackMessage = $input.first().json.text;
const query = slackMessage.replace('!research ', '');

// Run search
const projectPath = '/Users/daletaylor/Library/CloudStorage/OneDrive-Personal/All Coding Work/multi-agent-research-pipeline';
const { execSync } = require('child_process');

const result = execSync(`cd ${projectPath} && python3 -c "
from n8n_integration import sync_intelligent_search
import json
result = sync_intelligent_search('${query}', 3)
print(json.dumps(result))
"`, { encoding: 'utf8' });

const searchData = JSON.parse(result);

// Format for Slack
let slackResponse = `🔍 *Research Results for: ${query}*\n\n`;

if (searchData.ai_summary) {
  slackResponse += `📝 *Summary:* ${searchData.ai_summary}\n\n`;
}

slackResponse += `📚 *Results:*\n`;
searchData.results.forEach((r, i) => {
  slackResponse += `${i+1}. <${r.url}|${r.title}>\n`;
});

return [{ json: { text: slackResponse } }];
```

### **Example 3: Automated Research Reports**

1. **Schedule Trigger** → **Code Node** → **Email/Notion**

```javascript
// Daily research on trending topics
const topics = ['AI trends', 'Python updates', 'web development'];
const projectPath = '/Users/daletaylor/Library/CloudStorage/OneDrive-Personal/All Coding Work/multi-agent-research-pipeline';

const results = [];

for (const topic of topics) {
  const { execSync } = require('child_process');
  
  const result = execSync(`cd ${projectPath} && python3 -c "
from n8n_integration import sync_intelligent_search
import json
result = sync_intelligent_search('${topic} latest news', 3)
print(json.dumps(result))
  "`, { encoding: 'utf8' });
  
  results.push(JSON.parse(result));
}

return [{ json: { daily_research: results } }];
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **"Module not found" errors:**
   - Ensure the project path is correct
   - Check that `sys.path.insert()` is used
   - Verify Python dependencies are installed

2. **API key errors:**
   - Check `.env` file exists and has correct keys
   - Ensure `load_dotenv()` is called
   - Verify API keys are valid

3. **Timeout errors:**
   - Increase search timeout in settings
   - Check network connectivity
   - Try with fewer results

### **Debug Mode**

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🎯 **Production Deployment**

### **For Self-Hosted N8N on Railway:**

1. **Add to your Railway project:**
   - Copy the research pipeline to your Railway environment
   - Install dependencies via `requirements.txt`
   - Set environment variables in Railway dashboard

2. **Use in N8N workflows:**
   - Reference the correct path in your Railway container
   - Ensure Python is available in the container

3. **Alternative: API Service:**
   - Deploy FastAPI server separately
   - Use HTTP Request nodes to call the API
   - More scalable for multiple workflows

## 📈 **Performance Tips**

1. **Cache Results:** Store search results in N8N memory/database
2. **Batch Requests:** Combine multiple searches when possible
3. **Rate Limiting:** Respect API rate limits (Tavily: 1000/month, Serp: 100/month)
4. **Error Handling:** Always include try/catch blocks
5. **Monitoring:** Log search metrics and failures

## 🔄 **Next Steps**

1. **Import the workflow template**
2. **Update paths and API keys**
3. **Test with simple queries**
4. **Build custom workflows for your use cases**
5. **Scale with FastAPI server if needed**

---

**🎉 You now have a production-ready research pipeline integrated with N8N!**

The system provides AI-optimized search results with intelligent fallback, perfect for automating research workflows in your N8N instance.