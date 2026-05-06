import asyncio
import os
import pytest
from datetime import datetime
from dotenv import load_dotenv
from advanced_content_platform.app.services.llm import (
    LLMService, GenerationRequest, GenerationResult,
    OpenAIClient, AnthropicClient, ModelRouter
)

# Load environment variables from .env file
load_dotenv()

@pytest.fixture
def config():
    """Test configuration with API keys"""
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY"),
        "daily_cost_limit": 10.0,
        "cache_size": 100
    }

@pytest.fixture
def llm_service(config):
    """LLM service instance"""
    return LLMService(config)

@pytest.mark.asyncio
async def test_openai_integration(llm_service):
    """Test OpenAI API integration"""
    request = GenerationRequest(
        prompt="Write a one-sentence test response.",
        max_tokens=50,
        temperature=0.7,
        model_preference="gpt-3.5-turbo"
    )
    
    result = await llm_service.generate(request)
    
    assert isinstance(result, GenerationResult)
    assert result.provider == "openai"
    assert result.model_used == "gpt-3.5-turbo"
    assert len(result.content) > 0
    assert result.cost > 0
    assert result.total_tokens > 0
    assert not result.cached

@pytest.mark.asyncio
async def test_anthropic_integration(llm_service):
    """Test Anthropic API integration"""
    request = GenerationRequest(
        prompt="Write a one-sentence test response.",
        max_tokens=50,
        temperature=0.7,
        model_preference="claude-3-sonnet"
    )
    
    result = await llm_service.generate(request)
    
    assert isinstance(result, GenerationResult)
    assert result.provider == "anthropic"
    assert result.model_used == "claude-3-sonnet"
    assert len(result.content) > 0
    assert result.cost > 0
    assert result.total_tokens > 0
    assert not result.cached

@pytest.mark.asyncio
async def test_deepseek_integration(llm_service):
    """Test DeepSeek API integration"""
    request = GenerationRequest(
        prompt="Write a one-sentence test response.",
        max_tokens=50,
        temperature=0.7,
        model_preference="deepseek-chat"
    )
    
    result = await llm_service.generate(request)
    
    assert isinstance(result, GenerationResult)
    assert result.provider == "deepseek"
    assert result.model_used == "deepseek-chat"
    assert len(result.content) > 0
    assert result.cost > 0
    assert result.total_tokens > 0
    assert not result.cached

@pytest.mark.asyncio
async def test_deepseek_coder(llm_service):
    """Test DeepSeek Coder model"""
    request = GenerationRequest(
        prompt="Write a Python function to calculate factorial.",
        max_tokens=200,
        temperature=0.7,
        model_preference="deepseek-coder"
    )
    
    result = await llm_service.generate(request)
    
    assert isinstance(result, GenerationResult)
    assert result.provider == "deepseek"
    assert result.model_used == "deepseek-coder"
    assert len(result.content) > 0
    assert "def" in result.content.lower()  # Should contain code
    assert result.cost > 0
    assert result.total_tokens > 0
    assert not result.cached

@pytest.mark.asyncio
async def test_caching(llm_service):
    """Test response caching"""
    request = GenerationRequest(
        prompt="This is a test prompt for caching.",
        max_tokens=50,
        use_cache=True
    )
    
    # First request should not be cached
    result1 = await llm_service.generate(request)
    assert not result1.cached
    
    # Second identical request should be cached
    result2 = await llm_service.generate(request)
    assert result2.cached
    assert result2.content == result1.content

@pytest.mark.asyncio
async def test_model_routing(llm_service):
    """Test intelligent model routing"""
    # Test outline task
    request_outline = GenerationRequest(
        prompt="Create an outline for a test document.",
        max_tokens=100,
        cost_limit=0.10
    )
    result_outline = await llm_service.generate(request_outline, task_type="outline")
    assert result_outline.model_used in ["gpt-3.5-turbo", "claude-3-sonnet"]
    
    # Test final task
    request_final = GenerationRequest(
        prompt="Write a detailed analysis.",
        max_tokens=100,
        cost_limit=2.00
    )
    result_final = await llm_service.generate(request_final, task_type="final")
    assert result_final.model_used in ["gpt-4-turbo-preview", "claude-3-opus"]

@pytest.mark.asyncio
async def test_cost_limits(llm_service):
    """Test cost limiting functionality"""
    initial_cost = llm_service.total_cost
    
    # Generate until we hit the limit
    request = GenerationRequest(
        prompt="Generate test content.",
        max_tokens=1000,
        cost_limit=1.0
    )
    
    with pytest.raises(Exception, match="Daily cost limit exceeded"):
        while True:
            await llm_service.generate(request)
            if llm_service.total_cost >= llm_service.daily_cost_limit:
                break

@pytest.mark.asyncio
async def test_multi_stage_generation(llm_service):
    """Test multi-stage content generation"""
    stages = [
        {
            "task_type": "outline",
            "prompt": "Create a brief outline about AI.",
            "output_key": "outline"
        },
        {
            "task_type": "draft",
            "prompt": "Write a first draft based on this outline: {{ outline }}",
            "context_keys": ["outline"],
            "output_key": "draft"
        },
        {
            "task_type": "final",
            "prompt": "Polish this draft into a final version: {{ draft }}",
            "context_keys": ["draft"],
            "output_key": "final"
        }
    ]
    
    results = await llm_service.multi_stage_generation(stages)
    
    assert len(results) == 3
    assert all(isinstance(r, GenerationResult) for r in results)
    assert results[0].model_used in ["gpt-3.5-turbo", "claude-3-sonnet"]  # outline
    assert results[2].model_used in ["gpt-4-turbo-preview", "claude-3-opus"]  # final

@pytest.mark.asyncio
async def test_batch_generation(llm_service):
    """Test concurrent batch generation"""
    requests = [
        GenerationRequest(prompt=f"Generate test content {i}", max_tokens=50)
        for i in range(3)
    ]
    
    results = await llm_service.batch_generate(requests, concurrency=2)
    
    assert len(results) == 3
    assert all(isinstance(r, GenerationResult) for r in results)
    assert all(len(r.content) > 0 for r in results)

@pytest.mark.asyncio
async def test_health_check(llm_service):
    """Test service health check"""
    health = await llm_service.health_check()
    
    assert health["status"] == "healthy"
    assert "openai" in health["clients"]
    assert "anthropic" in health["clients"]
    assert isinstance(health["total_cost"], float)
    assert isinstance(health["cache_size"], int)
    assert "timestamp" in health

def test_cost_summary(llm_service):
    """Test cost tracking summary"""
    summary = llm_service.get_cost_summary()
    
    assert isinstance(summary["total_cost"], float)
    assert isinstance(summary["daily_limit"], float)
    assert isinstance(summary["remaining_budget"], float)
    assert 0 <= summary["utilization"] <= 1.0
    assert isinstance(summary["cache_hits"], int)
