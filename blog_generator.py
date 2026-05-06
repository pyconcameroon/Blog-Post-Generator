"""Main blog post generator class"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import os
import re
from datetime import datetime
from config import Config
from logger import Logger
from wordpress_client import WordPressClient
from deepseek_client import DeepSeekClient
from content_analyzer import ContentAnalyzer
from image_optimizer import ImageOptimizer

class BlogPostGenerator:
    def __init__(self):
        # Initialize configuration
        self.config = Config()
        valid, issues = self.config.validate()
        if not valid:
            raise ValueError(f"Invalid configuration: {', '.join(issues)}")
        
        # Initialize components
        self.logger = Logger()
        self.wordpress = WordPressClient(
            url=self.config.wordpress_url,
            username=self.config.wordpress_username,
            password=self.config.wordpress_password,
            logger=self.logger
        )
        self.deepseek = DeepSeekClient(api_key=self.config.deepseek_api_key)
        self.content_analyzer = ContentAnalyzer()
        self.image_optimizer = ImageOptimizer()
        
        # Set up image directory
        self.image_directory = "generated_images"
        
        # Initialize image sitemap tracking
        self.uploaded_images = []
        self.sitemap_path = "image_sitemap.xml"
        
        # Cache for existing posts (for internal linking)
        self._existing_posts_cache = None
        
    def process_csv(self, csv_path: str) -> None:
        """Process input CSV file and generate image sitemaps"""
        try:
            # Read and validate CSV
            df = self._read_csv(csv_path)
            self._validate_csv_columns(df)
            
            self.logger.info(f"Starting to process {len(df)} blog posts...")
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    self._process_single_post(row)
                except Exception as e:
                    self.logger.error(f"Failed to process row {index}: {str(e)}")
            
            # Generate image sitemaps after all posts are processed
            self.logger.info("All posts processed. Generating image sitemaps...")
            self._generate_all_sitemaps()
                    
        except Exception as e:
            self.logger.error(f"Failed to process CSV: {str(e)}")

    def _generate_all_sitemaps(self):
        """Generate all image sitemaps and update robots.txt"""
        try:
            if not self.uploaded_images:
                self.logger.warning("No images uploaded, skipping sitemap generation")
                return
            
            # Generate simple image sitemap
            simple_sitemap = self.generate_image_sitemap()
            
            # Generate comprehensive sitemap
            comprehensive_sitemap = self.generate_comprehensive_image_sitemap()
            
            # Update robots.txt
            robots_file = self.update_robots_txt()
            
            # Log summary
            self.logger.info(f"Sitemap generation complete:")
            self.logger.info(f"  - Simple sitemap: {simple_sitemap}")
            self.logger.info(f"  - Comprehensive sitemap: {comprehensive_sitemap}")
            self.logger.info(f"  - Robots.txt updated: {robots_file}")
            self.logger.info(f"  - Total images tracked: {len(self.uploaded_images)}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate sitemaps: {e}")
    
    def _read_csv(self, csv_path: str) -> pd.DataFrame:
        """Read CSV file with encoding detection"""
        import chardet
        
        with open(csv_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
        
        return pd.read_csv(csv_path, encoding=encoding)
    
    def _validate_csv_columns(self, df: pd.DataFrame) -> None:
        """Validate required CSV columns"""
        required_columns = {'URL Slug', 'Meta Title', 'Description'}
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
    
    def _process_single_post(self, row: pd.Series) -> None:
        """Process a single blog post"""
        try:
            self.logger.info(f"Processing: {row['Meta Title']}")
            
            # Extract keywords
            keywords = self._extract_keywords(row['Meta Title'], row['Description'])
            
            # Generate content with retry on timeout
            max_attempts = 3
            content = None
            
            for attempt in range(max_attempts):
                try:
                    content = self._generate_content(row['Meta Title'], row['Description'], keywords)
                    break  # Success, exit retry loop
                except Exception as e:
                    error_msg = str(e)
                    if "timeout" in error_msg.lower() or "timeouterror" in error_msg.lower():
                        self.logger.warning(f"Timeout on attempt {attempt + 1}/{max_attempts} for '{row['Meta Title']}'")
                        if attempt == max_attempts - 1:
                            self.logger.error(f"Failed after {max_attempts} attempts due to timeout: {row['Meta Title']}")
                            return  # Skip this article
                        # Wait before retry
                        import time
                        time.sleep(10 * (attempt + 1))  # Exponential backoff
                    else:
                        raise  # Re-raise non-timeout errors
            
            if content is None:
                self.logger.error(f"No content generated for: {row['Meta Title']}")
                return

            # SEO Optimization (fast but comprehensive)
            optimized_content = self._optimize_content_for_seo(content, keywords, row['Meta Title'])
            
            # Generate meta tags with proper length validation
            meta_tags = self._generate_seo_meta_tags(optimized_content, row['Meta Title'], row['Description'], keywords)
            
            # Handle images with alt tags
            featured_image_id = self._handle_seo_images(row['Meta Title'], keywords)

            # Post to WordPress with full SEO
            self._post_to_wordpress(
                title=row['Meta Title'],
                content=optimized_content,
                description=row['Description'],
                slug=row['URL Slug'],
                meta_tags=meta_tags,
                featured_image_id=featured_image_id
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process row {row.name}: {str(e)}")
            # Continue processing other rows
    
    def _extract_keywords(self, title: str, description: str) -> List[str]:
        """Extract keywords from title and description

        Returns a list of keyword strings. The content analyzer may return
        (keyword, score) tuples, so convert them to plain strings. If any
        error occurs, return an empty list to allow processing to continue.
        """
        try:
            raw_keywords = self.content_analyzer.extract_keywords(f"{title}. {description}")
            return [kw for kw, _ in raw_keywords]
        except Exception:
            # If keyword extraction fails, log a warning and continue with empty list
            self.logger.warning("Keyword extraction failed; continuing with no keywords")
            return []
    
    def _generate_content(self, title: str, description: str, keywords: List[str]) -> str:
        """Generate blog post content with fallback"""
        try:
            # Build the prompt for content generation with strict style guidelines
            prompt = f"""Generate comprehensive, detailed blog content for:
Title: {title}
Description: {description}
Keywords: {', '.join(keywords)}

CONTENT LENGTH REQUIREMENT: Generate 4000-5000 words of detailed, comprehensive content with multiple sections and subsections.

