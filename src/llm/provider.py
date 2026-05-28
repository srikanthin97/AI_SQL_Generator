from abc import ABC, abstractmethod
import os
import requests
from typing import Dict, Any, Optional
from openai import OpenAI
import logging

logger = logging.getLogger("ai_sql_generator.llm")

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        """Generates a text completion based on prompt and system_prompt."""
        pass

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API wrapper."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI Generation Error: {e}")
            raise RuntimeError(f"OpenAI request failed: {e}")

class OllamaProvider(BaseLLMProvider):
    """Ollama API wrapper for local models using direct API endpoint."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            logger.error(f"Ollama Generation Error: {e}")
            raise RuntimeError(f"Ollama request failed: {e}")

class GeminiProvider(BaseLLMProvider):
    """Google Gemini API wrapper."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model_name = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        import google.generativeai as genai
        config = genai.types.GenerationConfig(
            temperature=temperature
        )
        try:
            if system_prompt:
                model = genai.GenerativeModel(self.model_name, system_instruction=system_prompt)
            else:
                model = genai.GenerativeModel(self.model_name)
                
            response = model.generate_content(prompt, generation_config=config)
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini Generation Error: {e}")
            raise RuntimeError(f"Gemini request failed: {e}")

def get_llm_provider(provider_name: str, **kwargs) -> BaseLLMProvider:
    """Factory function to retrieve LLM provider instances."""
    provider_name = provider_name.lower().strip()
    if provider_name == "openai":
        api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        model = kwargs.get("model") or os.getenv("LLM_MODEL", "gpt-4o")
        return OpenAIProvider(api_key=api_key, model=model)
    elif provider_name == "ollama":
        base_url = kwargs.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = kwargs.get("model") or os.getenv("LLM_MODEL", "llama3")
        return OllamaProvider(base_url=base_url, model=model)
    elif provider_name == "gemini" or provider_name == "google":
        api_key = kwargs.get("api_key") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        model = kwargs.get("model") or os.getenv("LLM_MODEL", "gemini-1.5-pro")
        return GeminiProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
