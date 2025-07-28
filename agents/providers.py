"""
LLM provider configuration for multi-agent research pipeline.
Supports OpenAI and Gemini with automatic fallback.
"""

import logging
from typing import Optional, Dict, Any, Union
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ModelProvider:
    """LLM model provider factory and configuration."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize model provider.
        
        Args:
            settings: Application settings (optional, will load from env if not provided)
        """
        self.settings = settings or get_settings()
    
    def get_model(self, provider: Optional[str] = None) -> Model:
        """
        Get LLM model instance based on provider setting.
        
        Args:
            provider: Override provider ("openai" or "gemini")
            
        Returns:
            Configured model instance
            
        Raises:
            ValueError: If provider is invalid or API key is missing
        """
        provider = provider or self.settings.llm_provider
        
        if provider == "openai":
            return self._get_openai_model()
        elif provider == "gemini":
            return self._get_gemini_model()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _get_openai_model(self) -> OpenAIModel:
        """Get configured OpenAI model."""
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        
        # Set API key as environment variable for OpenAI
        import os
        os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        
        # Create model settings
        from pydantic_ai.models.openai import ModelSettings
        
        temperature = 0.7
        if "gpt-4" in self.settings.openai_model:
            temperature = 0.3  # More deterministic for research tasks
        
        settings = ModelSettings(temperature=temperature)
        
        logger.info(f"Initializing OpenAI model: {self.settings.openai_model}")
        return OpenAIModel(model_name=self.settings.openai_model, settings=settings)
    
    def _get_gemini_model(self) -> GeminiModel:
        """Get configured Gemini model."""
        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini provider")
        
        # Set API key as environment variable for Gemini
        import os
        os.environ["GEMINI_API_KEY"] = self.settings.gemini_api_key
        
        # Create model settings
        from pydantic_ai.models.gemini import ModelSettings
        
        temperature = 0.7
        if "pro" in self.settings.gemini_model:
            temperature = 0.2  # More focused for research analysis
        elif "flash" in self.settings.gemini_model:
            temperature = 0.4  # Balanced for speed and quality
        
        settings = ModelSettings(temperature=temperature)
        
        logger.info(f"Initializing Gemini model: {self.settings.gemini_model}")
        return GeminiModel(model_name=self.settings.gemini_model, settings=settings)
    
    def get_research_model(self) -> Model:
        """
        Get model optimized for research tasks.
        Gemini is preferred for search result processing.
        """
        # Prefer Gemini for research if available
        if self.settings.gemini_api_key:
            try:
                return self._get_gemini_model()
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini, falling back to OpenAI: {e}")
        
        # Fallback to OpenAI
        if self.settings.openai_api_key:
            return self._get_openai_model()
        
        raise ValueError("No valid LLM provider configured")
    
    def get_email_model(self) -> Model:
        """
        Get model optimized for email generation.
        Both providers work well for this task.
        """
        return self.get_model()  # Use default provider


def create_agent_with_model(
    system_prompt: str,
    deps_type: type,
    provider: Optional[str] = None,
    **kwargs
) -> Agent:
    """
    Create a Pydantic AI agent with the specified model provider.
    
    Args:
        system_prompt: System prompt for the agent
        deps_type: Dependencies type for the agent
        provider: LLM provider override
        **kwargs: Additional agent configuration
        
    Returns:
        Configured Agent instance
    """
    model_provider = ModelProvider()
    model = model_provider.get_model(provider)
    
    agent = Agent(
        model,
        system_prompt=system_prompt,
        deps_type=deps_type,
        **kwargs
    )
    
    logger.info(f"Created agent with {model.__class__.__name__}")
    return agent


def get_model_info(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """
    Get information about configured models.
    
    Args:
        settings: Application settings
        
    Returns:
        Dictionary with model information
    """
    settings = settings or get_settings()
    
    info = {
        "default_provider": settings.llm_provider,
        "available_providers": [],
        "models": {}
    }
    
    # Check OpenAI availability
    if settings.openai_api_key:
        info["available_providers"].append("openai")
        info["models"]["openai"] = {
            "model": settings.openai_model,
            "configured": True
        }
    else:
        info["models"]["openai"] = {"configured": False}
    
    # Check Gemini availability
    if settings.gemini_api_key:
        info["available_providers"].append("gemini")
        info["models"]["gemini"] = {
            "model": settings.gemini_model,
            "configured": True
        }
    else:
        info["models"]["gemini"] = {"configured": False}
    
    return info


# System prompts for different agent types
RESEARCH_AGENT_PROMPT = """
You are an expert research agent specializing in finding, analyzing, and synthesizing information from multiple sources.

Your capabilities:
- Search for information using Tavily (AI-optimized) and SerpAPI (Google search)
- Analyze and synthesize search results with deep contextual understanding
- Create comprehensive research summaries with proper source attribution
- Generate email drafts based on research findings
- Maintain focus on accuracy, relevance, and credibility

Guidelines:
- Always verify information across multiple sources when possible
- Provide clear source attribution for all claims
- Synthesize information rather than just summarizing individual sources
- Focus on the most recent and credible information
- Use clear, professional language appropriate for the intended audience
- When creating emails, adapt tone and complexity to the recipient

You have access to intelligent search tools that automatically choose the best search provider based on availability and performance.
"""

EMAIL_AGENT_PROMPT = """
You are an expert email composition agent specializing in creating professional, contextually appropriate email communications.

Your capabilities:
- Create well-structured emails based on research content
- Adapt tone and style to different recipients and contexts
- Include proper source attribution when referencing research
- Generate compelling subject lines
- Format emails with appropriate HTML structure when needed

Guidelines:
- Always maintain professional tone unless specifically requested otherwise
- Structure emails with clear introduction, body, and conclusion
- Include relevant research sources as references or links
- Use appropriate salutations and closings
- Keep emails concise while being comprehensive
- Adapt complexity and technical language to the intended audience

You work in conjunction with the research agent to create informed, valuable email communications.
"""


# Global model provider instance
_model_provider = None


def get_model_provider() -> ModelProvider:
    """Get global model provider instance."""
    global _model_provider
    if _model_provider is None:
        _model_provider = ModelProvider()
    return _model_provider


# Convenience functions
def get_default_model() -> Model:
    """Get the default configured model."""
    return get_model_provider().get_model()


def get_research_optimized_model() -> Model:
    """Get model optimized for research tasks."""
    return get_model_provider().get_research_model()


def get_email_optimized_model() -> Model:
    """Get model optimized for email generation."""
    return get_model_provider().get_email_model()