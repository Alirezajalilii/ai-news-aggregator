"""
AI News Aggregator - Entity Extractor
Extracts entities (companies, products, people) from article text
"""

import re
import logging
from typing import List, Set, Dict, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Extracted entity"""
    name: str
    type: str  # company, product, person, technology
    confidence: float = 1.0
    aliases: List[str] = field(default_factory=list)


class EntityExtractor:
    """
    Extracts named entities from article text
    Uses pattern matching and heuristics for entity extraction
    """
    
    # Known AI companies
    COMPANIES = {
        "OpenAI", "Anthropic", "Google", "DeepMind", "Google DeepMind",
        "Meta", "Facebook", "Microsoft", "Apple", "Amazon", "NVIDIA", "AMD",
        "Intel", "xAI", "Mistral", "Mistral AI", "Cohere", "Hugging Face",
        "Stability AI", "Midjourney", "Runway", "Scale AI", "HuggingFace",
        "Tencent", "Alibaba", "Baidu", "ByteDance", "Samsung",
        "IBM", "Oracle", "Salesforce", "Adobe", "Autodesk",
        "Tesla", "SpaceX", "Waymo", "Cruise", "Zoox",
        "Inflection", "Perplexity", "Character.AI", "Adept",
        "Flexion", "Scale", "Replicate", "Together", "Anyscale",
        "Vercel", "Cloudflare", "Databricks", "Snowflake", "MongoDB",
    }
    
    # Known AI products/models
    PRODUCTS = {
        "GPT-5", "GPT-4", "GPT-4o", "GPT-4 Turbo", "GPT-3.5", "GPT-3",
        "Claude", "Claude 2", "Claude 3", "Claude 3.5", "Claude Opus", "Claude Sonnet",
        "Gemini", "Gemini Ultra", "Gemini Pro", "Gemini 1.5", "Gemini 2.0",
        "Llama", "Llama 2", "Llama 3", "Llama 4",
        "DALL-E", "DALL-E 3", "Sora", "GPT-4V", "GPT-4 Vision",
        "Whisper", "ChatGPT", "Copilot", "Bard", "Gemini",
        "Gemma", "Mistral", "Mixtral", "Phi", "Orca", "Vicuna",
        "Falcon", "MPT", "RedPajama", "Bloom", "T5", "FLAN",
        "CLIP", "SAM", "Segment Anything", "Grounding DINO",
        "Stable Diffusion", "SDXL", "SD Turbo", "Playground",
        "Midjourney", "Leonardo", "Runway", "Pika", "Sora",
        "Llava", "MiniGPT-4", "LLaMA-Pro", "Code Llama",
        "Codex", "Devin", "Cursor", "Copilot", "Tabnine", "Codeium",
    }
    
    # AI-related technologies
    TECHNOLOGIES = {
        "Transformer", "Attention", "Self-Attention", "Multi-Head Attention",
        "RLHF", "Reinforcement Learning", "Fine-tuning", "LoRA", "QLoRA",
        "RAG", "Retrieval Augmented", "Vector Database", "Embedding",
        "Token", "Tokens", "Context Window", "Prompt Engineering",
        "Fine-tune", "Transfer Learning", "Zero-shot", "Few-shot",
        "Chain-of-Thought", "CoT", "Reasoning", "Agent", "Agents",
        "API", "SDK", "Cloud", "Edge", "On-premise", "Self-hosted",
        "Open Source", "Open-Source", "Proprietary", "Closed-source",
        "Hallucination", "Alignment", "Safety", "Red Teaming",
        "Benchmark", "Evaluation", "SOTA", "State of the Art",
    }
    
    # Patterns for entity extraction
    COMPANY_PATTERNS = [
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|Corporation|Ltd|LLC|AI|Technologies|Tech)\b",
        r"\bAI\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
        r"\b([A-Z][a-z]+)\s+AI\b",
    ]
    
    PRODUCT_PATTERNS = [
        r"\b(GPT-\d(?:\.\d)?(?:[oT]+)?)\b",
        r"\b(Claude\s+\d(?:\.\d)?(?:\s+(?:Opus|Sonnet|Haiku))?)\b",
        r"\b(Gemini\s+\d(?:\.\d)?(?:\s+(?:Ultra|Pro|Flash))?)\b",
        r"\b(Llama\s+\d(?:\s+\d+B)?)\b",
        r"\b(Stable\s+Diffusion\s+\d(?:\.\d)?)\b",
        r"\b(DALL-E\s+\d(?:\.\d)?)\b",
        r"\b(Mistral\s+\d(?:\.\d)?(?:\s+Instruct)?)\b",
    ]
    
    def __init__(self):
        self.company_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMPANY_PATTERNS]
        self.product_patterns = [re.compile(p, re.IGNORECASE) for p in self.PRODUCT_PATTERNS]
    
    def extract(self, text: str) -> Dict[str, Entity]:
        """
        Extract all entities from text
        
        Returns:
            Dict mapping entity names to Entity objects
        """
        entities = {}
        
        # Extract companies
        for company in self.COMPANIES:
            if company.lower() in text.lower():
                entities[company] = Entity(
                    name=company,
                    type="company",
                    confidence=1.0
                )
        
        # Extract products/models
        for product in self.PRODUCTS:
            if re.search(r'\b' + re.escape(product) + r'\b', text, re.IGNORECASE):
                entities[product] = Entity(
                    name=product,
                    type="product",
                    confidence=1.0
                )
        
        # Extract using patterns
        for pattern in self.company_patterns:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if name and len(name) > 2 and name not in entities:
                    entities[name] = Entity(
                        name=name,
                        type="company",
                        confidence=0.7
                    )
        
        for pattern in self.product_patterns:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if name and len(name) > 2 and name not in entities:
                    entities[name] = Entity(
                        name=name,
                        type="product",
                        confidence=0.8
                    )
        
        return entities
    
    def extract_to_list(self, text: str) -> List[str]:
        """Extract entity names as a list"""
        entities = self.extract(text)
        return [e.name for e in entities.values()]
    
    def extract_companies(self, text: str) -> List[str]:
        """Extract only company names"""
        entities = self.extract(text)
        return [e.name for e in entities.values() if e.type == "company"]
    
    def extract_products(self, text: str) -> List[str]:
        """Extract only product names"""
        entities = self.extract(text)
        return [e.name for e in entities.values() if e.type == "product"]
