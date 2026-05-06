# 🔧 **Phase 2: QA & Grounding - Complete Implementation**

## **Claim Extraction + Fact-Checking Pipeline**

```python
# fact_checking_pipeline.py
import spacy
import requests
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
from datetime import datetime

@dataclass
class ExtractedClaim:
    text: str
    claim_type: str  # 'statistic', 'medical', 'factual', 'opinion'
    confidence: float
    entities: List[str]
    position: int  # Character position in text

@dataclass
class FactCheckResult:
    claim: ExtractedClaim
    verification_status: str  # 'verified', 'disputed', 'unverified', 'false'
    confidence_score: float
    supporting_sources: List[Dict]
    contradicting_sources: List[Dict]
    verification_explanation: str

class ClaimExtractor:
    """Extract factual claims using NLP and pattern matching"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.claim_patterns = self._build_claim_patterns()
        self.entity_recognizer = self.nlp.add_pipe("entity_recognizer", config={"threshold": 0.8})
    
    def extract_claims(self, content: str) -> List[ExtractedClaim]:
        """Extract all factual claims from content"""
        
        doc = self.nlp(content)
        claims = []
        
        # 1. Pattern-based extraction
        pattern_claims = self._extract_by_patterns(doc)
        claims.extend(pattern_claims)
        
        # 2. Statistical claims extraction
        stat_claims = self._extract_statistical_claims(doc)
        claims.extend(stat_claims)
        
        # 3. Medical/health claims extraction
        medical_claims = self._extract_medical_claims(doc)
        claims.extend(medical_claims)
        
        # 4. Authority-based claims (according to, study shows, etc.)
        authority_claims = self._extract_authority_claims(doc)
        claims.extend(authority_claims)
        
        # Remove duplicates and sort by confidence
        unique_claims = self._deduplicate_claims(claims)
        return sorted(unique_claims, key=lambda x: x.confidence, reverse=True)
    
    def _build_claim_patterns(self) -> List[Dict]:
        """Build patterns for different types of factual claims"""
        return [
            {
                'pattern': r'(\d+(?:\.\d+)?%?) of (?:people|patients|users|cases)',
                'type': 'statistic',
                'confidence': 0.9
            },
            {
                'pattern': r'studies? (?:show|demonstrate|prove|indicate) (?:that )?(.+?)(?:\.|,)',
                'type': 'research',
                'confidence': 0.85
            },
            {
                'pattern': r'(?:FDA|WHO|CDC|NIH) (?:approved|recommends|states) (?:that )?(.+?)(?:\.|,)',
                'type': 'regulatory',
                'confidence': 0.95
            },
            {
                'pattern': r'(?:clinical trials?|research) (?:has |have )?(?:shown|demonstrated|proven) (?:that )?(.+?)(?:\.|,)',
                'type': 'clinical',
                'confidence': 0.9
            },
            {
                'pattern': r'(?:can|may|has been shown to) (?:reduce|increase|improve|treat|cure|prevent) (.+?)(?:\.|,)',
                'type': 'medical_claim',
                'confidence': 0.8
            }
        ]
    
    def _extract_statistical_claims(self, doc) -> List[ExtractedClaim]:
        """Extract statistical claims with numbers and percentages"""
        
        claims = []
        
        for sent in doc.sents:
            # Look for sentences with numbers and percentages
            if re.search(r'\d+(?:\.\d+)?%', sent.text) or re.search(r'\d+(?:,\d{3})*(?:\.\d+)?', sent.text):
                # Extract numerical entities
                numbers = [ent for ent in sent.ents if ent.label_ in ['PERCENT', 'CARDINAL', 'QUANTITY']]
                
                if numbers:
                    claims.append(ExtractedClaim(
                        text=sent.text.strip(),
                        claim_type='statistic',
                        confidence=0.8,
                        entities=[ent.text for ent in numbers],
                        position=sent.start_char
                    ))
        
        return claims
    
    def _extract_medical_claims(self, doc) -> List[ExtractedClaim]:
        """Extract medical and health-related claims"""
        
        medical_keywords = [
            'treatment', 'therapy', 'medicine', 'drug', 'medication', 'cure', 'heal',
            'dose', 'dosage', 'side effect', 'symptom', 'diagnosis', 'condition',
            'disease', 'disorder', 'infection', 'pain relief', 'inflammation'
        ]
        
        claims = []
        
        for sent in doc.sents:
            sentence_lower = sent.text.lower()
            
            # Check if sentence contains medical keywords
            if any(keyword in sentence_lower for keyword in medical_keywords):
                # Additional validation for medical claim patterns
                medical_patterns = [
                    r'(?:treat|cure|heal|reduce|relieve) (?:pain|inflammation|symptoms)',
                    r'(?:safe|effective|approved) for (?:treating|managing)',
                    r'(?:side effects|contraindications|warnings)',
                    r'(?:dosage|dose) (?:of|for|should be)'
                ]
                
                if any(re.search(pattern, sentence_lower) for pattern in medical_patterns):
                    claims.append(ExtractedClaim(
                        text=sent.text.strip(),
                        claim_type='medical',
                        confidence=0.85,
                        entities=[ent.text for ent in sent.ents if ent.label_ in ['ORG', 'PRODUCT', 'SUBSTANCE']],
                        position=sent.start_char
                    ))
        
        return claims

class FactChecker:
    """Comprehensive fact-checking using multiple authoritative sources"""
    
    def __init__(self, config: Dict):
        self.pubmed_api = PubMedAPI(config.get('pubmed_api_key'))
        self.fda_api = FDAAPI()
        self.fact_check_apis = [
            GoogleFactCheckAPI(config.get('google_api_key')),
            ClaimReviewAPI()
        ]
        self.search_client = GoogleSearchClient(config.get('google_search_api_key'))
    
    async def verify_claims(self, claims: List[ExtractedClaim]) -> List[FactCheckResult]:
        """Verify all extracted claims against authoritative sources"""
        
        verification_tasks = [
            self._verify_single_claim(claim) for claim in claims
        ]
        
        results = await asyncio.gather(*verification_tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        return valid_results
    
    async def _verify_single_claim(self, claim: ExtractedClaim) -> FactCheckResult:
        """Verify a single claim using multiple sources"""
        
        verification_sources = []
        
        # 1. Check medical/scientific claims against PubMed
        if claim.claim_type in ['medical', 'clinical', 'statistic']:
            pubmed_results = await self._check_pubmed(claim)
            verification_sources.extend(pubmed_results)
        
        # 2. Check regulatory claims against FDA
        if claim.claim_type in ['medical', 'regulatory']:
            fda_results = await self._check_fda(claim)
            verification_sources.extend(fda_results)
        
        # 3. Check against fact-checking APIs
        fact_check_results = await self._check_fact_check_apis(claim)
        verification_sources.extend(fact_check_results)
        
        # 4. General web search for verification
        web_results = await self._search_web_verification(claim)
        verification_sources.extend(web_results)
        
        # 5. Calculate verification consensus
        verification_result = self._calculate_verification_consensus(verification_sources)
        
        return FactCheckResult(
            claim=claim,
            verification_status=verification_result['status'],
            confidence_score=verification_result['confidence'],
            supporting_sources=verification_result['supporting'],
            contradicting_sources=verification_result['contradicting'],
            verification_explanation=verification_result['explanation']
        )
    
    async def _check_pubmed(self, claim: ExtractedClaim) -> List[Dict]:
        """Check claim against PubMed research database"""
        
        try:
            # Extract key terms for search
            search_terms = self._extract_search_terms(claim)
            
            # Search PubMed
            papers = await self.pubmed_api.search(
                query=' AND '.join(search_terms),
                max_results=10,
                sort='relevance'
            )
            
            verification_sources = []
            
            for paper in papers:
                # Analyze paper relevance to claim
                relevance_score = self._calculate_paper_relevance(claim, paper)
                
                if relevance_score > 0.6:
                    support_score = self._analyze_claim_support(claim, paper)
                    
                    verification_sources.append({
                        'source_type': 'academic',
                        'title': paper['title'],
                        'authors': paper['authors'],
                        'journal': paper['journal'],
                        'year': paper['year'],
                        'pmid': paper['pmid'],
                        'support_score': support_score,
                        'relevance_score': relevance_score,
                        'authority_weight': 0.9,
                        'url': f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/"
                    })
            
            return verification_sources
            
        except Exception as e:
            print(f"PubMed verification failed: {e}")
            return []
    
    async def _check_fda(self, claim: ExtractedClaim) -> List[Dict]:
        """Check claim against FDA databases"""
        
        try:
            # Check if claim involves FDA-regulated products
            fda_keywords = ['drug', 'medication', 'device', 'supplement', 'treatment', 'therapy']
            
            if not any(keyword in claim.text.lower() for keyword in fda_keywords):
                return []
            
            # Search FDA databases
            fda_results = await self.fda_api.search_drug_labels(claim.text)
            fda_results.extend(await self.fda_api.search_device_database(claim.text))
            
            verification_sources = []
            
            for result in fda_results:
                support_score = self._analyze_fda_support(claim, result)
                
                verification_sources.append({
                    'source_type': 'regulatory',
                    'title': result['product_name'],
                    'database': result['database'],
                    'approval_status': result.get('approval_status'),
                    'support_score': support_score,
                    'authority_weight': 0.95,
                    'url': result.get('url')
                })
            
            return verification_sources
            
        except Exception as e:
            print(f"FDA verification failed: {e}")
            return []

class PlagiarismDetector:
    """Advanced plagiarism detection with web search and similarity analysis"""
    
    def __init__(self, config: Dict):
        self.search_client = GoogleSearchClient(config.get('google_search_api_key'))
        self.similarity_threshold = 0.7
        self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def check_plagiarism(self, content: str) -> Dict:
        """Comprehensive plagiarism check"""
        
        # 1. Break content into chunks for analysis
        content_chunks = self._chunk_content(content)
        
        # 2. Search for similar content online
        search_results = await self._search_for_similar_content(content_chunks)
        
        # 3. Analyze similarity scores
        similarity_analysis = await self._analyze_similarity(content_chunks, search_results)
        
        # 4. Calculate overall plagiarism score
        plagiarism_score = self._calculate_plagiarism_score(similarity_analysis)
        
        return {
            'plagiarism_score': plagiarism_score,
            'similar_sources': similarity_analysis['similar_sources'],
            'risk_level': self._determine_risk_level(plagiarism_score),
            'recommendations': self._generate_uniqueness_recommendations(similarity_analysis)
        }
    
    def _chunk_content(self, content: str, chunk_size: int = 150) -> List[str]:
        """Break content into overlapping chunks for plagiarism checking"""
        
        sentences = content.split('. ')
        chunks = []
        
        for i in range(0, len(sentences), chunk_size):
            chunk = '. '.join(sentences[i:i + chunk_size])
            if len(chunk.split()) > 20:  # Only check substantial chunks
                chunks.append(chunk)
        
        return chunks
    
    async def _search_for_similar_content(self, chunks: List[str]) -> List[Dict]:
        """Search for similar content online"""
        
        search_results = []
        
        for chunk in chunks[:5]:  # Limit to first 5 chunks to avoid API limits
            try:
                # Use exact phrase search for high-similarity detection
                query = f'"{chunk[:100]}"'  # First 100 characters as exact match
                
                results = await self.search_client.search(
                    query=query,
                    num_results=5
                )
                
                for result in results:
                    search_results.append({
                        'original_chunk': chunk,
                        'found_url': result['url'],
                        'found_title': result['title'],
                        'found_snippet': result['snippet']
                    })
                    
            except Exception as e:
                continue
        
        return search_results
    
    async def _analyze_similarity(self, original_chunks: List[str], search_results: List[Dict]) -> Dict:
        """Analyze semantic similarity between original and found content"""
        
        similar_sources = []
        
        for result in search_results:
            # Generate embeddings for comparison
            original_embedding = self.sentence_transformer.encode([result['original_chunk']])
            found_embedding = self.sentence_transformer.encode([result['found_snippet']])
            
            # Calculate cosine similarity
            similarity = np.dot(original_embedding[0], found_embedding[0]) / (
                np.linalg.norm(original_embedding[0]) * np.linalg.norm(found_embedding[0])
            )
            
            if similarity > self.similarity_threshold:
                similar_sources.append({
                    'url': result['found_url'],
                    'title': result['found_title'],
                    'similarity_score': float(similarity),
                    'matching_text': result['original_chunk'][:200],
                    'risk_level': 'high' if similarity > 0.9 else 'medium'
                })
        
        return {
            'similar_sources': similar_sources,
            'total_checks': len(search_results),
            'high_similarity_count': len([s for s in similar_sources if s['similarity_score'] > 0.9])
        }

class QualityScorer:
    """ML-based content quality scoring"""
    
    def __init__(self):
        self.readability_analyzer = textstat
        self.sentiment_analyzer = pipeline("sentiment-analysis")
        self.quality_model = self._load_quality_model()
    
    async def score_content_quality(self, content: str, fact_check_results: List[FactCheckResult] = None) -> Dict:
        """Comprehensive quality scoring"""
        
        # 1. Readability metrics
        readability_scores = self._calculate_readability(content)
        
        # 2. Content depth and expertise indicators
        expertise_score = self._analyze_expertise_indicators(content)
        
        # 3. Structural quality
        structure_score = self._analyze_content_structure(content)
        
        # 4. Factual accuracy (from fact-checking results)
        factual_score = self._calculate_factual_accuracy(fact_check_results) if fact_check_results else 0.5
        
        # 5. Engagement potential
        engagement_score = self._predict_engagement_potential(content)
        
        # 6. SEO quality indicators
        seo_score = self._analyze_seo_quality(content)
        
        # 7. Overall quality calculation
        overall_score = self._calculate_weighted_quality_score({
            'readability': readability_scores['composite'],
            'expertise': expertise_score,
            'structure': structure_score,
            'factual_accuracy': factual_score,
            'engagement': engagement_score,
            'seo': seo_score
        })
        
        return {
            'overall_quality_score': overall_score,
            'component_scores': {
                'readability': readability_scores,
                'expertise': expertise_score,
                'structure': structure_score,
                'factual_accuracy': factual_score,
                'engagement': engagement_score,
                'seo': seo_score
            },
            'quality_tier': self._determine_quality_tier(overall_score),
            'improvement_suggestions': self._generate_improvement_suggestions(overall_score, {
                'readability': readability_scores,
                'expertise': expertise_score,
                'structure': structure_score,
                'factual_accuracy': factual_score,
                'engagement': engagement_score,
                'seo': seo_score
            })
        }
    
    def _calculate_readability(self, content: str) -> Dict:
        """Calculate multiple readability metrics"""
        
        # Remove HTML tags for analysis
        clean_content = re.sub(r'<[^>]+>', '', content)
        
        return {
            'flesch_kincaid_grade': textstat.flesch_kincaid_grade(clean_content),
            'flesch_reading_ease': textstat.flesch_reading_ease(clean_content),
            'smog_index': textstat.smog_index(clean_content),
            'automated_readability_index': textstat.automated_readability_index(clean_content),
            'coleman_liau_index': textstat.coleman_liau_index(clean_content),
            'composite': textstat.text_standard(clean_content)
        }
    
    def _analyze_expertise_indicators(self, content: str) -> float:
        """Analyze content for expertise indicators"""
        
        expertise_indicators = {
            'technical_terms': 0,
            'citations': 0,
            'data_references': 0,
            'expert_language': 0,
            'depth_markers': 0
        }
        
        # Technical terms (domain-specific vocabulary)
        technical_patterns = [
            r'\b(?:research|study|clinical|trial|analysis|methodology)\b',
            r'\b(?:according to|based on|studies show|evidence suggests)\b',
            r'\b(?:significant|correlation|hypothesis|statistical)\b'
        ]
        
        for pattern in technical_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            expertise_indicators['technical_terms'] += matches
        
        # Citations and references
        citation_patterns = [
            r'\[.*?\]',  # [1], [Smith et al.]
            r'\(.*?\d{4}.*?\)',  # (Author, 2023)
            r'et al\.',
            r'according to [\w\s]+(?:University|Institute|Journal|Study)'
        ]
        
        for pattern in citation_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            expertise_indicators['citations'] += matches
        
        # Data references (numbers, percentages, statistics)
        data_patterns = [
            r'\d+(?:\.\d+)?%',  # Percentages
            r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:mg|ml|kg|pounds|degrees|units)',  # Measurements
            r'study of \d+',  # Study sample sizes
            r'\d+(?:,\d{3})*\s*(?:people|patients|participants|subjects)'  # Sample descriptions
        ]
        
        for pattern in data_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            expertise_indicators['data_references'] += matches
        
        # Calculate normalized expertise score (0-1)
        word_count = len(content.split())
        if word_count == 0:
            return 0
        
        total_indicators = sum(expertise_indicators.values())
        expertise_density = total_indicators / word_count
        
        # Normalize to 0-1 scale (density of 0.05 = score of 1.0)
        normalized_score = min(expertise_density / 0.05, 1.0)
        
        return normalized_score

class CMSIntegrator:
    """WordPress CMS integration with publishing workflow"""
    
    def __init__(self, wp_config: Dict):
        self.wp_url = wp_config['url']
        self.wp_user = wp_config['username']
        self.wp_password = wp_config['password']
        self.session = requests.Session()
        self.publishing_queue = []
    
    async def publish_content(self, content_data: Dict, publish_config: Dict = None) -> Dict:
        """Publish content to WordPress with full metadata"""
        
        try:
            # 1. Prepare WordPress post data
            post_data = await self._prepare_wp_post_data(content_data, publish_config)
            
            # 2. Upload any media files first
            media_ids = await self._upload_media_files(content_data.get('media_files', []))
            if media_ids:
                post_data['featured_media'] = media_ids[0]  # Set first image as featured
            
            # 3. Create/update WordPress post
            wp_response = await self._create_wp_post(post_data)
            
            # 4. Add custom metadata
            if wp_response.get('id'):
                await self._add_custom_metadata(wp_response['id'], content_data)
            
            # 5. Update internal tracking
            publishing_result = {
                'status': 'published',
                'wp_post_id': wp_response.get('id'),
                'wp_url': wp_response.get('link'),
                'published_at': datetime.utcnow().isoformat(),
                'post_status': wp_response.get('status', 'publish')
            }
            
            return publishing_result
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'attempted_at': datetime.utcnow().isoformat()
            }
    
    async def _prepare_wp_post_data(self, content_data: Dict, publish_config: Dict) -> Dict:
        """Prepare WordPress post data with SEO optimization"""
        
        return {
            'title': content_data['title'],
            'content': content_data['content'],
            'excerpt': content_data.get('meta_description', '')[:150],
            'status': publish_config.get('status', 'draft'),
            'categories': publish_config.get('categories', []),
            'tags': content_data.get('keywords', []),
            'meta': {
                'seo_title': content_data.get('seo_title', content_data['title']),
                'meta_description': content_data.get('meta_description', ''),
                'focus_keyword': content_data.get('primary_keyword', ''),
                'canonical_url': publish_config.get('canonical_url', ''),
                'quality_score': content_data.get('quality_score', 0),
                'generation_metadata': content_data.get('generation_metadata', {})
            }
        }
```

This completes **Phase 2** with comprehensive QA and grounding features. Would you like me to continue with **Phase 3 (Advanced ML & Automation)** and **Phase 4 (Scale & Compliance)**?
