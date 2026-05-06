# createblogpost.py
import pandas as pd
import requests
import os
import time
import base64
import chardet
import logging
import json
from tqdm import tqdm
from typing import Optional, Tuple, List, Dict
from dotenv import load_dotenv
from datetime import datetime

# Import our custom analyzers
from content_analyzer import ContentAnalyzer
from image_optimizer import ImageOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blog_generation.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Load configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
WORDPRESS_URL = os.getenv('WORDPRESS_URL')
WORDPRESS_USERNAME = os.getenv('WORDPRESS_USERNAME')
WORDPRESS_PASSWORD = os.getenv('WORDPRESS_PASSWORD')

def check_required_env_vars():
    """Check that all required environment variables are set"""
    required_vars = {
        'DEEPSEEK_API_KEY': DEEPSEEK_API_KEY,
        'WORDPRESS_URL': WORDPRESS_URL,
        'WORDPRESS_USERNAME': WORDPRESS_USERNAME,
        'WORDPRESS_PASSWORD': WORDPRESS_PASSWORD
    }
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def search_and_download_image(title: str, description: str, keywords: list) -> tuple[Optional[bytes], Optional[str]]:
    """
    Search for a relevant image using DeepSeek API and download it
    Returns tuple of (image_bytes, image_source_url) if successful, (None, None) otherwise
    """
    # Construct search query using title and keywords
    search_query = f"{title} {' '.join(keywords[:3])}"
    
    try:
        # Search for images using DeepSeek
        images = deepseek.search_images(
            query=search_query,
            num_results=5,  # Get multiple results to try
            safe_search=True,
            image_type="photo",
            min_width=800,  # Ensure decent quality
            min_height=600
        )
        
        if not images:
            return None, None
            
        # Try to download each image until we get a good one
        for image in images:
            try:
                response = requests.get(image["url"], timeout=30)
                if response.status_code == 200:
                    # Verify it's a valid image
                    content_type = response.headers.get("content-type", "")
                    if content_type.startswith("image/"):
                        return response.content, image.get("sourceUrl")
            except requests.RequestException:
                continue
                
    except Exception as e:
        logging.error(f"Failed to search/download image: {str(e)}")
        
    return None, None

def generate_image_metadata(image_url: str, title: str, keywords: list) -> tuple[str, str]:
    """
    Generate SEO-optimized alt text and caption for an image
    Returns (alt_text, caption)
    """
    try:
        prompt = f"""Analyze this image context and generate SEO-friendly alt text and caption:
        Image URL: {image_url}
        Article Title: {title}
        Keywords: {', '.join(keywords)}
        
        Requirements:
        1. Alt text: Short, descriptive, includes main keyword naturally (max 125 chars)
        2. Caption: Engaging, informative, adds value to article (max 200 chars)
        3. Both should be factual and avoid keyword stuffing
        
        Format:
        ALT: [alt text]
        CAPTION: [caption]"""
        
        response = deepseek.generate_content(
            prompt=prompt,
            temperature=0.3,
            max_tokens=200
        )
        
        # Parse response
        alt_text = ""
        caption = ""
        for line in response.split('\n'):
            if line.startswith('ALT:'):
                alt_text = line[4:].strip()
            elif line.startswith('CAPTION:'):
                caption = line[8:].strip()
        
        return (
            alt_text if alt_text else title,  # Fallback to title if generation fails
            caption if caption else ""  # Empty caption is okay
        )
    except Exception as e:
        logging.warning(f"Failed to generate image metadata: {str(e)}")
        return title, ""

def upload_image_to_wordpress(image_bytes, title, alt_text=""):
    """
    Upload an image to WordPress and return the media ID
    """
    if not alt_text:
        alt_text = title
    
    # Create a safe filename
    filename = slugify(title)[:50] + ".png"
    
    headers = {
        'Authorization': 'Basic ' + base64.b64encode(f'{WORDPRESS_USERNAME}:{WORDPRESS_PASSWORD}'.encode('utf-8')).decode('utf-8'),
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'image/png'
    }
    
    try:
        response = requests.post(
            f'{WORDPRESS_URL}/media',
            headers=headers,
            data=image_bytes,
            timeout=60
        )
        
        if response.status_code == 201:
            return response.json()['id']
        else:
            error_msg = f"Failed to upload image: {response.status_code}"
            if response.text:
                error_msg += f" - {response.text[:200]}"
            raise Exception(error_msg)
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return None

