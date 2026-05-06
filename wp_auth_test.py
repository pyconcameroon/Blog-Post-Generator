import os
import base64
import requests

WORDPRESS_URL = os.environ.get('WORDPRESS_URL') or 'https://tiredealsnow.com/wp-json/wp/v2'
USERNAME = os.environ.get('WORDPRESS_USERNAME') or 'tires'
PASSWORD = os.environ.get('WORDPRESS_PASSWORD') or 'SpOQ Bi1R DxrI d1UM ya3q UbOT'

print('Testing WordPress API connectivity...')
print(f'Endpoint: {WORDPRESS_URL}/posts')
print(f'Using username: {USERNAME}')

headers = {
    'Authorization': 'Basic ' + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8')).decode('utf-8')
}

try:
    r = requests.get(f"{WORDPRESS_URL}/posts?per_page=1", headers=headers, timeout=10)
    print('Status code:', r.status_code)
    try:
        print('Response body:', r.text[:1000])
    except Exception as e:
        print('Failed to print response body:', str(e))
except Exception as e:
    print('Connection failed:', str(e))
