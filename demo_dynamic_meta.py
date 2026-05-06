#!/usr/bin/env python3
"""Complete demo of dynamic meta descriptions in blog generation"""

from blog_generator import BlogPostGenerator
import json

def demo_complete_generation():
    """Demonstrate complete blog generation with dynamic meta descriptions"""
    print("COMPLETE BLOG GENERATION WITH DYNAMIC META DESCRIPTIONS")
    print("=" * 65)
    
    generator = BlogPostGenerator()
    
    # Sample blog data simulating CSV input
    sample_entries = [
        {
            'URL Slug': 'best-winter-tires-2024-review',
            'Meta Title': 'Best Winter Tires 2024 - Expert Reviews & Ratings',
            'Description': 'Professional winter tire reviews and ratings for 2024.'
        },
        {
            'URL Slug': 'michelin-vs-bridgestone-comparison',
            'Meta Title': 'Michelin vs Bridgestone Tires - Complete Comparison',
            'Description': 'Compare Michelin and Bridgestone tire performance.'
        },
        {
            'URL Slug': '235-55r17-winter-tires-price',
            'Meta Title': '235/55R17 Winter Tires - Best Prices & Deals',
            'Description': 'Find the best deals on 235/55R17 winter tires.'
        }
    ]
    
    print("Generating blog posts with dynamic meta descriptions...\n")
    
    for i, entry in enumerate(sample_entries, 1):
        print(f"BLOG POST {i}: {entry['Meta Title']}")
        print("=" * 50)
        
        # Extract keywords
        keywords = generator._extract_keywords(entry['Meta Title'], entry['Description'])
        
        # Analyze search intent
        intent = generator._analyze_search_intent(entry['Meta Title'], keywords)
        
        # Generate dynamic meta description
        dynamic_desc = generator._generate_dynamic_meta_description(
            entry['Meta Title'], 
            entry['Description'], 
            keywords
        )
        
        # Generate complete meta tags
        meta_tags = generator._generate_seo_meta_tags(
            "Sample content for SEO optimization", 
            entry['Meta Title'], 
            entry['Description'], 
            keywords
        )
        
        print(f"🔍 Search Intent: {intent.upper()}")
        print(f"🎯 Keywords: {', '.join(keywords[:5])}...")
        print(f"📝 Original Description: {entry['Description']}")
        print(f"✨ Dynamic Description: {dynamic_desc}")
        print(f"📊 Final Meta Description: {meta_tags['yoast_wpseo_metadesc']}")
        print(f"📏 Length: {len(meta_tags['yoast_wpseo_metadesc'])} characters")
        
        # Show all meta tags
        print("\n🏷️ Complete SEO Meta Tags:")
        for key, value in meta_tags.items():
            print(f"   {key}: {value}")
        
        print("\n" + "-" * 50 + "\n")
    
    print("DYNAMIC META DESCRIPTION SYSTEM SUMMARY:")
    print("=" * 50)
    print("✅ IMPLEMENTED FEATURES:")
    print("  🎯 Search Intent Analysis")
    print("     • Price intent detection")
    print("     • Review intent detection") 
    print("     • Comparison intent detection")
    print("     • Brand-specific intent detection")
    print("     • Size-specific intent detection")
    print("     • Buying guide intent detection")
    print("")
    print("  📝 Dynamic Content Generation")
    print("     • Intent-specific templates")
    print("     • Product information extraction")
    print("     • Brand and size recognition")
    print("     • Category-specific language")
    print("")
    print("  📊 SEO Optimization")
    print("     • Optimal length (150-160 characters)")
    print("     • Keyword integration")
    print("     • Call-to-action inclusion")
    print("     • Search relevance improvement")
    print("")
    print("  🔄 Automation Features")
    print("     • Automatic intent detection")
    print("     • Template-based generation")
    print("     • Length optimization")
    print("     • Redundancy removal")
    print("")
    print("📈 BENEFITS:")
    print("  • Higher click-through rates")
    print("  • Better search rankings")
    print("  • Improved user experience")
    print("  • Automated optimization")
    print("  • Consistent quality")

if __name__ == "__main__":
    demo_complete_generation()
