from setuptools import setup, find_packages

setup(
    name="advanced_content_platform",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "deepseek",
        "nltk",
        "textstat",
        "yake",
        "python-Levenshtein",
        "pytest",
        "pytest-asyncio",
        "python-dotenv"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered content generation with SEO optimization",
    keywords="ai, content generation, seo, nlp",
    python_requires=">=3.8",
)
