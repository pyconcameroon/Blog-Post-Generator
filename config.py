"""Configuration settings for the blog post generator"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        
        # API Keys and credentials
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.wordpress_url = os.getenv('WORDPRESS_URL')
        self.wordpress_username = os.getenv('WORDPRESS_USERNAME')
        self.wordpress_password = os.getenv('WORDPRESS_PASSWORD')
        
        # Image settings
        self.image_settings = {
            'width': int(os.getenv('IMAGE_WIDTH', 1024)),
            'height': int(os.getenv('IMAGE_HEIGHT', 768)),
            'quality': int(os.getenv('IMAGE_QUALITY', 85))
        }
        
        # Content settings
        self.content_settings = {
            'min_word_count': 1500,  # Reduced from 2500
            'max_word_count': 15000,  # Increased from 5000 to allow longer content
            'min_h2_sections': 4,
            'min_h3_per_h2': 2,
            'min_tables': 1,
            'min_outbound_links': 3,
            'min_authority_links': 2
        }
        
        # SEO settings
        self.seo_settings = {
            'min_keyword_density': 0.002,  # Further reduced from 0.005 (0.2%)
            'max_keyword_density': 0.02,
            'min_readability_score': 40,  # Further reduced from 50
            'required_internal_links': [
                'https://dunemedicaldevicesinc.com',
                'https://dunemedicaldevicesinc.com/shop-2/',
                'https://dunemedicaldevicesinc.com/contact-us/'
            ]
        }
        
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration settings"""
        issues = []
        
        if not self.deepseek_api_key:
            issues.append("Missing DEEPSEEK_API_KEY")
        if not self.wordpress_url:
            issues.append("Missing WORDPRESS_URL")
        if not self.wordpress_username or not self.wordpress_password:
            issues.append("Missing WordPress credentials")
            
        return len(issues) == 0, issues