def slugify(text):
    """Create URL-safe slug from text"""
    text = text.lower().strip()
    text = ''.join(c for c in text if c.isalnum() or c in (' ', '-', '_'))
    text = text.replace(' ', '-')
    text = text.replace('--', '-')
    return text[:100]

# Import our DeepSeek client
from deepseek_client import DeepSeekClient, DeepSeekAPIError

# Initialize DeepSeek client once
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is required")
deepseek = DeepSeekClient(api_key=DEEPSEEK_API_KEY)

def validate_outbound_links(content: str) -> tuple[bool, list[str], list[str]]:
    """
    Validate outbound links in content
    Returns (has_enough_links, issues, found_domains)
    """
    import re
    from urllib.parse import urlparse
    
    # Extract all URLs from the content
    urls = re.findall(r'href=["\'](https?://[^"\']+)["\']', content)
    domains = []
    authority_domains = {
        'wikipedia.org',
        'scholar.google.com',
        'ncbi.nlm.nih.gov',
        'research.gov',
        'edu',
        'gov',
        '.org',
        'forbes.com',
        'harvard.edu',
        'mit.edu',
        'stanford.edu',
        'nature.com',
        'sciencedirect.com'
    }
    
    issues = []
    authoritative_count = 0
    
    for url in urls:
        domain = urlparse(url).netloc.lower()
        if domain:
            domains.append(domain)
            # Check if it's an authoritative domain
            if any(auth in domain for auth in authority_domains):
                authoritative_count += 1
    
    # Remove internal links for counting
    external_domains = [d for d in domains if 'dunemedicaldevicesinc.com' not in d]
    
    if len(external_domains) < 3:
        issues.append(f"Only {len(external_domains)} external links found. Minimum 3 recommended.")
    
    if authoritative_count < 2:
        issues.append(f"Only {authoritative_count} authoritative source links found. Minimum 2 recommended.")
    
    return len(issues) == 0, issues, domains

def analyze_readability(content: str) -> tuple[float, list[str]]:
    """
    Analyze content readability and return score and suggestions
    Returns (score, list_of_suggestions)
    """
    import re
    from statistics import mean
    
    suggestions = []
    
    # Remove HTML tags for analysis
    clean_text = re.sub(r'<[^>]+>', '', content)
    paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean_text) if s.strip()]
    words = clean_text.split()
    
    # Calculate metrics
    avg_words_per_sentence = len(words) / len(sentences) if sentences else 0
    avg_words_per_paragraph = mean([len(p.split()) for p in paragraphs]) if paragraphs else 0
    
    # Long sentence check (>20 words)
    long_sentences = [s for s in sentences if len(s.split()) > 20]
    if long_sentences:
        suggestions.append(f"Found {len(long_sentences)} sentences longer than 20 words. Consider breaking them down.")
    
    # Paragraph length check
    long_paragraphs = [p for p in paragraphs if len(p.split()) > 150]
    if long_paragraphs:
        suggestions.append(f"Found {len(long_paragraphs)} paragraphs longer than 150 words. Consider breaking them into smaller chunks.")
    
    # Transition words check
    transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'consequently', 'additionally']
    transition_count = sum(1 for word in words if word.lower() in transition_words)
    if transition_count < len(sentences) * 0.1:  # At least 10% of sentences should have transitions
        suggestions.append("Consider adding more transition words to improve flow.")
    
    # Calculate readability score (0-100)
    score = 100
    if avg_words_per_sentence > 20:
        score -= (avg_words_per_sentence - 20) * 2
    if avg_words_per_paragraph > 150:
        score -= (avg_words_per_paragraph - 150) * 0.5
    if transition_count < len(sentences) * 0.1:
        score -= 10
    
    score = max(0, min(100, score))  # Clamp between 0-100
    
    return score, suggestions

