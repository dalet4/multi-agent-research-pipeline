"""
Email Draft Agent for creating Gmail drafts based on research content.
"""

import asyncio
import logging
import time
from typing import List, Optional
from datetime import datetime

from pydantic_ai import Agent, RunContext
from pydantic import Field

from config.settings import AgentDependencies
from agents.models import EmailDraft, ResearchEmailRequest, AgentResponse, GmailAPIError
from agents.providers import get_email_optimized_model, EMAIL_AGENT_PROMPT
from tools.gmail_tool import GmailTool

logger = logging.getLogger(__name__)


class EmailAgentDeps(AgentDependencies):
    """Dependencies for the Email Agent."""
    
    gmail_tool: Optional[GmailTool] = Field(default=None)
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.gmail_tool:
            self.gmail_tool = GmailTool(self.gmail_credentials_path)


# Create the email agent
email_agent = Agent(
    get_email_optimized_model(),
    system_prompt=EMAIL_AGENT_PROMPT,
    deps_type=EmailAgentDeps,
    result_type=EmailDraft
)


@email_agent.tool
async def create_gmail_draft(
    ctx: RunContext[EmailAgentDeps],
    email_draft: EmailDraft
) -> str:
    """
    Create a Gmail draft using the Gmail API.
    
    Args:
        ctx: Agent run context
        email_draft: Email draft to create
        
    Returns:
        Draft ID of created Gmail draft
        
    Raises:
        GmailAPIError: If draft creation fails
    """
    try:
        logger.info(f"Creating Gmail draft: '{email_draft.subject}' to {email_draft.to}")
        
        # Create draft via Gmail API
        draft_id = await ctx.deps.gmail_tool.create_draft(email_draft)
        
        logger.info(f"Gmail draft created successfully: {draft_id}")
        return f"Gmail draft created with ID: {draft_id}"
        
    except GmailAPIError as e:
        logger.error(f"Failed to create Gmail draft: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating Gmail draft: {e}")
        raise GmailAPIError(f"Unexpected error: {str(e)}")


@email_agent.tool
async def format_research_content(
    ctx: RunContext[EmailAgentDeps],
    research_content: str,
    sources: List[str],
    include_sources: bool = True
) -> str:
    """
    Format research content for email inclusion.
    
    Args:
        ctx: Agent run context
        research_content: Raw research content
        sources: List of source URLs
        include_sources: Whether to include source links
        
    Returns:
        Formatted HTML content for email
    """
    html_content = f"<div>{research_content}</div>"
    
    if include_sources and sources:
        html_content += "\n\n<h3>Sources:</h3>\n<ul>\n"
        for i, source in enumerate(sources[:5], 1):  # Limit to top 5 sources
            html_content += f'<li><a href="{source}">Source {i}</a></li>\n'
        html_content += "</ul>"
    
    return html_content


async def run_email_agent(
    request: ResearchEmailRequest,
    research_content: str,
    sources: Optional[List[str]] = None,
    deps: Optional[EmailAgentDeps] = None
) -> AgentResponse:
    """
    Run the email agent to create an email draft.
    
    Args:
        request: Email request with context and recipient info
        research_content: Research content to include in email
        sources: List of research sources
        deps: Agent dependencies (optional)
        
    Returns:
        AgentResponse with EmailDraft or error
    """
    start_time = time.time()
    
    try:
        logger.info(f"Running email agent for: {request.recipient_email}")
        
        # Use provided deps or create default
        if not deps:
            deps = EmailAgentDeps()
        
        # Prepare email context
        sources = sources or []
        formatted_content = await format_research_content(
            None,  # Context not needed for this tool
            research_content,
            sources,
            request.include_sources
        )
        
        # Create comprehensive prompt for the agent
        agent_prompt = f"""
        Create a professional email for {request.recipient_email} based on the following research:

        **Research Query:** {request.research_query}
        **Context:** {request.email_context}
        **Tone:** {request.tone}
        **Subject Hint:** {request.subject_hint or "Generate appropriate subject"}

        **Research Content:**
        {formatted_content}

        Please create an email that:
        1. Has an appropriate subject line
        2. Addresses the recipient professionally
        3. Incorporates the research findings naturally
        4. Maintains the requested tone
        5. Includes proper source attribution if sources are provided
        6. Ends with an appropriate closing

        Return the email as an EmailDraft object with proper to, subject, and body fields.
        """
        
        # Run the agent
        result = await email_agent.run(
            agent_prompt,
            deps=deps
        )
        
        # Create Gmail draft if email was generated successfully
        if result.data:
            try:
                draft_id = await create_gmail_draft(
                    RunContext(deps=deps, usage=result.usage),
                    result.data
                )
                result.data.draft_id = draft_id.split(": ")[-1]  # Extract ID from response
            except Exception as e:
                logger.warning(f"Failed to create Gmail draft, but email generated: {e}")
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            success=True,
            data=result.data,
            message="Email draft created successfully",
            execution_time=execution_time,
            tokens_used=result.usage.total_tokens if result.usage else None
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Email agent failed: {str(e)}"
        logger.error(error_msg)
        
        return AgentResponse(
            success=False,
            data=None,
            message="Failed to create email draft",
            error=error_msg,
            execution_time=execution_time
        )


# Convenience function for simple email creation
async def create_simple_email(
    to: str,
    subject: str,
    research_content: str,
    context: str = "Based on recent research",
    tone: str = "professional",
    include_sources: bool = True,
    sources: Optional[List[str]] = None
) -> AgentResponse:
    """
    Create a simple email draft from research content.
    
    Args:
        to: Recipient email
        subject: Email subject
        research_content: Research findings
        context: Email context
        tone: Email tone
        include_sources: Whether to include sources
        sources: List of source URLs
        
    Returns:
        AgentResponse with EmailDraft
    """
    request = ResearchEmailRequest(
        research_query="User-provided research",
        email_context=context,
        recipient_email=to,
        subject_hint=subject,
        tone=tone,
        include_sources=include_sources
    )
    
    return await run_email_agent(request, research_content, sources)


# Example usage and testing
async def main():
    """Example usage of the email agent."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Example research content
    research_content = """
    Recent developments in AI safety research show significant progress in alignment techniques.
    Key findings include:
    - Constitutional AI methods showing promise in reducing harmful outputs
    - Improved techniques for AI interpretability and explainability
    - New frameworks for evaluating AI system safety and reliability
    - Collaborative efforts between industry and academia increasing
    """
    
    sources = [
        "https://example.com/ai-safety-research-2024",
        "https://example.com/constitutional-ai-paper",
        "https://example.com/alignment-techniques"
    ]
    
    # Create email request
    request = ResearchEmailRequest(
        research_query="latest AI safety research developments",
        email_context="Update on recent AI safety research for quarterly review",
        recipient_email="colleague@company.com",
        subject_hint="AI Safety Research Update - Q4 2024",
        tone="professional",
        include_sources=True
    )
    
    try:
        # Run the email agent
        response = await run_email_agent(request, research_content, sources)
        
        if response.success:
            print("✅ Email draft created successfully!")
            print(f"Execution time: {response.execution_time:.2f}s")
            if response.tokens_used:
                print(f"Tokens used: {response.tokens_used}")
            
            email_draft = response.data
            print(f"\nSubject: {email_draft.subject}")
            print(f"To: {', '.join(email_draft.to)}")
            print(f"Body preview: {email_draft.body[:200]}...")
            
            if email_draft.draft_id:
                print(f"Gmail Draft ID: {email_draft.draft_id}")
        else:
            print(f"❌ Email creation failed: {response.error}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())