"""
Tests for Tavily search functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from tools.tavily_search import TavilySearchTool, search_tavily
from agents.models import TavilySearchResult, SearchResults, TavilyAPIError


class TestTavilySearchTool:
    """Test suite for TavilySearchTool."""
    
    @pytest.fixture
    def tavily_tool(self):
        """Create TavilySearchTool instance for testing."""
        return TavilySearchTool("test_api_key", timeout=30)
    
    @pytest.fixture
    def mock_response_data(self):
        """Mock Tavily API response data."""
        return {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "content": "This is test content 1",
                    "score": 0.95,
                    "published_date": "2024-01-01",
                    "raw_content": "Raw content 1"
                },
                {
                    "title": "Test Result 2", 
                    "url": "https://example.com/2",
                    "content": "This is test content 2",
                    "score": 0.87,
                    "published_date": None,
                    "raw_content": "Raw content 2"
                }
            ],
            "answer": "This is an AI-generated summary of the search results."
        }
    
    @pytest.mark.asyncio
    async def test_successful_search(self, tavily_tool, mock_response_data):
        """Test successful Tavily search."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # Perform search
            results = await tavily_tool.search("test query", max_results=5)
            
            # Assertions
            assert isinstance(results, SearchResults)
            assert results.query == "test query"
            assert len(results.results) == 2
            assert results.total_results == 2
            assert results.ai_summary == "This is an AI-generated summary of the search results."
            
            # Check first result
            first_result = results.results[0]
            assert isinstance(first_result, TavilySearchResult)
            assert first_result.title == "Test Result 1"
            assert first_result.url == "https://example.com/1"
            assert first_result.content == "This is test content 1"
            assert first_result.score == 0.95
            assert first_result.published_date == "2024-01-01"
    
    @pytest.mark.asyncio
    async def test_api_error_response(self, tavily_tool):
        """Test handling of API error response."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock error response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "Invalid API key"}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # Should raise TavilyAPIError
            with pytest.raises(TavilyAPIError) as exc_info:
                await tavily_tool.search("test query")
            
            assert "401" in str(exc_info.value)
            assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, tavily_tool):
        """Test handling of timeout error."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock timeout
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            
            # Should raise TavilyAPIError
            with pytest.raises(TavilyAPIError) as exc_info:
                await tavily_tool.search("test query")
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_request_error(self, tavily_tool):
        """Test handling of request error."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock request error
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            
            # Should raise TavilyAPIError
            with pytest.raises(TavilyAPIError) as exc_info:
                await tavily_tool.search("test query")
            
            assert "request failed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_empty_results(self, tavily_tool):
        """Test handling of empty search results."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock empty response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": [], "answer": None}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # Perform search
            results = await tavily_tool.search("no results query")
            
            # Assertions
            assert isinstance(results, SearchResults)
            assert len(results.results) == 0
            assert results.total_results == 0
            assert results.ai_summary is None
    
    @pytest.mark.asyncio
    async def test_search_parameters(self, tavily_tool, mock_response_data):
        """Test that search parameters are correctly passed to API."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Perform search with specific parameters
            await tavily_tool.search(
                "test query",
                max_results=15,
                search_depth="basic",
                include_answer=False,
                include_domains=["example.com"],
                exclude_domains=["spam.com"]
            )
            
            # Check that correct parameters were sent
            call_args = mock_post.call_args
            json_payload = call_args[1]['json']
            
            assert json_payload['query'] == "test query"
            assert json_payload['max_results'] == 15
            assert json_payload['search_depth'] == "basic"
            assert json_payload['include_answer'] is False
            assert json_payload['include_domains'] == ["example.com"]
            assert json_payload['exclude_domains'] == ["spam.com"]


class TestTavilySearchFunction:
    """Test the simplified search_tavily function."""
    
    @pytest.mark.asyncio
    async def test_search_tavily_function(self, mock_response_data):
        """Test the search_tavily convenience function."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # Use convenience function
            results = await search_tavily("test query", "test_api_key", max_results=5)
            
            # Should return list of TavilySearchResult
            assert isinstance(results, list)
            assert len(results) == 2
            assert all(isinstance(r, TavilySearchResult) for r in results)
    
    @pytest.mark.asyncio
    async def test_search_tavily_with_kwargs(self, mock_response_data):
        """Test search_tavily with keyword arguments."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Use convenience function with kwargs
            await search_tavily(
                "test query", 
                "test_api_key", 
                max_results=10,
                search_depth="advanced",
                include_answer=True
            )
            
            # Verify parameters were passed correctly
            call_args = mock_post.call_args
            json_payload = call_args[1]['json']
            
            assert json_payload['search_depth'] == "advanced"
            assert json_payload['include_answer'] is True


@pytest.mark.integration
class TestTavilyIntegration:
    """Integration tests for Tavily (requires real API key)."""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--integration"),
        reason="Need --integration option to run"
    )
    @pytest.mark.asyncio
    async def test_real_tavily_search(self):
        """Test with real Tavily API (skipped by default)."""
        import os
        
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            pytest.skip("TAVILY_API_KEY not found in environment")
        
        tool = TavilySearchTool(api_key)
        results = await tool.search("artificial intelligence", max_results=3)
        
        assert isinstance(results, SearchResults)
        assert len(results.results) > 0
        assert all(isinstance(r, TavilySearchResult) for r in results.results)
        assert results.search_time > 0


def pytest_addoption(parser):
    """Add command line option for integration tests."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests"
    )