"""
N8N Integration Module for Multi-Agent Research Pipeline
Simplified functions for easy N8N node integration
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

async def n8n_intelligent_search(
    query: str, 
    max_results: int = 5,
    search_strategy: str = "intelligent"
) -> Dict[str, Any]:
    """
    N8N-ready intelligent search function.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (1-20)
        search_strategy: "intelligent", "tavily_only", or "serp_only"
    
    Returns:
        Dictionary with search results ready for N8N
    """
    try:
        from agents.research_agent import ResearchAgentDeps, intelligent_search
        
        # Create dependencies
        deps = ResearchAgentDeps()
        deps.settings.search_strategy = search_strategy
        
        # Mock context for the search
        class MockContext:
            def __init__(self, deps):
                self.deps = deps
        
        # Perform search
        results = await intelligent_search(MockContext(deps), query, max_results)
        
        # Convert to N8N-friendly format
        search_results = []
        for result in results.results:
            search_result = {
                "title": result.title,
                "url": result.url,
                "provider": result.provider.value,
                "content": getattr(result, 'content', '') or getattr(result, 'snippet', ''),
                "score": getattr(result, 'score', 0.0),
                "position": getattr(result, 'position', 0),
                "published_date": getattr(result, 'published_date', None)
            }
            search_results.append(search_result)
        
        return {
            "success": True,
            "query": query,
            "total_results": len(search_results),
            "search_time": results.search_time,
            "providers_used": [p.value for p in results.providers_used],
            "ai_summary": results.ai_summary,
            "results": search_results,
            "timestamp": results.timestamp.isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }


async def n8n_tavily_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    N8N-ready Tavily-only search function.
    
    Args:
        query: Search query
        max_results: Maximum results
    
    Returns:
        N8N-friendly search results
    """
    try:
        from tools.tavily_search import TavilySearchTool
        
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment")
        
        tool = TavilySearchTool(api_key)
        results = await tool.search(query, max_results, include_answer=True)
        
        search_results = []
        for result in results.results:
            search_results.append({
                "title": result.title,
                "url": result.url,
                "content": result.content,
                "score": result.score,
                "published_date": result.published_date,
                "provider": "tavily"
            })
        
        return {
            "success": True,
            "query": query,
            "total_results": len(search_results),
            "search_time": results.search_time,
            "ai_summary": results.ai_summary,
            "results": search_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }


async def n8n_serp_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    N8N-ready SerpAPI search function.
    
    Args:
        query: Search query
        max_results: Maximum results
    
    Returns:
        N8N-friendly search results
    """
    try:
        from tools.serp_search import SerpSearchTool
        
        api_key = os.getenv('SERP_API_KEY')
        if not api_key:
            raise ValueError("SERP_API_KEY not found in environment")
        
        tool = SerpSearchTool(api_key)
        results = await tool.search(query, max_results)
        
        search_results = []
        for result in results.results:
            search_results.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "position": result.position,
                "provider": "serp"
            })
        
        return {
            "success": True,
            "query": query,
            "total_results": len(search_results),
            "search_time": results.search_time,
            "results": search_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }


def sync_intelligent_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Synchronous wrapper for N8N nodes that don't support async.
    
    Args:
        query: Search query
        max_results: Maximum results
    
    Returns:
        Search results dictionary
    """
    return asyncio.run(n8n_intelligent_search(query, max_results))


def sync_tavily_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Synchronous Tavily search for N8N."""
    return asyncio.run(n8n_tavily_search(query, max_results))


def sync_serp_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Synchronous SerpAPI search for N8N."""
    return asyncio.run(n8n_serp_search(query, max_results))


# N8N Node Example Usage
if __name__ == "__main__":
    # Example of how to use in N8N Code Node
    
    # Get input from N8N
    query = "Python web frameworks 2024"  # This would come from N8N input
    max_results = 3
    
    # Perform search
    result = sync_intelligent_search(query, max_results)
    
    # Output for N8N
    print(json.dumps(result, indent=2))
    
    # In N8N, you would return:
    # return [result]