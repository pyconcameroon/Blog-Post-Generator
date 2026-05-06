import pytest
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm import LLMService, GenerationRequest
from app.services.seo_analyzer import SEOAnalyzer, SEORequirements
from app.services.content_strategy import ContentStrategyService
from app.services.content_pipeline import ContentGenerationPipeline, GenerationTask

# Load environment variables
load_dotenv()

@pytest.fixture
def llm_service():
    return LLMService({
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY")
    })

@pytest.fixture
def seo_analyzer():
    return SEOAnalyzer()

@pytest.fixture
def strategy_service():
    return ContentStrategyService()

@pytest.fixture
def pipeline(llm_service, seo_analyzer, strategy_service):
    return ContentGenerationPipeline(
        llm_service=llm_service,
        seo_analyzer=seo_analyzer,
        strategy_service=strategy_service
    )

@pytest.mark.asyncio
async def test_content_strategy_service(strategy_service):
    """Test content strategy creation with real keywords"""
    # Create a content strategy for a real niche
    strategy = strategy_service.create_content_strategy(
        niche="software development",
        timeframe="Q3 2025"
    )
    
    assert len(strategy.content_pillars) >= 5
    assert len(strategy.keyword_clusters) >= 3
    assert len(strategy.content_calendar) > 0
    assert all(key in strategy.target_metrics for key in [
        "organic_traffic",
        "conversion_rate",
        "bounce_rate",
        "avg_time_on_page"
    ])

@pytest.mark.asyncio
async def test_seo_analysis(seo_analyzer):
    """Test SEO analysis with real content"""
    test_content = """
# Understanding Machine Learning: A Comprehensive Guide

Machine learning is transforming the way we approach problem-solving in software development. This comprehensive guide explores the fundamentals of machine learning and its practical applications.

## What is Machine Learning?

Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience automatically. Unlike traditional programming, machine learning algorithms adapt and evolve as they process more data.

## Types of Machine Learning

### 1. Supervised Learning
Supervised learning involves training models on labeled data. Common applications include:
- Image classification
- Spam detection
- Price prediction

### 2. Unsupervised Learning
Unsupervised learning works with unlabeled data to discover patterns and relationships. Applications include:
- Customer segmentation
- Anomaly detection
- Feature learning

## Practical Applications

Machine learning is widely used in software development for:
1. Predictive analytics
2. Natural language processing
3. Computer vision
4. Recommendation systems

## Best Practices for Implementation

When implementing machine learning in your projects:
- Start with clean, well-structured data
- Choose appropriate algorithms
- Validate results thoroughly
- Monitor model performance

## Conclusion

Machine learning continues to evolve and create new opportunities in software development. Understanding its fundamentals is crucial for modern developers.
    """
    
    requirements = SEORequirements(
        primary_keyword="machine learning",
        secondary_keywords=["software development", "AI", "algorithms"],
        min_word_count=300,
        max_word_count=2000,
        target_readability_score=60.0
    )
    
    analysis = seo_analyzer.analyze_content(test_content, requirements)
    
    assert analysis.word_count >= 300
    assert "machine learning" in analysis.keyword_density
    assert analysis.readability_score > 0
    assert analysis.heading_count >= 5
    assert len(analysis.extracted_keywords) > 0

@pytest.mark.asyncio
async def test_llm_generation(llm_service):
    """Test real content generation with LLM"""
    request = GenerationRequest(
        prompt="Write a technical tutorial about implementing JWT authentication in Node.js",
        system_prompt="You are an expert software developer. Write detailed, accurate technical content with code examples.",
        max_tokens=1000,
        temperature=0.7
    )
    
    result = await llm_service.generate(request)
    
    assert len(result.content) > 0
    assert result.provider == "deepseek"
    assert "jwt" in result.content.lower() or "authentication" in result.content.lower()
    assert result.total_tokens > 0
    assert result.cost > 0

@pytest.mark.asyncio
async def test_full_content_pipeline(pipeline):
    """Test complete content generation pipeline with real requirements"""
    # Create content plan
    content_plan = pipeline.strategy_service.create_content_plan(
        topic="GraphQL API Development",
        keywords=[
            "GraphQL API",
            "API development",
            "GraphQL schema",
            "GraphQL resolvers",
            "API performance"
        ],
        content_type="technical_tutorial"
    )
    
    # Define strict SEO requirements
    seo_requirements = SEORequirements(
        primary_keyword="GraphQL API",
        secondary_keywords=[
            "API development",
            "GraphQL schema",
            "GraphQL resolvers"
        ],
        min_word_count=1200,
        max_word_count=2000,
        target_readability_score=65.0,
        min_keyword_density=0.5,
        max_keyword_density=2.5,
        target_headings=6
    )
    
    # Create generation task
    task = GenerationTask(
        content_plan=content_plan,
        seo_requirements=seo_requirements,
        max_retries=2,
        require_seo_optimization=True
    )
    
    # Generate content
    result = await pipeline.generate_content(task)
    
    # Validate content
    assert result.content is not None
    assert len(result.content) > 0
    assert result.is_optimized
    
    # Validate SEO metrics
    seo = result.seo_analysis
    assert seo.word_count >= seo_requirements.min_word_count
    assert seo.word_count <= seo_requirements.max_word_count
    assert seo.readability_score >= seo_requirements.target_readability_score
    assert seo.heading_count >= seo_requirements.target_headings
    
    # Validate keyword density
    for keyword in [seo_requirements.primary_keyword] + seo_requirements.secondary_keywords:
        density = seo.keyword_density.get(keyword, 0)
        assert seo_requirements.min_keyword_density <= density <= seo_requirements.max_keyword_density
    
    # Save the generated content for manual review
    output_dir = os.path.join("test_output", datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "graphql_api_tutorial.md"), "w", encoding="utf-8") as f:
        f.write(result.content)
    
    with open(os.path.join(output_dir, "seo_analysis.txt"), "w", encoding="utf-8") as f:
        f.write(f"Word Count: {seo.word_count}\n")
        f.write(f"Readability Score: {seo.readability_score}\n")
        f.write(f"Heading Count: {seo.heading_count}\n\n")
        f.write("Keyword Density:\n")
        for keyword, density in seo.keyword_density.items():
            f.write(f"- {keyword}: {density:.2f}%\n")
        f.write("\nImprovement Suggestions:\n")
        for suggestion in seo.improvement_suggestions:
            f.write(f"- {suggestion}\n")
