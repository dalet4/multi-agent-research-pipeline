#!/usr/bin/env python3
"""
Simple test script to verify the research pipeline works.
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up basic logging
logging.basicConfig(level=logging.INFO)

async def test_research():
    from agents.research_agent import ResearchAgentDeps, intelligent_search
    
    print("🔬 Testing Multi-Agent Research Pipeline")
    print("=" * 50)
    
    # Create dependencies
    deps = ResearchAgentDeps()
    
    class MockContext:
        def __init__(self, deps):
            self.deps = deps
    
    # Test search
    query = "latest Python web frameworks 2024"
    print(f"🔍 Searching: {query}")
    
    try:
        results = await intelligent_search(MockContext(deps), query, 3)
        
        print(f"✅ Found {len(results.results)} results in {results.search_time:.2f}s")
        print(f"📊 Providers used: {[p.value for p in results.providers_used]}")
        
        if results.ai_summary:
            print(f"\n📝 AI Summary:\n{results.ai_summary}")
        
        print(f"\n📚 Results:")
        for i, result in enumerate(results.results, 1):
            print(f"{i}. {result.title}")
            print(f"   {result.url}")
            if hasattr(result, 'content'):
                print(f"   {result.content[:100]}...")
            elif hasattr(result, 'snippet'):
                print(f"   {result.snippet[:100]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Research failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_research())
    if success:
        print("🎉 Research pipeline working correctly!")
    else:
        print("❌ Research pipeline has issues.")