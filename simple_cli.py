#!/usr/bin/env python3
"""
Simplified CLI for the Multi-Agent Research Pipeline.
"""

import asyncio
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from dotenv import load_dotenv

from agents.research_agent import ResearchAgentDeps, intelligent_search

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

class MockContext:
    def __init__(self, deps):
        self.deps = deps

@click.group()
def cli():
    """Multi-Agent Research Pipeline - Simplified CLI."""
    pass

@cli.command()
@click.argument('query')
@click.option('--max-results', '-n', default=5, help='Maximum search results')
def search(query, max_results):
    """Perform intelligent search on a query."""
    
    async def run_search():
        console.print(f"[bold blue]🔍 Searching:[/bold blue] {query}")
        console.print(f"[dim]Max results: {max_results}[/dim]\n")
        
        try:
            # Create dependencies and run search
            deps = ResearchAgentDeps()
            results = await intelligent_search(MockContext(deps), query, max_results)
            
            # Show results summary
            console.print(f"[green]✅ Found {len(results.results)} results in {results.search_time:.2f}s[/green]")
            console.print(f"[dim]Providers: {', '.join([p.value for p in results.providers_used])}[/dim]\n")
            
            # Show AI summary if available
            if results.ai_summary:
                console.print("[bold cyan]📝 AI Summary:[/bold cyan]")
                console.print(Panel(
                    Markdown(results.ai_summary),
                    title="Summary",
                    border_style="cyan"
                ))
                console.print()
            
            # Show results
            console.print("[bold blue]📚 Search Results:[/bold blue]")
            
            for i, result in enumerate(results.results, 1):
                title = f"[bold]{result.title}[/bold]"
                url = f"[blue]{result.url}[/blue]"
                
                if hasattr(result, 'content') and result.content:
                    content = result.content[:200] + "..." if len(result.content) > 200 else result.content
                elif hasattr(result, 'snippet') and result.snippet:
                    content = result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet
                else:
                    content = "No content available"
                
                console.print(Panel(
                    f"{title}\n{url}\n\n{content}",
                    title=f"Result {i}",
                    border_style="blue"
                ))
                console.print()
            
        except Exception as e:
            console.print(f"[red]❌ Search failed: {e}[/red]")
    
    asyncio.run(run_search())

@cli.command()
def info():
    """Display system information."""
    
    banner = """
# 🔬 Multi-Agent Research Pipeline

**AI-Powered Search with Tavily + SerpAPI**

- 🔍 **Tavily Search**: AI-optimized results with summaries
- 🌐 **SerpAPI Fallback**: Google search integration  
- 🚀 **Intelligent Routing**: Automatic provider selection
    """
    
    console.print(Panel(
        Markdown(banner),
        title="Research System",
        border_style="green"
    ))
    
    # Show provider status
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    table = Table(title="🔍 Search Providers", show_header=True, header_style="bold cyan")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Free Tier", style="dim")
    
    tavily_key = os.getenv('TAVILY_API_KEY')
    serp_key = os.getenv('SERP_API_KEY')
    
    table.add_row(
        "Tavily", 
        "✅ Configured" if tavily_key else "❌ Not configured",
        "1000 searches/month"
    )
    table.add_row(
        "SerpAPI", 
        "✅ Configured" if serp_key else "❌ Not configured",
        "100 searches/month"
    )
    
    console.print(table)

@cli.command()
def interactive():
    """Start interactive search session."""
    
    console.print("[bold green]🚀 Interactive Research Session[/bold green]")
    console.print("Type your search queries or 'quit' to exit\n")
    
    while True:
        try:
            query = console.input("[bold cyan]search> [/bold cyan]").strip()
            
            if not query:
                continue
            elif query.lower() in ['quit', 'exit', 'q']:
                console.print("[bold green]👋 Goodbye![/bold green]")
                break
            else:
                # Run search
                async def run_search():
                    try:
                        deps = ResearchAgentDeps()
                        results = await intelligent_search(MockContext(deps), query, 3)
                        
                        console.print(f"\n[green]Found {len(results.results)} results:[/green]")
                        
                        if results.ai_summary:
                            console.print(f"[cyan]Summary:[/cyan] {results.ai_summary}\n")
                        
                        for i, r in enumerate(results.results, 1):
                            console.print(f"{i}. [bold]{r.title}[/bold]")
                            console.print(f"   [blue]{r.url}[/blue]")
                        console.print()
                        
                    except Exception as e:
                        console.print(f"[red]❌ Search failed: {e}[/red]\n")
                
                asyncio.run(run_search())
                
        except KeyboardInterrupt:
            console.print("\n[bold green]👋 Goodbye![/bold green]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")

if __name__ == "__main__":
    cli()