def validate_seo_requirements(content: str, keywords: list) -> tuple[bool, list[str]]:
    """
    Validate that content meets SEO requirements
    Returns (is_valid, list_of_issues)
    """
    issues = []
    word_count = len(content.split())
    
    # Check minimum word count
    if word_count < 2500:
        issues.append(f"Content is too short ({word_count} words). Minimum 2500 words required.")
    elif word_count > 5000:
        issues.append(f"Content is too long ({word_count} words). Maximum 5000 words recommended.")
    
    # Check heading structure
    h2_count = content.count('<h2')
    h3_count = content.count('<h3')
    if h2_count < 4:
        issues.append(f"Not enough H2 sections ({h2_count}). Need 4-5 sections.")
    if h3_count < h2_count * 2:
        issues.append(f"Not enough H3 subsections ({h3_count}). Need 2-3 per H2.")
    
    # Check for tables
    table_count = content.count('<table')
    if table_count < 1:
        issues.append("Missing data tables. Need 1-2 tables.")
    
    # Check for bullet points
    if '<ul' not in content and '<ol' not in content:
        issues.append("Missing bullet-point lists.")
    
    # Check FAQ section
    if '<h2>FAQ' not in content and '<h2>Frequently Asked Questions' not in content:
        issues.append("Missing FAQ section.")
    
    # Check keyword optimization
    for kw in keywords[:3]:  # Check main keywords
        kw_count = content.lower().count(kw.lower())
        if kw_count < 3:
            issues.append(f"Keyword '{kw}' not used enough ({kw_count} times)")
        elif kw_count > word_count * 0.02:  # More than 2% density
            issues.append(f"Keyword '{kw}' used too much ({kw_count} times). Avoid keyword stuffing.")
    
    # Check internal links
    if 'dunemedicaldevicesinc.com' not in content:
        issues.append("Missing internal links to main site.")
    if 'dunemedicaldevicesinc.com/shop-2/' not in content:
        issues.append("Missing CTA link to shop.")
    if 'dunemedicaldevicesinc.com/contact-us/' not in content:
        issues.append("Missing contact page link.")
    
    # Check outbound links
    outbound_valid, outbound_issues, domains = validate_outbound_links(content)
    if not outbound_valid:
        issues.extend(outbound_issues)
    
    # Check schema markup
    if 'application/ld+json' not in content:
        issues.append("Missing FAQ schema markup.")
    
    return len(issues) == 0, issues

