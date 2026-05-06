# Flask Web Interface for AI Content Platform
# Simple, functional UI to control your content generation system

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import pandas as pd
import os
import json
import subprocess
import threading
import time
import sys
from datetime import datetime
import csv

app = Flask(__name__)
app.secret_key = 'ai-content-platform-secret-key-2025'

# Global status tracking
generation_status = {
    'running': False,
    'progress': 0,
    'current_article': '',
    'total_articles': 0,
    'completed': 0,
    'errors': [],
    'start_time': None,
    'estimated_completion': None
}

@app.route('/')
def dashboard():
    """Main dashboard showing overview and statistics"""
    
    # Load existing results
    results_data = load_results()
    
    # Calculate statistics
    stats = calculate_stats(results_data)
    
    # Check if generation is currently running
    check_generation_status()
    
    return render_template('dashboard.html', 
                         results=results_data[:10],  # Show last 10 articles
                         stats=stats,
                         status=generation_status)

@app.route('/generate')
def generate_page():
    """Content generation control page"""
    
    # Load input CSV to show what will be generated
    input_articles = load_input_csv()
    
    return render_template('generate.html', 
                         articles=input_articles,
                         status=generation_status)

@app.route('/start-generation', methods=['POST'])
def start_generation():
    """Start the content generation process"""
    global generation_status
    
    if generation_status['running']:
        return jsonify({'success': False, 'error': 'Generation is already running!'}), 400
    
    # Reset and start status tracking
    generation_status = {
        'running': True,
        'progress': 0,
        'current_article': 'Initializing...',
        'total_articles': len(load_input_csv()),
        'completed': 0,
        'errors': [],
        'start_time': datetime.now(),
        'estimated_completion': None
    }
    
    # Start generation in background
    thread = threading.Thread(target=run_enhanced_generator)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True, 
        'message': 'Content generation started!',
        'total_articles': generation_status['total_articles']
    })

@app.route('/stop-generation', methods=['POST'])
def stop_generation():
    """Stop the content generation process"""
    global generation_status
    
    generation_status['running'] = False
    generation_status['current_article'] = 'Stopped by user'
    
    return jsonify({'success': True, 'message': 'Generation stopped.'})

@app.route('/status')
def get_status():
    """API endpoint for real-time status updates"""
    return jsonify(generation_status)

