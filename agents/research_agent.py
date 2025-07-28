"""
Research Agent with intelligent multi-search capabilities and email integration.
"""

import asyncio
import logging
import time
from typing import List, Optional, Union

from pydantic_ai import Agent, RunContext
from pydantic import Field

from config.settings import AgentDependencies
from agents.models import (
    SearchResults, 
    ResearchQuery, 
    ResearchEmailRequest,
    AgentResponse,
    SearchError,
    SearchProvider,
    TavilySearchResult,
    SerpSearchResult
)
from agents.providers import get_research_optimized_model, RESEARCH_AGENT_PROMPT
from agents.email_agent import run_email_agent, EmailAgentDeps
from tools.tavily_search import TavilySearchTool
from tools.serp_search import SerpSearchTool

logger = logging.getLogger(__name__)


class ResearchAgentDeps(AgentDependencies):
    """Dependencies for the Research Agent."""
    
    tavily_tool: Optional[TavilySearchTool] = Field(default=None)
    serp_tool: Optional[SerpSearchTool] = Field(default=None)
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Initialize search tools based on available API keys
        if self.tavily_api_key:
            self.tavily_tool = TavilySearchTool(
                self.tavily_api_key, 
                timeout=self.settings.search_timeout
            )
        
        if self.serp_api_key:
            self.serp_tool = SerpSearchTool(
                self.serp_api_key,
                timeout=self.settings.search_timeout
            )


# Create the research agent
research_agent = Agent(
    get_research_optimized_model(),
    system_prompt=RESEARCH_AGENT_PROMPT,
    deps_type=ResearchAgentDeps,
    result_type=str  # Research summary as string
)


@research_agent.tool
async def intelligent_search(
    ctx: RunContext[ResearchAgentDeps],
    query: str,
    max_results: int = 10
) -> SearchResults:
    """
    Perform intelligent search with automatic provider selection and fallback.
    
    Args:
        ctx: Agent run context
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        SearchResults with combined results from available providers
        
    Raises:
        SearchError: If all search providers fail
    """
    strategy = ctx.deps.settings.search_strategy
    logger.info(f"Intelligent search: '{query}' (strategy={strategy}, max_results={max_results})")
    
    search_results = SearchResults(
        query=query,
        results=[],
        total_results=0,
        search_time=0.0,
        providers_used=[]
    )
    
    start_time = time.time()
    
    try:
        # Strategy: tavily_only
        if strategy == "tavily_only":
            if not ctx.deps.tavily_tool:
                raise SearchError("Tavily API key not configured")
            
            tavily_results = await ctx.deps.tavily_tool.search(
                query, max_results, search_depth="advanced", include_answer=True
            )
            search_results = tavily_results
        
        # Strategy: serp_only
        elif strategy == "serp_only":
            if not ctx.deps.serp_tool:
                raise SearchError("SerpAPI key not configured")
            
            serp_results = await ctx.deps.serp_tool.search(query, max_results)
            search_results = serp_results
        
        # Strategy: intelligent (default)
        else:
            # Try Tavily first (AI-optimized)
            if ctx.deps.tavily_tool:
                try:
                    logger.info("Attempting Tavily search...")
                    tavily_results = await ctx.deps.tavily_tool.search(
                        query, max_results, search_depth="advanced", include_answer=True
                    )
                    search_results = tavily_results
                    logger.info(f"Tavily search successful: {len(tavily_results.results)} results")
                    
                except Exception as e:
                    logger.warning(f"Tavily search failed: {e}, trying SerpAPI fallback")
            
            # Fallback to SerpAPI if Tavily failed or unavailable
            if not search_results.results and ctx.deps.serp_tool:
                try:
                    logger.info("Attempting SerpAPI search...")
                    serp_results = await ctx.deps.serp_tool.search(query, max_results)
                    search_results = serp_results
                    logger.info(f"SerpAPI search successful: {len(serp_results.results)} results")
                    
                except Exception as e:
                    logger.error(f"SerpAPI search also failed: {e}")
                    raise SearchError(f"All search providers failed: Tavily and SerpAPI errors")
            
            # If still no results, raise error
            if not search_results.results:
                available_providers = []
                if ctx.deps.tavily_tool:
                    available_providers.append("Tavily")
                if ctx.deps.serp_tool:
                    available_providers.append("SerpAPI")
                
                if not available_providers:
                    raise SearchError("No search providers configured")
                else:
                    raise SearchError(f"All configured providers failed: {', '.join(available_providers)}")
        
        # Update timing
        search_results.search_time = time.time() - start_time
        
        logger.info(f"Search completed: {search_results.total_results} results in {search_results.search_time:.2f}s")
        return search_results
        
    except SearchError:
        raise
    except Exception as e:
        error_msg = f"Unexpected search error: {str(e)}"
        logger.error(error_msg)
        raise SearchError(error_msg)


