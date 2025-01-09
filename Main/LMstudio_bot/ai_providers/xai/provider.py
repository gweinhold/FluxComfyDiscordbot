import os
import aiohttp
import logging
from typing import Optional
from ..base import AIProvider

logger = logging.getLogger(__name__)

class XAIProvider(AIProvider):
    """XAI provider implementation."""
    
    def __init__(self):
        """Initialize XAI provider with API key."""
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY environment variable is not set")
        self.model = "grok-2-latest"  # Using latest Grok model
        logger.info(f"Initialized XAI provider with model: {self.model}")
        
        # Define word limits for each creativity level
        self.word_limits = {
            1: 0,      
            2: 10,     
            3: 20,     
            4: 30,    
            5: 40,     
            6: 50,     
            7: 60,     
            8: 70,     
            9: 80,     
            10: 90    
        }

    def _get_word_limit(self, temperature: float) -> int:
        """Get word limit based on temperature/creativity level."""
        # Convert temperature (0.1-1.0) to creativity level (1-10)
        creativity_level = round(temperature * 10)
        # Get word limit for this level
        return self.word_limits.get(creativity_level, 100)  # Default to 100 if level not found

    def _enforce_word_limit(self, text: str, limit: int) -> str:
        """Enforce word limit on generated text."""
        if limit == 0:
            return text
            
        words = text.split()
        if len(words) > limit:
            limited_text = ' '.join(words[:limit])
            # logger.info(f"Truncated response from {len(words)} to {limit} words")
            return limited_text
        return text

    @property
    def base_url(self) -> str:
        """Get the base URL for the XAI API."""
        return "https://api.x.ai/v1"

    async def test_connection(self) -> bool:
        """Test the connection to XAI API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Test with a simple completion request
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"XAI connection test failed: {e}")
            return False

    async def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate an enhanced prompt using XAI API."""
        try:
            # Level 1 means no enhancement
            if temperature == 0.1:
                logger.info("Creativity level 1: Using original prompt")
                return prompt

            # Get word limit for this creativity level
            word_limit = self._get_word_limit(temperature)
            
            # Add word limit instruction to system prompt
            word_limit_instruction = f"\n\nIMPORTANT: Your response must not exceed {word_limit} words. Be concise and precise."

            # Scale the system prompt based on temperature
            if temperature <= 0.2:  # Level 2
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make minimal enhancements:"
                    "\n1. Keep the original prompt almost entirely intact"
                    "\n2. Only add basic descriptive details if absolutely necessary"
                    "\n3. Do not change the core concept or style"
                    + word_limit_instruction
                )
            elif temperature <= 0.3:  # Level 3
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation, make light enhancements:"
                    "\n1. Keep the main elements of the original prompt"
                    "\n2. Add minimal artistic style suggestions"
                    "\n3. Include basic descriptive details"
                    + word_limit_instruction
                )
            elif temperature <= 0.4:  # Level 4
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make moderate enhancements:"
                    "\n1. Preserve the core concept"
                    "\n2. Add some artistic style elements"
                    "\n3. Include additional descriptive details"
                    + word_limit_instruction
                )
            elif temperature <= 0.5:  # Level 5
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make balanced enhancements:"
                    "\n1. Keep the main theme while adding detail"
                    "\n2. Suggest complementary artistic styles"
                    "\n3. Add meaningful descriptive elements"
                    + word_limit_instruction
                )
            elif temperature <= 0.6:  # Level 6
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make notable enhancements:"
                    "\n1. Expand on the original concept"
                    "\n2. Add specific artistic style recommendations"
                    "\n3. Include detailed visual descriptions"
                    + word_limit_instruction
                )
            elif temperature <= 0.7:  # Level 7
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make significant enhancements:"
                    "\n1. Build upon the core concept"
                    "\n2. Add rich artistic style elements"
                    "\n3. Include comprehensive visual details"
                    + word_limit_instruction
                )
            elif temperature <= 0.8:  # Level 8
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make extensive enhancements:"
                    "\n1. Elaborate on the original concept"
                    "\n2. Add detailed artistic direction"
                    "\n3. Include rich visual descriptions"
                    + word_limit_instruction
                )
            elif temperature <= 0.9:  # Level 9
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make substantial enhancements:"
                    "\n1. Significantly expand the concept"
                    "\n2. Add comprehensive artistic direction"
                    "\n3. Include intricate visual details"
                    + word_limit_instruction
                )
            else:  # Level 10
                system_prompt = (
                    "You are an expert in crafting detailed, imaginative, and visually descriptive prompts for AI image generation. For this prompt, make maximum enhancements:"
                    "\n1. Fully develop and expand the concept"
                    "\n2. Add extensive artistic direction"
                    "\n3. Include highly detailed visual descriptions"
                    + word_limit_instruction
                )

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Original prompt: {prompt}\n\nEnhanced prompt:"}
                ],
                "temperature": temperature,
                "max_tokens": 1024,
                "n": 1,
                "stop": ["\n"]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"XAI API error: HTTP {response.status} - {error_text}")
                        raise Exception(f"XAI API error: HTTP {response.status} - {error_text}")
                    
                    data = await response.json()
                    if not data.get("choices") or not data["choices"][0].get("message"):
                        raise Exception("Invalid response format from XAI API")
                        
                    enhanced_prompt = data["choices"][0]["message"]["content"].strip()
                    
                    # Enforce word limit
                    enhanced_prompt = self._enforce_word_limit(enhanced_prompt, word_limit)
                    
                    #logger.info(f"Enhanced prompt with temperature {temperature} (limit {word_limit} words): {enhanced_prompt}")
                    
                    return enhanced_prompt

        except Exception as e:
            logger.error(f"XAI API error: {e}", exc_info=True)
            raise Exception(f"XAI API error: {str(e)}")