STRICT WRITING STYLE REQUIREMENTS:
- Use clear, simple language
- Be spartan and informative
- Use short, impactful sentences
- Use active voice, avoid passive voice
- Focus on practical, actionable insights
- Use "you" and "your" to directly address the reader
- Include detailed sections: buying guide, performance analysis, maintenance tips, cost considerations, safety standards
- Add comprehensive subsections with specific details and examples
- AVOID em dashes, use commas or periods only
- AVOID markdown formatting, asterisks, hashtags
- AVOID these words: can, may, just, that, very, really, literally, actually, certainly, probably, basically, could, maybe, delve, embark, enlightening, esteemed, shed light, craft, crafting, imagine, realm, game-changer, unlock, discover, skyrocket, abyss, not alone, in a world where, revolutionize, disruptive, utilize, utilizing, dive deep, tapestry, illuminate, unveil, pivotal, intricate, elucidate, hence, furthermore, realm, however, harness, exciting, groundbreaking, cutting-edge, remarkable, it, remains to be seen, glimpse into, navigating, landscape, stark, testament, in summary, in conclusion, moreover, boost, skyrocketing, opened up, powerful, inquiries, ever-evolving
- AVOID constructions like "not just this, but also this"
- AVOID metaphors and clichés
- AVOID generalizations
- AVOID setup language like "in conclusion", "in closing"
- AVOID semicolons
- Use data and examples when possible
- Output clean HTML with proper headings (h1, h2, h3)
- Include detailed lists, explanations, and step-by-step guides
"""
            content = self.deepseek.generate_content(prompt=prompt)
            cleaned_content = self._clean_content_formatting(content)
            
            # Content length optimization - expand to 5000+ words if needed
            optimized_content = self._optimize_content_length(cleaned_content, title, keywords, target_words=5000)
            
            return optimized_content
            
        except Exception as e:
            self.logger.error(f"DeepSeek API failed: {str(e)}")
            self.logger.info("Using fallback content generation...")
            fallback_content = self._generate_fallback_content(title, description, keywords)
            
            # Apply length optimization to fallback content too
            return self._optimize_content_length(fallback_content, title, keywords, target_words=5000)
    
    def _clean_content_formatting(self, content: str) -> str:
        """Clean content to remove unwanted formatting characters and follow style guidelines"""
        try:
            # Remove markdown formatting
            content = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong>\1</strong>', content)  # Bold
            content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)     # Bold
            content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)                 # Italic
            
            # Convert markdown headers to HTML
            content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
            content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
            content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
            
            # Convert markdown lists to HTML
            content = re.sub(r'^- (.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
            content = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', content, flags=re.MULTILINE)
            
            # Wrap consecutive list items in ul/ol tags
            content = re.sub(r'(<li>.*?</li>)(\n<li>.*?</li>)*', lambda m: f'<ul>{m.group(0).replace(chr(10), "")}</ul>', content)
            
            # Clean up any remaining asterisks or hash symbols
            content = re.sub(r'\*+', '', content)
            content = re.sub(r'#+', '', content)
            
            # Remove em dashes and replace with commas or periods
            content = content.replace('—', ', ')
            content = content.replace('–', ', ')
            
            # Remove forbidden words and phrases (case insensitive)
            forbidden_words = [
                'can', 'may', 'just', 'that', 'very', 'really', 'literally', 'actually',
                'certainly', 'probably', 'basically', 'could', 'maybe', 'delve', 'embark',
                'enlightening', 'esteemed', 'shed light', 'craft', 'crafting', 'imagine',
                'realm', 'game-changer', 'unlock', 'discover', 'skyrocket', 'abyss',
                'not alone', 'in a world where', 'revolutionize', 'disruptive', 'utilize',
                'utilizing', 'dive deep', 'tapestry', 'illuminate', 'unveil', 'pivotal',
                'intricate', 'elucidate', 'hence', 'furthermore', 'however', 'harness',
                'exciting', 'groundbreaking', 'cutting-edge', 'remarkable', 'remains to be seen',
                'glimpse into', 'navigating', 'landscape', 'stark', 'testament',
                'in summary', 'in conclusion', 'moreover', 'boost', 'skyrocketing',
                'opened up', 'powerful', 'inquiries', 'ever-evolving'
            ]
            
            # Replace forbidden phrases with neutral alternatives
            replacements = {
                'can ': 'will ',
                'may ': 'might ',
                'just ': '',
                'very ': '',
                'really ': '',
                'actually ': '',
                'basically ': '',
                'could ': 'might ',
                'in conclusion': 'to summarize',
                'however,': 'but',
                'furthermore,': 'also,',
                'moreover,': 'also,',
                'utilize': 'use',
                'utilizing': 'using'
            }
            
            for old, new in replacements.items():
                content = re.sub(old, new, content, flags=re.IGNORECASE)
            
            # Wrap paragraphs in HTML p tags
            paragraphs = content.split('\n\n')
            clean_paragraphs = []
            for para in paragraphs:
                para = para.strip()
                if para and not para.startswith('<'):
                    para = f'<p>{para}</p>'
                if para:
                    clean_paragraphs.append(para)
            
            content = '\n\n'.join(clean_paragraphs)
            
            # Final cleanup
            content = re.sub(r'\n+', '\n', content)  # Remove extra newlines
            content = content.strip()
            
            return content
            
        except Exception as e:
            self.logger.warning(f"Content cleaning failed: {e}")
            return content

    def _optimize_content_length(self, content: str, title: str, keywords: List[str], target_words: int = 5000) -> str:
        """Automatically expand content to reach target word count for better SEO"""
        try:
            # Count current words
            current_words = len(content.split())
            self.logger.info(f"Current content length: {current_words} words")
            
            if current_words >= target_words:
                self.logger.info(f"Content already meets target length ({target_words} words)")
                return content
            
            words_needed = target_words - current_words
            self.logger.info(f"Expanding content by {words_needed} words to reach {target_words} words")
            
            # Generate additional sections to expand the content
            expanded_content = content
            main_keyword = keywords[0] if keywords else title.split()[0]
            
            # Add comprehensive sections for length expansion
            expansion_sections = self._generate_expansion_sections(title, main_keyword, keywords)
            
            for section_title, section_content in expansion_sections:
                expanded_content += f"\n\n<h2>{section_title}</h2>\n{section_content}"
                
                # Check if we've reached target length
                if len(expanded_content.split()) >= target_words:
                    break
            
            # Final word count check
            final_words = len(expanded_content.split())
            self.logger.info(f"Final content length: {final_words} words (target: {target_words})")
            
            return expanded_content
            
        except Exception as e:
            self.logger.warning(f"Content length optimization failed: {e}")
            return content

    def _generate_expansion_sections(self, title: str, main_keyword: str, keywords: List[str]) -> List[tuple]:
        """Generate additional sections to expand content length"""
        sections = []
        
        # Detailed buying guide section
        sections.append((
            f"Complete {main_keyword} Buying Guide",
            f"""<p>When shopping for {main_keyword}, you need to consider multiple factors to make the right choice. Your decision impacts safety, performance, and long-term value.</p>

<h3>Research Phase</h3>
<p>Start by identifying your specific needs. Consider your vehicle type, driving conditions, and budget constraints. Research different brands and read professional reviews.</p>

