"""
WordPress Authentication Fix for Enhanced Blog Generator V2
"""

import requests
import base64
import json

def test_wordpress_auth():
    """Test WordPress authentication"""
    
    # Test different authentication methods
    wp_url = 'https://dunemedicaldevicesinc.com/wp-json/wp/v2'
    username = 'dune'
    
    # Application passwords to try
    passwords = [
        'ork8 Grtg sZEy Q1w1 dtgl 37oE',  # Current
        # Add more if needed
    ]
    
    for password in passwords:
        try:
            print(f"Testing authentication...")
            
            headers = {
                'Authorization': 'Basic ' + base64.b64encode(
                    f'{username}:{password}'.encode('utf-8')
                ).decode('utf-8'),
                'Content-Type': 'application/json'
            }
            
            # Test with a simple GET request first
            response = requests.get(f'{wp_url}/users/me', headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Authentication SUCCESS!")
                print(f"   User: {user_data.get('name', 'Unknown')}")
                print(f"   Roles: {user_data.get('roles', [])}")
                return True
            else:
                print(f"❌ Auth failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
    
    print("\n💡 Checking if we can continue without WordPress publishing...")
    return False

def create_modified_generator():
    """Create a version that skips WordPress on auth failure"""
    
    print("Creating fallback version that saves content locally...")
    
    # Read the original script
    with open('enhanced_blog_generator_v2.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Modify the post_to_wordpress function to handle auth failures gracefully
    modified_content = content.replace(
        'return False',
        '''# Save content locally as backup
            backup_filename = f"article_{result.slug}.html"
            try:
                with open(backup_filename, 'w', encoding='utf-8') as backup_file:
                    backup_file.write(f"<!-- WordPress Publishing Failed - Saved Locally -->\\n")
                    backup_file.write(f"<!-- Title: {result.title} -->\\n")
                    backup_file.write(f"<!-- Meta Title: {result.meta_title} -->\\n") 
                    backup_file.write(f"<!-- Meta Description: {result.meta_description} -->\\n")
                    backup_file.write(result.content)
                logger.info(f"Content saved locally as {backup_filename}")
            except Exception as backup_error:
                logger.warning(f"Failed to save backup: {str(backup_error)}")
            return False'''
    )
    
    # Save the modified version
    with open('enhanced_blog_generator_v2_fallback.py', 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("✅ Created enhanced_blog_generator_v2_fallback.py")

if __name__ == "__main__":
    print("🔧 WordPress Authentication Troubleshooter")
    print("=" * 50)
    
    auth_works = test_wordpress_auth()
    
    if not auth_works:
        print("\n🔄 Creating fallback solution...")
        create_modified_generator()
        print("\n💡 RECOMMENDATION:")
        print("   1. Content generation will continue successfully")
        print("   2. Articles will be saved as local HTML files")
        print("   3. You can manually upload them to WordPress later")
        print("   4. All SEO data and quality metrics will be preserved")
    else:
        print("\n✅ WordPress authentication is working!")
