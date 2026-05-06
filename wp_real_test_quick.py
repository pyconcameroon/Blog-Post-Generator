import os
import json
import base64
import requests

def load_creds():
    WP_URL = os.environ.get('WORDPRESS_URL')
    WP_USER = os.environ.get('WORDPRESS_USERNAME')
    WP_PASS = os.environ.get('WORDPRESS_PASSWORD')
    if not (WP_URL and WP_USER and WP_PASS):
        try:
            with open('blog_settings.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                WP_URL = WP_URL or cfg.get('wordpress_url')
                WP_USER = WP_USER or cfg.get('wordpress_username')
                WP_PASS = WP_PASS or cfg.get('wordpress_password')
        except Exception:
            pass
    return WP_URL, WP_USER, WP_PASS

def main():
    WP_URL, WP_USER, WP_PASS = load_creds()
    if not (WP_URL and WP_USER and WP_PASS):
        print('Missing WordPress credentials in env or blog_settings.json')
        raise SystemExit(2)

    if WP_URL.endswith('/wp-json/wp/v2'):
        base = WP_URL[:-len('/wp-json/wp/v2')]
    else:
        base = WP_URL
    api_base = base.rstrip('/') + '/wp-json/wp/v2'

    auth_header = 'Basic ' + base64.b64encode(f"{WP_USER}:{WP_PASS}".encode('utf-8')).decode('utf-8')
    headers = {'Authorization': auth_header, 'Content-Type': 'application/json'}

    print('Endpoint:', api_base + '/posts')
    print('Using username:', WP_USER)

    payload = {
        'title': 'Automated test post - quick check',
        'content': 'Quick test created by wp_real_test_quick.py',
        'status': 'draft'
    }

    try:
        r = requests.post(f"{api_base}/posts", headers=headers, json=payload, timeout=20)
        print('Create status:', r.status_code)
        try:
            print('Create response:', r.text[:8000])
        except Exception as e:
            print('Failed to print create response:', e)

        if r.status_code in (200,201):
            try:
                post_id = r.json().get('id')
                print('Post id:', post_id)
                dr = requests.delete(f"{api_base}/posts/{post_id}", headers=headers, params={'force': True}, timeout=20)
                print('Delete status:', dr.status_code)
                print('Delete response:', dr.text[:8000])
            except Exception as e:
                print('Error during delete or parsing:', e)
        else:
            print('Failed to create post; response body below:')
            print(r.text[:8000])
    except Exception as e:
        print('Request exception:', e)

if __name__ == '__main__':
    main()