@research_agent.tool
async def create_email_draft(
    ctx: RunContext[ResearchAgentDeps],
    research_summary: str,
    sources: List[str],
    recipient_email: str,
    email_context: str,
    subject_hint: Optional[str] = None,
    tone: str = "professional"
) -> str:
    """
    Create an email draft based on research findings.
    
    Args:
        ctx: Agent run context
        research_summary: Summary of research findings
        sources: List of source URLs
        recipient_email: Email recipient
        email_context: Context for the email
        subject_hint: Suggested email subject
        tone: Email tone
        
    Returns:
        Status message about email creation
        
    Raises:
        Exception: If email creation fails
    """
    try:
        logger.info(f"Creating email draft for {recipient_email}")
        
        # Create email request
        email_request = ResearchEmailRequest(
            research_query="Research query from agent",
            email_context=email_context,
            recipient_email=recipient_email,
            subject_hint=subject_hint,
            tone=tone,
            include_sources=True
        )
        
        # Create email agent dependencies
        email_deps = EmailAgentDeps(
            settings=ctx.deps.settings,
            gmail_credentials_path=ctx.deps.gmail_credentials_path
        )
        
        # Run email agent
        email_response = await run_email_agent(
            email_request,
            research_summary,
            sources,
            email_deps
        )
        
        if email_response.success:
            draft_info = email_response.data
            return f"Email draft created successfully! Subject: '{draft_info.subject}' | Draft ID: {draft_info.draft_id}"
        else:
            return f"Failed to create email draft: {email_response.error}"
            
    except Exception as e:
        error_msg = f"Email creation failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


async def run_research_agent(
    query: str,
    max_results: int = 10,
    create_summary: bool = True,
    deps: Optional[ResearchAgentDeps] = None
) -> AgentResponse:
    """
    Run the research agent to perform comprehensive research.
    
    Args:
        query: Research query
        max_results: Maximum search results
        create_summary: Whether to create AI summary
        deps: Agent dependencies (optional)
        
    Returns:
        AgentResponse with research summary
    """
    start_time = time.time()
    
    try:
        logger.info(f"Running research agent: '{query}'")
        
        # Use provided deps or create default
        if not deps:
            deps = ResearchAgentDeps()
        
        # Create a mock context for the search function
        class MockContext:
            def __init__(self, deps):
                self.deps = deps
        
        # Perform intelligent search
        search_results = await intelligent_search(
            MockContext(deps),
            query,
            max_results
        )
        
        if not search_results.results:
            return AgentResponse(
                success=False,
                data=None,
                message="No search results found",
                error="Search returned no results",
                execution_time=time.time() - start_time
            )
        
        # Create comprehensive research prompt
        results_text = ""
        sources = []
        
        for i, result in enumerate(search_results.results, 1):
            if isinstance(result, TavilySearchResult):
                results_text += f"\n{i}. **{result.title}**\n"
                results_text += f"   Source: {result.url}\n"
                results_text += f"   Content: {result.content}\n"
                if result.published_date:
                    results_text += f"   Published: {result.published_date}\n"
                sources.append(result.url)
                
            elif isinstance(result, SerpSearchResult):
                results_text += f"\n{i}. **{result.title}**\n"
                results_text += f"   Source: {result.url}\n"
                results_text += f"   Snippet: {result.snippet}\n"
                sources.append(result.url)
        
        # Add AI summary if available
        ai_summary = search_results.ai_summary or ""
        
        research_prompt = f"""
        Analyze and synthesize the following search results for the query: "{query}"

        {f"AI Summary from Tavily: {ai_summary}" if ai_summary else ""}

        Search Results:
        {results_text}

        Please provide a comprehensive research summary that:
        1. Synthesizes key findings across all sources
        2. Identifies main themes and trends
        3. Highlights the most credible and recent information
        4. Notes any conflicting information or gaps
        5. Provides actionable insights where appropriate
        6. Maintains proper attribution to sources

        Focus on accuracy, clarity, and usefulness for the reader.
        """
        
        # Run the research agent
        if create_summary:
            result = await research_agent.run(research_prompt, deps=deps)
            research_summary = result.data
            tokens_used = result.usage.total_tokens if result.usage else None
        else:
            research_summary = results_text
            tokens_used = None
        
        execution_time = time.time() - start_time
        
        # Store search metadata for potential use
        response_data = {
            "summary": research_summary,
            "search_results": search_results,
            "sources": sources,
            "query": query
        }
        
        return AgentResponse(
            success=True,
            data=response_data,
            message=f"Research completed successfully with {len(search_results.results)} sources",
            execution_time=execution_time,
            tokens_used=tokens_used
        )
        
    except SearchError as e:
        execution_time = time.time() - start_time
        error_msg = f"Search failed: {str(e)}"
        logger.error(error_msg)
        
        return AgentResponse(
            success=False,
            data=None,
            message="Research failed due to search error",
            error=error_msg,
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Research agent failed: {str(e)}"
        logger.error(error_msg)
        
        return AgentResponse(
            success=False,
            data=None,
            message="Research failed due to unexpected error",
            error=error_msg,
            execution_time=execution_time
        )


# Example usage and testing
async def main():
    """Example usage of the research agent."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    try:
        # Run research
        response = await run_research_agent(
            "latest developments in AI safety research 2024",
            max_results=5,
            create_summary=True
        )
        
        if response.success:
            print("✅ Research completed successfully!")
            print(f"Execution time: {response.execution_time:.2f}s")
            if response.tokens_used:
                print(f"Tokens used: {response.tokens_used}")
            
            data = response.data
            print(f"\nQuery: {data['query']}")
            print(f"Sources found: {len(data['sources'])}")
            print(f"\nResearch Summary:\n{data['summary']}")
            
            print(f"\nSources:")
            for i, source in enumerate(data['sources'][:5], 1):
                print(f"{i}. {source}")
                
        else:
            print(f"❌ Research failed: {response.error}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())