"""
SerpAPI Search integration for Google search results.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any

import httpx
from agents.models import (
    SerpSearchResult, 
    SearchResults, 
    ResearchQuery,
    SerpAPIError,
    SearchProvider
)

logger = logging.getLogger(__name__)


class SerpSearchTool:
    """SerpAPI client for Google search results."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize SerpAPI search tool.
        
        Args:
            api_key: SerpAPI key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://serpapi.com/search"
        
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        country: str = "us",
        language: str = "en",
        safe_search: str = "off",
        time_period: Optional[str] = None
    ) -> SearchResults:
        """
        Perform Google search using SerpAPI.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (1-100)
            country: Country code for search (us, uk, etc.)
            language: Language code (en, es, etc.)
            safe_search: Safe search setting (off, moderate, strict)
            time_period: Time period filter (past hour, day, week, month, year)
            
        Returns:
            SearchResults object with SerpAPI results
            
        Raises:
            SerpAPIError: If API request fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"SerpAPI search: '{query}' (max_results={max_results})")
            
            # Prepare request parameters
            params = {
                "api_key": self.api_key,
                "engine": "google",
                "q": query,
                "num": min(max_results, 100),  # Google max is 100
                "google_domain": "google.com",
                "gl": country,
                "hl": language,
                "safe": safe_search
            }
            
            # Add time period filter if specified
            time_filters = {
                "hour": "qdr:h",
                "day": "qdr:d", 
                "week": "qdr:w",
                "month": "qdr:m",
                "year": "qdr:y"
            }
            if time_period and time_period in time_filters:
                params["tbs"] = time_filters[time_period]
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                
                # Handle API errors
                if response.status_code != 200:
                    error_msg = f"SerpAPI returned {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f": {error_data['error']}"
                    except Exception:
                        error_msg += f": {response.text[:200]}"
                    
                    logger.error(error_msg)
                    raise SerpAPIError(error_msg, response.status_code)
                
                # Parse response
                data = response.json()
                
                # Check for API errors in response
                if "error" in data:
                    error_msg = f"SerpAPI error: {data['error']}"
                    logger.error(error_msg)
                    raise SerpAPIError(error_msg)
                
                # Convert to our data models
                results = []
                organic_results = data.get("organic_results", [])
                
                for i, result in enumerate(organic_results):
                    serp_result = SerpSearchResult(
                        title=result.get("title", ""),
                        url=result.get("link", ""),
                        snippet=result.get("snippet", ""),
                        position=result.get("position", i + 1),
                        displayed_link=result.get("displayed_link"),
                        cached_page_link=result.get("cached_page_link"),
                        provider=SearchProvider.SERP
                    )
                    results.append(serp_result)
                
                execution_time = time.time() - start_time
                
                # Create search results
                search_results = SearchResults(
                    query=query,
                    results=results,
                    total_results=len(results),
                    search_time=execution_time,
                    providers_used=[SearchProvider.SERP],
                    ai_summary=self._generate_summary(results) if results else None
                )
                
                logger.info(f"SerpAPI search completed: {len(results)} results in {execution_time:.2f}s")
                return search_results
                
        except httpx.TimeoutException:
            error_msg = f"SerpAPI search timeout after {self.timeout}s"
            logger.error(error_msg)
            raise SerpAPIError(error_msg)
            
        except httpx.RequestError as e:
            error_msg = f"SerpAPI request failed: {str(e)}"
            logger.error(error_msg)
            raise SerpAPIError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected SerpAPI search error: {str(e)}"
            logger.error(error_msg)
            raise SerpAPIError(error_msg)
    
    def _generate_summary(self, results: List[SerpSearchResult]) -> str:
        """
        Generate a basic summary from search results.
        
        Args:
            results: List of search results
            
        Returns:
            Summary string
        """
        if not results:
            return "No search results found."
        
        # Extract key information from top results
        top_results = results[:3]
        sources = [result.url for result in top_results]
        
        summary_parts = [
            f"Found {len(results)} search results.",
            "Top sources: " + ", ".join(sources[:3])
        ]
        
        return " ".join(summary_parts)


async def search_serp(
    query: str, 
    api_key: str, 
    max_results: int = 10,
    **kwargs
) -> List[SerpSearchResult]:
    """
    Simplified function for SerpAPI search.
    
    Args:
        query: Search query
        api_key: SerpAPI key
        max_results: Maximum results to return
        **kwargs: Additional search parameters
        
    Returns:
        List of SerpSearchResult objects
        
    Raises:
        SerpAPIError: If search fails
    """
    tool = SerpSearchTool(api_key)
    search_results = await tool.search(query, max_results, **kwargs)
    return search_results.results


# Example usage and testing
async def main():
    """Example usage of SerpAPI search."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        print("SERP_API_KEY not found in environment")
        return
    
    tool = SerpSearchTool(api_key)
    
    try:
        results = await tool.search(
            "latest AI safety research 2024",
            max_results=5,
            country="us",
            language="en"
        )
        
        print(f"\nSearch Results for: '{results.query}'")
        print(f"Total: {results.total_results} results in {results.search_time:.2f}s")
        
        if results.ai_summary:
            print(f"\nSummary:\n{results.ai_summary}")
        
        print("\nResults:")
        for i, result in enumerate(results.results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Position: {result.position}")
            print(f"   Snippet: {result.snippet[:200]}...")
            print()
            
    except SerpAPIError as e:
        print(f"SerpAPI search error: {e}")


if __name__ == "__main__":
    asyncio.run(main())