# AI Blog Post Generator

An automated, production-grade blog content pipeline that uses **DeepSeek AI** to generate SEO-optimised blog posts and publishes them directly to **WordPress** — all from a simple CSV input file.

---

## What It Does

- Reads a CSV of blog topics / keywords
- Generates high-quality, long-form blog content via the DeepSeek API
- Scores each post for **SEO quality** and **readability**
- Uploads images, builds an **XML image sitemap**, and manages internal linking
- Publishes each post to WordPress automatically via the REST API
- Tracks progress and logs errors in real time

---

## Key Features

| Feature | Details |
|---|---|
| AI Content Generation | DeepSeek LLM with configurable writing style |
| SEO Analysis | Keyword density, meta titles/descriptions, readability scores |
| WordPress Integration | REST API with application password auth |
| Image Optimisation | Auto-resize, alt-text generation, XML sitemap output |
| Internal Linking | Automatic cross-linking between published posts |
| Bulk Processing | Process dozens of articles from one CSV |
| Logging | Structured logs + error reporting |

---

## Project Structure

```
├── main.py                    # Entry point — run this
├── blog_generator.py          # Core pipeline orchestration
├── deepseek_client.py         # DeepSeek AI API client
├── wordpress_client.py        # WordPress REST API client
├── content_analyzer.py        # SEO & readability scoring
├── image_optimizer.py         # Image processing & sitemap
├── config.py                  # Configuration loader
├── logger.py                  # Logging utility
├── web_interface.py           # Optional web UI
├── input.csv                  # Sample input (topics + keywords)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── tests/                     # Test suite
```

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/ai-blog-generator.git
cd ai-blog-generator
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your real values:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your_username
WORDPRESS_PASSWORD=your_application_password
```

> **WordPress tip:** Generate an Application Password in your WordPress dashboard under  
> *Users → Profile → Application Passwords*.

### 5. Prepare your CSV

Create an `input.csv` with at least these columns:

```
title,keyword,category
"How to Lose Weight Fast","weight loss tips","Health"
"Best Electric Cars 2025","electric vehicles","Technology"
```

### 6. Run the generator

```bash
python main.py input.csv
```

Posts are generated, scored, and published automatically. Progress is logged to the console and `error_log.txt`.

---

## Configuration

All settings are loaded from the `.env` file. See `.env.example` for a full list of supported variables.

---

## Tech Stack

- **Python 3.10+**
- **DeepSeek AI** — content generation
- **WordPress REST API** — publishing
- **pandas** — CSV processing
- **NLTK / textstat** — readability analysis
- **YAKE** — keyword extraction
- **BeautifulSoup4** — HTML processing
- **tenacity** — API retry logic

---

## License

MIT License — free to use and modify.
