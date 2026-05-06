"""Free and open-source content analysis tools"""
import re
import nltk
import yake
import textstat
from bs4 import BeautifulSoup
from collections import Counter
from typing import List, Dict, Tuple, Optional
from newspaper import Article
from pytrends.request import TrendReq
import logging

# Initialize NLTK components
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class ContentAnalyzer:
    def __init__(self):
        self.kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=2,  # ngram size
            dedupLim=0.3,  # deduplication threshold
            top=20,
            features=None
        )
        self.pytrends = None  # Initialize only when needed
        
    def _get_pytrends(self):
        """Lazy initialization of PyTrends to avoid startup network issues"""
        if self.pytrends is None:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
            except Exception as e:
                logging.warning(f"Failed to initialize Google Trends: {str(e)}")
                self.pytrends = False  # Mark as failed to avoid retrying
        return self.pytrends if self.pytrends is not False else None
        
    def analyze_readability(self, content: str) -> Dict[str, any]:
        """Analyze content readability using multiple metrics"""
        # Clean HTML
        clean_text = BeautifulSoup(content, 'html.parser').get_text()
        
        # Calculate various readability scores
        scores = {
            'flesch_reading_ease': textstat.flesch_reading_ease(clean_text),
            'flesch_kincaid_grade': textstat.flesch_kincaid_grade(clean_text),
            'gunning_fog': textstat.gunning_fog(clean_text),
            'smog_index': textstat.smog_index(clean_text),
            'automated_readability_index': textstat.automated_readability_index(clean_text),
            'coleman_liau_index': textstat.coleman_liau_index(clean_text),
            'dale_chall_score': textstat.dale_chall_readability_score(clean_text)
        }
        
        # Get sentence info; fall back to naive splitting if NLTK data missing
        try:
            sentences = nltk.sent_tokenize(clean_text)
            words = nltk.word_tokenize(clean_text)
        except LookupError:
            # punkt or other tokenizer data missing; use naive fallbacks
            sentences = [s.strip() for s in clean_text.split('.') if s.strip()]
            words = clean_text.split()
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        
        # Generate suggestions
        suggestions = []
        if avg_sentence_length > 20:
            suggestions.append("Consider breaking down longer sentences")
        if scores['flesch_reading_ease'] < 60:
            suggestions.append("Content may be too complex for general audience")
        if len(sentences) < 10:
            suggestions.append("Consider adding more content for completeness")
            
        return {
            'scores': scores,
            'metrics': {
                'sentence_count': len(sentences),
                'word_count': len(words),
                'avg_sentence_length': avg_sentence_length
            },
            'suggestions': suggestions
        }
    
    def extract_keywords(self, content: str, title: str = "") -> List[Tuple[str, float]]:
        """Extract keywords using YAKE"""
        # Clean HTML
        clean_text = BeautifulSoup(content, 'html.parser').get_text()
        
        # Extract keywords
        keywords = self.kw_extractor.extract_keywords(f"{title}. {clean_text}")
        
        # Sort by score (lower is better in YAKE)
        try:
            return sorted(keywords, key=lambda x: x[1])
        except Exception:
            # If YAKE returns unexpected format, coerce to strings with dummy scores
            return [(k if isinstance(k, str) else str(k), 0.0) for k in keywords]
    
    def analyze_trends(self, keywords: List[str]) -> Dict[str, List[int]]:
        """Analyze keyword trends using PyTrends"""
        try:
            # Get PyTrends instance (lazy-loaded)
            pytrends = self._get_pytrends()
            if not pytrends:
                logging.warning("Google Trends not available - skipping trend analysis")
                return {}
            
            # Get top 5 keywords
            top_keywords = keywords[:5]
            
            # Build payload
            pytrends.build_payload(top_keywords, timeframe='today 12-m')
            
            # Get interest over time
            interest_over_time_df = pytrends.interest_over_time()
            
            return {kw: interest_over_time_df[kw].tolist() 
                   for kw in top_keywords if kw in interest_over_time_df.columns}
        except Exception as e:
            logging.warning(f"Failed to get trends: {str(e)}")
            return {}
    
    def analyze_competition(self, url: str) -> Dict[str, any]:
        """Analyze competitor content using Newspaper3k"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()
            
            return {
                'title': article.title,
                'keywords': article.keywords,
                'summary': article.summary,
                'word_count': len(article.text.split()),
                'top_image': article.top_image,
            }
        except Exception as e:
            logging.warning(f"Failed to analyze competitor: {str(e)}")
            return {}
    
    def generate_schema_markup(self, content: str, title: str, author: str = "") -> Dict[str, any]:
        """Generate schema.org markup"""
        # Extract FAQ content
        soup = BeautifulSoup(content, 'html.parser')
        faq_items = []
        
        # Look for FAQ sections
        faq_section = soup.find(lambda tag: tag.name == 'h2' and 
                              ('faq' in tag.text.lower() or 
                               'frequently asked' in tag.text.lower()))
        if faq_section:
            questions = soup.find_all(['h3', 'h4'], recursive=True)
            for q in questions:
                answer = q.find_next(['p', 'div'])
                if answer:
                    faq_items.append({
                        "@type": "Question",
                        "name": q.text.strip(),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": answer.text.strip()
                        }
                    })
        
        # Build schema
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "author": {
                "@type": "Person",
                "name": author or "Editorial Team"
            },
            "datePublished": "",  # Add current date
            "dateModified": "",   # Add current date
        }
        
        # Add FAQ if found
        if faq_items:
            schema["hasPart"] = {
                "@type": "FAQPage",
                "mainEntity": faq_items
            }
            
        return schema
    
    def suggest_internal_links(self, content: str, site_content: Dict[str, str]) -> List[Dict[str, str]]:
        """Suggest internal linking opportunities"""
        suggestions = []
        
        # Clean HTML
        clean_text = BeautifulSoup(content, 'html.parser').get_text()
        
        # Extract keywords from current content
        current_keywords = set(kw for kw, _ in self.extract_keywords(clean_text)[:10])
        
        # Compare with other pages
        for url, other_content in site_content.items():
            other_keywords = set(kw for kw, _ in self.extract_keywords(other_content)[:10])
            
            # Find matching keywords
            matches = current_keywords.intersection(other_keywords)
            if matches:
                suggestions.append({
                    'url': url,
                    'matching_keywords': list(matches),
                    'relevance_score': len(matches) / len(current_keywords)
                })
        
        # Sort by relevance
        return sorted(suggestions, key=lambda x: x['relevance_score'], reverse=True)

    def generate_meta_tags(self, content: str, title: str, keywords: List[str]) -> Dict[str, str]:
        """Generate meta tags using content analysis"""
        # Clean HTML
        clean_text = BeautifulSoup(content, 'html.parser').get_text()
        
        # Extract important phrases
        sentences = nltk.sent_tokenize(clean_text)
        
        meta = {
            'title': title[:60],
            'description': sentences[0][:160] if sentences else title,
            'keywords': ', '.join(kw for kw, _ in self.extract_keywords(clean_text)[:10]),
            'og:title': title[:95],
            'og:description': ' '.join(sentences[:2])[:200] if len(sentences) > 1 else sentences[0][:200] if sentences else title,
            'twitter:title': title[:70],
            'twitter:description': sentences[0][:200] if sentences else title
        }
        
        return meta
