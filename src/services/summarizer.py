"""
AI News Aggregator - Summarization Service
Uses LLM to generate proper Persian summaries for articles
"""

import logging
import re
from typing import Optional
import httpx

from src.core.config import get_config

logger = logging.getLogger(__name__)

# Fallback model order: try these models if the configured one fails
FALLBACK_MODELS = ["glm-pro:latest", "minimax-pro:latest"]

# Maximum content length to send to the model (chars)
MAX_CONTENT_LENGTH = 2500


class SummarizationService:
    """Service for generating article summaries using LLM via Ollama"""
    
    def __init__(self):
        self.config = get_config()
        self.summarization_config = self.config.news.summarization
        self._client: Optional[httpx.AsyncClient] = None
        self._working_model: Optional[str] = None  # Cache the model that works
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Ollama"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client
    
    def _get_model(self) -> str:
        """Get the model to use, preferring cached working model"""
        if self._working_model:
            return self._working_model
        return self.summarization_config.model
    
    def _clean_summary(self, text: str) -> str:
        """Clean the generated summary, removing meta-commentary and thinking artifacts"""
        if not text:
            return ""
        # Remove common LLM meta-phrases
        meta_patterns = [
            r'Here (?:is|are) (?:the |a )?(?:Persian|Farsi|farsi|persian)\s*(?:translation|summary|version).*?:',
            r'Translation:',
            r'Summary:',
            r'^(?:Sure|Certainly|Of course),?\s*(?:here\'s|here is|below is).*?\n',
            r'^(?:ترجمه|خلاصه)\s*(?:فارسی|به فارسی)?\s*[:：]\s*',
        ]
        for pattern in meta_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        text = text.strip()
        
        # Truncate at the last sentence end if too long
        if len(text) > 1000:
            # Find last sentence boundary before 1000
            last_dot = text.rfind('.', 0, 1000)
            last_excl = text.rfind('!', 0, 1000)
            last_quest = text.rfind('؟', 0, 1000)
            last_boundary = max(last_dot, last_excl, last_quest)
            if last_boundary > 500:
                text = text[:last_boundary + 1]
        
        return text
    
    def _extract_persian_from_thinking(self, thinking: str) -> Optional[str]:
        """Extract Persian text from the model's thinking/reasoning field.
        
        Thinking models like glm-pro put their reasoning in the 'thinking' field
        and often the actual Persian summary is embedded there. This method extracts
        the Persian portions from the thinking text.
        """
        if not thinking:
            return None
        
        # Strategy 1: Look for the last substantial Persian text block in thinking
        # Persian text typically comes after patterns like "*Draft 2*" or after the final "4.  **Refining"
        # Try to find the most refined version (Draft 2, Draft 3, etc.)
        drafts = re.split(r'\*\*Draft \d+\*\*|Draft \d+|draft \d+', thinking)
        
        # The last draft is usually the most refined
        for draft in reversed(drafts):
            draft = draft.strip()
            # Check if this draft is substantial Persian text
            persian_chars = sum(1 for c in draft if '\u0600' <= c <= '\u06FF')
            if persian_chars > 50 and len(draft) > 100:
                # Clean up the draft
                clean = draft.strip()
                # Remove line numbers and bullet points at the start
                clean = re.sub(r'^\s*\d+\.\s*', '', clean)
                # Remove markdown bold
                clean = re.sub(r'\*\*[^*]+\*\*', '', clean)
                # Remove character count annotations
                clean = re.sub(r'\(\d+\s*chars?\)', '', clean)
                clean = clean.strip()
                if len(clean) > 200:
                    return clean
        
        # Strategy 2: Find any Persian paragraph that's long enough
        persian_blocks = []
        current_block = []
        
        for line in thinking.split('\n'):
            line = line.strip()
            if not line:
                if current_block:
                    block = ' '.join(current_block)
                    persian_chars = sum(1 for c in block if '\u0600' <= c <= '\u06FF')
                    if persian_chars > 30:
                        persian_blocks.append(block)
                    current_block = []
                continue
            
            persian_chars = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
            if persian_chars > len(line) * 0.3:  # More than 30% Persian
                current_block.append(line)
            elif current_block:
                block = ' '.join(current_block)
                persian_chars = sum(1 for c in block if '\u0600' <= c <= '\u06FF')
                if persian_chars > 30:
                    persian_blocks.append(block)
                current_block = []
        
        if current_block:
            block = ' '.join(current_block)
            persian_chars = sum(1 for c in block if '\u0600' <= c <= '\u06FF')
            if persian_chars > 30:
                persian_blocks.append(block)
        
        # Return the longest Persian block
        if persian_blocks:
            return max(persian_blocks, key=len)
        
        return None
    
    def _has_persian(self, text: str) -> bool:
        """Check if text contains Persian characters"""
        if not text:
            return False
        for char in text:
            if '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
                return True
        return False
    
    def _truncate_content(self, content: str, max_len: int = MAX_CONTENT_LENGTH) -> str:
        """Truncate content to a reasonable length for the LLM.
        
        Try to find a natural break point (paragraph, sentence) rather than
        cutting mid-sentence. This helps the model generate better summaries.
        """
        if not content or len(content) <= max_len:
            return content
        
        truncated = content[:max_len]
        
        # Try to find a paragraph break within the limit
        last_para = max(truncated.rfind('\n\n'), truncated.rfind('\r\n\r\n'))
        if last_para > max_len * 0.5:
            return content[:last_para].strip()
        
        # Look for sentence end
        for end_char in ['. ', '! ', '? ', '۔ ']:
            last_sent = truncated.rfind(end_char)
            if last_sent > max_len * 0.5:
                return content[:last_sent + 1].strip()
        
        return truncated.strip()
    
    async def summarize(self, content: str, article_url: str) -> Optional[str]:
        """
        Generate a summary for the given article content
        
        Uses the /api/chat endpoint which works reliably with Ollama models.
        Falls back through available models if the primary one fails.
        Also falls back to shorter content if the model returns empty responses.
        
        Args:
            content: Full article text
            article_url: Article URL for context
            
        Returns:
            Generated summary in Persian, or None on failure
        """
        if not self.summarization_config.enabled:
            logger.debug("Summarization disabled")
            return None
        
        if not content or len(content) < 30:
            logger.warning(f"Content too short to summarize ({len(content) if content else 0} chars): {article_url}")
            return None
        
        # Build prompt from template with truncated content
        prompt = self.summarization_config.prompt_template.format(
            content=self._truncate_content(content),
            min_len=self.summarization_config.min_summary_length,
            max_len=self.summarization_config.max_summary_length
        )
        
        # Try models in order: cached working model first, then configured, then fallbacks
        models_to_try = []
        if self._working_model:
            models_to_try.append(self._working_model)
        models_to_try.append(self.summarization_config.model)
        for model in FALLBACK_MODELS:
            if model not in models_to_try:
                models_to_try.append(model)
        
        # Remove duplicates while preserving order
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
        
        for model in models_to_try:
            try:
                summary = await self._call_ollama_chat(model, prompt, article_url)
                if summary and self._has_persian(summary):
                    self._working_model = model  # Cache the working model
                    return self._clean_summary(summary)
                elif summary:
                    logger.warning(f"Model {model} returned non-Persian summary for {article_url}")
                    self._working_model = model
                    return self._clean_summary(summary)
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        
        # If all models failed with full content, try with much shorter content
        if len(content) > 500:
            logger.info(f"Retrying with shorter content for {article_url}")
            short_prompt = self.summarization_config.prompt_template.format(
                content=self._truncate_content(content, 1200),
                min_len=self.summarization_config.min_summary_length,
                max_len=self.summarization_config.max_summary_length
            )
            
            for model in models_to_try[:2]:  # Only try top 2 models with shorter content
                try:
                    summary = await self._call_ollama_chat(model, short_prompt, article_url)
                    if summary and self._has_persian(summary):
                        self._working_model = model
                        return self._clean_summary(summary)
                    elif summary:
                        self._working_model = model
                        return self._clean_summary(summary)
                except Exception as e:
                    logger.warning(f"Model {model} failed on retry: {e}")
                    continue
        
        # Final fallback: try with just the title
        if len(content) > 100:
            logger.info(f"Last resort: trying with title-only for {article_url}")
            title_prompt = self.summarization_config.prompt_template.format(
                content=content[:200],
                min_len=self.summarization_config.min_summary_length,
                max_len=self.summarization_config.max_summary_length
            )
            for model in models_to_try[:1]:
                try:
                    summary = await self._call_ollama_chat(model, title_prompt, article_url)
                    if summary:
                        return self._clean_summary(summary)
                except Exception:
                    continue
        
        logger.error(f"All models failed for {article_url}")
        return None
    
    async def _call_ollama_chat(self, model: str, prompt: str, article_url: str) -> Optional[str]:
        """Call Ollama using the /api/chat endpoint.
        
        Handles thinking models that put content in 'thinking' field.
        Uses high num_predict to ensure both thinking AND content tokens are generated.
        Connects to Ollama at the configured base URL (supports Docker networking).
        """
        ollama_url = self.summarization_config.ollama_base_url.rstrip("/")
        
        try:
            response = await self.client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a professional Persian news summarizer. Output ONLY the Persian summary text. No thinking, no reasoning, no explanations. Just the summary in Farsi."},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": 2048,
                        "temperature": 0.3
                    }
                },
                timeout=300.0
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama chat API error for model {model}: {response.status_code}")
                return None
            
            result = response.json()
            message = result.get("message", {})
            content = message.get("content", "").strip()
            
            # If content is present and non-empty, use it
            if content and len(content) > 10:
                logger.info(f"Generated Persian summary ({len(content)} chars) using {model} for {article_url[:60]}")
                return content
            
            # If content is empty, check the thinking field (for thinking models like glm-pro)
            thinking = message.get("thinking", "") or result.get("thinking", "")
            if thinking:
                extracted = self._extract_persian_from_thinking(thinking)
                if extracted and self._has_persian(extracted):
                    logger.info(f"Extracted Persian summary from thinking ({len(extracted)} chars) using {model} for {article_url[:60]}")
                    return extracted
            
            # Check done_reason - if it's "length", the model ran out of tokens
            done_reason = result.get("done_reason", "")
            if done_reason == "length":
                logger.warning(f"Model {model} hit token limit for {article_url} - need more num_predict")
            
            logger.warning(f"Empty response from Ollama model {model}")
            return None
                
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama")
            return None
        except httpx.TimeoutException:
            logger.error(f"Ollama timeout for model {model}")
            return None
        except Exception as e:
            logger.error(f"Ollama chat error for model {model}: {e}")
            return None
    
    async def summarize_batch(self, articles: list) -> list:
        """
        Generate summaries for multiple articles
        
        Args:
            articles: List of (content, url) tuples
            
        Returns:
            List of summaries
        """
        results = []
        for content, url in articles:
            summary = await self.summarize(content, url)
            results.append(summary)
            # Rate limit to avoid overwhelming Ollama
            import asyncio
            await asyncio.sleep(1.0)
        
        return results
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_summarization_service: Optional[SummarizationService] = None


def get_summarization_service() -> SummarizationService:
    """Get singleton summarization service instance"""
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService()
    return _summarization_service