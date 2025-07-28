"""
Core data models for the multi-agent research pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from datetime import datetime
from enum import Enum


class SearchProvider(str, Enum):
    """Available search providers."""
    TAVILY = "tavily"
    SERP = "serp"


class ResearchQuery(BaseModel):
    """Research query request model."""
    
    query: str = Field(..., description="Research topic to investigate", min_length=1)
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of search results")
    include_summary: bool = Field(default=True, description="Include AI-generated summary")
    search_depth: Literal["basic", "advanced"] = Field(default="advanced", description="Search depth for Tavily")


class TavilySearchResult(BaseModel):
    """Search result from Tavily API (AI-optimized)."""
    
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    content: str = Field(..., description="Full content snippet from Tavily")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score")
    published_date: Optional[str] = Field(default=None, description="Publication date if available")
    raw_content: Optional[str] = Field(default=None, description="Raw scraped content")
    provider: SearchProvider = Field(default=SearchProvider.TAVILY)


class SerpSearchResult(BaseModel):
    """Search result from SerpAPI (Google search)."""
    
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL") 
    snippet: str = Field(..., description="Result snippet")
    position: int = Field(..., ge=1, description="Search result position")
    displayed_link: Optional[str] = Field(default=None, description="Displayed link")
    cached_page_link: Optional[str] = Field(default=None, description="Cached page URL")
    provider: SearchProvider = Field(default=SearchProvider.SERP)


class SearchResults(BaseModel):
    """Combined search results from multiple providers."""
    
    query: str = Field(..., description="Original search query")
    results: List[Union[TavilySearchResult, SerpSearchResult]] = Field(default_factory=list)  
    total_results: int = Field(default=0, description="Total number of results")
    search_time: float = Field(default=0.0, description="Search execution time in seconds")
    providers_used: List[SearchProvider] = Field(default_factory=list)
    ai_summary: Optional[str] = Field(default=None, description="AI-generated summary of results")
    timestamp: datetime = Field(default_factory=datetime.now)


class EmailDraft(BaseModel):
    """Email draft model."""
    
    to: List[str] = Field(..., min_items=1, description="Recipient email addresses")
    subject: str = Field(..., min_length=1, description="Email subject")
    body: str = Field(..., min_length=1, description="Email body content")
    cc: Optional[List[str]] = Field(default=None, description="CC recipients")
    bcc: Optional[List[str]] = Field(default=None, description="BCC recipients")
    attachments: Optional[List[str]] = Field(default=None, description="Attachment file paths")
    draft_id: Optional[str] = Field(default=None, description="Gmail draft ID")
    created_at: datetime = Field(default_factory=datetime.now)


class ResearchEmailRequest(BaseModel):
    """Request to create an email based on research."""
    
    research_query: str = Field(..., description="Original research query")
    email_context: str = Field(..., description="Context for email generation")
    recipient_email: str = Field(..., description="Primary recipient email")
    subject_hint: Optional[str] = Field(default=None, description="Suggested email subject")
    tone: Literal["professional", "casual", "formal", "friendly"] = Field(default="professional")
    include_sources: bool = Field(default=True, description="Include research sources in email")


class AgentResponse(BaseModel):
    """Standard agent response model."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[Union[SearchResults, EmailDraft, str]] = Field(default=None)
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: float = Field(default=0.0, description="Execution time in seconds")
    tokens_used: Optional[int] = Field(default=None, description="LLM tokens consumed")


class SearchError(Exception):
    """Custom exception for search-related errors."""
    
    def __init__(self, message: str, provider: Optional[SearchProvider] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class TavilyAPIError(SearchError):
    """Tavily API specific error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, SearchProvider.TAVILY, status_code)


class SerpAPIError(SearchError):
    """SerpAPI specific error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, SearchProvider.SERP, status_code)


class GmailAPIError(Exception):
    """Gmail API specific error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# Type aliases for convenience
SearchResult = Union[TavilySearchResult, SerpSearchResult]
APIError = Union[TavilyAPIError, SerpAPIError, GmailAPIError]