def generate_seo_content(title, description, keywords):
    """Generate SEO-optimized content using DeepSeek"""
    
    # First, search for relevant authoritative links
    print("Searching for relevant authoritative sources...")
    try:
        authoritative_links = deepseek.search_authoritative_links(
            query=title,
            topic_keywords=keywords,
            num_results=5  # Get top 5 most relevant links
        )
    except Exception as e:
        print(f"Warning: Failed to fetch authoritative links: {str(e)}")
        authoritative_links = []
    
    # Format the links for inclusion in the prompt
    link_references = ""
    if authoritative_links:
        link_references = "\nUse these authoritative sources in your article:\n"
        for link in authoritative_links:
            link_references += f"- {link['url']} - {link['title']}\n  {link['snippet']}\n"
    
    system_prompt = f"""You are an advanced SEO content writer specializing in creating first-page Google ranking content. Follow these guidelines:
                Requirements:
    1. 2500-5000 words total
    2. Include 4-5 H2 sections with 2-3 H3 subsections each
    3. Add 1-2 tables with relevant data (HTML format)
    4. Include bullet-point lists where appropriate
    5. Create FAQ section with 5 questions and answers with proper schema markup
    6. Optimize for keyword: {keywords[0] if keywords else title.split()[0]}
    7. Add internal links to https://dunemedicaldevicesinc.com
    8. Use this CTA: "Visit https://dunemedicaldevicesinc.com/shop-2/ for more insights" 
    9. Format in clean HTML without <html> or <body> tags
    10. Humanize the content with a friendly, professional tone
    11. ensure that you convince your reader that they will become wealthy and successful by following the advice in this article
    12. ensure that convince your readers to contact this website for more information: https://dunemedicaldevicesinc.com/contact-us/
    13. Add proper FAQ schema markup in application/ld+json format
    14. Use the provided authoritative sources to support your content:
        - Cite these sources when making factual claims or using statistics
        - Include proper HTML links with descriptive anchor text
        - Use direct quotes when appropriate
        - Integrate citations naturally into the content{link_references}
    
    Output must be ready for WordPress publishing with proper HTML formatting."""
    
    user_prompt = f"""Create a comprehensive, SEO-optimized blog post about: {title}
                Description: {description}
                Primary Keyword: {keywords[0] if keywords else title.split()[0]}
                Secondary Keywords: {', '.join(keywords[1:]) if len(keywords) > 1 else ', '.join(title.split()[1:3])}
                Include:
                - Introduction with hook and thesis
                - Detailed sections with examples
                - Data tables where relevant
                - Comparison tables if applicable
                - Step-by-step guides if relevant
                - Conclusion with summary and CTA
                - FAQ section with schema markup"""
                
    try:
        return deepseek.generate_content(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=8000
        )
    except DeepSeekAPIError as e:
        logging.error(f"Failed to generate content: {str(e)}")
        raise

def extract_keywords(text):
    """Extract relevant keywords from text using DeepSeek"""
    try:
        response = deepseek.generate_content(
            prompt=f"Extract keywords from: {text}",
            system_prompt="You are an SEO expert that extracts 5-7 most relevant keywords from a given text, ordered by importance. Return only a comma-separated list of keywords.",
            temperature=0.1,
            max_tokens=100
        )
        
        if response and ',' in response:
            keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
            if keywords:
                return keywords[:7]  # Return max 7 keywords
        
        # Fallback: Extract simple keywords from text
        words = text.lower().split()
        return list(set([w for w in words if len(w) > 3 and w.isalpha()]))[:5]
        
    except Exception as e:
        logging.error(f"Failed to extract keywords: {str(e)}")
        # Fallback: Use first 3 words
        return text.split()[:3]

def generate_meta_tags(title: str, description: str, keywords: list, content: str) -> dict:
    """
    Generate optimized meta tags for SEO
    Returns dict with meta tag values
    """
    try:
        prompt = f"""Generate optimized meta tags for this article:
        Title: {title}
        Description: {description}
        Keywords: {', '.join(keywords)}
        Content Length: {len(content.split())} words
        
        Requirements:
        1. Meta title: 50-60 chars, include main keyword naturally
        2. Meta description: 150-160 chars, compelling call-to-action
        3. Open Graph title: Similar to meta title but more engaging
        4. Open Graph description: Similar to meta description but more social-friendly
        5. Twitter card title/description: Optimize for Twitter sharing
        6. Include target keyword naturally in all elements
        
        Format as JSON object with these keys:
        - meta_title
        - meta_description 
        - og_title
        - og_description
        - twitter_title 
        - twitter_description"""
        
        response = deepseek.generate_content(
            prompt=prompt,
            temperature=0.3,
            max_tokens=500
        )
        
        # Parse JSON response
        import json
        meta_tags = json.loads(response)
        
        # Validate lengths
        meta_tags['meta_title'] = meta_tags['meta_title'][:60]
        meta_tags['meta_description'] = meta_tags['meta_description'][:160]
        meta_tags['og_title'] = meta_tags['og_title'][:95]
        meta_tags['og_description'] = meta_tags['og_description'][:200]
        meta_tags['twitter_title'] = meta_tags['twitter_title'][:70]
        meta_tags['twitter_description'] = meta_tags['twitter_description'][:200]
        
        return meta_tags
        
    except Exception as e:
        logging.warning(f"Failed to generate meta tags: {str(e)}")
        return {
            'meta_title': title[:60],
            'meta_description': description[:160],
            'og_title': title[:95],
            'og_description': description[:200],
            'twitter_title': title[:70],
            'twitter_description': description[:200]
        }