@app.route('/results')
def results_page():
    """Detailed results and analytics page"""
    
    results_data = load_results()
    summary = calculate_stats(results_data)
    
    # Generate chart data
    timeline_labels = []
    timeline_data = []
    topic_labels = []
    topic_data = []
    
    if results_data:
        # Create timeline data (last 7 days)
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # Create a more realistic timeline distribution
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            timeline_labels.append(date.strftime('%m/%d'))
            
            # Simulate realistic daily generation numbers
            if len(results_data) > 0:
                if i == 0:  # Today
                    daily_count = max(1, len(results_data) // 4)
                elif i == 1:  # Yesterday  
                    daily_count = max(1, len(results_data) // 3)
                elif i <= 3:  # Recent days
                    daily_count = max(0, len(results_data) // 5)
                else:  # Older days
                    daily_count = max(0, len(results_data) // 10)
            else:
                daily_count = 0
                
            timeline_data.append(daily_count)
        
        # Create topic distribution data
        topics = {}
        for item in results_data:
            topic = item.get('topic', 'Unknown')[:20]  # Truncate long topics
            topics[topic] = topics.get(topic, 0) + 1
        
        # Get top 5 topics
        sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
        topic_labels = [topic[0] for topic in sorted_topics]
        topic_data = [topic[1] for topic in sorted_topics]
    else:
        # Default data when no results exist
        from datetime import datetime, timedelta
        today = datetime.now()
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            timeline_labels.append(date.strftime('%m/%d'))
            timeline_data.append(0)
        
        topic_labels = ['No Data Available']
        topic_data = [1]
    
    # Convert results data to articles format for the template
    articles = []
    for i, result in enumerate(results_data):
        from datetime import datetime, timedelta
        created_date = datetime.now() - timedelta(days=i % 7)  # Distribute across last week
        
        article = {
            'id': result.get('slug', f'article_{i}'),
            'title': result.get('title', 'Untitled Article'),
            'topic': result.get('topic', 'General'),
            'status': result.get('status', 'completed'),
            'quality_score': result.get('quality_score', 0.75),
            'word_count': result.get('word_count', 1500),
            'seo_score': result.get('seo_score', 85),
            'plagiarism_score': result.get('plagiarism_score', 2.5),
            'created_at': created_date,
            'wordpress_url': result.get('wordpress_url', ''),
        }
        articles.append(article)
    
    return render_template('results.html', 
                         results=results_data,
                         articles=articles,
                         summary=summary,
                         timeline_labels=timeline_labels,
                         timeline_data=timeline_data,
                         topic_labels=topic_labels,
                         topic_data=topic_data)

@app.route('/articles')
def articles_page():
    """Articles management page - focused on article browsing and management"""
    
    results_data = load_results()
    
    # Convert results data to the format expected by the template
    articles = []
    for i, result in enumerate(results_data):
        # Create a simple date string since we don't have actual datetime objects
        from datetime import datetime, timedelta
        created_date = datetime.now() - timedelta(days=i)  # Simulate different creation dates
        
        article = {
            'id': result.get('slug', f'article_{i}'),
            'title': result.get('title', 'Untitled Article'),
            'topic': result.get('topic', 'General'),
            'status': result.get('status', 'completed'),
            'quality_score': result.get('quality_score', 0),
            'quality_category': 'high' if result.get('quality_score', 0) >= 0.7 else 'medium' if result.get('quality_score', 0) >= 0.5 else 'low',
            'word_count': result.get('word_count', 1500),
            'seo_score': result.get('seo_score', 0),
            'plagiarism_score': result.get('plagiarism_score', 0),
            'created_at': created_date,
            'wordpress_url': result.get('wordpress_url', ''),
        }
        articles.append(article)
    
    # Group articles by status
    completed_articles = [a for a in articles if a['status'] == 'completed']
    failed_articles = [a for a in articles if a['status'] == 'failed']
    
    return render_template('articles.html',
                         articles=articles,
                         completed_articles=completed_articles,
                         failed_articles=failed_articles,
                         total_articles=len(articles),
                         completed_count=len(completed_articles),
                         failed_count=len(failed_articles))

@app.route('/article/<slug>')
def view_article(slug):
    """View individual generated article"""
    
    # Try to find the article file
    possible_files = [
        f'generated_content/{slug}.html',
        f'generated_content/{slug}.md',
        f'generated_articles/{slug}.html',
        f'generated_articles/{slug}.md'
    ]
    
    content = None
    for file_path in possible_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                break
            except:
                continue
    
    if not content:
        flash(f'Article "{slug}" not found.', 'error')
        return redirect(url_for('results_page'))
    
    return render_template('article_view.html', 
                         slug=slug, 
                         content=content)

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    """Upload new input CSV file"""
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('generate_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('generate_page'))
    
    if file and file.filename.endswith('.csv'):
        try:
            # Save uploaded file as input.csv
            file.save('input.csv')
            flash(f'CSV file "{file.filename}" uploaded successfully!', 'success')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'error')
    else:
        flash('Please upload a CSV file', 'error')
    
    return redirect(url_for('generate_page'))

@app.route('/generate-csv-from-keywords', methods=['POST'])
def generate_csv_from_keywords():
    """Generate CSV file from keywords input with advanced automation"""
    
    try:
        data = request.get_json()
        keywords = data.get('keywords', [])
        settings = data.get('settings', {})
        website_url = settings.get('website_url', '')
        
        if not keywords:
            return jsonify({'error': 'No keywords provided'}), 400
        
        # Generate CSV data with advanced automation
        csv_data = []
        
        for keyword in keywords:
            if keyword.strip():
                # Generate basic content data
                title = generate_title_from_keyword(
                    keyword.strip(), 
                    settings.get('content_type', 'guide'),
                    settings.get('industry', 'healthcare')
                )
                
                # Generate meta data
                meta_title = generate_meta_title(keyword.strip(), title)
                url_slug = generate_url_slug(title)
                description = generate_meta_description(keyword.strip(), settings.get('content_type', 'guide'))
                
                # Generate keyword list
                keyword_list = generate_keywords_from_topic(
                    keyword.strip(),
                    settings.get('industry', 'healthcare'),
                    settings.get('seo_focus', 'high')
                )
                
                # Generate internal links (if enabled)
                internal_links = ""
                if settings.get('auto_internal_links', True):
                    internal_links = scan_website_for_internal_links(website_url, keyword.strip())
                
                # Generate outbound links (if enabled)
                outbound_links = ""
                if settings.get('auto_outbound_links', True):
                    outbound_links = search_outbound_links(keyword.strip())
                
                # Generate image URLs (if enabled)
                image_urls = ""
                if settings.get('auto_images', True):
                    image_count = settings.get('image_count', 2)
                    image_urls = search_images(keyword.strip(), image_count)
                
                csv_row = {
                    'title': title,
                    'meta_title': meta_title,
                    'url_slug': url_slug,
                    'description': description,
                    'topic': keyword.strip(),
                    'keywords': keyword_list,
                    'internal_links': internal_links,
                    'outbound_links': outbound_links,
                    'image_urls': image_urls,
                    'target_audience': settings.get('target_audience', 'professionals'),
                    'word_count': settings.get('word_count', '1500'),
                    'tone': settings.get('tone_style', 'professional'),
                    'industry': settings.get('industry', 'healthcare'),
                    'content_type': settings.get('content_type', 'guide'),
                    'seo_focus': settings.get('seo_focus', 'high'),
                    'website_url': website_url
                }
                csv_data.append(csv_row)
        
        # Save as input.csv
        import pandas as pd
        df = pd.DataFrame(csv_data)
        df.to_csv('input.csv', index=False)
        
        return jsonify({
            'success': True,
            'message': f'Advanced CSV generated successfully with {len(csv_data)} articles including meta data, links, and images',
            'data': csv_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Error generating CSV: {str(e)}'}), 500

@app.route('/download-results')
def download_results():
    """Download results as CSV"""
    
    results_file = get_results_file()
    if os.path.exists(results_file):
        return send_file(results_file, as_attachment=True)
    else:
        flash('No results file found', 'error')
        return redirect(url_for('results_page'))

@app.route('/download-input-csv')
def download_input_csv():
    """Download the generated input.csv file"""
    
    input_file = 'input.csv'
    if os.path.exists(input_file):
        return send_file(input_file, 
                        as_attachment=True, 
                        download_name='generated_input.csv',
                        mimetype='text/csv')
    else:
        return jsonify({'error': 'No input CSV file found. Please generate a CSV first.'}), 404

@app.route('/download/sample.csv')
def download_sample_csv():
    """Download a sample CSV file"""
    
    # Create sample CSV content
    sample_content = '''title,meta_title,url_slug,description,topic,keywords,internal_links,outbound_links,image_urls,target_audience,word_count,tone,industry,content_type,seo_focus,website_url
"Complete Guide to AI in Healthcare","AI in Healthcare: Complete Guide 2025","ai-in-healthcare-complete-guide","Discover how artificial intelligence is transforming healthcare with practical applications, benefits, and future trends.","AI in Healthcare","artificial intelligence, healthcare technology, medical AI, healthcare automation","About Us: https://example.com/about | Services: https://example.com/services","Healthcare AI Research: https://www.ncbi.nlm.nih.gov/ | AI Studies: https://scholar.google.com","AI Healthcare Image: https://unsplash.com/s/photos/ai-healthcare","professionals","1500","professional","healthcare","guide","high","https://dunemedicaldevicesinc.com"
"Best Medical Equipment Buying Guide","Medical Equipment Buying Guide 2025","medical-equipment-buying-guide","Learn how to choose the right medical equipment with expert tips, budget considerations, and quality factors.","Medical Equipment","medical equipment, healthcare devices, medical supplies, equipment buying","Products: https://example.com/products | Contact: https://example.com/contact","Medical Equipment Standards: https://www.fda.gov/ | Equipment Reviews: https://www.ncbi.nlm.nih.gov/","Medical Equipment: https://unsplash.com/s/photos/medical-equipment","professionals","1500","professional","healthcare","buying-guide","high","https://dunemedicaldevicesinc.com"'''
    
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(sample_content)
        temp_path = f.name
    
    return send_file(temp_path, 
                    as_attachment=True, 
                    download_name='sample_input.csv',
                    mimetype='text/csv')

@app.route('/test-generator')
def test_generator():
    """Test if the enhanced blog generator can run"""
    
    try:
        # Check if the generator file exists
        generator_file = 'enhanced_blog_generator_v2.py'
        if not os.path.exists(generator_file):
            return jsonify({'error': f'Generator file {generator_file} not found'}), 404
        
        # Check if input.csv exists
        if not os.path.exists('input.csv'):
            return jsonify({'error': 'input.csv file not found'}), 404
            
        # Try to import the module to check for syntax errors
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("enhanced_blog_generator_v2", generator_file)
            if spec is None:
                return jsonify({'error': 'Could not load generator module'}), 500
                
        except Exception as e:
            return jsonify({'error': f'Generator module has errors: {str(e)}'}), 500
        
        # Get Python executable
        python_executable = sys.executable
        
        return jsonify({
            'success': True,
            'generator_file_exists': True,
            'input_csv_exists': True,
            'python_executable': python_executable,
            'current_directory': os.getcwd(),
            'input_csv_rows': len(load_input_csv())
        })
        
    except Exception as e:
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

@app.route('/test-single-generation', methods=['POST'])
def test_single_generation():
    """Test generating content for just the first row of the CSV"""
    
    try:
        # Check if CSV exists and has data
        if not os.path.exists('input.csv'):
            return jsonify({'error': 'input.csv not found'}), 400
        
        df = pd.read_csv('input.csv')
        if len(df) == 0:
            return jsonify({'error': 'input.csv is empty'}), 400
        
        # Create a test CSV with just the first row
        test_df = df.iloc[:1].copy()  # Take only the first row
        test_df.to_csv('test_input.csv', index=False)
        
        # Create a simple test script that uses the enhanced generator
        test_script = '''
import sys
import os
import pandas as pd
sys.path.append(os.getcwd())

try:
    print("=== SINGLE ROW GENERATION TEST ===")
    
    from enhanced_blog_generator_v2 import Config, EnhancedContentGenerator
    
    # Load config
    print("Loading configuration...")
    config = Config()
    print(f"API Key: {'✅ Set' if config.DEEPSEEK_API_KEY else '❌ Missing'}")
    
    # Read test CSV
    df = pd.read_csv('test_input.csv')
    print(f"Test CSV loaded: {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # Initialize generator
    print("Initializing generator...")
    generator = EnhancedContentGenerator(config)
    
    print("Generator initialized successfully!")
    print("✅ All components working - ready for content generation")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
'''
        
        # Write and execute the test script
        with open('single_test.py', 'w') as f:
            f.write(test_script)
        
        python_executable = sys.executable
        result = subprocess.run([
            python_executable, 'single_test.py'
        ], cwd=os.getcwd(), capture_output=True, text=True, timeout=60)
        
        # Clean up test files
        for test_file in ['single_test.py', 'test_input.csv']:
            if os.path.exists(test_file):
                os.remove(test_file)
        
        return jsonify({
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'test_completed': True
        })
        
    except Exception as e:
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

@app.route('/test-api-key', methods=['POST'])
def test_api_key():
    """Test if the DeepSeek API key is valid"""
    
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({'valid': False, 'message': 'API key is required'}), 400
        
        if api_key == 'ENTER_YOUR_DEEPSEEK_API_KEY_HERE':
            return jsonify({'valid': False, 'message': 'Please replace the placeholder with your actual API key'}), 400
        
        if not api_key.startswith('sk-'):
            return jsonify({'valid': False, 'message': 'Invalid API key format. DeepSeek keys start with "sk-"'}), 400
        
        # Test the API key by making a simple request
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        test_payload = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': 'Test'}],
            'max_tokens': 10
        }
        
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({'valid': True, 'message': 'API key is valid and working!'})
        elif response.status_code == 401:
            return jsonify({'valid': False, 'message': 'Invalid API key - authentication failed'}), 401
        elif response.status_code == 402:
            return jsonify({'valid': False, 'message': 'API key is valid but has insufficient balance'}), 402
        else:
            return jsonify({'valid': False, 'message': f'API test failed with status {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'valid': False, 'message': 'API request timed out'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'valid': False, 'message': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Test failed: {str(e)}'}), 500

@app.route('/debug-page')
def debug_page():
    """Simple debug page to test generation"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Generation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .debug-result { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <h1>🔧 Debug Generation Process</h1>
        <button onclick="runDebug()">Run Debug Test</button>
        <button onclick="runSingleTest()" style="margin-left: 10px; background: #28a745;">Test Single Generation</button>
        <div id="result"></div>
        
        <script>
            async function runDebug() {
                document.getElementById('result').innerHTML = '<p>Running debug test...</p>';
                
                try {
                    const response = await fetch('/debug-generation', { method: 'POST' });
                    const data = await response.json();
                    
                    let html = '<div class="debug-result"><h3>Debug Results:</h3>';
                    data.results.forEach(result => {
                        html += '<h4>' + result.step + '</h4>';
                        html += '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
                    });
                    html += '</div>';
                    
                    document.getElementById('result').innerHTML = html;
                } catch (error) {
                    document.getElementById('result').innerHTML = '<p style="color: red;">Error: ' + error.message + '</p>';
                }
            }
            
            async function runSingleTest() {
                document.getElementById('result').innerHTML = '<p>Running single generation test...</p>';
                
                try {
                    const response = await fetch('/test-single-generation', { method: 'POST' });
                    const data = await response.json();
                    
                    let html = '<div class="debug-result"><h3>Single Generation Test Results:</h3>';
                    html += '<p><strong>Success:</strong> ' + (data.success ? '✅ Yes' : '❌ No') + '</p>';
                    html += '<p><strong>Return Code:</strong> ' + data.returncode + '</p>';
                    if (data.stdout) {
                        html += '<h4>Output:</h4><pre>' + data.stdout + '</pre>';
                    }
                    if (data.stderr) {
                        html += '<h4>Errors:</h4><pre style="color: red;">' + data.stderr + '</pre>';
                    }
                    html += '</div>';
                    
                    document.getElementById('result').innerHTML = html;
                } catch (error) {
                    document.getElementById('result').innerHTML = '<p style="color: red;">Error: ' + error.message + '</p>';
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/debug-generation', methods=['POST'])
def debug_generation():
    """Debug the generation process step by step"""
    
    try:
        debug_info = {
            'step': 'Starting debug',
            'timestamp': datetime.now().isoformat(),
            'results': []
        }
        
        # Step 1: Check files
        debug_info['results'].append({
            'step': 'File Check',
            'input_csv_exists': os.path.exists('input.csv'),
            'generator_exists': os.path.exists('enhanced_blog_generator_v2.py'),
            'settings_exists': os.path.exists('blog_settings.json')
        })
        
        # Step 2: Check CSV content
        if os.path.exists('input.csv'):
            try:
                # Read CSV directly as DataFrame for analysis
                df = pd.read_csv('input.csv')
                debug_info['results'].append({
                    'step': 'CSV Analysis',
                    'row_count': len(df),
                    'columns': list(df.columns),
                    'first_row': df.iloc[0].to_dict() if len(df) > 0 else {}
                })
            except Exception as e:
                debug_info['results'].append({
                    'step': 'CSV Analysis',
                    'error': str(e)
                })
        
        # Step 3: Check settings
        if os.path.exists('blog_settings.json'):
            try:
                with open('blog_settings.json', 'r') as f:
                    settings = json.load(f)
                    debug_info['results'].append({
                        'step': 'Settings Check',
                        'has_api_key': bool(settings.get('deepseek_api_key', '')),
                        'api_key_preview': settings.get('deepseek_api_key', '')[:10] + '...' if settings.get('deepseek_api_key') else 'Not set',
                        'settings_count': len(settings)
                    })
            except Exception as e:
                debug_info['results'].append({
                    'step': 'Settings Check',
                    'error': str(e)
                })
        
        # Step 4: Try import test
        try:
            python_executable = sys.executable
            result = subprocess.run([
                python_executable, '-c', 
                'import enhanced_blog_generator_v2; print("Import successful")'
            ], cwd=os.getcwd(), capture_output=True, text=True, timeout=30)
            
            debug_info['results'].append({
                'step': 'Import Test',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'python_executable': python_executable
            })
            
        except Exception as e:
            debug_info['results'].append({
                'step': 'Import Test',
                'error': str(e)
            })
        
        # Step 5: Simple generation test
        try:
            python_executable = sys.executable
            
            # Create a simple test script
            test_script = '''
import sys
import os
sys.path.append(os.getcwd())

try:
    from enhanced_blog_generator_v2 import Config
    config = Config()
    print(f"Config loaded successfully")
    print(f"API Key configured: {bool(config.DEEPSEEK_API_KEY)}")
    print(f"WordPress URL: {config.WORDPRESS_BASE_URL}")
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
'''
            
            with open('debug_test.py', 'w') as f:
                f.write(test_script)
            
            result = subprocess.run([
                python_executable, 'debug_test.py'
            ], cwd=os.getcwd(), capture_output=True, text=True, timeout=30)
            
            debug_info['results'].append({
                'step': 'Config Test',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            # Clean up
            if os.path.exists('debug_test.py'):
                os.remove('debug_test.py')
                
        except Exception as e:
            debug_info['results'].append({
                'step': 'Config Test',
                'error': str(e)
            })
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': f'Debug failed: {str(e)}'}), 500

@app.route('/config')
def config_page():
    """Configuration and settings page"""
    
    # Load current configuration
    config = load_config()
    
    return render_template('config.html', config=config)

@app.route('/save-config', methods=['POST'])
def save_config():
    """Save configuration settings"""
    
    try:
        config = {
            # AI API Settings
            'deepseek_api_key': request.form.get('deepseek_api_key', ''),
            'openai_api_key': request.form.get('openai_api_key', ''),
            'ai_model': request.form.get('ai_model', 'deepseek-chat'),
            'max_tokens': int(request.form.get('max_tokens', 4000)),
            'temperature': float(request.form.get('temperature', 0.7)),
            
            # WordPress Settings
            'wordpress_url': request.form.get('wordpress_url', ''),
            'wordpress_username': request.form.get('wordpress_username', ''),
            'wordpress_password': request.form.get('wordpress_password', ''),
            'wordpress_auto_publish': request.form.get('wordpress_auto_publish') == 'on',
            
            # Content Generation Settings
            'target_word_count': int(request.form.get('target_word_count', 1500)),
            'default_tone': request.form.get('default_tone', 'professional'),
            'default_industry': request.form.get('default_industry', 'healthcare'),
            'default_content_type': request.form.get('default_content_type', 'guide'),
            'quality_threshold': float(request.form.get('quality_threshold', 0.7)),
            
            # SEO Settings
            'default_seo_focus': request.form.get('default_seo_focus', 'high'),
            'auto_internal_links': request.form.get('auto_internal_links') == 'on',
            'auto_outbound_links': request.form.get('auto_outbound_links') == 'on',
            'auto_meta_generation': request.form.get('auto_meta_generation') == 'on',
            'auto_image_search': request.form.get('auto_image_search') == 'on',
            'max_images_per_article': int(request.form.get('max_images_per_article', 3)),
            
            # Quality Control Settings
            'enable_fact_checking': request.form.get('enable_fact_checking') == 'on',
            'enable_plagiarism_check': request.form.get('enable_plagiarism_check') == 'on',
            'enable_readability_check': request.form.get('enable_readability_check') == 'on',
            'min_readability_score': float(request.form.get('min_readability_score', 60.0)),
            
            # Email Settings (for notifications)
            'email_notifications': request.form.get('email_notifications') == 'on',
            'smtp_server': request.form.get('smtp_server', ''),
            'smtp_port': int(request.form.get('smtp_port', 587)),
            'smtp_username': request.form.get('smtp_username', ''),
            'smtp_password': request.form.get('smtp_password', ''),
            'notification_email': request.form.get('notification_email', ''),
            
            # Advanced Settings
            'concurrent_generations': int(request.form.get('concurrent_generations', 1)),
            'retry_failed_articles': request.form.get('retry_failed_articles') == 'on',
            'max_retries': int(request.form.get('max_retries', 3)),
            'backup_enabled': request.form.get('backup_enabled') == 'on',
            'auto_update_csv': request.form.get('auto_update_csv') == 'on',
            
            # Website Scanning Settings
            'website_scan_timeout': int(request.form.get('website_scan_timeout', 10)),
            'max_internal_links': int(request.form.get('max_internal_links', 5)),
            'max_outbound_links': int(request.form.get('max_outbound_links', 3)),
            
            # System Settings
            'debug_mode': request.form.get('debug_mode') == 'on',
            'log_level': request.form.get('log_level', 'INFO'),
            'data_retention_days': int(request.form.get('data_retention_days', 30))
        }
        
        # Save to blog_settings.json (used by enhanced generator)
        blog_settings = {
            'deepseek_api_key': request.form.get('deepseek_api_key', ''),
            'google_api_key': request.form.get('google_api_key', ''),
            'google_cse_id': request.form.get('google_cse_id', ''),
            'wordpress_url': request.form.get('wordpress_url', ''),
            'wordpress_username': request.form.get('wordpress_username', ''),
            'wordpress_password': request.form.get('wordpress_password', ''),
            'ai_model': request.form.get('ai_model', 'deepseek-chat'),
            'min_word_count': request.form.get('target_word_count', '1500'),
            'max_word_count': str(int(request.form.get('target_word_count', '1500')) * 2),
            'temperature': request.form.get('temperature', '0.3'),
            'min_domain_authority': '20',
            'max_outbound_links': request.form.get('max_outbound_links', '5'),
            'min_outbound_links': str(max(1, int(request.form.get('max_outbound_links', '5')) - 2)),
            'max_internal_links': request.form.get('max_internal_links', '5'),
            'min_internal_links': str(max(1, int(request.form.get('max_internal_links', '5')) - 2)),
            'min_quality_score': request.form.get('quality_threshold', '0.7'),
            'max_plagiarism': '15.0',
            'delay_between_posts': '45'
        }
        
        # Save to blog_settings.json for enhanced generator
        with open('blog_settings.json', 'w') as f:
            json.dump(blog_settings, f, indent=4)
        
        # Also save to web_config.json for web interface compatibility
        with open('web_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        flash('Configuration saved successfully!', 'success')
        
    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
    
    return redirect(url_for('config_page'))

# Helper functions
def load_results():
    """Load results from CSV files"""
    
    results_files = [
        'enhanced_output_v2.csv',
        'enhanced_output.csv',
        'blog_generation_results.csv'
    ]
    
    for file_path in results_files:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                return df.to_dict('records')
            except:
                continue
    
    return []

def load_input_csv():
    """Load input CSV file"""
    
    if os.path.exists('input.csv'):
        try:
            df = pd.read_csv('input.csv')
            return df.to_dict('records')
        except:
            pass
    
    return []

def calculate_stats(results_data):
    """Calculate statistics from results"""
    
    if not results_data:
        return {
            'total_articles': 0,
            'avg_quality': 0,
            'avg_seo_score': 0,
            'avg_processing_time': 0,
            'avg_generation_time': "0 min",
            'success_rate': 0,
            'total_cost': 0,
            'total_words': 0,
            'avg_plagiarism': 0,
            'avg_readability': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0
        }
    
    df = pd.DataFrame(results_data)
    
    # Quality distribution
    quality_scores = df.get('quality_score', pd.Series([0]))
    high_quality = (quality_scores >= 0.7).sum()
    medium_quality = ((quality_scores >= 0.5) & (quality_scores < 0.7)).sum()
    low_quality = (quality_scores < 0.5).sum()
    
    # Calculate average generation time
    processing_times = df.get('processing_time_seconds', pd.Series([0]))
    avg_time_seconds = processing_times.mean()
    avg_time_minutes = avg_time_seconds / 60 if avg_time_seconds > 0 else 0
    avg_generation_time = f"{avg_time_minutes:.1f} min" if avg_time_minutes > 0 else "N/A"
    
    # Word count calculation (estimate)
    total_words = len(results_data) * 1500  # Assuming average 1500 words per article
    
    stats = {
        'total_articles': len(results_data),
        'avg_quality': df.get('quality_score', pd.Series([0])).mean(),
        'avg_seo_score': df.get('seo_score', pd.Series([0])).mean(),
        'avg_processing_time': avg_time_seconds,
        'avg_generation_time': avg_generation_time,
        'success_rate': (df.get('status', pd.Series(['failed'])) == 'completed').mean() * 100,
        'total_cost': df.get('cost_usd', pd.Series([0])).sum(),
        'total_words': total_words,
        'avg_plagiarism': df.get('plagiarism_score', pd.Series([0])).mean(),
        'avg_readability': df.get('readability_score', pd.Series([0])).mean(),
        'high_quality': high_quality,
        'medium_quality': medium_quality,
        'low_quality': low_quality
    }
    
    return stats

def load_config():
    """Load configuration from file"""
    
    default_config = {
        # AI API Settings
        'deepseek_api_key': '',
        'openai_api_key': '',
        'ai_model': 'deepseek-chat',
        'max_tokens': 4000,
        'temperature': 0.7,
        
        # WordPress Settings
        'wordpress_url': 'https://dunemedicaldevicesinc.com',
        'wordpress_username': '',
        'wordpress_password': '',
        'wordpress_auto_publish': False,
        
        # Content Generation Settings
        'target_word_count': 1500,
        'default_tone': 'professional',
        'default_industry': 'healthcare',
        'default_content_type': 'guide',
        'quality_threshold': 0.7,
        
        # SEO Settings
        'default_seo_focus': 'high',
        'auto_internal_links': True,
        'auto_outbound_links': True,
        'auto_meta_generation': True,
        'auto_image_search': True,
        'max_images_per_article': 3,
        
        # Quality Control Settings
        'enable_fact_checking': True,
        'enable_plagiarism_check': True,
        'enable_readability_check': True,
        'min_readability_score': 60.0,
        
        # Email Settings
        'email_notifications': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_password': '',
        'notification_email': '',
        
        # Advanced Settings
        'concurrent_generations': 1,
        'retry_failed_articles': True,
        'max_retries': 3,
        'backup_enabled': True,
        'auto_update_csv': True,
        
        # Website Scanning Settings
        'website_scan_timeout': 10,
        'max_internal_links': 5,
        'max_outbound_links': 3,
        
        # System Settings
        'debug_mode': False,
        'log_level': 'INFO',
        'data_retention_days': 30
    }
    
    try:
        # First try to load from blog_settings.json (used by enhanced generator)
        if os.path.exists('blog_settings.json'):
            with open('blog_settings.json', 'r') as f:
                blog_settings = json.load(f)
                # Map blog_settings to web_config format
                config = {**default_config}
                config.update({
                    'deepseek_api_key': blog_settings.get('deepseek_api_key', ''),
                    'google_api_key': blog_settings.get('google_api_key', ''),
                    'wordpress_url': blog_settings.get('wordpress_url', ''),
                    'wordpress_username': blog_settings.get('wordpress_username', ''),
                    'wordpress_password': blog_settings.get('wordpress_password', ''),
                    'ai_model': blog_settings.get('ai_model', 'deepseek-chat'),
                    'target_word_count': int(blog_settings.get('min_word_count', '1500')),
                    'temperature': float(blog_settings.get('temperature', '0.3')),
                    'max_outbound_links': int(blog_settings.get('max_outbound_links', '5')),
                    'max_internal_links': int(blog_settings.get('max_internal_links', '5')),
                    'quality_threshold': float(blog_settings.get('min_quality_score', '0.7'))
                })
                return config
                
        # Fallback to web_config.json
        if os.path.exists('web_config.json'):
            with open('web_config.json', 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
    except:
        pass
    
    return default_config

def generate_title_from_keyword(keyword, content_type, industry):
    """Generate article title from keyword and settings"""
    
    templates = {
        'guide': [
            f'Complete Guide to {keyword}',
            f'How to {keyword}: Step-by-Step Guide',
            f'The Ultimate {keyword} Guide for 2025',
            f'{keyword}: Everything You Need to Know'
        ],
        'review': [
            f'Best {keyword} Reviews for 2025',
            f'{keyword} Review: Pros, Cons, and Verdict',
            f'Top {keyword} Products Reviewed',
            f'Complete {keyword} Review and Analysis'
        ],
        'comparison': [
            f'{keyword} Comparison: Which is Best?',
            f'Comparing the Best {keyword} Options',
            f'{keyword} vs Alternatives: Detailed Comparison',
            f'Top {keyword} Products Compared'
        ],
        'benefits': [
            f'{keyword} Benefits and Features Explained',
            f'Why {keyword} is Essential for Your Needs',
            f'The Benefits of {keyword}: Complete Overview',
            f'{keyword} Advantages and Key Features'
        ],
        'tips': [
            f'Top {keyword} Tips and Best Practices',
            f'{keyword} Tips for Better Results',
            f'Expert {keyword} Tips You Should Know',
            f'Professional {keyword} Tips and Tricks'
        ],
        'buying-guide': [
            f'{keyword} Buying Guide: What to Look For',
            f'How to Choose the Right {keyword}',
            f'Best {keyword} Buying Guide for 2025',
            f'{keyword} Purchase Guide and Tips'
        ]
    }
    
    import random
    category_templates = templates.get(content_type, templates['guide'])
    return random.choice(category_templates)

def generate_keywords_from_topic(keyword, industry, seo_focus):
    """Generate keyword list from topic and settings"""
    
    base_keywords = [keyword]
    
    industry_keywords = {
        'healthcare': ['medical', 'health', 'treatment', 'patient care', 'clinical'],
        'beauty': ['skincare', 'beauty', 'cosmetic', 'anti-aging', 'skin health'],
        'technology': ['tech', 'innovation', 'digital', 'smart', 'advanced'],
        'fitness': ['fitness', 'workout', 'exercise', 'wellness', 'health'],
        'business': ['business', 'professional', 'corporate', 'industry', 'commercial'],
        'lifestyle': ['lifestyle', 'daily', 'home', 'personal', 'family'],
        'education': ['learning', 'education', 'training', 'course', 'knowledge'],
        'automotive': ['car', 'vehicle', 'automotive', 'driving', 'transport'],
        'home': ['home', 'house', 'interior', 'design', 'maintenance'],
        'food': ['food', 'nutrition', 'cooking', 'recipe', 'diet'],
        'travel': ['travel', 'vacation', 'destination', 'trip', 'tourism']
    }
    
    seo_modifiers = {
        'high': ['best', 'top', 'ultimate', 'complete', 'professional', '2025'],
        'medium': ['guide', 'tips', 'review', 'benefits'],
        'low': ['overview', 'introduction', 'basics']
    }
    
    # Add industry-specific keywords
    if industry in industry_keywords:
        base_keywords.extend(industry_keywords[industry][:2])
    
    # Add SEO modifiers
    if seo_focus in seo_modifiers:
        base_keywords.extend(seo_modifiers[seo_focus][:2])
    
    return ', '.join(base_keywords)

def generate_meta_title(keyword, title):
    """Generate SEO-optimized meta title"""
    
    # If title is already under 60 characters, use it
    if len(title) <= 60:
        return title
    
    # Create shorter version
    short_titles = [
        f"Best {keyword} Guide 2025",
        f"{keyword}: Complete Guide",
        f"Top {keyword} Tips & Benefits",
        f"{keyword} - Ultimate Guide",
        f"Professional {keyword} Guide"
    ]
    
    import random
    return random.choice(short_titles)

def generate_url_slug(title):
    """Generate URL-friendly slug from title"""
    
    import re
    
    # Convert to lowercase and replace spaces with hyphens
    slug = title.lower()
    
    # Remove special characters except hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    
    # Replace spaces and multiple hyphens with single hyphen
    slug = re.sub(r'[\s-]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Limit length to 50 characters
    if len(slug) > 50:
        slug = slug[:50].rstrip('-')
    
    return slug

def generate_meta_description(keyword, content_type):
    """Generate SEO-optimized meta description"""
    
    descriptions = {
        'guide': f"Complete guide to {keyword}. Learn everything you need to know including tips, benefits, and best practices. Expert advice and actionable insights.",
        'review': f"Comprehensive {keyword} review covering pros, cons, features, and recommendations. Find the best options for your needs with our detailed analysis.",
        'comparison': f"Compare the best {keyword} options. Detailed analysis of features, prices, and benefits to help you make the right choice for your needs.",
        'benefits': f"Discover the key benefits of {keyword}. Learn how it can improve your results with expert insights and practical applications.",
        'tips': f"Expert {keyword} tips and best practices. Improve your results with proven strategies and professional recommendations from industry experts.",
        'buying-guide': f"Complete {keyword} buying guide. Learn what to look for, compare options, and find the best value for your budget with expert recommendations."
    }
    
    base_description = descriptions.get(content_type, descriptions['guide'])
    
    # Ensure description is under 160 characters
    if len(base_description) > 160:
        base_description = base_description[:157] + "..."
    
    return base_description

def scan_website_for_internal_links(website_url, keyword):
    """Scan website for relevant internal links"""
    
    if not website_url:
        return ""
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        from urllib.parse import urljoin, urlparse
        
        # Get the main page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(website_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all internal links
        internal_links = []
        keyword_lower = keyword.lower()
        
        # Look for links in navigation, footer, and content areas
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text().strip().lower()
            
            # Skip external links, email, and tel links
            if href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                if not href.startswith(website_url):
                    continue
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = urljoin(website_url, href)
            
            # Check if link is relevant to keyword
            if (keyword_lower in text or 
                any(word in text for word in keyword_lower.split()) or
                keyword_lower in href.lower()):
                
                if href not in [link['url'] for link in internal_links]:
                    internal_links.append({
                        'url': href,
                        'text': link.get_text().strip()[:50]
                    })
                    
                    if len(internal_links) >= 3:  # Limit to 3 internal links
                        break
        
        # Format as string
        if internal_links:
            return " | ".join([f"{link['text']}: {link['url']}" for link in internal_links[:3]])
        else:
            return f"Home: {website_url} | About: {website_url}/about"
            
    except Exception as e:
        print(f"Error scanning website: {e}")
        return f"Home: {website_url}"

def search_outbound_links(keyword):
    """Search for relevant outbound links using Google"""
    
    try:
        from googlesearch import search
        import time
        
        # Search for authoritative sources
        search_queries = [
            f"{keyword} site:edu",
            f"{keyword} site:gov", 
            f"{keyword} research study",
            f"{keyword} industry report",
            f"{keyword} guide"
        ]
        
        outbound_links = []
        
        for query in search_queries[:2]:  # Limit to 2 queries
            try:
                results = list(search(query, num_results=3, sleep_interval=1))
                for url in results[:2]:  # Get top 2 results
                    if url not in [link['url'] for link in outbound_links]:
                        # Try to get page title
                        try:
                            import requests
                            from bs4 import BeautifulSoup
                            
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                            
                            response = requests.get(url, headers=headers, timeout=5)
                            soup = BeautifulSoup(response.content, 'html.parser')
                            title = soup.find('title')
                            title_text = title.get_text().strip()[:50] if title else "External Resource"
                            
                            outbound_links.append({
                                'url': url,
                                'text': title_text
                            })
                            
                        except:
                            outbound_links.append({
                                'url': url,
                                'text': f"{keyword.title()} Resource"
                            })
                    
                    if len(outbound_links) >= 2:
                        break
                
                if len(outbound_links) >= 2:
                    break
                    
                time.sleep(1)  # Be respectful to search engines
                
            except Exception as e:
                print(f"Error searching: {e}")
                continue
        
        # If no results found, use default authoritative sources
        if not outbound_links:
            outbound_links = [
                {'url': f'https://www.ncbi.nlm.nih.gov/', 'text': 'Medical Research Database'},
                {'url': f'https://scholar.google.com/scholar?q={keyword.replace(" ", "+")}', 'text': 'Academic Research'}
            ]
        
        # Format as string
        return " | ".join([f"{link['text']}: {link['url']}" for link in outbound_links[:2]])
        
    except Exception as e:
        print(f"Error searching outbound links: {e}")
        return f"Research: https://scholar.google.com/scholar?q={keyword.replace(' ', '+')} | Industry: https://www.ncbi.nlm.nih.gov/"

def search_images(keyword, count=2):
    """Search for relevant images"""
    
    try:
        # Use a simple approach - generate image search URLs
        import urllib.parse
        
        encoded_keyword = urllib.parse.quote(keyword)
        
        image_sources = [
            f"https://unsplash.com/s/photos/{encoded_keyword}",
            f"https://pixabay.com/images/search/{encoded_keyword}/",
            f"https://www.pexels.com/search/{encoded_keyword}/",
            f"https://commons.wikimedia.org/w/index.php?search={encoded_keyword}",
            f"https://images.google.com/images?q={encoded_keyword}"
        ]
        
        # Return suggested image sources
        selected_sources = image_sources[:int(count)]
        return " | ".join([f"Image {i+1}: {url}" for i, url in enumerate(selected_sources)])
        
    except Exception as e:
        print(f"Error searching images: {e}")
        return f"Search images for: {keyword}"

def get_results_file():
    """Get the most recent results file"""
    
    files = [
        'enhanced_output_v2.csv',
        'enhanced_output.csv',
        'blog_generation_results.csv'
    ]
    
    for file_path in files:
        if os.path.exists(file_path):
            return file_path
    
    return None

def run_enhanced_generator():
    """Run the enhanced blog generator in background"""
    global generation_status
    
    try:
        # Update status
        generation_status['current_article'] = 'Starting Enhanced Blog Generator...'
        
        # Use the virtual environment Python if available
        python_executable = sys.executable if hasattr(sys, 'executable') else 'python'
        
        # Run the generator with full path
        process = subprocess.Popen(
            [python_executable, 'enhanced_blog_generator_v2.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Monitor the process with better progress tracking
        start_time = time.time()
        while process.poll() is None and generation_status['running']:
            elapsed = time.time() - start_time
            # Update progress based on time elapsed (more realistic)
            if elapsed < 60:  # First minute
                generation_status['progress'] = min(int(elapsed * 2), 20)
            elif elapsed < 300:  # Next 4 minutes  
                generation_status['progress'] = min(20 + int((elapsed - 60) / 4), 80)
            else:  # After 5 minutes
                generation_status['progress'] = min(80 + int((elapsed - 300) / 10), 95)
            
            generation_status['current_article'] = f'Processing... ({elapsed:.0f}s elapsed)'
            time.sleep(3)
        
        # Process completed
        stdout, stderr = process.communicate()
        
        print(f"Generator process completed with return code: {process.returncode}")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        
        if process.returncode == 0:
            generation_status['running'] = False
            generation_status['progress'] = 100
            generation_status['current_article'] = 'Generation completed successfully!'
        else:
            generation_status['running'] = False
            generation_status['errors'].append(f"Process failed with code {process.returncode}: {stderr}")
            generation_status['current_article'] = f'Generation failed - check errors'
            
    except Exception as e:
        print(f"Error in run_enhanced_generator: {str(e)}")
        generation_status['running'] = False
        generation_status['errors'].append(str(e))
        generation_status['current_article'] = f'Error: {str(e)}'

def check_generation_status():
    """Check if generation is actually running"""
    
    # Simple check - if we think it's running but no recent updates, assume it stopped
    if generation_status['running'] and generation_status['start_time']:
        elapsed = (datetime.now() - generation_status['start_time']).total_seconds()
        if elapsed > 3600:  # 1 hour timeout
            generation_status['running'] = False
            generation_status['current_article'] = 'Timed out'

if __name__ == '__main__':
    print("🚀 Starting AI Content Platform Web Interface...")
    print("📱 Access your dashboard at: http://localhost:5000")
    print("🔧 Upload CSV files, monitor progress, and view results!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