<ul>
<li>Compare specifications across multiple brands</li>
<li>Read customer reviews and expert opinions</li>
<li>Check warranty coverage and terms</li>
<li>Evaluate long-term value propositions</li>
</ul>

<h3>Selection Criteria</h3>
<p>Focus on these key selection criteria:</p>

<ul>
<li>Performance ratings and test results</li>
<li>Durability and expected lifespan</li>
<li>Price point and value analysis</li>
<li>Brand reputation and support</li>
<li>Availability and local service options</li>
</ul>"""
        ))
        
        # Performance and testing section
        sections.append((
            f"Performance Testing and Analysis",
            f"""<p>Understanding performance metrics helps you make informed decisions about {main_keyword}. Professional testing provides objective data for comparison.</p>

<h3>Test Categories</h3>
<p>Industry testing covers multiple performance areas:</p>

<ul>
<li>Safety performance under various conditions</li>
<li>Durability testing over extended periods</li>
<li>Environmental impact assessments</li>
<li>Real-world performance validation</li>
</ul>

<h3>Measurement Standards</h3>
<p>Professional testing follows standardized protocols. These standards ensure consistent and reliable results across different products and brands.</p>

<p>Test results help you understand expected performance in your specific use conditions. Compare test data from multiple sources for comprehensive evaluation.</p>"""
        ))
        
        # Maintenance and care section
        sections.append((
            f"Maintenance and Care Guide",
            f"""<p>Proper maintenance extends the life of your {main_keyword} and ensures optimal performance. Follow these essential maintenance practices.</p>

<h3>Regular Inspection Schedule</h3>
<p>Establish a routine inspection schedule to identify potential issues early:</p>

<ul>
<li>Visual inspection for wear patterns</li>
<li>Performance monitoring during use</li>
<li>Documentation of maintenance activities</li>
<li>Professional inspection when needed</li>
</ul>

<h3>Preventive Maintenance</h3>
<p>Preventive maintenance prevents costly repairs and replacements:</p>

<ul>
<li>Follow manufacturer recommendations</li>
<li>Use appropriate tools and materials</li>
<li>Keep detailed maintenance records</li>
<li>Address minor issues promptly</li>
</ul>

<h3>Professional Service</h3>
<p>Some maintenance tasks require professional expertise. Know when to seek professional service and choose qualified service providers.</p>"""
        ))
        
        # Cost analysis section
        sections.append((
            f"Cost Analysis and Value Considerations",
            f"""<p>Understanding the total cost of ownership helps you make financially sound decisions about {main_keyword}. Consider both initial costs and long-term expenses.</p>

<h3>Initial Investment</h3>
<p>The purchase price represents your initial investment:</p>

<ul>
<li>Base product pricing across brands</li>
<li>Additional features and options</li>
<li>Installation and setup costs</li>
<li>Warranty and service packages</li>
</ul>

<h3>Operating Costs</h3>
<p>Factor in ongoing operational expenses:</p>

<ul>
<li>Regular maintenance requirements</li>
<li>Replacement part availability and pricing</li>
<li>Energy efficiency and consumption</li>
<li>Service and support costs</li>
</ul>

<h3>Value Assessment</h3>
<p>Calculate the total value proposition by comparing costs against benefits. Consider performance improvements, safety enhancements, and longevity when evaluating value.</p>"""
        ))
        
        # Safety and regulations section
        sections.append((
            f"Safety Standards and Regulations",
            f"""<p>Safety standards ensure {main_keyword} meets minimum performance requirements. Understanding these standards helps you make informed safety decisions.</p>

<h3>Industry Standards</h3>
<p>Multiple organizations establish safety standards:</p>

<ul>
<li>Federal safety requirements and regulations</li>
<li>Industry association standards</li>
<li>International safety protocols</li>
<li>Professional certification programs</li>
</ul>

<h3>Compliance Verification</h3>
<p>Verify that products meet applicable safety standards:</p>

<ul>
<li>Check certification marks and documentation</li>
<li>Review testing reports and results</li>
<li>Confirm compliance with local regulations</li>
<li>Understand warranty implications</li>
</ul>

<h3>Safety Best Practices</h3>
<p>Follow safety best practices during installation, use, and maintenance. Proper safety procedures protect you and others while ensuring optimal performance.</p>"""
        ))
        
        # Future trends section
        sections.append((
            f"Future Trends and Technology",
            f"""<p>Technology advances continue to improve {main_keyword} performance and capabilities. Stay informed about emerging trends and innovations.</p>

<h3>Technology Developments</h3>
<p>Current technology trends include:</p>

<ul>
<li>Advanced materials and manufacturing processes</li>
<li>Smart technology integration</li>
<li>Environmental sustainability improvements</li>
<li>Performance optimization systems</li>
</ul>

<h3>Market Evolution</h3>
<p>The market continues to evolve with new products and features:</p>

<ul>
<li>Emerging brand competition</li>
<li>Price point diversification</li>
<li>Service model innovations</li>
<li>Consumer preference shifts</li>
</ul>

<h3>Future Considerations</h3>
<p>Plan for future needs when making current decisions. Consider upgrade paths, compatibility requirements, and long-term technology trends.</p>"""
        ))
        
        return sections

    def _generate_fallback_content(self, title: str, description: str, keywords: List[str]) -> str:
        """Generate fallback content following strict style guidelines"""
        keyword_list = keywords[:5] if keywords else ["key topics"]
        main_keyword = keyword_list[0]
        
        return f"""<h1>{title}</h1>

<h2>What You Need to Know</h2>

<p>{description}</p>

<p>This guide covers {main_keyword} in detail. You will learn practical steps to make informed decisions.</p>

<h2>Key Areas We Cover</h2>

<ul>
{chr(10).join([f"<li>{kw}</li>" for kw in keyword_list])}
</ul>

<h2>Your Action Plan</h2>

<p>When choosing {main_keyword}, follow these steps:</p>

<ol>
<li>Define your specific needs</li>
<li>Research available options</li>
<li>Compare features and prices</li>
<li>Read user reviews</li>
<li>Make your decision</li>
</ol>

<h2>Benefits You Get</h2>

<p>Quality {main_keyword} provides these advantages:</p>

<ul>
<li>Better performance for your needs</li>
<li>Long-term value and durability</li>
<li>Reliable operation</li>
<li>Professional results</li>
</ul>

<h2>Expert Tips</h2>

<p>Industry professionals recommend these approaches:</p>

<ul>
<li>Research thoroughly before buying</li>
<li>Compare multiple options</li>
<li>Consider total cost of ownership</li>
<li>Seek expert advice when needed</li>
</ul>

<h2>Factors to Consider</h2>

<p>Evaluate these important aspects:</p>