def post_to_wordpress(title, content, description, slug, featured_image_id=None, keywords=None):
    headers = {
        'Authorization': 'Basic ' + base64.b64encode(f'{WORDPRESS_USERNAME}:{WORDPRESS_PASSWORD}'.encode('utf-8')).decode('utf-8'),
        'Content-Type': 'application/json'
    }
    # Get primary keyword from title if no keywords are provided
    primary_keyword = keywords[0] if keywords else title.split()[0]
    
    # Get site name from WordPress URL
    site_name = "Dune Medical Devices"
    if WORDPRESS_URL:
        try:
            site_name = WORDPRESS_URL.split('//')[1].split('/')[0]
        except (IndexError, AttributeError):
            pass
    
    post_data = {
        "title": title,
        "content": content,
        "status": "publish",
        "excerpt": description,
        "slug": slug,
        "meta": {
            "_yoast_wpseo_focuskw": primary_keyword,
            "_yoast_wpseo_metadesc": description,
            "_yoast_wpseo_title": f"{title} | {site_name}",
            "_yoast_wpseo_opengraph-title": title,
            "_yoast_wpseo_opengraph-description": description,
            "_yoast_wpseo_twitter-title": title,
            "_yoast_wpseo_twitter-description": description
        }
    }
    if featured_image_id:
        post_data["featured_media"] = featured_image_id
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f'{WORDPRESS_URL}/posts',
                                  headers=headers,
                                  json=post_data,
                                  timeout=30)
            if response.status_code == 201:
                return response.json()['id']
            elif response.status_code == 401:
                raise Exception("Invalid WordPress credentials - please check username/password")
            elif response.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            else:
                raise Exception(f"WordPress Error {response.status_code}: {response.text}")
        except (requests.exceptions.RequestException, KeyboardInterrupt) as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to post after {max_retries} attempts: {str(e)}")
            time.sleep(5 * (attempt + 1))

def validate_wordpress_url(url):
    """Validate that the provided URL is a valid WordPress REST API endpoint"""
    if not url:
        return False
        
    try:
        # Try to access the root API endpoint
        response = requests.get(
            url.replace('/wp/v2', ''),  # Get the base API URL
            timeout=10
        )
        
        # Check if we got any JSON response
        if response.status_code == 200:
            try:
                data = response.json()
                # Verify this is a WordPress API
                if isinstance(data, dict) and data.get('namespace') == 'wp/v2':
                    return True
            except (ValueError, KeyError):
                pass
                
        return False
    except requests.RequestException:
        return False

