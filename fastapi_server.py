"""
FastAPI server for N8N HTTP integration
Multi-Agent Research Pipeline API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import logging

from n8n_integration import sync_intelligent_search, sync_tavily_search, sync_serp_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Research Pipeline API",
    description="AI-powered research API with Tavily and SerpAPI integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    search_strategy: Optional[str] = "intelligent"

class SearchResult(BaseModel):
    title: str
    url: str
    content: Optional[str] = ""
    snippet: Optional[str] = ""  
    score: Optional[float] = 0.0
    position: Optional[int] = 0
    provider: str
    published_date: Optional[str] = None

class SearchResponse(BaseModel):
    success: bool
    query: str
    total_results: int
    search_time: float
    providers_used: List[str]
    ai_summary: Optional[str] = None
    results: List[Dict[str, Any]]
    timestamp: Optional[str] = None
    error: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Multi-Agent Research Pipeline API",
        "version": "1.0.0"
    }

# Main search endpoint
@app.post("/search", response_model=SearchResponse)
async def intelligent_search(request: SearchRequest):
    """
    Perform intelligent search using Tavily (primary) and SerpAPI (fallback)
    
    - **query**: Search query string
    - **max_results**: Maximum number of results (1-20)
    - **search_strategy**: "intelligent", "tavily_only", or "serp_only"
    """
    try:
        logger.info(f"Search request: '{request.query}' (max_results={request.max_results})")
        
        # Validate input
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if request.max_results < 1 or request.max_results > 20:
            raise HTTPException(status_code=400, detail="max_results must be between 1 and 20")
        
        # Perform search
        result = sync_intelligent_search(
            query=request.query.strip(),
            max_results=request.max_results
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown search error'))
        
        logger.info(f"Search completed: {result['total_results']} results in {result['search_time']:.2f}s")
        return SearchResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Tavily-only search endpoint
@app.post("/search/tavily", response_model=SearchResponse)
async def tavily_search(request: SearchRequest):
    """
    Perform search using Tavily API only (AI-optimized results with summaries)
    
    - **query**: Search query string
    - **max_results**: Maximum number of results (1-20)
    """
    try:
        logger.info(f"Tavily search: '{request.query}' (max_results={request.max_results})")
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
            
        result = sync_tavily_search(
            query=request.query.strip(),
            max_results=request.max_results
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=500, detail=result.get('error', 'Tavily search failed'))
        
        return SearchResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tavily search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tavily search error: {str(e)}")

# SerpAPI-only search endpoint
@app.post("/search/serp", response_model=SearchResponse)
async def serp_search(request: SearchRequest):
    """
    Perform search using SerpAPI only (Google search results)
    
    - **query**: Search query string
    - **max_results**: Maximum number of results (1-20)
    """
    try:
        logger.info(f"SerpAPI search: '{request.query}' (max_results={request.max_results})")
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
            
        result = sync_serp_search(
            query=request.query.strip(),
            max_results=request.max_results
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=500, detail=result.get('error', 'SerpAPI search failed'))
        
        return SearchResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SerpAPI search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SerpAPI search error: {str(e)}")

# Batch search endpoint
@app.post("/search/batch")
async def batch_search(queries: List[str], max_results_per_query: int = 3):
    """
    Perform batch searches on multiple queries
    
    - **queries**: List of search queries
    - **max_results_per_query**: Maximum results per query
    """
    try:
        if len(queries) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 queries per batch")
        
        results = []
        for query in queries:
            if query.strip():
                result = sync_intelligent_search(query.strip(), max_results_per_query)
                results.append(result)
        
        return {
            "success": True,
            "total_queries": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch search error: {str(e)}")

# API status endpoint
@app.get("/status")
async def api_status():
    """Get API status and configuration"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    return {
        "api_status": "running",
        "search_providers": {
            "tavily": "configured" if os.getenv('TAVILY_API_KEY') else "not configured",
            "serp": "configured" if os.getenv('SERP_API_KEY') else "not configured"
        },
        "search_strategy": os.getenv('SEARCH_STRATEGY', 'intelligent'),
        "max_search_results": int(os.getenv('MAX_SEARCH_RESULTS', 10)),
        "endpoints": {
            "intelligent_search": "/search",
            "tavily_only": "/search/tavily", 
            "serp_only": "/search/serp",
            "batch_search": "/search/batch",
            "health": "/health",
            "docs": "/docs"
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "message": "Multi-Agent Research Pipeline API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "status": "/status"
    }

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    
    print("🚀 Starting Multi-Agent Research Pipeline API...")
    print(f"📝 API Documentation: http://0.0.0.0:{port}/docs")
    print(f"🔍 Example: curl -X POST http://0.0.0.0:{port}/search -H 'Content-Type: application/json' -d '{{\"query\":\"Python frameworks\",\"max_results\":3}}'")
    print()
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )