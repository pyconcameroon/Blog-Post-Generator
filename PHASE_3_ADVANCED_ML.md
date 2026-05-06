# 🚀 **Phase 3: Advanced ML & Automation**

## **Fine-tuned Brand Voice Adapters**

```python
# brand_voice_fine_tuning.py
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, 
    TrainingArguments, Trainer, DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
import torch
from datasets import Dataset
from typing import Dict, List
import json

class BrandVoiceFineTuner:
    """Fine-tune models for brand-specific voice and style"""
    
    def __init__(self, config: Dict):
        self.model_name = config.get('base_model', 'microsoft/DialoGPT-medium')
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.base_model = AutoModelForCausalLM.from_pretrained(self.model_name)
        
        # LoRA configuration for efficient fine-tuning
        self.lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=16,  # LoRA rank
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj", "k_proj", "out_proj"]
        )
        
        self.brand_corpus = []
        self.fine_tuned_models = {}
    
    async def prepare_brand_training_data(self, brand_corpus: List[Dict]) -> Dataset:
        """Prepare brand corpus for fine-tuning"""
        
        training_examples = []
        
        for article in brand_corpus:
            # Create input-output pairs for style learning
            content = article['content']
            
            # Split into paragraph-level examples
            paragraphs = content.split('\n\n')
            
            for i, paragraph in enumerate(paragraphs):
                if len(paragraph.split()) > 20:  # Substantial paragraphs only
                    # Create context-response pairs
                    context = f"Write a {article.get('content_type', 'article')} paragraph about {article['title']} in the brand voice:"
                    response = paragraph.strip()
                    
                    training_examples.append({
                        'input_text': context,
                        'output_text': response,
                        'article_title': article['title'],
                        'content_type': article.get('content_type', 'article'),
                        'style_features': self._extract_style_features(paragraph)
                    })
        
        # Convert to Hugging Face Dataset
        dataset = Dataset.from_list(training_examples)
        
        # Tokenize for training
        def tokenize_function(examples):
            # Combine input and output for causal language modeling
            full_text = [f"{inp} {out}" for inp, out in zip(examples['input_text'], examples['output_text'])]
            
            return self.tokenizer(
                full_text,
                truncation=True,
                padding='max_length',
                max_length=512,
                return_tensors='pt'
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        return tokenized_dataset
    
    async def fine_tune_brand_voice(self, training_dataset: Dataset, brand_name: str) -> str:
        """Fine-tune model for specific brand voice"""
        
        # Apply LoRA to base model
        model = get_peft_model(self.base_model, self.lora_config)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=f'./brand_models/{brand_name}',
            num_train_epochs=3,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=f'./logs/{brand_name}',
            logging_steps=10,
            save_steps=500,
            eval_steps=500,
            evaluation_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False  # Causal language modeling
        )
        
        # Split dataset for training/validation
        train_size = int(0.8 * len(training_dataset))
        train_dataset = training_dataset.select(range(train_size))
        eval_dataset = training_dataset.select(range(train_size, len(training_dataset)))
        
        # Initialize trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer
        )
        
        # Fine-tune model
        trainer.train()
        
        # Save fine-tuned model
        model_path = f'./brand_models/{brand_name}_final'
        trainer.save_model(model_path)
        
        # Store model reference
        self.fine_tuned_models[brand_name] = model_path
        
        return model_path
    
    def _extract_style_features(self, text: str) -> Dict:
        """Extract style features for analysis"""
        
        sentences = text.split('.')
        words = text.split()
        
        return {
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'formal_tone_indicators': len([w for w in words if w.lower() in ['therefore', 'furthermore', 'however', 'moreover']]),
            'conversational_tone_indicators': len([w for w in words if w.lower() in ['you', 'your', 'we', 'our', 'let\'s']])
        }

## **Reinforcement Learning from Human Preferences (RLHF)**

```python
# rlhf_system.py
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer
from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class HumanFeedback:
    content_id: str
    editor_rating: float  # 1-5 scale
    specific_feedback: Dict[str, float]  # {'clarity': 4.0, 'accuracy': 5.0, 'engagement': 3.0}
    editor_id: str
    feedback_date: str
    revision_suggestions: List[str]

class RewardModel(nn.Module):
    """Reward model trained on human preferences"""
    
    def __init__(self, base_model_name: str):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(base_model_name)
        self.reward_head = nn.Sequential(
            nn.Linear(self.encoder.config.hidden_size, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 1)  # Single reward score
        )
    
    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state.mean(dim=1)  # Mean pooling
        reward = self.reward_head(pooled_output)
        return reward

class RLHFTrainer:
    """Reinforcement Learning from Human Feedback system"""
    
    def __init__(self, config: Dict):
        self.tokenizer = AutoTokenizer.from_pretrained(config['base_model'])
        self.reward_model = RewardModel(config['base_model'])
        self.feedback_database = []
        self.preference_pairs = []
    
    async def collect_human_feedback(self, content_data: Dict, editor_feedback: HumanFeedback) -> None:
        """Collect and store human feedback for training"""
        
        # Store individual feedback
        self.feedback_database.append({
            'content': content_data['content'],
            'title': content_data['title'],
            'feedback': editor_feedback,
            'content_features': self._extract_content_features(content_data)
        })
        
        # Create preference pairs for ranking
        await self._create_preference_pairs(content_data, editor_feedback)
    
    async def _create_preference_pairs(self, new_content: Dict, new_feedback: HumanFeedback) -> None:
        """Create preference pairs for ranking-based training"""
        
        # Find similar content for comparison
        similar_content = self._find_similar_content(new_content)
        
        for similar in similar_content:
            # Create preference pair based on ratings
            if new_feedback.editor_rating > similar['feedback'].editor_rating:
                preferred = new_content
                rejected = similar
            else:
                preferred = similar
                rejected = new_content
            
            self.preference_pairs.append({
                'preferred': preferred,
                'rejected': rejected,
                'preference_strength': abs(new_feedback.editor_rating - similar['feedback'].editor_rating)
            })
    
    async def train_reward_model(self) -> None:
        """Train reward model on human preferences"""
        
        if len(self.preference_pairs) < 100:
            print("Insufficient preference data for training. Need at least 100 pairs.")
            return
        
        # Prepare training data
        training_data = []
        
        for pair in self.preference_pairs:
            preferred_text = pair['preferred']['content']
            rejected_text = pair['rejected']['content']
            
            training_data.append({
                'preferred': preferred_text,
                'rejected': rejected_text,
                'margin': pair['preference_strength']
            })
        
        # Training loop
        optimizer = torch.optim.AdamW(self.reward_model.parameters(), lr=1e-5)
        
        for epoch in range(10):
            total_loss = 0
            
            for batch in self._create_batches(training_data, batch_size=8):
                optimizer.zero_grad()
                
                # Tokenize preferred and rejected texts
                preferred_inputs = self.tokenizer(
                    [item['preferred'] for item in batch],
                    padding=True,
                    truncation=True,
                    return_tensors='pt',
                    max_length=512
                )
                
                rejected_inputs = self.tokenizer(
                    [item['rejected'] for item in batch],
                    padding=True,
                    truncation=True,
                    return_tensors='pt',
                    max_length=512
                )
                
                # Get reward scores
                preferred_rewards = self.reward_model(
                    preferred_inputs['input_ids'],
                    preferred_inputs['attention_mask']
                )
                
                rejected_rewards = self.reward_model(
                    rejected_inputs['input_ids'],
                    rejected_inputs['attention_mask']
                )
                
                # Calculate ranking loss
                margins = torch.tensor([item['margin'] for item in batch], dtype=torch.float32)
                loss = torch.mean(torch.clamp(margins - (preferred_rewards.squeeze() - rejected_rewards.squeeze()), min=0))
                
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            print(f"Epoch {epoch + 1}, Average Loss: {total_loss / len(training_data):.4f}")
        
        # Save trained reward model
        torch.save(self.reward_model.state_dict(), 'reward_model.pth')
    
    async def predict_content_reward(self, content: str) -> float:
        """Predict reward score for content"""
        
        inputs = self.tokenizer(
            content,
            padding=True,
            truncation=True,
            return_tensors='pt',
            max_length=512
        )
        
        with torch.no_grad():
            reward = self.reward_model(inputs['input_ids'], inputs['attention_mask'])
        
        return reward.item()

## **A/B Testing & Analytics Closed-Loop**

```python
# ab_testing_system.py
import hashlib
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import scipy.stats as stats

@dataclass
class ABTestExperiment:
    experiment_id: str
    experiment_name: str
    hypothesis: str
    variants: List[Dict]  # [{'name': 'control', 'config': {...}}, {'name': 'treatment', 'config': {...}}]
    traffic_split: Dict[str, float]  # {'control': 0.5, 'treatment': 0.5}
    success_metrics: List[str]  # ['click_through_rate', 'time_on_page', 'conversion_rate']
    start_date: datetime
    end_date: datetime
    status: str  # 'running', 'completed', 'paused'

class ABTestingEngine:
    """A/B testing system for content optimization"""
    
    def __init__(self, analytics_config: Dict):
        self.experiments = {}
        self.user_assignments = {}
        self.analytics_client = AnalyticsClient(analytics_config)
        self.statistical_analyzer = StatisticalAnalyzer()
    
    async def create_experiment(self, experiment_config: Dict) -> str:
        """Create new A/B testing experiment"""
        
        experiment_id = hashlib.md5(f"{experiment_config['name']}{datetime.now()}".encode()).hexdigest()[:8]
        
        experiment = ABTestExperiment(
            experiment_id=experiment_id,
            experiment_name=experiment_config['name'],
            hypothesis=experiment_config['hypothesis'],
            variants=experiment_config['variants'],
            traffic_split=experiment_config.get('traffic_split', {'control': 0.5, 'treatment': 0.5}),
            success_metrics=experiment_config['success_metrics'],
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=experiment_config.get('duration_days', 14)),
            status='running'
        )
        
        self.experiments[experiment_id] = experiment
        
        return experiment_id
    
    async def assign_user_to_variant(self, user_id: str, experiment_id: str) -> str:
        """Assign user to experiment variant using consistent hashing"""
        
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self.experiments[experiment_id]
        
        # Check if user already assigned
        assignment_key = f"{user_id}:{experiment_id}"
        if assignment_key in self.user_assignments:
            return self.user_assignments[assignment_key]
        
        # Consistent hash-based assignment
        hash_input = f"{user_id}{experiment_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
        
        # Determine variant based on traffic split
        cumulative_probability = 0
        normalized_hash = (hash_value % 10000) / 10000  # 0-1 range
        
        for variant_name, probability in experiment.traffic_split.items():
            cumulative_probability += probability
            if normalized_hash <= cumulative_probability:
                self.user_assignments[assignment_key] = variant_name
                return variant_name
        
        # Fallback to control
        self.user_assignments[assignment_key] = 'control'
        return 'control'
    
    async def track_experiment_event(self, user_id: str, experiment_id: str, 
                                   event_type: str, event_data: Dict) -> None:
        """Track experiment events for analysis"""
        
        variant = await self.assign_user_to_variant(user_id, experiment_id)
        
        event_record = {
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'experiment_id': experiment_id,
            'variant': variant,
            'event_type': event_type,
            'event_data': event_data
        }
        
        # Send to analytics
        await self.analytics_client.track_event(event_record)
    
    async def analyze_experiment_results(self, experiment_id: str) -> Dict:
        """Analyze A/B test results with statistical significance"""
        
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self.experiments[experiment_id]
        
        # Get experiment data
        experiment_data = await self.analytics_client.get_experiment_data(
            experiment_id=experiment_id,
            start_date=experiment.start_date,
            end_date=experiment.end_date
        )
        
        # Calculate metrics for each variant
        variant_results = {}
        
        for variant_name in experiment.traffic_split.keys():
            variant_data = experiment_data[experiment_data['variant'] == variant_name]
            
            metrics = {}
            for metric in experiment.success_metrics:
                metrics[metric] = self._calculate_metric(variant_data, metric)
            
            variant_results[variant_name] = {
                'sample_size': len(variant_data),
                'metrics': metrics
            }
        
        # Statistical significance testing
        significance_results = {}
        control_metrics = variant_results.get('control', {}).get('metrics', {})
        
        for variant_name, variant_data in variant_results.items():
            if variant_name == 'control':
                continue
            
            variant_metrics = variant_data['metrics']
            
            for metric in experiment.success_metrics:
                if metric in control_metrics and metric in variant_metrics:
                    significance = await self.statistical_analyzer.test_significance(
                        control_metrics[metric],
                        variant_metrics[metric],
                        variant_results['control']['sample_size'],
                        variant_data['sample_size']
                    )
                    
                    significance_results[f"{variant_name}_{metric}"] = significance
        
        return {
            'experiment_id': experiment_id,
            'experiment_name': experiment.experiment_name,
            'status': experiment.status,
            'duration_days': (datetime.utcnow() - experiment.start_date).days,
            'variant_results': variant_results,
            'significance_tests': significance_results,
            'recommendation': self._generate_recommendation(variant_results, significance_results)
        }

class ContentOptimizationLoop:
    """Closed-loop content optimization using A/B testing results"""
    
    def __init__(self, ab_testing_engine: ABTestingEngine):
        self.ab_testing = ab_testing_engine
        self.optimization_history = []
        self.performance_threshold = 0.05  # 5% improvement threshold
    
    async def optimize_content_generation(self, content_request: Dict) -> Dict:
        """Optimize content generation based on A/B test learnings"""
        
        # 1. Check for relevant A/B test results
        relevant_experiments = await self._find_relevant_experiments(content_request)
        
        # 2. Extract optimization insights
        optimization_insights = await self._extract_optimization_insights(relevant_experiments)
        
        # 3. Apply optimizations to content request
        optimized_request = await self._apply_optimizations(content_request, optimization_insights)
        
        # 4. Create new A/B test for this content type if needed
        if self._should_create_new_experiment(content_request, relevant_experiments):
            experiment_id = await self._create_optimization_experiment(optimized_request)
            optimized_request['ab_experiment_id'] = experiment_id
        
        return optimized_request
    
    async def _extract_optimization_insights(self, experiments: List[Dict]) -> Dict:
        """Extract actionable insights from A/B test results"""
        
        insights = {
            'proven_strategies': [],
            'content_structure_preferences': {},
            'tone_preferences': {},
            'length_preferences': {},
            'seo_optimizations': []
        }
        
        for experiment in experiments:
            results = experiment['results']
            
            # Find winning variants
            for variant_name, variant_data in results['variant_results'].items():
                if variant_name == 'control':
                    continue
                
                # Check if variant significantly outperformed control
                for metric in experiment['experiment']['success_metrics']:
                    significance_key = f"{variant_name}_{metric}"
                    if (significance_key in results['significance_tests'] and 
                        results['significance_tests'][significance_key]['is_significant'] and
                        results['significance_tests'][significance_key]['improvement'] > self.performance_threshold):
                        
                        # Extract what made this variant successful
                        variant_config = next(v for v in experiment['experiment']['variants'] if v['name'] == variant_name)
                        
                        insights['proven_strategies'].append({
                            'strategy': variant_config['config'],
                            'improvement': results['significance_tests'][significance_key]['improvement'],
                            'metric': metric,
                            'confidence': results['significance_tests'][significance_key]['confidence']
                        })
        
        return insights

## **Multi-language Support with Localization**

```python
# multilingual_system.py
from transformers import MarianMTModel, MarianTokenizer, pipeline
from typing import Dict, List
import langdetect
from googletrans import Translator

class MultilingualContentGenerator:
    """Multi-language content generation with localization"""
    
    def __init__(self, config: Dict):
        self.supported_languages = config.get('languages', ['en', 'es', 'fr', 'de', 'it', 'pt'])
        self.translation_models = {}
        self.localization_rules = {}
        self.cultural_adapters = {}
        
        # Initialize translation models for each language pair
        self._initialize_translation_models()
        
        # Load localization rules
        self._load_localization_rules()
    
    def _initialize_translation_models(self):
        """Initialize translation models for supported languages"""
        
        for lang in self.supported_languages:
            if lang != 'en':  # English as source language
                model_name = f"Helsinki-NLP/opus-mt-en-{lang}"
                try:
                    tokenizer = MarianTokenizer.from_pretrained(model_name)
                    model = MarianMTModel.from_pretrained(model_name)
                    
                    self.translation_models[f"en-{lang}"] = {
                        'tokenizer': tokenizer,
                        'model': model
                    }
                except:
                    print(f"Translation model for {lang} not available, using Google Translate")
                    self.translation_models[f"en-{lang}"] = 'google_translate'
    
    async def generate_multilingual_content(self, content_request: Dict, target_languages: List[str]) -> Dict:
        """Generate content in multiple languages with localization"""
        
        # 1. Generate content in source language (English)
        source_content = await self._generate_source_content(content_request)
        
        # 2. Translate and localize for each target language
        multilingual_content = {'en': source_content}
        
        for lang in target_languages:
            if lang != 'en':
                localized_content = await self._translate_and_localize(source_content, lang, content_request)
                multilingual_content[lang] = localized_content
        
        return multilingual_content
    
    async def _translate_and_localize(self, source_content: Dict, target_lang: str, 
                                    original_request: Dict) -> Dict:
        """Translate content and apply cultural localization"""
        
        # 1. Translate main content
        translated_content = await self._translate_content(source_content['content'], target_lang)
        
        # 2. Translate and localize metadata
        translated_title = await self._translate_content(source_content['title'], target_lang)
        translated_meta_desc = await self._translate_content(source_content['meta_description'], target_lang)
        
        # 3. Apply cultural localization
        localized_content = await self._apply_cultural_localization(
            translated_content, target_lang, original_request
        )
        
        # 4. Localize SEO elements
        localized_seo = await self._localize_seo_elements(source_content, target_lang)
        
        return {
            'title': translated_title,
            'content': localized_content,
            'meta_description': translated_meta_desc,
            'seo_elements': localized_seo,
            'language': target_lang,
            'localization_applied': True
        }
    
    async def _apply_cultural_localization(self, content: str, target_lang: str, 
                                         original_request: Dict) -> str:
        """Apply cultural and regional localization"""
        
        localization_rules = self.localization_rules.get(target_lang, {})
        localized_content = content
        
        # Currency localization
        if 'currency' in localization_rules:
            currency_map = localization_rules['currency']
            for original_currency, local_currency in currency_map.items():
                localized_content = localized_content.replace(f"${original_currency}", local_currency)
        
        # Unit conversions
        if 'units' in localization_rules:
            unit_conversions = localization_rules['units']
            for imperial_unit, metric_unit in unit_conversions.items():
                localized_content = self._convert_units(localized_content, imperial_unit, metric_unit)
        
        # Cultural references
        if 'cultural_adaptations' in localization_rules:
            cultural_rules = localization_rules['cultural_adaptations']
            for original_ref, localized_ref in cultural_rules.items():
                localized_content = localized_content.replace(original_ref, localized_ref)
        
        # Regional compliance (medical disclaimers, legal requirements)
        if 'compliance' in localization_rules:
            compliance_additions = localization_rules['compliance']
            for section_type, disclaimer in compliance_additions.items():
                if section_type in original_request.get('content_type', ''):
                    localized_content += f"\n\n{disclaimer}"
        
        return localized_content

## **Cost Optimization with Hybrid Models**

```python
# cost_optimization.py
from typing import Dict, List, Optional
import asyncio
import json
from dataclasses import dataclass

@dataclass
class ModelCost:
    model_name: str
    cost_per_1k_tokens: float
    quality_score: float
    speed_score: float
    context_window: int

class CostOptimizer:
    """Intelligent cost optimization using hybrid model strategy"""
    
    def __init__(self, config: Dict):
        self.models = {
            'premium': [
                ModelCost('gpt-4-turbo', 0.01, 0.95, 0.7, 128000),
                ModelCost('claude-3-opus', 0.015, 0.97, 0.6, 200000)
            ],
            'balanced': [
                ModelCost('gpt-3.5-turbo', 0.0015, 0.80, 0.9, 16000),
                ModelCost('claude-3-sonnet', 0.003, 0.90, 0.8, 200000)
            ],
            'economy': [
                ModelCost('deepseek-chat', 0.0002, 0.75, 0.85, 32000),
                ModelCost('local-llama-3-70b', 0.0001, 0.70, 0.6, 8000)
            ]
        }
        
        self.cost_tracking = {
            'total_spent': 0,
            'monthly_budget': config.get('monthly_budget', 1000),
            'cost_per_article': [],
            'quality_cost_correlation': []
        }
        
        self.caching_system = ModelCacheSystem()
    
    async def select_optimal_model(self, request: Dict, constraints: Dict = None) -> str:
        """Select optimal model based on cost, quality, and constraints"""
        
        # Analyze request requirements
        complexity = self._analyze_complexity(request)
        quality_requirement = constraints.get('min_quality', 0.7) if constraints else 0.7
        budget_limit = constraints.get('max_cost', float('inf')) if constraints else float('inf')
        urgency = constraints.get('urgency', 'normal') if constraints else 'normal'
        
        # Check cache first
        cached_result = await self.caching_system.check_cache(request)
        if cached_result:
            return {
                'model': 'cached',
                'cost': 0,
                'content': cached_result,
                'cache_hit': True
            }
        
        # Model selection logic
        if urgency == 'high' and self._remaining_budget() > 50:
            # Use premium model for urgent requests
            selected_model = self._select_from_tier('premium', quality_requirement, budget_limit)
        
        elif complexity > 0.8 or quality_requirement > 0.85:
            # Use balanced or premium model for complex content
            if self._remaining_budget() > 20:
                selected_model = self._select_from_tier('balanced', quality_requirement, budget_limit)
            else:
                selected_model = self._select_from_tier('economy', quality_requirement, budget_limit)
        
        else:
            # Use economy model for simple content
            selected_model = self._select_from_tier('economy', quality_requirement, budget_limit)
        
        return selected_model
    
    def _select_from_tier(self, tier: str, min_quality: float, max_cost: float) -> ModelCost:
        """Select best model from specific tier"""
        
        available_models = [
            model for model in self.models[tier]
            if model.quality_score >= min_quality and model.cost_per_1k_tokens <= max_cost
        ]
        
        if not available_models:
            # Fallback to economy tier
            available_models = self.models['economy']
        
        # Select based on cost-quality ratio
        best_model = min(available_models, 
                        key=lambda m: m.cost_per_1k_tokens / m.quality_score)
        
        return best_model
    
    async def track_generation_cost(self, model_used: str, tokens_used: int, 
                                  quality_achieved: float) -> None:
        """Track costs and quality correlation"""
        
        model = next((m for tier in self.models.values() for m in tier if m.model_name == model_used), None)
        
        if model:
            cost = (tokens_used / 1000) * model.cost_per_1k_tokens
            
            self.cost_tracking['total_spent'] += cost
            self.cost_tracking['cost_per_article'].append(cost)
            self.cost_tracking['quality_cost_correlation'].append({
                'cost': cost,
                'quality': quality_achieved,
                'model': model_used,
                'tokens': tokens_used
            })
    
    def _remaining_budget(self) -> float:
        """Calculate remaining monthly budget"""
        return self.cost_tracking['monthly_budget'] - self.cost_tracking['total_spent']
    
    async def generate_cost_report(self) -> Dict:
        """Generate comprehensive cost analysis report"""
        
        recent_generations = self.cost_tracking['quality_cost_correlation'][-100:]  # Last 100
        
        if not recent_generations:
            return {'error': 'No generation data available'}
        
        avg_cost = sum(g['cost'] for g in recent_generations) / len(recent_generations)
        avg_quality = sum(g['quality'] for g in recent_generations) / len(recent_generations)
        
        # Cost efficiency by model
        model_efficiency = {}
        for generation in recent_generations:
            model = generation['model']
            if model not in model_efficiency:
                model_efficiency[model] = {'costs': [], 'qualities': []}
            
            model_efficiency[model]['costs'].append(generation['cost'])
            model_efficiency[model]['qualities'].append(generation['quality'])
        
        # Calculate efficiency scores
        for model, data in model_efficiency.items():
            avg_cost_model = sum(data['costs']) / len(data['costs'])
            avg_quality_model = sum(data['qualities']) / len(data['qualities'])
            model_efficiency[model]['efficiency'] = avg_quality_model / avg_cost_model
        
        return {
            'total_spent': self.cost_tracking['total_spent'],
            'remaining_budget': self._remaining_budget(),
            'average_cost_per_article': avg_cost,
            'average_quality': avg_quality,
            'cost_efficiency_by_model': model_efficiency,
            'recommendations': self._generate_cost_optimization_recommendations(model_efficiency)
        }
```

This completes **Phase 3: Advanced ML & Automation** with:

✅ **Brand Voice Fine-tuning:** LoRA adapters for custom voice  
✅ **RLHF System:** Human feedback integration  
✅ **A/B Testing:** Closed-loop optimization  
✅ **Multi-language:** Cultural localization  
✅ **Cost Optimization:** Hybrid model strategy  

Would you like me to continue with **Phase 4: Scale & Compliance** for the complete enterprise roadmap?
