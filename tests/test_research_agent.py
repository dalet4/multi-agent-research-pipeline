"""
Tests for the Research Agent functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from agents.research_agent import run_research_agent, ResearchAgentDeps, intelligent_search
from agents.models import SearchResults, TavilySearchResult, SerpSearchResult, SearchProvider, AgentResponse
from config.settings import Settings


class TestResearchAgent:
    """Test suite for Research Agent."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.search_strategy = "intelligent"
        settings.search_timeout = 30
        settings.llm_provider = "gemini"
        settings.gemini_api_key = "test_gemini_key"
        settings.tavily_api_key = "test_tavily_key"
        settings.serp_api_key = "test_serp_key"
        return settings
    
    @pytest.fixture
    def mock_tavily_results(self):
        """Create mock Tavily search results."""
        results = [
            TavilySearchResult(
                title="AI Safety Research 2024",
                url="https://example.com/ai-safety-2024",
                content="Comprehensive overview of AI safety developments in 2024...",
                score=0.95,
                published_date="2024-01-15",
                provider=SearchProvider.TAVILY
            ),
            TavilySearchResult(
                title="Constitutional AI Methods",
                url="https://example.com/constitutional-ai",
                content="New approaches to constitutional AI and alignment...",
                score=0.88,
                published_date="2024-02-01",
                provider=SearchProvider.TAVILY
            )
        ]
        
        return SearchResults(
            query="AI safety research 2024",
            results=results,
            total_results=2,
            search_time=1.5,
            providers_used=[SearchProvider.TAVILY],
            ai_summary="Recent AI safety research shows significant progress in alignment and constitutional AI methods."
        )
    
    @pytest.fixture
    def mock_serp_results(self):
        """Create mock SerpAPI search results."""
        results = [
            SerpSearchResult(
                title="Google AI Safety Research",
                url="https://ai.google/safety",
                snippet="Google's approach to AI safety and responsible development...",
                position=1,
                provider=SearchProvider.SERP
            ),
            SerpSearchResult(
                title="OpenAI Safety Research",
                url="https://openai.com/safety",
                snippet="OpenAI's research into AI alignment and safety measures...",
                position=2,
                provider=SearchProvider.SERP
            )
        ]
        
        return SearchResults(
            query="AI safety research 2024",
            results=results,
            total_results=2,
            search_time=2.1,
            providers_used=[SearchProvider.SERP],
            ai_summary="Found 2 search results from Google search."
        )
    
    @pytest.mark.asyncio
    async def test_successful_research_with_tavily(self, mock_settings, mock_tavily_results):
        """Test successful research using Tavily search."""
        with patch('agents.research_agent.intelligent_search') as mock_search, \
             patch('agents.research_agent.research_agent.run') as mock_agent_run:
            
            # Mock search results
            mock_search.return_value = mock_tavily_results
            
            # Mock agent response
            mock_agent_response = MagicMock()
            mock_agent_response.data = "Comprehensive analysis of AI safety research showing significant progress..."
            mock_agent_response.usage.total_tokens = 1500
            mock_agent_run.return_value = mock_agent_response
            
            # Run research
            response = await run_research_agent(
                query="AI safety research 2024",
                max_results=5,
                create_summary=True
            )
            
            # Assertions
            assert response.success is True
            assert isinstance(response.data, dict)
            assert "summary" in response.data
            assert "search_results" in response.data
            assert "sources" in response.data
            assert "query" in response.data
            
            assert response.data["query"] == "AI safety research 2024"
            assert len(response.data["sources"]) == 2
            assert response.tokens_used == 1500
            assert response.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_research_with_search_fallback(self, mock_settings, mock_serp_results):
        """Test research with fallback to SerpAPI when Tavily fails."""
        with patch('agents.research_agent.intelligent_search') as mock_search, \
             patch('agents.research_agent.research_agent.run') as mock_agent_run:
            
            # Mock search results (SerpAPI fallback)
            mock_search.return_value = mock_serp_results
            
            # Mock agent response
            mock_agent_response = MagicMock()
            mock_agent_response.data = "Analysis based on Google search results..."
            mock_agent_response.usage.total_tokens = 1200
            mock_agent_run.return_value = mock_agent_response
            
            # Run research
            response = await run_research_agent(
                query="AI safety research 2024",
                max_results=5,
                create_summary=True
            )
            
            # Assertions
            assert response.success is True
            assert response.data["sources"][0] == "https://ai.google/safety"
            assert SearchProvider.SERP in response.data["search_results"].providers_used
    
    @pytest.mark.asyncio
    async def test_research_without_summary(self, mock_settings, mock_tavily_results):
        """Test research without AI summary generation."""
        with patch('agents.research_agent.intelligent_search') as mock_search:
            
            # Mock search results
            mock_search.return_value = mock_tavily_results
            
            # Run research without summary
            response = await run_research_agent(
                query="AI safety research 2024",
                max_results=5,
                create_summary=False
            )
            
            # Assertions
            assert response.success is True
            assert response.tokens_used is None  # No LLM usage
            assert "summary" in response.data
            # Summary should be raw results text, not AI-generated
            assert "AI Safety Research 2024" in response.data["summary"]
    
    @pytest.mark.asyncio
    async def test_research_no_results(self, mock_settings):
        """Test research when no search results are found."""
        with patch('agents.research_agent.intelligent_search') as mock_search:
            
            # Mock empty search results
            empty_results = SearchResults(
                query="nonexistent query",
                results=[],
                total_results=0,
                search_time=1.0,
                providers_used=[SearchProvider.TAVILY]
            )
            mock_search.return_value = empty_results
            
            # Run research
            response = await run_research_agent(
                query="nonexistent query",
                max_results=5
            )
            
            # Assertions
            assert response.success is False
            assert "No search results found" in response.message
            assert response.data is None
    
    @pytest.mark.asyncio
    async def test_research_search_error(self, mock_settings):
        """Test research when search fails completely."""
        with patch('agents.research_agent.intelligent_search') as mock_search:
            
            # Mock search error
            from agents.models import SearchError
            mock_search.side_effect = SearchError("All search providers failed")
            
            # Run research
            response = await run_research_agent(
                query="test query",
                max_results=5
            )
            
            # Assertions
            assert response.success is False
            assert "search error" in response.message.lower()
            assert "All search providers failed" in response.error


