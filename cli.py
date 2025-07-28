"""
Command Line Interface for the Multi-Agent Research Pipeline.
"""

import asyncio
import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown
from dotenv import load_dotenv

from config.settings import get_settings, validate_api_keys, setup_logging
from agents.research_agent import run_research_agent, ResearchAgentDeps
from agents.email_agent import run_email_agent, EmailAgentDeps
from agents.models import ResearchEmailRequest
from agents.providers import get_model_info

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()
logger = logging.getLogger(__name__)


class ResearchCLI:
    """CLI application for the research pipeline."""
    
    def __init__(self):
        """Initialize the CLI application."""
        try:
            self.settings = get_settings()
            setup_logging(self.settings)
            validate_api_keys(self.settings)
            self.session_history = []
            logger.info("Research CLI initialized successfully")
        except Exception as e:
            console.print(f"[red]❌ Initialization failed: {e}[/red]")
            sys.exit(1)
    
    def display_banner(self):
        """Display the application banner."""
        banner_text = """
# 🔬 Multi-Agent Research Pipeline

**AI-Powered Research with Intelligent Search & Email Integration**

- 🔍 **Tavily Search**: AI-optimized search results
- 🌐 **SerpAPI Fallback**: Google search integration  
- 🤖 **Gemini + OpenAI**: Advanced LLM processing
- 📧 **Gmail Integration**: Automated email drafts
        """
        console.print(Panel(Markdown(banner_text), title="Research Agent", border_style="blue"))
    
    def display_model_info(self):
        """Display configured model information."""
        model_info = get_model_info(self.settings)
        
        table = Table(title="🤖 LLM Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="green")
        table.add_column("Status", justify="center")
        
        for provider, info in model_info["models"].items():
            status = "✅ Configured" if info["configured"] else "❌ Not configured"
            model_name = info.get("model", "N/A") if info["configured"] else "N/A"
            
            # Highlight default provider
            provider_name = f"[bold]{provider}[/bold]" if provider == model_info["default_provider"] else provider
            
            table.add_row(provider_name, model_name, status)
        
        console.print(table)
        console.print(f"Default Provider: [bold cyan]{model_info['default_provider']}[/bold cyan]")
        console.print()
    
    async def run_research(
        self, 
        query: str, 
        max_results: int = 10,
        show_sources: bool = True,
        create_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Run research with progress indication.
        
        Args:
            query: Research query
            max_results: Maximum search results
            show_sources: Whether to display sources
            create_summary: Whether to create AI summary
            
        Returns:
            Research results dictionary
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            # Start research task
            task = progress.add_task("🔍 Searching and analyzing...", total=None)
            
            try:
                # Run research agent
                response = await run_research_agent(
                    query=query,
                    max_results=max_results,
                    create_summary=create_summary
                )
                
                progress.update(task, description="✅ Research completed!")
                
                if response.success:
                    # Display results
                    data = response.data
                    
                    # Show query and metadata
                    console.print(f"\n[bold blue]Query:[/bold blue] {data['query']}")
                    console.print(f"[dim]Found {len(data['sources'])} sources in {response.execution_time:.2f}s[/dim]")
                    
                    if response.tokens_used:
                        console.print(f"[dim]Tokens used: {response.tokens_used:,}[/dim]")
                    
                    # Display research summary
                    console.print("\n[bold green]📋 Research Summary:[/bold green]")
                    console.print(Panel(
                        Markdown(data['summary']), 
                        title="Analysis", 
                        border_style="green",
                        padding=(1, 2)
                    ))
                    
                    # Display sources if requested
                    if show_sources and data['sources']:
                        console.print("\n[bold cyan]📚 Sources:[/bold cyan]")
                        sources_table = Table(show_header=True, header_style="bold cyan")
                        sources_table.add_column("#", width=3)
                        sources_table.add_column("URL", style="blue")
                        
                        for i, source in enumerate(data['sources'][:10], 1):  # Limit to 10 sources
                            sources_table.add_row(str(i), source)
                        
                        console.print(sources_table)
                    
                    # Store in session history
                    self.session_history.append({
                        "type": "research",
                        "query": query,
                        "response": response,
                        "timestamp": datetime.now()
                    })
                    
                    return data
                else:
                    console.print(f"\n[red]❌ Research failed: {response.error}[/red]")
                    return {}
                    
            except Exception as e:
                progress.update(task, description="❌ Research failed!")
                console.print(f"\n[red]❌ Research error: {str(e)}[/red]")
                return {}
    
    async def create_email_from_research(
        self,
        research_data: Dict[str, Any],
        recipient: str,
        context: str,
        subject_hint: Optional[str] = None,
        tone: str = "professional"
    ) -> bool:
        """
        Create email draft from research results.
        
        Args:
            research_data: Research results from run_research
            recipient: Email recipient
            context: Email context
            subject_hint: Suggested subject
            tone: Email tone
            
        Returns:
            Success status
        """
        if not research_data:
            console.print("[red]❌ No research data available for email creation[/red]")
            return False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            task = progress.add_task("📧 Creating email draft...", total=None)
            
            try:
                # Create email request
                email_request = ResearchEmailRequest(
                    research_query=research_data.get('query', 'Research query'),
                    email_context=context,
                    recipient_email=recipient,
                    subject_hint=subject_hint,
                    tone=tone,
                    include_sources=True
                )
                
                # Run email agent
                email_response = await run_email_agent(
                    email_request,
                    research_data['summary'],
                    research_data['sources']
                )
                
                progress.update(task, description="✅ Email created!")
                
                if email_response.success:
                    email_draft = email_response.data
                    
                    # Display email info
                    console.print(f"\n[bold green]📧 Email Draft Created![/bold green]")
                    console.print(f"[bold]To:[/bold] {', '.join(email_draft.to)}")
                    console.print(f"[bold]Subject:[/bold] {email_draft.subject}")
                    
                    if email_draft.draft_id:
                        console.print(f"[bold]Gmail Draft ID:[/bold] {email_draft.draft_id}")
                    
                    console.print(f"[dim]Execution time: {email_response.execution_time:.2f}s[/dim]")
                    
                    # Show email preview
                    console.print("\n[bold blue]📝 Email Preview:[/bold blue]")
                    # Strip HTML for preview
                    import re
                    clean_body = re.sub('<[^<]+?>', '', email_draft.body)
                    preview = clean_body[:300] + "..." if len(clean_body) > 300 else clean_body
                    
                    console.print(Panel(
                        preview,
                        title="Body Preview",
                        border_style="blue",
                        padding=(1, 2)
                    ))
                    
                    # Store in session history
                    self.session_history.append({
                        "type": "email",
                        "recipient": recipient,
                        "response": email_response,
                        "timestamp": datetime.now()
                    })
                    
                    return True
                else:
                    console.print(f"\n[red]❌ Email creation failed: {email_response.error}[/red]")
                    return False
                    
            except Exception as e:
                progress.update(task, description="❌ Email creation failed!")
                console.print(f"\n[red]❌ Email creation error: {str(e)}[/red]")
                return False
    
    def show_session_history(self):
        """Display session history."""
        if not self.session_history:
            console.print("[yellow]No session history available[/yellow]")
            return
        
        console.print(f"\n[bold cyan]📊 Session History ({len(self.session_history)} items):[/bold cyan]")
        
        history_table = Table(show_header=True, header_style="bold cyan")
        history_table.add_column("Time", width=20)
        history_table.add_column("Type", width=10)
        history_table.add_column("Details", style="dim")
        
        for item in self.session_history[-10:]:  # Show last 10 items
            timestamp = item["timestamp"].strftime("%H:%M:%S")
            
            if item["type"] == "research":
                details = f"Query: {item['query'][:50]}..."
            elif item["type"] == "email":
                details = f"To: {item['recipient']}"
            else:
                details = "Unknown"
            
            history_table.add_row(timestamp, item["type"].title(), details)
        
        console.print(history_table)


# CLI Commands
@click.group()
@click.pass_context
def cli(ctx):
    """Multi-Agent Research Pipeline CLI."""
    ctx.ensure_object(dict)
    ctx.obj['app'] = ResearchCLI()


@cli.command()
@click.pass_context
def info(ctx):
    """Display system information and configuration."""
    app = ctx.obj['app']
    app.display_banner()
    app.display_model_info()


@cli.command()
@click.argument('query')
@click.option('--max-results', '-n', default=10, help='Maximum search results')
@click.option('--no-sources', is_flag=True, help='Hide source URLs')
@click.option('--no-summary', is_flag=True, help='Skip AI summary generation')
@click.pass_context
def research(ctx, query, max_results, no_sources, no_summary):
    """Perform research on a given query."""
    app = ctx.obj['app']
    
    async def run():
        await app.run_research(
            query=query,
            max_results=max_results,
            show_sources=not no_sources,
            create_summary=not no_summary
        )
    
    asyncio.run(run())


@cli.command()
@click.argument('query')
@click.argument('recipient')
@click.option('--context', '-c', default="Based on recent research", help='Email context')
@click.option('--subject', '-s', help='Email subject hint')
@click.option('--tone', '-t', default='professional', help='Email tone')
@click.option('--max-results', '-n', default=10, help='Maximum search results')
@click.pass_context
def research_and_email(ctx, query, recipient, context, subject, tone, max_results):
    """Research a topic and create an email draft."""
    app = ctx.obj['app']
    
    async def run():
        # First, perform research
        console.print(f"[bold blue]Step 1:[/bold blue] Researching '{query}'...")
        research_data = await app.run_research(
            query=query,
            max_results=max_results,
            show_sources=True,
            create_summary=True
        )
        
        if research_data:
            # Then create email
            console.print(f"\n[bold blue]Step 2:[/bold blue] Creating email for {recipient}...")
            await app.create_email_from_research(
                research_data=research_data,
                recipient=recipient,
                context=context,
                subject_hint=subject,
                tone=tone
            )
    
    asyncio.run(run())


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive research session."""
    app = ctx.obj['app']
    app.display_banner()
    
    console.print("[bold green]🚀 Interactive Research Session Started![/bold green]")
    console.print("Commands: 'research <query>', 'email <recipient>', 'history', 'help', 'quit'")
    console.print()
    
    current_research = None
    
    while True:
        try:
            command = console.input("\n[bold cyan]research> [/bold cyan]").strip()
            
            if not command:
                continue
            elif command.lower() in ['quit', 'exit', 'q']:
                console.print("[bold green]👋 Goodbye![/bold green]")
                break
            elif command.startswith('research '):
                query = command[9:].strip()
                if query:
                    async def run():
                        nonlocal current_research
                        current_research = await app.run_research(query)
                    asyncio.run(run())
            elif command.startswith('email '):
                recipient = command[6:].strip()
                if recipient and current_research:
                    context = console.input("Email context: ").strip() or "Based on recent research"
                    subject = console.input("Subject hint (optional): ").strip() or None
                    
                    async def run():
                        await app.create_email_from_research(
                            current_research, recipient, context, subject
                        )
                    asyncio.run(run())
                elif not current_research:
                    console.print("[yellow]⚠️  No research data available. Run 'research <query>' first.[/yellow]")
                else:
                    console.print("[red]❌ Please provide recipient email[/red]")
            elif command == 'history':
                app.show_session_history()
            elif command == 'help':
                console.print("""
[bold]Available Commands:[/bold]
• [cyan]research <query>[/cyan] - Perform research
• [cyan]email <recipient>[/cyan] - Create email from last research
• [cyan]history[/cyan] - Show session history
• [cyan]help[/cyan] - Show this help
• [cyan]quit[/cyan] - Exit interactive session
                """)
            else:
                console.print("[red]❌ Unknown command. Type 'help' for available commands.[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[bold green]👋 Goodbye![/bold green]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error: {str(e)}[/red]")


@cli.command()
@click.pass_context
def history(ctx):
    """Show session history."""
    app = ctx.obj['app']
    app.show_session_history()


if __name__ == "__main__":
    cli()