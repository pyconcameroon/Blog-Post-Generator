import os
import json
import base64
import requests

OUTFILE = os.path.join('logs', 'wp_real_test_output.txt')

def write(msg):
    print(msg)
    try:
        os.makedirs(os.path.dirname(OUTFILE), exist_ok=True)
        with open(OUTFILE, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except Exception:
        # If we can't write to the logfile, at least don't crash; printing is sufficient for now
        pass

# Load config from environment or blog_settings.json
WP_URL = os.environ.get('WORDPRESS_URL')
WP_USER = os.environ.get('WORDPRESS_USERNAME')
WP_PASS = os.environ.get('WORDPRESS_PASSWORD')

if not (WP_URL and WP_USER and WP_PASS):
    try:
        with open('blog_settings.json', 'r') as f:
            cfg = json.load(f)
            WP_URL = WP_URL or cfg.get('wordpress_url')
            WP_USER = WP_USER or cfg.get('wordpress_username')
            WP_PASS = WP_PASS or cfg.get('wordpress_password')
    except Exception as e:
        write('No credentials found in env or blog_settings.json: ' + str(e))
        raise SystemExit(1)

# Normalize URL
if WP_URL.endswith('/wp-json/wp/v2'):
    base = WP_URL[:-len('/wp-json/wp/v2')]
else:
    base = WP_URL
api_base = base.rstrip('/') + '/wp-json/wp/v2'

# Prepare auth header
auth_header = 'Basic ' + base64.b64encode(f"{WP_USER}:{WP_PASS}".encode('utf-8')).decode('utf-8')
headers = {
    'Authorization': auth_header,
    'Content-Type': 'application/json'
}

write('Testing WordPress API: creating draft post...')
write('Endpoint: ' + api_base + '/posts')
write('Using username: ' + WP_USER)

post_payload = {
    'title': 'Automated test post - please delete',
    'content': 'This is a real test post created by the enhanced_blog_generator test script. It will be deleted immediately.',
    'status': 'draft'
}

try:
    r = requests.post(f"{api_base}/posts", headers=headers, json=post_payload, timeout=20)
    write('Create status: ' + str(r.status_code))
    try:
        write('Create response: ' + r.text[:5000])
    except Exception as e:
        write('Failed to print create response: ' + str(e))

    if r.status_code in (200, 201):
        try:
            post_id = r.json().get('id')
            if post_id:
                write('Post created with id: ' + str(post_id))
                # Now delete it
                dr = requests.delete(f"{api_base}/posts/{post_id}", headers=headers, params={'force': True}, timeout=20)
                write('Delete status: ' + str(dr.status_code))
                try:
                    write('Delete response: ' + dr.text[:5000])
                except Exception:
                    write('Failed to print delete response')
            else:
                write('Warning: post created but no id returned')
        except Exception as e:
            write('Error parsing create response: ' + str(e))
    else:
        write('Failed to create post; check credentials and REST API endpoint')
        try:
            write('Response body: ' + r.text[:5000])
        except Exception as e:
            write('Failed to print response body: ' + str(e))

except Exception as e:
    write('Request failed: ' + str(e))