class TestIntelligentSearch:
    """Test suite for intelligent search functionality."""
    
    @pytest.fixture
    def mock_deps(self, mock_settings):
        """Create mock ResearchAgentDeps."""
        deps = MagicMock(spec=ResearchAgentDeps)
        deps.settings = mock_settings
        deps.tavily_tool = MagicMock()
        deps.serp_tool = MagicMock()
        return deps
    
    @pytest.fixture
    def mock_context(self, mock_deps):
        """Create mock RunContext."""
        context = MagicMock()
        context.deps = mock_deps
        return context
    
    @pytest.mark.asyncio
    async def test_intelligent_search_tavily_success(self, mock_context, mock_tavily_results):
        """Test intelligent search with successful Tavily search."""
        # Mock successful Tavily search
        mock_context.deps.tavily_tool.search = AsyncMock(return_value=mock_tavily_results)
        
        # Run intelligent search
        results = await intelligent_search(mock_context, "test query", max_results=5)
        
        # Assertions
        assert isinstance(results, SearchResults)
        assert len(results.results) == 2
        assert results.providers_used == [SearchProvider.TAVILY]
        
        # Verify Tavily was called
        mock_context.deps.tavily_tool.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_intelligent_search_fallback_to_serp(self, mock_context, mock_serp_results):
        """Test intelligent search with fallback to SerpAPI."""
        # Mock Tavily failure and SerpAPI success
        mock_context.deps.tavily_tool.search = AsyncMock(side_effect=Exception("Tavily failed"))
        mock_context.deps.serp_tool.search = AsyncMock(return_value=mock_serp_results)
        
        # Run intelligent search
        results = await intelligent_search(mock_context, "test query", max_results=5)
        
        # Assertions
        assert isinstance(results, SearchResults)
        assert len(results.results) == 2
        assert results.providers_used == [SearchProvider.SERP]
        
        # Verify both tools were called
        mock_context.deps.tavily_tool.search.assert_called_once()
        mock_context.deps.serp_tool.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_intelligent_search_all_providers_fail(self, mock_context):
        """Test intelligent search when all providers fail."""
        # Mock both providers failing
        mock_context.deps.tavily_tool.search = AsyncMock(side_effect=Exception("Tavily failed"))
        mock_context.deps.serp_tool.search = AsyncMock(side_effect=Exception("SerpAPI failed"))
        
        # Should raise SearchError
        from agents.models import SearchError
        with pytest.raises(SearchError) as exc_info:
            await intelligent_search(mock_context, "test query", max_results=5)
        
        assert "All configured providers failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_intelligent_search_tavily_only_strategy(self, mock_context, mock_tavily_results):
        """Test intelligent search with tavily_only strategy."""
        # Set strategy to tavily_only
        mock_context.deps.settings.search_strategy = "tavily_only"
        mock_context.deps.tavily_tool.search = AsyncMock(return_value=mock_tavily_results)
        
        # Run intelligent search
        results = await intelligent_search(mock_context, "test query", max_results=5)
        
        # Assertions
        assert isinstance(results, SearchResults)
        assert results.providers_used == [SearchProvider.TAVILY]
        
        # Verify only Tavily was called
        mock_context.deps.tavily_tool.search.assert_called_once()
        mock_context.deps.serp_tool.search.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_intelligent_search_serp_only_strategy(self, mock_context, mock_serp_results):
        """Test intelligent search with serp_only strategy."""
        # Set strategy to serp_only
        mock_context.deps.settings.search_strategy = "serp_only"
        mock_context.deps.serp_tool.search = AsyncMock(return_value=mock_serp_results)
        
        # Run intelligent search
        results = await intelligent_search(mock_context, "test query", max_results=5)
        
        # Assertions
        assert isinstance(results, SearchResults)
        assert results.providers_used == [SearchProvider.SERP]
        
        # Verify only SerpAPI was called
        mock_context.deps.serp_tool.search.assert_called_once()
        mock_context.deps.tavily_tool.search.assert_not_called()


@pytest.mark.integration
class TestResearchAgentIntegration:
    """Integration tests for Research Agent (requires real API keys)."""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--integration"),
        reason="Need --integration option to run"
    )
    @pytest.mark.asyncio
    async def test_real_research_workflow(self):
        """Test complete research workflow with real APIs."""
        import os
        
        # Check for required API keys
        required_keys = ["TAVILY_API_KEY", "GEMINI_API_KEY"]
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            pytest.skip(f"Missing required API keys: {', '.join(missing_keys)}")
        
        # Run real research
        response = await run_research_agent(
            query="latest artificial intelligence developments",
            max_results=3,
            create_summary=True
        )
        
        # Assertions
        assert response.success is True
        assert isinstance(response.data, dict)
        assert len(response.data["sources"]) > 0
        assert len(response.data["summary"]) > 100  # Should be substantial
        assert response.execution_time > 0