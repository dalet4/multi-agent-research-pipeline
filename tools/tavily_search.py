"""
Tavily Search API integration for AI-optimized search results.
"""

import asyncio
import logging
import time
from typing import List, Optional

import httpx
from agents.models import (
    TavilySearchResult, 
    SearchResults, 
    ResearchQuery,
    TavilyAPIError,
    SearchProvider
)

logger = logging.getLogger(__name__)


class TavilySearchTool:
    """Tavily Search API client optimized for AI agents."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize Tavily search tool.
        
        Args:
            api_key: Tavily API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.tavily.com"
        
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> SearchResults:
        """
        Perform AI-optimized search using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (1-50)
            search_depth: Search depth ("basic" or "advanced")
            include_answer: Include AI-generated answer
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            
        Returns:
            SearchResults object with Tavily results
            
        Raises:
            TavilyAPIError: If API request fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Tavily search: '{query}' (max_results={max_results})")
            
            # Prepare request payload
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": True,  # Get raw content for better processing
                "max_results": min(max_results, 50),  # Tavily max is 50
                "include_domains": include_domains or [],
                "exclude_domains": exclude_domains or []
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload,
                    timeout=self.timeout,
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                
                # Handle API errors
                if response.status_code != 200:
                    error_msg = f"Tavily API returned {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f": {error_data['error']}"
                    except Exception:
                        error_msg += f": {response.text[:200]}"
                    
                    logger.error(error_msg)
                    raise TavilyAPIError(error_msg, response.status_code)
                
                # Parse response
                data = response.json()
                
                # Convert to our data models
                results = []
                for result in data.get("results", []):
                    tavily_result = TavilySearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        content=result.get("content", ""),
                        score=result.get("score", 0.0),
                        published_date=result.get("published_date"),
                        raw_content=result.get("raw_content"),
                        provider=SearchProvider.TAVILY
                    )
                    results.append(tavily_result)
                
                execution_time = time.time() - start_time
                
                search_results = SearchResults(
                    query=query,
                    results=results,
                    total_results=len(results),
                    search_time=execution_time,
                    providers_used=[SearchProvider.TAVILY],
                    ai_summary=data.get("answer") if include_answer else None
                )
                
                logger.info(f"Tavily search completed: {len(results)} results in {execution_time:.2f}s")
                return search_results
                
        except httpx.TimeoutException:
            error_msg = f"Tavily search timeout after {self.timeout}s"
            logger.error(error_msg)
            raise TavilyAPIError(error_msg)
            
        except httpx.RequestError as e:
            error_msg = f"Tavily request failed: {str(e)}"
            logger.error(error_msg)
            raise TavilyAPIError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected Tavily search error: {str(e)}"
            logger.error(error_msg)
            raise TavilyAPIError(error_msg)


async def search_tavily(
    query: str, 
    api_key: str, 
    max_results: int = 10,
    **kwargs
) -> List[TavilySearchResult]:
    """
    Simplified function for Tavily search.
    
    Args:
        query: Search query
        api_key: Tavily API key
        max_results: Maximum results to return
        **kwargs: Additional search parameters
        
    Returns:
        List of TavilySearchResult objects
        
    Raises:
        TavilyAPIError: If search fails
    """
    tool = TavilySearchTool(api_key)
    search_results = await tool.search(query, max_results, **kwargs)
    return search_results.results


# Example usage and testing
async def main():
    """Example usage of Tavily search."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("TAVILY_API_KEY not found in environment")
        return
    
    tool = TavilySearchTool(api_key)
    
    try:
        results = await tool.search(
            "latest AI safety research 2024",
            max_results=5,
            search_depth="advanced",
            include_answer=True
        )
        
        print(f"\nSearch Results for: '{results.query}'")
        print(f"Total: {results.total_results} results in {results.search_time:.2f}s")
        
        if results.ai_summary:
            print(f"\nAI Summary:\n{results.ai_summary}")
        
        print("\nResults:")
        for i, result in enumerate(results.results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Score: {result.score:.2f}")
            print(f"   Content: {result.content[:200]}...")
            print()
            
    except TavilyAPIError as e:
        print(f"Tavily search error: {e}")


if __name__ == "__main__":
    asyncio.run(main())