<ul>
<li>Budget and cost requirements</li>
<li>Quality and durability needs</li>
<li>Specific use requirements</li>
<li>Maintenance and support needs</li>
</ul>

<h2>Best Practices</h2>

<p>Follow these proven strategies:</p>

<ol>
<li>Plan with clear objectives</li>
<li>Gather complete information</li>
<li>Evaluate all options</li>
<li>Make informed choices</li>
</ol>

<h2>Common Mistakes</h2>

<p>Avoid these frequent errors:</p>

<ul>
<li>Rushing important decisions</li>
<li>Ignoring quality for price</li>
<li>Forgetting future needs</li>
<li>Skipping professional advice</li>
</ul>

<h2>Final Thoughts</h2>

<p>Understanding {main_keyword} helps you make better decisions. This guide gives you the foundation for choosing the right option for your situation.</p>

<p>Focus on quality, value, and long-term satisfaction when making your choice.</p>

<h2>Frequently Asked Questions</h2>

<p><strong>Q: What factors should I prioritize?</strong><br>
A: Focus on quality, reliability, and value that matches your specific needs.</p>

<p><strong>Q: How do I compare different options?</strong><br>
A: Research thoroughly, read reviews, and consult with industry experts.</p>

<p><strong>Q: What are the most common mistakes?</strong><br>
A: Rushing decisions, ignoring quality, and failing to plan for future needs.</p>
"""
    
    def _validate_content(self, content: str, keywords: List[str]) -> None:
        """Validate generated content"""
        issues = []
        
        # Check word count
        word_count = len(content.split())
        min_words = self.config.content_settings['min_word_count']
        max_words = self.config.content_settings['max_word_count']
        
        if word_count < min_words:
            issues.append(f"Content too short: {word_count} words (min: {min_words})")
        elif word_count > max_words:
            issues.append(f"Content too long: {word_count} words (max: {max_words})")
        else:
            self.logger.info(f"Content length valid: {word_count} words (range: {min_words}-{max_words})")
        
        # Check keyword density (make this a warning, not an error)
        density_warnings = []
        for kw in keywords[:3]:
            # Handle multi-word keywords by checking individual words and full phrase
            content_lower = content.lower()
            kw_lower = kw.lower()
            
            # Count exact phrase matches
            exact_matches = content_lower.count(kw_lower)
            
            # For multi-word keywords, also count individual word occurrences
            if ' ' in kw_lower:
                word_matches = sum(content_lower.count(word.strip()) for word in kw_lower.split())
                # Use the higher count but cap it reasonably
                total_matches = max(exact_matches, min(word_matches, exact_matches + len(kw_lower.split()) * 2))
            else:
                total_matches = exact_matches
            
            density = total_matches / word_count if word_count > 0 else 0
            
            if density < self.config.seo_settings['min_keyword_density']:
                density_warnings.append(f"Low keyword density for '{kw}' (found: {density:.3f}, min: {self.config.seo_settings['min_keyword_density']:.3f})")
            elif density > self.config.seo_settings['max_keyword_density']:
                issues.append(f"Keyword stuffing detected for '{kw}' (found: {density:.3f}, max: {self.config.seo_settings['max_keyword_density']:.3f})")
        
        # Log keyword density warnings but don't fail validation
        if density_warnings:
            self.logger.warning("Keyword density issues: " + "; ".join(density_warnings))
        
        if issues:
            raise ValueError("Content validation failed: " + "; ".join(issues))
    
    def _handle_images(self, title: str, keywords: List[str]) -> Optional[int]:
        """Handle image search, optimization, and upload"""
        try:
            # Search for image using title and keywords in query
            search_query = f"{title} {' '.join(keywords[:3])}"
            image_list = self.deepseek.search_images(query=search_query)
            
            if not image_list:
                return None
            
            # Get first image URL from results
            image_url = image_list[0] if isinstance(image_list, list) else image_list
            
            # Download image bytes
            import requests
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                return None
            image_bytes = response.content
            
            # Optimize image
            optimized_bytes, mime_type = self.image_optimizer.optimize_image(image_bytes)
            
            # Generate alt text
            alt_text = self.image_optimizer.generate_alt_text(
                image_url=image_url, 
                title=title, 
                content_context=' '.join(keywords)
            )
            
            # Upload to WordPress
            return self.wordpress.upload_media(
                file_content=optimized_bytes,
                filename=f"{self._slugify(title)}.jpg",
                alt_text=alt_text
            )
            
        except Exception as e:
            self.logger.warning(f"Image handling failed: {str(e)}")
            return None
    
    def _generate_meta_tags(self, content: str, title: str, keywords: List[str]) -> Dict[str, str]:
        """Generate meta tags for the post"""
        return self.content_analyzer.generate_meta_tags(content, title, keywords)
    
    def _optimize_content_for_seo(self, content, keywords, title):
        """Optimize content for all SEO requirements."""
        try:
            # Clean up formatting first
            content = self._clean_content_formatting(content)
            
            # Extract main keyword
            main_keyword = keywords[0] if keywords else title.split()[0]
            
            # Ensure keyword in first 100 words
            content_words = content.split()
            first_100 = ' '.join(content_words[:100])
            if main_keyword.lower() not in first_100.lower():
                # Add keyword naturally to beginning
                content = f"When exploring {main_keyword}, " + content
            
            # Check and optimize keyword density (target 1%)
            total_words = len(content_words)
            keyword_count = content.lower().count(main_keyword.lower())
            target_density = 0.01  # 1%
            target_count = int(total_words * target_density)
            
            if keyword_count < target_count:
                # Add keyword naturally in content
                paragraphs = content.split('\n\n')
                new_paragraphs = []
                keywords_added = 0
                
                for para in paragraphs:
                    if keywords_added < (target_count - keyword_count) and main_keyword.lower() not in para.lower():
                        para = para.replace('.', f' related to {main_keyword}.', 1)
                        keywords_added += 1
                    new_paragraphs.append(para)
                
                content = '\n\n'.join(new_paragraphs)
            
            # Ensure proper heading structure
            content = self._optimize_heading_structure(content, main_keyword)
            
            # Add internal and external links
            content = self._add_seo_links(content, main_keyword)
            
            # Add schema markup
            content = self._add_schema_markup(content, title, main_keyword)
            
            return content
            
        except Exception as e:
            self.logger.warning(f"SEO optimization failed: {e}")
            return content

    def _optimize_heading_structure(self, content, keyword):
        """Ensure proper H1, H2, H3 structure with clean HTML."""
        lines = content.split('\n')
        optimized_lines = []
        h1_added = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('<h'):
                # Work with HTML headers
                if '<h3>' in line and not h1_added:
                    # Convert first H3 to H1 with keyword
                    line = f'<h1>{keyword}: {line.replace("<h3>", "").replace("</h3>", "")}</h1>'
                    h1_added = True
                elif '<h2>' in line and not h1_added:
                    # Convert first H2 to H1 with keyword
                    line = f'<h1>{keyword}: {line.replace("<h2>", "").replace("</h2>", "")}</h1>'
                    h1_added = True
                elif '<h1>' in line and h1_added:
                    # Convert additional H1 to H2
                    line = line.replace('<h1>', '<h2>').replace('</h1>', '</h2>')
            elif line.startswith('#'):
                # Handle any remaining markdown headers
                if not h1_added and ('##' in line or '###' in line):
                    line = f"<h1>{keyword}: {line.replace('#', '').strip()}</h1>"
                    h1_added = True
                elif line.startswith('###'):
                    line = f"<h3>{line.replace('###', '').strip()}</h3>"
                elif line.startswith('##'):
                    line = f"<h2>{line.replace('##', '').strip()}</h2>"
                elif line.startswith('#') and h1_added:
                    line = f"<h2>{line.replace('#', '').strip()}</h2>"
                    
            optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)

    def _add_seo_links(self, content, keyword):
        """Add internal and external links with real tire industry URLs."""
        # Add external authoritative link
        if 'research' in content.lower() or 'studies' in content.lower():
            content = content.replace('research', '<a href="https://scholar.google.com" target="_blank" rel="noopener">research</a>', 1)
        elif 'quality' in content.lower():
            content = content.replace('quality', '<a href="https://en.wikipedia.org" target="_blank" rel="noopener">quality</a>', 1)
        elif 'professional' in content.lower():
            content = content.replace('professional', '<a href="https://www.nhtsa.gov" target="_blank" rel="noopener">professional</a>', 1)
        else:
            # Ensure at least one external link
            content += f'\n\n<p>For more information about {keyword}, visit <a href="https://wikipedia.org" target="_blank" rel="noopener">Wikipedia</a>.</p>'
        
        # Add realistic internal links based on existing posts or tire categories
        internal_links = self._generate_internal_links_with_existing(keyword)
        for link_text, link_url in internal_links:
            content += f'\n\n<p>Read more: <a href="{link_url}">{link_text}</a></p>'
        
        return content

    def _generate_internal_links(self, keyword):
        """Generate realistic internal links based on tire categories."""
        # Common tire-related categories that would exist on a tire site
        tire_categories = {
            'winter': [
                ('Winter Tire Buying Guide', '/winter-tire-buying-guide/'),
                ('Snow Tire Installation Tips', '/snow-tire-installation/'),
                ('Winter Driving Safety', '/winter-driving-safety/')
            ],
            'summer': [
                ('Summer Tire Performance Guide', '/summer-tire-performance/'),
                ('Hot Weather Tire Care', '/hot-weather-tire-care/'),
                ('Summer Tire Reviews', '/summer-tire-reviews/')
            ],
            'suv': [
                ('SUV Tire Selection Guide', '/suv-tire-selection/'),
                ('Best SUV Tires 2024', '/best-suv-tires-2024/'),
                ('SUV Tire Maintenance', '/suv-tire-maintenance/')
            ],
            'truck': [
                ('Truck Tire Buying Guide', '/truck-tire-buying-guide/'),
                ('Heavy Duty Tire Reviews', '/heavy-duty-tire-reviews/'),
                ('Commercial Tire Solutions', '/commercial-tire-solutions/')
            ],
            'performance': [
                ('Performance Tire Guide', '/performance-tire-guide/'),
                ('High Speed Tire Safety', '/high-speed-tire-safety/'),
                ('Track Day Tire Selection', '/track-day-tire-selection/')
            ],
            'all-season': [
                ('All Season Tire Reviews', '/all-season-tire-reviews/'),
                ('Year Round Tire Guide', '/year-round-tire-guide/'),
                ('All Weather Performance', '/all-weather-performance/')
            ]
        }
        
        # Default general tire links
        default_links = [
            ('Tire Installation Services', '/tire-installation/'),
            ('Tire Maintenance Tips', '/tire-maintenance/'),
            ('Tire Safety Guide', '/tire-safety/')
        ]
        
        # Match keyword to appropriate category
        keyword_lower = keyword.lower()
        
        if 'winter' in keyword_lower or 'snow' in keyword_lower:
            return tire_categories['winter'][:2]
        elif 'summer' in keyword_lower:
            return tire_categories['summer'][:2]
        elif 'suv' in keyword_lower:
            return tire_categories['suv'][:2]
        elif 'truck' in keyword_lower:
            return tire_categories['truck'][:2]
        elif 'performance' in keyword_lower or 'speed' in keyword_lower:
            return tire_categories['performance'][:2]
        elif 'all' in keyword_lower and 'season' in keyword_lower:
            return tire_categories['all-season'][:2]
        else:
            return default_links[:2]

    def _get_existing_posts(self):
        """Fetch existing posts from WordPress for internal linking."""
        if self._existing_posts_cache is not None:
            return self._existing_posts_cache
        
        try:
            # Fetch recent posts from WordPress
            response = self.wordpress._make_request('wp/v2/posts?per_page=50&status=publish')
            posts = []
            
            for post in response:
                posts.append({
                    'title': post.get('title', {}).get('rendered', ''),
                    'slug': post.get('slug', ''),
                    'url': f"/{post.get('slug', '')}/"
                })
            
            self._existing_posts_cache = posts
            self.logger.info(f"Cached {len(posts)} existing posts for internal linking")
            return posts
            
        except Exception as e:
            self.logger.warning(f"Could not fetch existing posts: {e}")
            return []

    def _find_related_posts(self, keyword, max_links=2):
        """Find existing posts related to the keyword."""
        existing_posts = self._get_existing_posts()
        related_posts = []
        keyword_lower = keyword.lower()
        
        # Look for posts with related keywords in titles
        related_keywords = [
            keyword_lower,
            'tire', 'tires', 'wheel', 'wheels', 'automotive', 'vehicle',
            'car', 'truck', 'suv', 'performance', 'safety', 'maintenance',
            'winter', 'summer', 'all-season', 'snow', 'rain'
        ]
        
        for post in existing_posts:
            title_lower = post['title'].lower()
            
            # Check if any related keywords appear in the title
            for related_keyword in related_keywords:
                if related_keyword in title_lower and post not in related_posts:
                    related_posts.append(post)
                    break
            
            if len(related_posts) >= max_links:
                break
        
        return related_posts[:max_links]

    def _generate_internal_links_with_existing(self, keyword):
        """Generate internal links using real existing posts when possible."""
        # First try to find real existing posts
        related_posts = self._find_related_posts(keyword, max_links=2)
        
        if related_posts:
            return [(post['title'], post['url']) for post in related_posts]
        
        # Fallback to the existing category-based system
        return self._generate_internal_links(keyword)

    def _add_schema_markup(self, content, title, keyword):
        """Add structured data markup."""
        schema = f'''
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "Comprehensive guide about {keyword}",
  "author": {{
    "@type": "Organization",
    "name": "TireDealsNow"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "TireDealsNow"
  }},
  "datePublished": "{datetime.now().isoformat()}",
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "https://tiredealsnow.com/"
  }}
}}
</script>'''
        
        return content + schema

    def _generate_seo_meta_tags(self, content, title, description, keywords):
        """Generate SEO-optimized meta tags with dynamic descriptions based on search intent."""
        # Optimize meta title (50-60 characters)
        meta_title = title
        if len(meta_title) > 60:
            meta_title = meta_title[:57] + "..."
        elif len(meta_title) < 50:
            main_keyword = keywords[0] if keywords else ""
            meta_title = f"{meta_title} - {main_keyword}"[:60]
        
        # Generate dynamic meta description based on search query intent
        meta_description = self._generate_dynamic_meta_description(title, description, keywords)
        
        # Ensure optimal length (150-160 characters)
        if len(meta_description) > 160:
            meta_description = meta_description[:157] + "..."
        elif len(meta_description) < 150:
            # Pad with relevant search-intent based content
            padding = self._get_meta_description_padding(title, keywords)
            meta_description = (meta_description + " " + padding)[:160]
        
        return {
            'yoast_wpseo_title': meta_title,
            'yoast_wpseo_metadesc': meta_description,
            'yoast_wpseo_canonical': f"https://tiredealsnow.com/{title.lower().replace(' ', '-')}/",
            'yoast_wpseo_meta-robots-noindex': '0',
            'yoast_wpseo_meta-robots-nofollow': '0',
            'yoast_wpseo_focuskw': keywords[0] if keywords else title.split()[0]
        }

    def _generate_dynamic_meta_description(self, title, description, keywords):
        """Generate dynamic meta descriptions based on search query intent."""
        # Analyze search intent from title and keywords
        search_intent = self._analyze_search_intent(title, keywords)
        
        # Create intent-specific descriptions
        intent_templates = {
            'price': {
                'template': "Compare {product} prices and find the best deals. Save money with our price comparison and exclusive discounts on top-rated {category}.",
                'cta': "Get instant price quotes and save up to 30% today!"
            },
            'review': {
                'template': "Expert {product} reviews and ratings. Read real customer experiences and professional test results to make the right choice for {category}.",
                'cta': "See why customers rate these products 5 stars!"
            },
            'comparison': {
                'template': "Compare {product} features, performance, and prices. Side-by-side analysis of top brands with pros, cons, and expert recommendations.",
                'cta': "Find your perfect match with our comparison tool!"
            },
            'buying_guide': {
                'template': "Complete {product} buying guide with expert tips. Everything you need to know before purchasing {category} including size charts and recommendations.",
                'cta': "Make the right choice with our expert guidance!"
            },
            'brand_specific': {
                'template': "Official {brand} {product} collection. Authentic products with warranty, competitive prices, and fast shipping on all {category}.",
                'cta': "Shop authentic products with confidence!"
            },
            'size_specific': {
                'template': "{size} {product} - perfect fit guaranteed. Wide selection of {category} in stock with fast delivery and expert fitting advice.",
                'cta': "Get the perfect fit for your vehicle today!"
            },
            'general': {
                'template': "Premium {product} selection with expert advice. Top-quality {category} from leading brands with competitive prices and fast shipping.",
                'cta': "Shop now and experience the difference!"
            }
        }
        
        # Get template based on intent
        template_data = intent_templates.get(search_intent, intent_templates['general'])
        
        # Extract product and category information
        product_info = self._extract_product_info(title, keywords)
        
        # Generate base description
        base_description = template_data['template'].format(**product_info)
        
        # Add CTA if space allows
        if len(base_description) < 120:
            full_description = f"{base_description} {template_data['cta']}"
        else:
            full_description = base_description
            
        return full_description

    def _analyze_search_intent(self, title, keywords):
        """Analyze search intent from title and keywords."""
        title_lower = title.lower()
        keywords_text = ' '.join(keywords).lower() if keywords else ''
        combined_text = f"{title_lower} {keywords_text}"
        
        # Intent detection patterns
        intent_patterns = {
            'price': ['price', 'cost', 'cheap', 'discount', 'deal', 'sale', 'budget', 'affordable'],
            'review': ['review', 'rating', 'test', 'opinion', 'experience', 'best', 'top rated'],
            'comparison': ['vs', 'compare', 'comparison', 'difference', 'better', 'versus'],
            'buying_guide': ['guide', 'how to', 'buying', 'choose', 'select', 'tips'],
            'brand_specific': ['bfgoodrich', 'bf goodrich', 'goodyear', 'michelin', 'bridgestone', 'maxxis', 'continental'],
            'size_specific': [r'\d+/\d+', r'\d+-\d+', r'r\d+', 'size']
        }
        
        # Check each intent pattern
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if pattern in combined_text or (intent == 'size_specific' and re.search(pattern, combined_text)):
                    return intent
        
        return 'general'

    def _extract_product_info(self, title, keywords):
        """Extract product and category information for template filling."""
        # Extract tire size if present
        size_pattern = r'(\d+[/-]\d+[/]?[rR]?\d+)'
        size_match = re.search(size_pattern, title)
        tire_size = size_match.group(1) if size_match else ''
        
        # Extract brand if present
        brand_patterns = {
            'BFGoodrich': ['bfgoodrich', 'bf goodrich', 'bf-goodrich'],
            'Goodyear': ['goodyear'],
            'Michelin': ['michelin'],
            'Bridgestone': ['bridgestone'],
            'Maxxis': ['maxxis'],
            'Continental': ['continental']
        }
        
        brand = ''
        title_lower = title.lower()
        for brand_name, patterns in brand_patterns.items():
            if any(pattern in title_lower for pattern in patterns):
                brand = brand_name
                break
        
        # Determine product type
        if 'all terrain' in title_lower or 'all-terrain' in title_lower:
            product_type = 'all terrain tyres'
        elif 'off road' in title_lower or 'off-road' in title_lower:
            product_type = 'off road tyres'
        elif 'mud' in title_lower:
            product_type = 'mud terrain tyres'
        elif 'highway' in title_lower:
            product_type = 'highway tyres'
        else:
            product_type = 'tyres'
        
        # Create product description (avoid redundancy)
        product_parts = []
        if brand:
            product_parts.append(brand)
        if tire_size:
            product_parts.append(tire_size)
        product_parts.append(product_type)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_parts = []
        for part in product_parts:
            if part.lower() not in seen:
                unique_parts.append(part)
                seen.add(part.lower())
        
        product = ' '.join(unique_parts)
        
        return {
            'product': product,
            'category': product_type,
            'brand': brand,
            'size': tire_size
        }

    def _get_meta_description_padding(self, title, keywords):
        """Generate relevant padding content for meta descriptions."""
        intent = self._analyze_search_intent(title, keywords)
        
        padding_options = {
            'price': "Best prices guaranteed with free shipping.",
            'review': "Read verified customer reviews and ratings.",
            'comparison': "Expert comparisons and recommendations.",
            'buying_guide': "Complete buying guide with expert tips.",
            'brand_specific': "Authentic products with full warranty.",
            'size_specific': "Perfect fit guaranteed for your vehicle.",
            'general': "Premium quality with fast delivery."
        }
        
        return padding_options.get(intent, padding_options['general'])

    def _handle_seo_images(self, title, keywords):
        """Handle images with proper alt tags - improved matching."""
        try:
            # Generate image filename from title
            safe_title = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
            safe_title = re.sub(r'\s+', '-', safe_title.strip())
            image_filename = f"{safe_title}.png"
            image_path = os.path.join(self.image_directory, image_filename)
            
            # If exact match exists, use it
            if os.path.exists(image_path):
                main_keyword = keywords[0] if keywords else title
                alt_text = f"{main_keyword} - {title}"
                return self._upload_image_with_alt(image_path, alt_text)
            
            # If no exact match, try to find related images
            related_image = self._find_related_image(title, keywords)
            if related_image:
                main_keyword = keywords[0] if keywords else title
                alt_text = f"{main_keyword} - {title}"
                return self._upload_image_with_alt(related_image, alt_text)
            
            # Log when no image is found
            self.logger.info(f"No suitable image found for: {title}")
            return None
            
        except Exception as e:
            self.logger.warning(f"Image handling failed: {e}")
            return None

    def _find_related_image(self, title, keywords):
        """Find a related image when exact match doesn't exist."""
        try:
            # Get all available images
            available_images = [f for f in os.listdir(self.image_directory) if f.endswith('.png')]
            
            # Keywords to search for in image filenames
            search_terms = []
            
            # Add keywords
            if keywords:
                search_terms.extend([kw.lower().replace(' ', '-') for kw in keywords])
            
            # Add title words
            title_words = [word.lower() for word in title.split() if len(word) > 3]
            search_terms.extend(title_words)
            
            # Common tire-related terms
            tire_terms = ['tire', 'tires', 'truck', 'suv', 'tractor', 'winter', 'summer', 'performance', 'heavy', 'duty']
            search_terms.extend(tire_terms)
            
            # Score images based on how many search terms they contain
            image_scores = {}
            for image in available_images:
                score = 0
                image_lower = image.lower()
                for term in search_terms:
                    if term in image_lower:
                        score += 1
                if score > 0:
                    image_scores[image] = score
            
            # Return the highest scoring image
            if image_scores:
                best_image = max(image_scores.items(), key=lambda x: x[1])[0]
                best_path = os.path.join(self.image_directory, best_image)
                self.logger.info(f"Found related image for '{title}': {best_image} (score: {image_scores[best_image]})")
                return best_path
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Related image search failed: {e}")
            return None

    def _upload_image_with_alt(self, image_path, alt_text):
        """Upload image with proper alt text to WordPress and track for sitemap."""
        try:
            # Read the image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Get filename
            filename = os.path.basename(image_path)
            
            # Upload to WordPress
            media_id = self.wordpress.upload_media(
                file_content=image_data,
                filename=filename,
                alt_text=alt_text,
                caption=alt_text
            )
            
            # Track uploaded image for sitemap
            self._track_uploaded_image(media_id, filename, alt_text, image_path)
            
            self.logger.info(f"Successfully uploaded image: {filename} with ID: {media_id}")
            return media_id
            
        except Exception as e:
            self.logger.error(f"Failed to upload image {image_path}: {e}")
            return None

    def _track_uploaded_image(self, media_id, filename, alt_text, image_path):
        """Track uploaded image for sitemap generation."""
        try:
            # Get image dimensions
            import os
            from PIL import Image
            
            # Get file stats
            file_stats = os.stat(image_path)
            file_size = file_stats.st_size
            
            # Get image dimensions
            with Image.open(image_path) as img:
                width, height = img.size
            
            # Create image URL (WordPress media URL pattern)
            image_url = f"https://tiredealsnow.com/wp-content/uploads/{filename}"
            
            # Track image data
            image_data = {
                'media_id': media_id,
                'filename': filename,
                'alt_text': alt_text,
                'url': image_url,
                'width': width,
                'height': height,
                'file_size': file_size,
                'upload_date': datetime.now().isoformat(),
                'title': alt_text,
                'caption': alt_text
            }
            
            self.uploaded_images.append(image_data)
            self.logger.info(f"Tracked image for sitemap: {filename}")
            
        except Exception as e:
            self.logger.warning(f"Failed to track image {filename}: {e}")

    def generate_image_sitemap(self):
        """Generate XML image sitemap for Google."""
        try:
            if not self.uploaded_images:
                self.logger.warning("No images to include in sitemap")
                return None
            
            # Create XML structure
            from xml.etree.ElementTree import Element, SubElement, tostring
            from xml.dom import minidom
            
            # Root element
            urlset = Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            urlset.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
            
            # Group images by associated pages (for now, create individual entries)
            for image in self.uploaded_images:
                # Create URL entry
                url_elem = SubElement(urlset, 'url')
                
                # Page location (image gallery or media page)
                loc = SubElement(url_elem, 'loc')
                loc.text = f"https://tiredealsnow.com/wp-content/uploads/{image['filename']}"
                
                # Last modified
                lastmod = SubElement(url_elem, 'lastmod')
                lastmod.text = image['upload_date'].split('T')[0]  # Date only
                
                # Image information
                image_elem = SubElement(url_elem, 'image:image')
                
                # Image location
                image_loc = SubElement(image_elem, 'image:loc')
                image_loc.text = image['url']
                
                # Image title
                image_title = SubElement(image_elem, 'image:title')
                image_title.text = image['title']
                
                # Image caption
                if image.get('caption'):
                    image_caption = SubElement(image_elem, 'image:caption')
                    image_caption.text = image['caption']
                
                # Image description (alt text)
                image_desc = SubElement(image_elem, 'image:description')
                image_desc.text = image['alt_text']
            
            # Format XML
            rough_string = tostring(urlset, 'unicode')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            # Remove extra blank lines
            clean_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
            
            # Write to file
            with open(self.sitemap_path, 'w', encoding='utf-8') as f:
                f.write(clean_xml)
            
            self.logger.info(f"Generated image sitemap with {len(self.uploaded_images)} images: {self.sitemap_path}")
            return self.sitemap_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate image sitemap: {e}")
            return None

    def generate_comprehensive_image_sitemap(self):
        """Generate comprehensive image sitemap with page associations."""
        try:
            if not self.uploaded_images:
                self.logger.warning("No images to include in comprehensive sitemap")
                return None
            
            from xml.etree.ElementTree import Element, SubElement, tostring
            from xml.dom import minidom
            
            # Root element
            urlset = Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            urlset.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
            
            # Create main site pages with associated images
            site_pages = {
                'https://tiredealsnow.com/': {
                    'title': 'Tire Deals Now - Premium Tire Selection',
                    'images': []
                },
                'https://tiredealsnow.com/all-terrain-tires/': {
                    'title': 'All Terrain Tires Collection',
                    'images': []
                },
                'https://tiredealsnow.com/tire-brands/': {
                    'title': 'Top Tire Brands',
                    'images': []
                }
            }
            
            # Categorize images by content type
            for image in self.uploaded_images:
                alt_text_lower = image['alt_text'].lower()
                
                if 'all terrain' in alt_text_lower:
                    site_pages['https://tiredealsnow.com/all-terrain-tires/']['images'].append(image)
                elif any(brand in alt_text_lower for brand in ['bfgoodrich', 'goodyear', 'michelin', 'bridgestone']):
                    site_pages['https://tiredealsnow.com/tire-brands/']['images'].append(image)
                else:
                    site_pages['https://tiredealsnow.com/']['images'].append(image)
            
            # Generate XML for each page with its images
            for page_url, page_data in site_pages.items():
                if page_data['images']:
                    url_elem = SubElement(urlset, 'url')
                    
                    # Page location
                    loc = SubElement(url_elem, 'loc')
                    loc.text = page_url
                    
                    # Last modified (most recent image upload)
                    lastmod = SubElement(url_elem, 'lastmod')
                    lastmod.text = max([img['upload_date'] for img in page_data['images']]).split('T')[0]
                    
                    # Add all images for this page
                    for image in page_data['images']:
                        image_elem = SubElement(url_elem, 'image:image')
                        
                        # Image location
                        image_loc = SubElement(image_elem, 'image:loc')
                        image_loc.text = image['url']
                        
                        # Image title
                        image_title = SubElement(image_elem, 'image:title')
                        image_title.text = image['title']
                        
                        # Image caption
                        if image.get('caption'):
                            image_caption = SubElement(image_elem, 'image:caption')
                            image_caption.text = image['caption']
                        
                        # Image description
                        image_desc = SubElement(image_elem, 'image:description')
                        image_desc.text = image['alt_text']
            
            # Format and save
            rough_string = tostring(urlset, 'unicode')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            clean_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
            
            comprehensive_sitemap_path = "comprehensive_image_sitemap.xml"
            with open(comprehensive_sitemap_path, 'w', encoding='utf-8') as f:
                f.write(clean_xml)
            
            self.logger.info(f"Generated comprehensive image sitemap: {comprehensive_sitemap_path}")
            return comprehensive_sitemap_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate comprehensive image sitemap: {e}")
            return None

    def update_robots_txt(self):
        """Update robots.txt to include image sitemaps."""
        try:
            robots_content = []
            
            # Read existing robots.txt if it exists
            robots_path = "robots.txt"
            if os.path.exists(robots_path):
                with open(robots_path, 'r', encoding='utf-8') as f:
                    robots_content = f.readlines()
            
            # Clean up existing sitemap entries
            robots_content = [line for line in robots_content if not line.strip().startswith('Sitemap:')]
            
            # Add sitemap references
            sitemap_entries = [
                "# Image Sitemaps\n",
                "Sitemap: https://tiredealsnow.com/image_sitemap.xml\n",
                "Sitemap: https://tiredealsnow.com/comprehensive_image_sitemap.xml\n",
                "\n"
            ]
            
            # Combine content
            final_content = robots_content + sitemap_entries
            
            # Write updated robots.txt
            with open(robots_path, 'w', encoding='utf-8') as f:
                f.writelines(final_content)
            
            self.logger.info("Updated robots.txt with image sitemap references")
            return robots_path
            
        except Exception as e:
            self.logger.error(f"Failed to update robots.txt: {e}")
            return None

    def regenerate_sitemaps_from_wordpress(self):
        """Regenerate image sitemaps using existing tracked images."""
        try:
            self.logger.info("Regenerating sitemaps from tracked images...")
            
            # For now, use existing tracked images if available
            if not self.uploaded_images:
                self.logger.warning("No tracked images available for regeneration")
                return 0
            
            self.logger.info(f"Regenerating sitemaps with {len(self.uploaded_images)} tracked images")
            
            # Generate new sitemaps
            self._generate_all_sitemaps()
            
            return len(self.uploaded_images)
            
        except Exception as e:
            self.logger.error(f"Failed to regenerate sitemaps: {e}")
            return None

    def get_sitemap_stats(self):
        """Get statistics about generated sitemaps."""
        try:
            stats = {
                'tracked_images': len(self.uploaded_images),
                'simple_sitemap_exists': os.path.exists(self.sitemap_path),
                'comprehensive_sitemap_exists': os.path.exists('comprehensive_image_sitemap.xml'),
                'robots_txt_exists': os.path.exists('robots.txt'),
                'total_file_size': 0,
                'image_categories': {}
            }
            
            # Calculate file sizes
            for filename in [self.sitemap_path, 'comprehensive_image_sitemap.xml', 'robots.txt']:
                if os.path.exists(filename):
                    stats['total_file_size'] += os.path.getsize(filename)
            
            # Categorize images
            for image in self.uploaded_images:
                alt_text = image.get('alt_text', '').lower()
                
                if 'all terrain' in alt_text:
                    stats['image_categories']['all_terrain'] = stats['image_categories'].get('all_terrain', 0) + 1
                elif 'winter' in alt_text:
                    stats['image_categories']['winter'] = stats['image_categories'].get('winter', 0) + 1
                elif any(brand in alt_text for brand in ['bfgoodrich', 'goodyear', 'michelin']):
                    stats['image_categories']['branded'] = stats['image_categories'].get('branded', 0) + 1
                else:
                    stats['image_categories']['general'] = stats['image_categories'].get('general', 0) + 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get sitemap stats: {e}")
            return None

    def _post_to_wordpress(
        self,
        title: str,
        content: str,
        description: str,
        slug: str,
        meta_tags: Dict[str, str],
        featured_image_id: Optional[int] = None
    ) -> None:
        """Post content directly to WordPress"""
        try:
            post_id = self.wordpress.create_post(
                title=title,
                content=content,
                excerpt=description,
                slug=slug,
                meta=meta_tags,
                featured_media_id=featured_image_id
            )
            self.logger.info(f"Successfully published post with ID: {post_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish post: {str(e)}")
            raise
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Create URL-safe slug from text"""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:100]