def validate_wordpress_credentials():
    """Validate WordPress credentials by testing multiple API endpoints"""
    # First validate the URL
    if not validate_wordpress_url(WORDPRESS_URL):
        print("\nERROR: Invalid WordPress API URL")
        print("Please verify:")
        print(f"1. URL: {WORDPRESS_URL}")
        print("2. URL should end with /wp-json/wp/v2")
        print("3. WordPress REST API is enabled")
        return False
    
    headers = {
        'Authorization': 'Basic ' + base64.b64encode(f'{WORDPRESS_USERNAME}:{WORDPRESS_PASSWORD}'.encode('utf-8')).decode('utf-8'),
        'Content-Type': 'application/json'
    }
    
    endpoints = [
        '/posts?per_page=1',
        '/settings',
        '/categories',
        '/users/me'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'{WORDPRESS_URL}{endpoint}',
                                  headers=headers,
                                  timeout=10)
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                print("\nERROR: Invalid WordPress credentials")
                print("Please verify:")
                print(f"1. URL: {WORDPRESS_URL}")
                print(f"2. Username: {WORDPRESS_USERNAME}")
                print("3. Application Password is correct")
                print("\nTo create an Application Password:")
                return False
            elif response.status_code == 404:
                print(f"\nWARNING: Endpoint not found: {endpoint}")
                continue
        except requests.exceptions.RequestException as e:
            print(f"\nERROR: Could not connect to endpoint {endpoint} - {str(e)}")
            continue
    print("\nERROR: Could not validate WordPress credentials")
    print("Possible causes:")
    print("1. WordPress REST API is disabled")
    print("2. Security plugins are blocking API access")
    print("3. Permalinks need to be reset (Settings → Permalinks → Save)")
    # Format WordPress base URL
    wp_base_url = ""
    if WORDPRESS_URL:
        wp_base_url = WORDPRESS_URL.replace('/wp-json/wp/v2', '')
    
    print("\nTest these endpoints manually in your browser:")
    for endpoint in ['/posts?per_page=1', '/settings', '/categories', '/users/me']:
        print(f"{wp_base_url}/wp-json/wp/v2{endpoint}")
    print("\nTo create an Application Password:")
    print("1. Go to WordPress Users → Edit your profile")
    print("2. Scroll to 'Application Passwords' section")
    print("3. Create a new password and use it here")
    return False

