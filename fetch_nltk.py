import nltk
import os
nltk_data_dir = r"C:\Users\Code Farm\Desktop\scripts\BLOG_POST\ENVIRONMENT\nltk_data"
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)
print('NLTK data paths:', nltk.data.path)
for pkg in ['punkt','stopwords']:
    print('Downloading', pkg)
    nltk.download(pkg, download_dir=nltk_data_dir, quiet=True)
print('Done')