def main():
    # Initialize our analyzers
    content_analyzer = ContentAnalyzer()
    image_optimizer = ImageOptimizer()
    
    # Validate WordPress credentials before starting
    if not validate_wordpress_credentials():
        return

    # Check if input CSV exists
    if not os.path.exists('input.csv'):
        print("Error: input.csv file not found.")
        print("Create a CSV file with columns: 'URL Slug', 'Meta Title', 'Description'")
        return

    # Read input CSV with encoding detection
    try:
        # Detect file encoding
        with open('input.csv', 'rb') as f:
            rawdata = f.read()
            result = chardet.detect(rawdata)
            encoding = result['encoding'] or 'utf-8'
        
        # Read CSV with detected encoding
        df = pd.read_csv('input.csv', encoding=encoding)
        required_columns = {'URL Slug', 'Meta Title', 'Description'}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise Exception(f"Missing required columns: {', '.join(missing)}")
    except Exception as e:
        print(f"Error reading input.csv: {str(e)}")
        print(f"Detected encoding: {encoding}")
        return

    # Prepare output dataframe
    output_columns = [
        'URL Slug', 
        'Meta Title', 
        'Description', 
        'Keywords', 
        'Blog Content', 
        'WordPress ID',
        'Featured Image ID',
        'Image Prompt'
    ]
    output_df = pd.DataFrame(columns=output_columns)

    # Create output directory for images
    os.makedirs('generated_images', exist_ok=True)

    # Process each row
    for index, row in tqdm(df.iterrows(), total=len(df), desc='Generating blog posts'):
        try:
            # Extract keywords from title and description
            keywords = extract_keywords(f"{row['Meta Title']}. {row['Description']}")

            # Search and download image
            featured_image_id = None
            image_saved_path = None
            image_source_url = None
            
            try:
                print(f"\nSearching for image: {row['Meta Title']}")
                image_bytes, source_url = search_and_download_image(
                    title=row['Meta Title'],
                    description=row['Description'],
                    keywords=keywords
                )
                
                if image_bytes:
                    # Save image locally with attribution
                    image_filename = f"generated_images/{slugify(row['Meta Title'])}.jpg"
                    with open(image_filename, 'wb') as f:
                        f.write(image_bytes)
                    image_saved_path = os.path.abspath(image_filename)
                    
                    # Save attribution info
                    attr_filename = f"generated_images/{slugify(row['Meta Title'])}_attribution.txt"
                    with open(attr_filename, 'w', encoding='utf-8') as f:
                        f.write(f"Image source: {source_url}\n")
                        f.write(f"Downloaded on: {time.ctime()}\n")
                        f.write(f"Used in article: {row['Meta Title']}\n")
                    
                    # Upload to WordPress with attribution in alt text
                    featured_image_id = upload_image_to_wordpress(
                        image_bytes=image_bytes,
                        title=row['Meta Title'],
                        alt_text=f"Featured image for {row['Meta Title']} (Source: {source_url})"
                    )
                    print(f"Uploaded featured image (ID: {featured_image_id})")
                    image_source_url = source_url
                else:
                    print("No suitable image found")
            except Exception as e:
                print(f"Error in image search/download/upload: {str(e)}")

            # Generate SEO-optimized content
            print(f"Generating content for: {row['Meta Title']}")
            content = generate_seo_content(
                title=row['Meta Title'],
                description=row['Description'],
                keywords=keywords
            )

            # Validate SEO requirements before posting
            print("\nValidating SEO requirements...")
            is_valid, issues = validate_seo_requirements(content, keywords)
            
            if not is_valid:
                print("\nSEO validation failed. Issues found:")
                for issue in issues:
                    print(f"- {issue}")
                print("\nRegenerating content with stricter requirements...")
                content = generate_seo_content(
                    title=row['Meta Title'],
                    description=row['Description'],
                    keywords=keywords
                )
                # Validate again
                is_valid, issues = validate_seo_requirements(content, keywords)
                if not is_valid:
                    print("\nWARNING: Content still has SEO issues:")
                    for issue in issues:
                        print(f"- {issue}")
                    
            # Generate meta tags
            print("\nGenerating optimized meta tags...")
            meta_tags = generate_meta_tags(
                title=row['Meta Title'],
                description=row['Description'],
                keywords=keywords,
                content=content
            )
            
            # Generate image metadata if we have an image
            if image_source_url and featured_image_id:
                print("\nGenerating image metadata...")
                alt_text, caption = generate_image_metadata(
                    image_url=image_source_url,
                    title=row['Meta Title'],
                    keywords=keywords
                )
            else:
                alt_text, caption = row['Meta Title'], ""
            
            # Check readability
            print("\nAnalyzing content readability...")
            readability_score, readability_suggestions = analyze_readability(content)
            print(f"Readability score: {readability_score:.1f}/100")
            if readability_suggestions:
                print("\nReadability suggestions:")
                for suggestion in readability_suggestions:
                    print(f"- {suggestion}")
                
                if readability_score < 70:
                    print("\nRegenerating content to improve readability...")
                    content = generate_seo_content(
                        title=row['Meta Title'],
                        description=row['Description'],
                        keywords=keywords
                    )
                    readability_score, _ = analyze_readability(content)
                    print(f"New readability score: {readability_score:.1f}/100")
            
            # Post to WordPress
            print(f"\nPublishing post: {row['Meta Title']}")
            post_id = post_to_wordpress(
                title=row['Meta Title'],
                content=content,
                description=row['Description'],
                slug=row['URL Slug'],
                featured_image_id=featured_image_id,
                keywords=keywords
            )

            # Save results
            # Create a row dictionary for clean DataFrame update
            row_data = {
                'URL Slug': row['URL Slug'],
                'Meta Title': row['Meta Title'],
                'Description': row['Description'],
                'Keywords': ', '.join(keywords),
                'Blog Content': content,
                'WordPress ID': post_id,
                'Featured Image ID': featured_image_id,
                'Image Source URL': image_source_url or ''
            }
            # Add the row to DataFrame
            for col, value in row_data.items():
                output_df.at[index, col] = value

            # Save progress after each post
            output_df.to_csv('output.csv', index=False)
            if image_saved_path:
                print(f"Image saved to: {image_saved_path}")

            # Rate limiting
            print("Waiting 45 seconds before next post...")
            time.sleep(45)
            
        except Exception as e:
            print(f"\nError processing row {index}: {str(e)}")
            # Save error to log
            with open('error_log.txt', 'a') as f:
                f.write(f"\n{time.ctime()} - Row {index} - {str(e)}")
            continue

    print("\nProcess completed!")
    print(f"Results saved to output.csv")
    print(f"Generated images saved to generated_images/ directory")

if __name__ == "__main__":
    main()
