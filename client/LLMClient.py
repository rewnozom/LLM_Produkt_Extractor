

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ./client/LLMClient.py

"""
LLM-klientklass för Produktinformationsextraktor

Denna modul innehåller:
1. LLMClient - En kraftfull klientklass för att interagera med olika LLM-tjänster
2. ResponseParser - Klass för att tolka och strukturera LLM-svar
3. ChunkManager - Klass för att dela upp stora textfiler i hanterbara delar
4. ProviderFactory - Fabriksklass för att skapa rätt LLM-provider baserat på konfiguration

Modulen stödjer olika LLM-tjänster som Ollama, LM Studio, OpenAI, Claude och OpenRouter och hanterar:
- Automatiska återförsök med exponentiell backoff
- Uppdelning av stora texter som överskrider kontextstorleken
- Strukturerad tolkning av LLM-svar
- Felhantering och loggning
"""

import re
import json
import time
import random
import requests
import hashlib
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass
from pathlib import Path
import logging
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from prompts.PromptTemplate import PromptTemplate
from prompts.ExtractionPrompt import ExtractionPrompt
import os

# Typ för LLM-tjänster
class LLMProvider(Enum):
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    OOBABOOGA = "oobabooga"
    OPENAI = "openai"
    CLAUDE = "claude"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


@dataclass
class LLMRequest:
    """Representerar en begäran till LLM-tjänsten"""
    prompt: str
    model: str
    max_tokens: int = 2048
    temperature: float = 0.1
    stop_sequences: List[str] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    request_id: str = None
    
    def __post_init__(self):
        """Genererar ett request_id om det inte anges"""
        if not self.request_id:
            self.request_id = hashlib.md5(f"{self.prompt}-{random.random()}".encode()).hexdigest()[:10]
        
        # Standardisera stop_sequences till en lista
        if self.stop_sequences is None:
            self.stop_sequences = []
        elif isinstance(self.stop_sequences, str):
            self.stop_sequences = [self.stop_sequences]


@dataclass
class LLMResponse:
    """Representerar ett svar från LLM-tjänsten"""
    text: str
    request_id: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = None
    raw_response: Dict[str, Any] = None
    error: str = None
    latency_ms: int = 0
    
    @property
    def successful(self) -> bool:
        """Kontrollerar om svaret var framgångsrikt"""
        return self.error is None and self.text is not None


class LLMProviderBase(ABC):
    """Basklass för LLM-providerimplementationer"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initierar LLM-providern
        
        Args:
            config: Konfiguration för providern
            logger: Logger för att logga meddelanden
        """
        self.config = config
        self.logger = logger
        self.base_url = config.get("base_url")
        self.model = config.get("model")
        self.session = requests.Session()
        self.initialize_session()
    
    def initialize_session(self) -> None:
        """Initialiserar sessionen med rätt headers etc."""
        if "headers" in self.config:
            self.session.headers.update(self.config["headers"])
        
        # Konfigurera timeout
        timeout = self.config.get("timeout", 60)
        self.session.request = lambda method, url, **kwargs: super(requests.Session, self.session).request(
            method=method, url=url, timeout=timeout, **kwargs
        )
    
    @abstractmethod
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """
        Genererar nyttolast för begäran till LLM-tjänsten
        
        Args:
            request: LLM-begäran
            
        Returns:
            Dict[str, Any]: Nyttolast för begäran
        """
        pass
    
    @abstractmethod
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """
        Tolkar svaret från LLM-tjänsten
        
        Args:
            response: HTTP-svar från tjänsten
            request: Ursprunglig LLM-begäran
            
        Returns:
            LLMResponse: Strukturerat LLM-svar
        """
        pass
    
    def send_request(self, request: LLMRequest) -> LLMResponse:
        """
        Skickar en begäran till LLM-tjänsten
        
        Args:
            request: LLM-begäran att skicka
            
        Returns:
            LLMResponse: Svaret från LLM-tjänsten
        """
        start_time = time.time()
        
        try:
            # Generera nyttolast
            payload = self.generate_request_payload(request)
            
            # Skicka begäran
            endpoint = self.get_endpoint()
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=payload
            )
            
            # Beräkna latens
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Tolka svaret
            llm_response = self.parse_response(response, request)
            llm_response.latency_ms = latency_ms
            
            return llm_response
            
        except requests.RequestException as e:
            # Hantera nätverksfel
            latency_ms = int((time.time() - start_time) * 1000)
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model,
                error=f"Nätverksfel: {str(e)}",
                latency_ms=latency_ms,
                raw_response={"error": str(e)}
            )
        except Exception as e:
            # Hantera övriga fel
            latency_ms = int((time.time() - start_time) * 1000)
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model,
                error=f"Oväntat fel: {str(e)}",
                latency_ms=latency_ms,
                raw_response={"error": str(e)}
            )
    
    def get_endpoint(self) -> str:
        """Hämtar rätt endpoint för tjänsten"""
        return self.config.get("api_parameters", {}).get("generate_endpoint", "")
    
    def verify_connection(self) -> Tuple[bool, str]:
        """
        Verifierar anslutningen till LLM-tjänsten
        
        Returns:
            Tuple[bool, str]: (framgång, meddelande)
        """
        try:
            # Implementera tjänstspecifik verifiering här
            return True, "Anslutning verifierad"
        except Exception as e:
            return False, f"Anslutningsfel: {str(e)}"


class OllamaProvider(LLMProviderBase):
    """Provider för Ollama LLM-tjänst"""
    
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Genererar Ollama-specifik nyttolast"""
        return {
            "model": request.model or self.model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty
        }
    
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """Tolkar Ollama-specifikt svar"""
        if response.status_code != 200:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"HTTP-fel {response.status_code}: {response.text}",
                raw_response=response.json() if self._is_json(response) else {"text": response.text}
            )
        
        try:
            response_json = response.json()
            completion_text = response_json.get("response", "")
            
            return LLMResponse(
                text=completion_text,
                request_id=request.request_id,
                model=request.model or self.model,
                prompt_tokens=response_json.get("prompt_eval_count", 0),
                completion_tokens=response_json.get("eval_count", 0),
                total_tokens=response_json.get("prompt_eval_count", 0) + response_json.get("eval_count", 0),
                finish_reason=response_json.get("done", False) and "stop" or "unknown",
                raw_response=response_json
            )
        except Exception as e:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"Fel vid tolkning av svar: {str(e)}",
                raw_response={"error": str(e), "response_text": response.text}
            )
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verifierar anslutning till Ollama"""
        try:
            response = self.session.get(f"{self.base_url}/tags")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [m.get("name") for m in models]
                
                if self.model and self.model not in available_models:
                    return False, f"Modell '{self.model}' inte tillgänglig. Tillgängliga modeller: {', '.join(available_models)}"
                
                return True, f"Anslutning till Ollama verifierad. Tillgängliga modeller: {', '.join(available_models)}"
            else:
                return False, f"Kunde inte ansluta till Ollama. Status: {response.status_code}"
        except Exception as e:
            return False, f"Anslutningsfel till Ollama: {str(e)}"
    
    def _is_json(self, response: requests.Response) -> bool:
        """Kontrollerar om svaret är JSON"""
        try:
            response.json()
            return True
        except:
            return False


class LMStudioProvider(LLMProviderBase):
    """Provider för LM Studio LLM-tjänst med OpenAI-kompatibelt API"""
    
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Genererar LM Studio-specifik nyttolast"""
        return {
            "model": request.model or self.model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False
        }
    
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """Tolkar LM Studio-specifikt svar"""
        if response.status_code != 200:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"HTTP-fel {response.status_code}: {response.text}",
                raw_response=response.json() if self._is_json(response) else {"text": response.text}
            )
        
        try:
            response_json = response.json()
            choices = response_json.get("choices", [])
            
            if not choices:
                return LLMResponse(
                    text=None,
                    request_id=request.request_id,
                    model=request.model or self.model,
                    error="Inga val returnerades i svaret",
                    raw_response=response_json
                )
            
            completion_text = choices[0].get("text", "")
            
            return LLMResponse(
                text=completion_text,
                request_id=request.request_id,
                model=request.model or self.model,
                prompt_tokens=response_json.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_json.get("usage", {}).get("completion_tokens", 0),
                total_tokens=response_json.get("usage", {}).get("total_tokens", 0),
                finish_reason=choices[0].get("finish_reason", "unknown"),
                raw_response=response_json
            )
        except Exception as e:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"Fel vid tolkning av svar: {str(e)}",
                raw_response={"error": str(e), "response_text": response.text}
            )
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verifierar anslutning till LM Studio"""
        try:
            response = self.session.get(f"{self.base_url}/models")
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                available_models = [m.get("id") for m in models] if models else ["local-model"]
                
                return True, f"Anslutning till LM Studio verifierad. Tillgängliga modeller: {', '.join(available_models)}"
            else:
                return False, f"Kunde inte ansluta till LM Studio. Status: {response.status_code}"
        except Exception as e:
            return False, f"Anslutningsfel till LM Studio: {str(e)}"
    
    def _is_json(self, response: requests.Response) -> bool:
        """Kontrollerar om svaret är JSON"""
        try:
            response.json()
            return True
        except:
            return False


class OobaboogaProvider(LLMProviderBase):
    """Provider för Oobabooga Text Generation Web UI med OpenAI-kompatibelt API"""
    
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Genererar Oobabooga-specifik nyttolast"""
        return {
            "model": request.model or self.model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False
        }
    
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """Tolkar Oobabooga-specifikt svar"""
        if response.status_code != 200:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"HTTP-fel {response.status_code}: {response.text}",
                raw_response=response.json() if self._is_json(response) else {"text": response.text}
            )
        
        try:
            response_json = response.json()
            choices = response_json.get("choices", [])
            
            if not choices:
                return LLMResponse(
                    text=None,
                    request_id=request.request_id,
                    model=request.model or self.model,
                    error="Inga val returnerades i svaret",
                    raw_response=response_json
                )
            
            completion_text = choices[0].get("text", "")
            
            return LLMResponse(
                text=completion_text,
                request_id=request.request_id,
                model=request.model or self.model,
                prompt_tokens=response_json.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_json.get("usage", {}).get("completion_tokens", 0),
                total_tokens=response_json.get("usage", {}).get("total_tokens", 0),
                finish_reason=choices[0].get("finish_reason", "unknown"),
                raw_response=response_json
            )
        except Exception as e:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"Fel vid tolkning av svar: {str(e)}",
                raw_response={"error": str(e), "response_text": response.text}
            )
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verifierar anslutning till Oobabooga"""
        try:
            response = self.session.get(f"{self.base_url}/models")
            
            if response.status_code == 200:
                return True, "Anslutning till Oobabooga verifierad"
            else:
                return False, f"Kunde inte ansluta till Oobabooga. Status: {response.status_code}"
        except Exception as e:
            return False, f"Anslutningsfel till Oobabooga: {str(e)}"
    
    def _is_json(self, response: requests.Response) -> bool:
        """Kontrollerar om svaret är JSON"""
        try:
            response.json()
            return True
        except:
            return False


class OpenAIProvider(LLMProviderBase):
    """Provider för OpenAI API"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initierar OpenAI providern
        
        Args:
            config: Konfiguration för providern
            logger: Logger för att logga meddelanden
        """
        super().__init__(config, logger)
        # Sätt API-nyckeln i headers
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API-nyckel saknas i konfiguration och miljövariabler")
        
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        # Standardmodell om ingen anges
        if not self.model:
            self.model = "gpt-3.5-turbo"
        
        # Om base_url inte är angivet, använd standardvärden
        if not self.base_url:
            self.base_url = "https://api.openai.com/v1"
    
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Genererar OpenAI-specifik nyttolast"""
        # OpenAI använder messages-format
        messages = [{"role": "user", "content": request.prompt}]
        
        return {
            "model": request.model or self.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences if request.stop_sequences else None,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty
        }
    
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """Tolkar OpenAI-specifikt svar"""
        if response.status_code != 200:
            error_msg = "Okänt fel"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", "Okänt fel")
            except:
                error_msg = f"HTTP-fel {response.status_code}: {response.text}"
            
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=error_msg,
                raw_response=response.json() if self._is_json(response) else {"text": response.text}
            )
        
        try:
            response_json = response.json()
            choices = response_json.get("choices", [])
            
            if not choices:
                return LLMResponse(
                    text=None,
                    request_id=request.request_id,
                    model=request.model or self.model,
                    error="Inga val returnerades i svaret",
                    raw_response=response_json
                )
            
            # Extrahera text baserat på OpenAI-format (använder messages)
            completion_text = choices[0].get("message", {}).get("content", "")
            
            return LLMResponse(
                text=completion_text,
                request_id=request.request_id,
                model=request.model or self.model,
                prompt_tokens=response_json.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_json.get("usage", {}).get("completion_tokens", 0),
                total_tokens=response_json.get("usage", {}).get("total_tokens", 0),
                finish_reason=choices[0].get("finish_reason", "unknown"),
                raw_response=response_json
            )
        except Exception as e:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"Fel vid tolkning av svar: {str(e)}",
                raw_response={"error": str(e), "response_text": response.text}
            )
    
    def get_endpoint(self) -> str:
        """Hämtar rätt endpoint för tjänsten"""
        return "/chat/completions"
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verifierar anslutning till OpenAI"""
        try:
            response = self.session.get(f"{self.base_url}/models")
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                available_models = [m.get("id") for m in models if m.get("id")]
                
                if self.model and self.model not in available_models:
                    return True, f"Varning: Modell '{self.model}' hittades inte i modellistan, men kan fortfarande vara tillgänglig."
                
                return True, f"Anslutning till OpenAI verifierad."
            else:
                error_msg = "Okänt fel"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", "Okänt fel")
                except:
                    error_msg = f"HTTP-fel {response.status_code}: {response.text}"
                
                return False, f"Kunde inte ansluta till OpenAI. {error_msg}"
        except Exception as e:
            return False, f"Anslutningsfel till OpenAI: {str(e)}"
    
    def _is_json(self, response: requests.Response) -> bool:
        """Kontrollerar om svaret är JSON"""
        try:
            response.json()
            return True
        except:
            return False


class ClaudeProvider(LLMProviderBase):
    """Provider för Anthropic Claude API"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initierar Claude providern
        
        Args:
            config: Konfiguration för providern
            logger: Logger för att logga meddelanden
        """
        super().__init__(config, logger)
        # Sätt API-nyckeln i headers
        api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("Anthropic API-nyckel saknas i konfiguration och miljövariabler")
        
        self.session.headers.update({
            "x-api-key": api_key,
            "anthropic-version": config.get("api_version", "2023-06-01"),
            "Content-Type": "application/json"
        })
        
        # Standardmodell om ingen anges
        if not self.model:
            self.model = "claude-3-opus-20240229"
        
        # Om base_url inte är angivet, använd standardvärden
        if not self.base_url:
            self.base_url = "https://api.anthropic.com/v1"
    
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Genererar Claude-specifik nyttolast"""
        return {
            "model": request.model or self.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop_sequences": request.stop_sequences if request.stop_sequences else []
        }
    
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """Tolkar Claude-specifikt svar"""
        if response.status_code != 200:
            error_msg = "Okänt fel"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Okänt fel")
            except:
                error_msg = f"HTTP-fel {response.status_code}: {response.text}"
            
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=error_msg,
                raw_response=response.json() if self._is_json(response) else {"text": response.text}
            )
        
        try:
            response_json = response.json()
            content = response_json.get("content", [])
            
            if not content:
                return LLMResponse(
                    text=None,
                    request_id=request.request_id,
                    model=request.model or self.model,
                    error="Inget innehåll returnerades i svaret",
                    raw_response=response_json
                )
            
            # Extrahera text baserat på Claude-format
            completion_text = ""
            for block in content:
                if block.get("type") == "text":
                    completion_text += block.get("text", "")
            
            return LLMResponse(
                text=completion_text,
                request_id=request.request_id,
                model=request.model or self.model,
                prompt_tokens=response_json.get("usage", {}).get("input_tokens", 0),
                completion_tokens=response_json.get("usage", {}).get("output_tokens", 0),
                total_tokens=response_json.get("usage", {}).get("input_tokens", 0) + response_json.get("usage", {}).get("output_tokens", 0),
                finish_reason=response_json.get("stop_reason", "unknown"),
                raw_response=response_json
            )
        except Exception as e:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"Fel vid tolkning av svar: {str(e)}",
                raw_response={"error": str(e), "response_text": response.text}
            )
    
    def get_endpoint(self) -> str:
        """Hämtar rätt endpoint för tjänsten"""
        return "/messages"
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verifierar anslutning till Claude"""
        try:
            # Claude har ingen enkel verifieringsendpoint, så vi skickar en minimal begäran
            test_payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Test connection"}],
                "max_tokens": 10
            }
            
            response = self.session.post(f"{self.base_url}/messages", json=test_payload)
            
            if response.status_code == 200:
                return True, f"Anslutning till Claude verifierad med modell {self.model}"
            else:
                error_msg = "Okänt fel"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Okänt fel")
                except:
                    error_msg = f"HTTP-fel {response.status_code}: {response.text}"
                
                return False, f"Kunde inte ansluta till Claude. {error_msg}"
        except Exception as e:
            return False, f"Anslutningsfel till Claude: {str(e)}"
    
    def _is_json(self, response: requests.Response) -> bool:
        """Kontrollerar om svaret är JSON"""
        try:
            response.json()
            return True
        except:
            return False




class OpenRouterProvider(LLMProviderBase):
    """Provider för OpenRouter API som stödjer många olika LLM-modeller"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initierar OpenRouter providern
        
        Args:
            config: Konfiguration för providern
            logger: Logger för att logga meddelanden
        """
        super().__init__(config, logger)
        # Sätt API-nyckeln i headers
        api_key = config.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("OpenRouter API-nyckel saknas i konfiguration och miljövariabler")
        
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": config.get("referer", "https://localhost"),  # Krävs för OpenRouter
            "X-Title": config.get("title", "Produktinformationsextraktor")  # Valfritt
        })
        
        # Standardmodell om ingen anges
        if not self.model:
            self.model = "openai/gpt-3.5-turbo"
        
        # Om base_url inte är angivet, använd standardvärden
        if not self.base_url:
            self.base_url = "https://openrouter.ai/api/v1"
    
    def generate_request_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Genererar OpenRouter-specifik nyttolast"""
        return {
            "model": request.model or self.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences if request.stop_sequences else None,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty
        }
    
    def parse_response(self, response: requests.Response, request: LLMRequest) -> LLMResponse:
        """Tolkar OpenRouter-specifikt svar"""
        if response.status_code != 200:
            error_msg = "Okänt fel"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", "Okänt fel")
            except:
                error_msg = f"HTTP-fel {response.status_code}: {response.text}"
            
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=error_msg,
                raw_response=response.json() if self._is_json(response) else {"text": response.text}
            )
        
        try:
            response_json = response.json()
            choices = response_json.get("choices", [])
            
            if not choices:
                return LLMResponse(
                    text=None,
                    request_id=request.request_id,
                    model=request.model or self.model,
                    error="Inga val returnerades i svaret",
                    raw_response=response_json
                )
            
            # Extrahera text baserat på OpenRouter-format (följer OpenAI-format)
            completion_text = choices[0].get("message", {}).get("content", "")
            
            return LLMResponse(
                text=completion_text,
                request_id=request.request_id,
                model=response_json.get("model", request.model or self.model),  # Använd faktisk modell från svaret
                prompt_tokens=response_json.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_json.get("usage", {}).get("completion_tokens", 0),
                total_tokens=response_json.get("usage", {}).get("total_tokens", 0),
                finish_reason=choices[0].get("finish_reason", "unknown"),
                raw_response=response_json
            )
        except Exception as e:
            return LLMResponse(
                text=None,
                request_id=request.request_id,
                model=request.model or self.model,
                error=f"Fel vid tolkning av svar: {str(e)}",
                raw_response={"error": str(e), "response_text": response.text}
            )
    
    def get_endpoint(self) -> str:
        """Hämtar rätt endpoint för tjänsten"""
        return "/chat/completions"
    
    def verify_connection(self) -> Tuple[bool, str]:
        """Verifierar anslutning till OpenRouter"""
        try:
            response = self.session.get(f"{self.base_url}/models")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                available_models = [m.get("id") for m in models if m.get("id")]
                
                if self.model and self.model not in available_models:
                    return True, f"Varning: Modell '{self.model}' hittades inte i modellistan, men kan fortfarande vara tillgänglig."
                
                return True, f"Anslutning till OpenRouter verifierad."
            else:
                error_msg = "Okänt fel"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", "Okänt fel")
                except:
                    error_msg = f"HTTP-fel {response.status_code}: {response.text}"
                
                return False, f"Kunde inte ansluta till OpenRouter. {error_msg}"
        except Exception as e:
            return False, f"Anslutningsfel till OpenRouter: {str(e)}"
    
    def _is_json(self, response: requests.Response) -> bool:
        """Kontrollerar om svaret är JSON"""
        try:
            response.json()
            return True
        except:
            return False


class ProviderFactory:
    """Fabriksklass för att skapa rätt LLM-provider"""
    
    @staticmethod
    def create_provider(provider_type: LLMProvider, config: Dict[str, Any], 
                         logger: logging.Logger) -> LLMProviderBase:
        """
        Skapar och returnerar rätt provider baserat på typ
        
        Args:
            provider_type: Typ av provider att skapa
            config: Konfiguration för providern
            logger: Logger för att logga meddelanden
            
        Returns:
            LLMProviderBase: Den skapade providern
            
        Raises:
            ValueError: Om provider_type är okänd
        """
        if provider_type == LLMProvider.OLLAMA:
            return OllamaProvider(config, logger)
        elif provider_type == LLMProvider.LMSTUDIO:
            return LMStudioProvider(config, logger)
        elif provider_type == LLMProvider.OOBABOOGA:
            return OobaboogaProvider(config, logger)
        elif provider_type == LLMProvider.OPENAI:
            return OpenAIProvider(config, logger)
        elif provider_type == LLMProvider.CLAUDE:
            return ClaudeProvider(config, logger)
        elif provider_type == LLMProvider.OPENROUTER:
            return OpenRouterProvider(config, logger)
        else:
            raise ValueError(f"Okänd provider-typ: {provider_type}")


class ChunkManager:
    """
    Klass för att dela upp stora textfiler i hanterbara bitar
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initierar chunk-hanteraren
        
        Args:
            config: Konfiguration för chunking
            logger: Logger för att logga meddelanden
        """
        self.config = config
        self.logger = logger
        self.chunk_size = config.get("chunk_size", 15000)
        self.chunk_overlap = config.get("chunk_overlap", 2000)
        self.max_file_size = config.get("max_file_size", 5000000)  # 5MB
    
    def should_chunk(self, text: str) -> bool:
        """
        Kontrollerar om texten behöver delas upp
        
        Args:
            text: Text att kontrollera
            
        Returns:
            bool: True om texten behöver delas upp, annars False
        """
        return len(text) > self.chunk_size
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Delar upp texten i hanterbara bitar
        
        Args:
            text: Text att dela upp
            
        Returns:
            List[str]: Lista med textbitar
        """
        if not self.should_chunk(text):
            return [text]
        
        # Dela upp texten i bitar
        chunks = []
        start = 0
        
        while start < len(text):
            # Beräkna slutposition för denna bit
            end = min(start + self.chunk_size, len(text))
            
            # Justera slutposition för att inte dela upp meningar
            if end < len(text):
                # Sök efter lämpliga avgränsare: punkt+mellanslag, nyrad
                sentence_end = text.rfind('. ', start, end)
                paragraph_end = text.rfind('\n\n', start, end)
                
                # Välj den bästa brytpunkten
                if paragraph_end > 0.8 * self.chunk_size:
                    end = paragraph_end + 2  # Inkludera dubbla nyradstecken
                elif sentence_end > 0.6 * self.chunk_size:
                    end = sentence_end + 2  # Inkludera punkt och mellanslag
            
            # Lägg till denna bit till listan
            chunks.append(text[start:end])
            
            # Flytta startpositionen, minus överlappning
            start = end - min(self.chunk_overlap, end - start - 1)
            
            # Säkerställ att vi inte går bakåt (kan hända med lång överlappning)
            if start <= 0 or start >= end:
                start = end  # Ingen överlappning om bitarna blir för små
        
        self.logger.info(f"Text uppdelad i {len(chunks)} bitar (original längd: {len(text)})")
        return chunks
    
    def is_file_too_large(self, file_path: Union[str, Path]) -> bool:
        """
        Kontrollerar om en fil är för stor för att bearbeta
        
        Args:
            file_path: Sökväg till filen att kontrollera
            
        Returns:
            bool: True om filen är för stor, annars False
        """
        file_size = Path(file_path).stat().st_size
        return file_size > self.max_file_size
    
    def chunk_file(self, file_path: Union[str, Path], encoding: str = 'utf-8') -> List[str]:
        """
        Läser en fil och delar upp innehållet i hanterbara bitar
        
        Args:
            file_path: Sökväg till filen att läsa
            encoding: Teckenkodning för filen
            
        Returns:
            List[str]: Lista med textbitar
            
        Raises:
            ValueError: Om filen är för stor eller inte kan läsas
        """
        file_path = Path(file_path)
        
        if self.is_file_too_large(file_path):
            raise ValueError(f"Filen {file_path} är för stor för att bearbeta (max: {self.max_file_size} bytes)")
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            
            return self.chunk_text(text)
        except Exception as e:
            self.logger.error(f"Fel vid läsning av fil {file_path}: {str(e)}")
            raise ValueError(f"Kunde inte läsa fil: {str(e)}")


class ResponseParser:
    """
    Klass för att tolka och strukturera LLM-svar
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initierar svarsparser
        
        Args:
            logger: Logger för att logga meddelanden
        """
        self.logger = logger
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extraherar JSON från textsvar
        
        Args:
            text: Text att extrahera JSON från
            
        Returns:
            Optional[Dict[str, Any]]: Extraherad JSON eller None om ingen JSON hittades
        """
        if not text:
            return None
        
        # Försök hitta JSON omsluten av ```json och ```
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # Försök hitta något som ser ut som JSON (börjar med { och slutar med })
            json_match = re.search(r'(\{[\s\S]*\})', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                self.logger.warning("Kunde inte hitta JSON i svaret")
                return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Fel vid tolkning av JSON: {str(e)}")
            self.logger.debug(f"JSON-sträng som orsakade felet: {json_str}")
            
            # Försök reparera JSON och tolka igen
            repaired_json = self._repair_json(json_str)
            if repaired_json:
                try:
                    return json.loads(repaired_json)
                except json.JSONDecodeError:
                    self.logger.error("Kunde inte reparera JSON-strängen")
            
            return None
    
    def _repair_json(self, json_str: str) -> Optional[str]:
        """
        Försöker reparera felaktig JSON
        
        Args:
            json_str: JSON-sträng att reparera
            
        Returns:
            Optional[str]: Reparerad JSON-sträng eller None om reparation misslyckades
        """
        # Vanliga reparationer
        try:
            # Ersätt enkla citattecken med dubbla
            if "'" in json_str and '"' not in json_str:
                json_str = json_str.replace("'", '"')
            
            # Rätta till saknade citattecken kring nycklar
            json_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', json_str)
            
            # Ta bort eventuella enstaka bakåtsnedstreck före citattecken
            json_str = json_str.replace('\\"', '"')
            
            # Försök rätta till saknade kommatecken
            json_str = re.sub(r'}\s*{', '},{', json_str)
            
            # Rätta till avslutande kommatecken i listor/objektet
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            return json_str
        except Exception as e:
            self.logger.error(f"Fel vid reparation av JSON: {str(e)}")
            return None
    
    def parse_combined_data(self, text: str) -> Dict[str, Any]:
        """
        Tolkar kombinerad data (produkt, kompatibilitet, tech specs) från LLM-svar
        
        Args:
            text: Text att tolka
            
        Returns:
            Dict[str, Any]: Strukturerad data
        """
        json_data = self.extract_json(text)
        
        if not json_data:
            return {
                "parsing_error": "Kunde inte extrahera JSON från svaret"
            }
        
        # Validera produktinformation om det finns
        if "product" in json_data:
            if not isinstance(json_data["product"], dict):
                self.logger.warning("JSON har 'product' som inte är ett objekt")
                json_data.pop("product")
            elif "title" not in json_data["product"]:
                self.logger.warning("Produktobjekt saknar 'title'-fältet")
        
        # Validera kompatibilitetsrelationer
        if "relations" in json_data:
            if not isinstance(json_data["relations"], list):
                self.logger.warning("JSON har 'relations' som inte är en lista")
                json_data["relations"] = []
            else:
                # Validera varje relation
                for i, relation in enumerate(json_data["relations"]):
                    required_fields = ["relation_type", "related_product"]
                    missing_fields = [field for field in required_fields if field not in relation]
                    if missing_fields:
                        self.logger.warning(f"Relation {i} saknar obligatoriska fält: {', '.join(missing_fields)}")
                        relation["validation_error"] = f"Saknar obligatoriska fält: {', '.join(missing_fields)}"
        
        # Validera tekniska specifikationer
        if "specifications" in json_data:
            if not isinstance(json_data["specifications"], list):
                self.logger.warning("JSON har 'specifications' som inte är en lista")
                json_data["specifications"] = []
            else:
                # Validera varje specifikation
                for i, spec in enumerate(json_data["specifications"]):
                    required_fields = ["category", "name", "raw_value"]
                    missing_fields = [field for field in required_fields if field not in spec]
                    if missing_fields:
                        self.logger.warning(f"Specifikation {i} saknar obligatoriska fält: {', '.join(missing_fields)}")
                        spec["validation_error"] = f"Saknar obligatoriska fält: {', '.join(missing_fields)}"
        
        # Validera datatabeller
        if "data_tables" in json_data:
            if not isinstance(json_data["data_tables"], list):
                self.logger.warning("JSON har 'data_tables' som inte är en lista")
                json_data["data_tables"] = []
            else:
                # Validera varje datatabell
                for i, table in enumerate(json_data["data_tables"]):
                    required_fields = ["title", "rows"]
                    missing_fields = [field for field in required_fields if field not in table]
                    if missing_fields:
                        self.logger.warning(f"Datatabell {i} saknar obligatoriska fält: {', '.join(missing_fields)}")
                        table["validation_error"] = f"Saknar obligatoriska fält: {', '.join(missing_fields)}"
        
        return json_data
    
    def parse_compatibility_data(self, text: str) -> Dict[str, Any]:
        """
        Tolkar kompatibilitetsdata från LLM-svar
        
        Args:
            text: Text att tolka
            
        Returns:
            Dict[str, Any]: Strukturerad kompatibilitetsdata
        """
        # Extrahera JSON från svaret
        json_data = self.extract_json(text)
        
        if not json_data:
            # Grundläggande fallback-struktur
            return {
                "relations": [],
                "parsing_error": "Kunde inte extrahera JSON från svaret"
            }
        
        # Kontrollera om detta är kombinerad data
        if "relations" in json_data and isinstance(json_data["relations"], list):
            # Extrahera bara relations-delen
            return {"relations": json_data["relations"]}
        
        # Verifiera strukturen
        if "relations" not in json_data:
            self.logger.warning("JSON saknar 'relations'-nyckeln")
            json_data["relations"] = []
            json_data["parsing_error"] = "Svaret saknar korrekt struktur (ingen 'relations'-nyckel)"
        
        # Validera varje relation
        for i, relation in enumerate(json_data.get("relations", [])):
            # Kontrollera obligatoriska fält
            required_fields = ["relation_type", "related_product", "context"]
            missing_fields = [field for field in required_fields if field not in relation]
            
            if missing_fields:
                self.logger.warning(f"Relation {i} saknar obligatoriska fält: {', '.join(missing_fields)}")
                relation["validation_error"] = f"Saknar obligatoriska fält: {', '.join(missing_fields)}"
        
        return json_data
    
    def parse_technical_specs(self, text: str) -> Dict[str, Any]:
        """
        Tolkar tekniska specifikationer från LLM-svar
        
        Args:
            text: Text att tolka
            
        Returns:
            Dict[str, Any]: Strukturerade tekniska specifikationer
        """
        # Extrahera JSON från svaret
        json_data = self.extract_json(text)
        
        if not json_data:
            # Grundläggande fallback-struktur
            return {
                "specifications": [],
                "parsing_error": "Kunde inte extrahera JSON från svaret"
            }
        
        # Kontrollera om detta är kombinerad data
        if "specifications" in json_data and isinstance(json_data["specifications"], list):
            # Extrahera bara specifications-delen
            return {"specifications": json_data["specifications"]}
        
        # Verifiera strukturen
        if "specifications" not in json_data:
            self.logger.warning("JSON saknar 'specifications'-nyckeln")
            json_data["specifications"] = []
            json_data["parsing_error"] = "Svaret saknar korrekt struktur (ingen 'specifications'-nyckel)"
        
        # Validera varje specifikation
        for i, spec in enumerate(json_data.get("specifications", [])):
            # Kontrollera obligatoriska fält
            required_fields = ["category", "name", "raw_value"]
            missing_fields = [field for field in required_fields if field not in spec]
            
            if missing_fields:
                self.logger.warning(f"Specifikation {i} saknar obligatoriska fält: {', '.join(missing_fields)}")
                spec["validation_error"] = f"Saknar obligatoriska fält: {', '.join(missing_fields)}"
        
        return json_data
    
    def merge_chunked_results(self, results: List[Dict[str, Any]], result_type: str = "combined") -> Dict[str, Any]:
        """
        Sammanfogar resultat från uppdelade chunks
        
        Args:
            results: Lista med resultat att sammanfoga
            result_type: Typ av resultat ("combined", "compatibility" eller "technical")
            
        Returns:
            Dict[str, Any]: Sammanfogat resultat
        """
        if not results:
            return {}
        
        # För kombinerad extraktion
        if result_type == "combined":
            merged_result = {}
            
            # Samla alla produkt-info och välj den mest kompletta
            if any("product" in result for result in results):
                product_infos = [result.get("product", {}) for result in results if "product" in result]
                if product_infos:
                    best_product = max(product_infos, key=lambda p: len(p))
                    merged_result["product"] = best_product
            
            # Samla alla relationer
            all_relations = []
            for result in results:
                relations = result.get("relations", [])
                if isinstance(relations, list):
                    all_relations.extend(relations)
            
            if all_relations:
                # Ta bort eventuella dubbletter baserat på relation och produkt
                unique_relations = {}
                for relation in all_relations:
                    if not isinstance(relation, dict):
                        continue
                    
                    # Skapa en nyckel baserad på relationstyp och relaterad produkt
                    related_name = ""
                    if isinstance(relation.get("related_product"), dict):
                        related_name = relation["related_product"].get("name", "").lower()
                    else:
                        related_name = str(relation.get("related_product", "")).lower()
                    
                    key = f"{relation.get('relation_type', '')}-{related_name}"
                    
                    # Behåll den första förekomsten av varje unik relation
                    if key not in unique_relations:
                        unique_relations[key] = relation
                
                merged_result["relations"] = list(unique_relations.values())
            
            # Samla alla specifikationer
            all_specs = []
            for result in results:
                specs = result.get("specifications", [])
                if isinstance(specs, list):
                    all_specs.extend(specs)
            
            if all_specs:
                # Ta bort dubbletter baserat på kategori och namn
                unique_specs = {}
                for spec in all_specs:
                    if not isinstance(spec, dict):
                        continue
                    
                    key = f"{spec.get('category', '')}-{spec.get('name', '')}"
                    
                    # Behåll den första förekomsten av varje unik specifikation
                    if key not in unique_specs:
                        unique_specs[key] = spec
                
                merged_result["specifications"] = list(unique_specs.values())
            
            # Samla alla datatabeller
            all_tables = []
            for result in results:
                tables = result.get("data_tables", [])
                if isinstance(tables, list):
                    all_tables.extend(tables)
            
            if all_tables:
                # Ta bort dubbletter baserat på titel
                unique_tables = {}
                for table in all_tables:
                    if not isinstance(table, dict):
                        continue
                    
                    key = table.get("title", "").lower()
                    
                    # Behåll den mest detaljerade tabellen (med flest rader)
                    if key not in unique_tables or (
                        len(table.get("rows", [])) > len(unique_tables[key].get("rows", []))
                    ):
                        unique_tables[key] = table
                
                merged_result["data_tables"] = list(unique_tables.values())
            
            return merged_result
        
        elif result_type == "compatibility":
            # Sammanfoga kompatibilitetsrelationer
            all_relations = []
            for result in results:
                relations = result.get("relations", [])
                if isinstance(relations, list):
                    all_relations.extend(relations)
            
            # Ta bort eventuella dubbletter baserat på kontexten
            unique_relations = {}
            for relation in all_relations:
                # Skapa en nyckel baserad på relation och produkt
                key = f"{relation.get('relation_type', '')}-{relation.get('related_product', '')}"
                
                # Behåll relationen med högst förtroende om det finns flera med samma nyckel
                if key not in unique_relations or relation.get('confidence', 0) > unique_relations[key].get('confidence', 0):
                    unique_relations[key] = relation
            
            return {"relations": list(unique_relations.values())}
        
        elif result_type == "technical":
            # Sammanfoga tekniska specifikationer
            all_specs = []
            for result in results:
                specs = result.get("specifications", [])
                if isinstance(specs, list):
                    all_specs.extend(specs)
            
            # Ta bort dubbletter baserat på kategori och namn
            unique_specs = {}
            for spec in all_specs:
                # Skapa en nyckel baserad på kategori och namn
                key = f"{spec.get('category', '')}-{spec.get('name', '')}"
                
                # Behåll specifikationen med högst förtroende om det finns flera med samma nyckel
                if key not in unique_specs or spec.get('confidence', 0) > unique_specs[key].get('confidence', 0):
                    unique_specs[key] = spec
            
            return {"specifications": list(unique_specs.values())}
        
        else:
            self.logger.warning(f"Okänd resultattyp: {result_type}")
            return {}


class LLMClient:
    """
    Huvudklass för att interagera med LLM-tjänster
    """
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger, visualizer=None):
        """
        Initierar LLM-klienten
        
        Args:
            config: Konfiguration för klienten
            logger: Logger för att logga meddelanden
            visualizer: Visualiserare för att visa information i terminalen
        """
        self.config = config
        self.logger = logger
        self.visualizer = visualizer
        
        # Skapa provider baserat på konfiguration
        provider_type = LLMProvider(config.get("provider", "ollama"))
        provider_config = config.get("providers", {}).get(provider_type.value, {})
        
        # Fyll i saknade värden från root-konfigurationen
        for key in ["base_url", "model", "max_tokens", "temperature"]:
            if key not in provider_config and key in config:
                provider_config[key] = config[key]
        
        self.logger.info(f"Initierar primär LLM-provider av typen: {provider_type.value}")
        
        # Skapa primär provider
        try:
            self.provider = ProviderFactory.create_provider(provider_type, provider_config, logger)
        except Exception as e:
            self.logger.error(f"Fel vid initialisering av primär provider: {str(e)}")
            self.provider = None
        
        # Skapa fallback-provider om konfigurerad
        self.fallback_provider = None
        if config.get("fallback_provider"):
            fallback_type = LLMProvider(config.get("fallback_provider"))
            fallback_config = config.get("providers", {}).get(fallback_type.value, {})
            
            self.logger.info(f"Initierar fallback LLM-provider av typen: {fallback_type.value}")
            
            # Fyll i saknade värden
            if "base_url" not in fallback_config and "fallback_base_url" in config:
                fallback_config["base_url"] = config["fallback_base_url"]
            
            for key in ["model", "max_tokens", "temperature"]:
                if key not in fallback_config and key in config:
                    fallback_config[key] = config[key]
            
            try:
                self.fallback_provider = ProviderFactory.create_provider(fallback_type, fallback_config, logger)
            except Exception as e:
                self.logger.error(f"Fel vid initialisering av fallback-provider: {str(e)}")
        
        # Skapa chunk-hanterare
        self.chunk_manager = ChunkManager(config.get("extraction", {}), logger)
        
        # Skapa svarsparser
        self.response_parser = ResponseParser(logger)
        
        # Konfigurera återförsök
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 2)
        
        # Begränsning (throttling)
        self.throttling_enabled = config.get("throttling", {}).get("enabled", False)
        self.requests_per_minute = config.get("throttling", {}).get("requests_per_minute", 30)
        self.last_request_time = time.time()
        self.request_timestamps = []
        
        # Spåra senaste svarstid
        self.last_latency_ms = 0
        
        # Prompthanterare (om tillgänglig)
        self.prompt_manager = None
    
    def set_prompt_manager(self, prompt_manager) -> None:
        """
        Sätter prompthanteraren
        
        Args:
            prompt_manager: Prompthanteraren att använda
        """
        self.prompt_manager = prompt_manager
        self.logger.debug("Prompthanterare installerad i LLM-klienten")
    
    def verify_connection(self) -> bool:
        """
        Verifierar anslutningen till LLM-tjänsten
        
        Returns:
            bool: True om anslutningen är OK, annars False
        """
        if not self.provider:
            self.logger.error("Ingen primär provider initialiserad")
            return False
            
        success, message = self.provider.verify_connection()
        
        if success:
            self.logger.info(message)
            return True
        else:
            self.logger.error(message)
            
            # Försök med fallback om tillgänglig
            if self.fallback_provider:
                self.logger.info("Försöker med fallback-provider...")
                success, message = self.fallback_provider.verify_connection()
                
                if success:
                    self.logger.info(message)
                    self.logger.warning("Använder fallback-provider som primär provider")
                    self.provider, self.fallback_provider = self.fallback_provider, self.provider
                    return True
                else:
                    self.logger.error(message)
            
            return False
    
    def apply_throttling(self) -> None:
        """Tillämpar begränsning av antal förfrågningar per minut"""
        if not self.throttling_enabled:
            return
        
        current_time = time.time()
        
        # Rensa gamla tidsstämplar (äldre än 60 sekunder)
        self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 60]
        
        # Kontrollera om vi behöver vänta
        if len(self.request_timestamps) >= self.requests_per_minute:
            # Beräkna hur länge vi behöver vänta
            oldest_timestamp = min(self.request_timestamps)
            wait_time = 60 - (current_time - oldest_timestamp)
            
            if wait_time > 0:
                self.logger.info(f"Throttling aktivt: väntar {wait_time:.2f} sekunder")
                time.sleep(wait_time)
        
        # Lägg till ny tidsstämpel
        self.request_timestamps.append(time.time())
    
    def get_completion(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Hämtar ett svar från LLM-tjänsten med automatiska återförsök
        
        Args:
            prompt: Prompten att skicka
            **kwargs: Ytterligare argument för begäran
            
        Returns:
            LLMResponse: Svaret från LLM-tjänsten
        """
        if not self.provider:
            error_msg = "Ingen LLM-provider tillgänglig"
            self.logger.error(error_msg)
            return LLMResponse(
                text=None,
                request_id=hashlib.md5(prompt.encode()).hexdigest()[:10],
                model="none",
                error=error_msg
            )
            
        # Skapa begäran
        request = LLMRequest(
            prompt=prompt,
            model=kwargs.get("model", self.config.get("model")),
            max_tokens=kwargs.get("max_tokens", self.config.get("max_tokens", 2048)),
            temperature=kwargs.get("temperature", self.config.get("temperature", 0.1)),
            stop_sequences=kwargs.get("stop_sequences"),
            top_p=kwargs.get("top_p", 1.0),
            frequency_penalty=kwargs.get("frequency_penalty", 0.0),
            presence_penalty=kwargs.get("presence_penalty", 0.0)
        )
        
        # Visa prompt i terminalen om visualizer finns
        if self.visualizer:
            self.visualizer.display_prompt(prompt, "LLM Prompt")
        
        # Tillämpa begränsning
        self.apply_throttling()
        
        # Försök skicka begäran med återförsök
        response = None
        for attempt in range(self.max_retries):
            try:
                # Skicka begäran
                self.logger.prompt(f"Skickar prompt (försök {attempt+1}/{self.max_retries})")
                response = self.provider.send_request(request)
                
                # Kontrollera om svaret var framgångsrikt
                if response.successful:
                    # Visa svaret i terminalen om visualizer finns
                    if self.visualizer:
                        self.visualizer.display_response(response.text, "LLM Response")
                    
                    self.logger.llm_response(f"Fick svar ({response.total_tokens} tokens, {response.latency_ms} ms)")
                    break
                
                # Misslyckades, använd fallback om tillgänglig och det är sista försöket
                elif self.fallback_provider and attempt == self.max_retries - 1:
                    self.logger.retry(f"Alla försök misslyckades med primär provider, använder fallback")
                    
                    # Skicka begäran med fallback-provider
                    fallback_response = self.fallback_provider.send_request(request)
                    
                    if fallback_response.successful:
                        # Visa svaret i terminalen om visualizer finns
                        if self.visualizer:
                            self.visualizer.display_response(fallback_response.text, "LLM Response (Fallback)")
                        
                        self.logger.llm_response(f"Fick svar från fallback ({fallback_response.total_tokens} tokens, {fallback_response.latency_ms} ms)")
                        response = fallback_response
                        break
                
                # Logga fel och försök igen
                error_msg = response.error or "Okänt fel"
                self.logger.retry(f"Försök {attempt+1} misslyckades: {error_msg}")
                
                # Vänta innan nästa försök
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponentiell backoff
                    self.logger.info(f"Väntar {wait_time} sekunder innan nästa försök")
                    time.sleep(wait_time)
            
            except Exception as e:
                self.logger.retry(f"Oväntat fel i försök {attempt+1}: {str(e)}")
                
                # Vänta innan nästa försök
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponentiell backoff
                    self.logger.info(f"Väntar {wait_time} sekunder innan nästa försök")
                    time.sleep(wait_time)
        
        # Alla försök misslyckades
        if response is None or not response.successful:
            error_msg = "Alla försök misslyckades"
            self.logger.error(error_msg)
            
            # Returnera ett misslyckat svar
            if response is None:
                response = LLMResponse(
                    text=None,
                    request_id=request.request_id,
                    model=request.model,
                    error=error_msg,
                    raw_response={"error": error_msg}
                )
        
        # Efter alla försök, oavsett resultat:
        self.last_latency_ms = response.latency_ms if response.successful else 0
        
        return response
    
    def extract_with_template(self, text: str, prompt_template: PromptTemplate, result_type: str) -> Dict[str, Any]:
        """
        Generell metod för att extrahera information med en given promptmall
        
        Args:
            text: Text att extrahera information från
            prompt_template: Mall för prompten
            result_type: Typ av resultat som ska extraheras (för parsning)
            
        Returns:
            Dict[str, Any]: Extraherad information
        """
        # Kontrollera om det finns en cachad version av svaret om prompthanterare är tillgänglig
        if self.prompt_manager:
            formatted_prompt = prompt_template.format(text=text)
            cached_response = self.prompt_manager.get_cached_response(formatted_prompt)
            if cached_response:
                self.logger.debug(f"Använder cachat svar för {result_type}-extraktion")
                return cached_response
        
        # Kontrollera om texten behöver delas upp
        if self.chunk_manager.should_chunk(text):
            self.logger.workflow("Text för stor, delar upp i mindre bitar")
            chunks = self.chunk_manager.chunk_text(text)
            
            # Bearbeta varje bit och samla resultaten
            chunk_results = []
            progress_tracker = self.visualizer.create_progress_bar(len(chunks), f"Extraherar {result_type}") if self.visualizer else None
            
            for i, chunk in enumerate(chunks):
                self.logger.workflow(f"Bearbetar bit {i+1}/{len(chunks)}")
                
                # Skapa prompt för denna bit
                prompt = prompt_template.format(text=chunk)
                
                # Hämta LLM-svar
                response = self.get_completion(prompt)
                
                if response.successful:
                    # Tolka svaret baserat på typ
                    if result_type == "combined":
                        # För kombinerad extraktion, använd generell JSON-extrahering
                        result = self.response_parser.extract_json(response.text)
                    elif result_type == "compatibility":
                        result = self.response_parser.parse_compatibility_data(response.text)
                    elif result_type == "technical":
                        result = self.response_parser.parse_technical_specs(response.text)
                    else:
                        # För andra typer, använd generell JSON-extrahering
                        result = self.response_parser.extract_json(response.text)
                    
                    if result:
                        chunk_results.append(result)
                else:
                    self.logger.error(f"Kunde inte extrahera {result_type}-information från bit {i+1}")
                
                # Uppdatera framstegsspårare
                if progress_tracker:
                    progress_tracker.update()
            
            # Stäng framstegsspårare
            if progress_tracker:
                progress_tracker.close()
            
            # Sammanfoga resultaten baserat på typ
            if result_type == "combined":
                # För kombinerad extraktion, gör en speciell sammanslagning
                result = self._merge_combined_results(chunk_results)
            else:
                # För andra typer, använd befintlig sammanslagningslogik
                result = self.response_parser.merge_chunked_results(chunk_results, result_type)
            
            # Cacha svaret om prompthanterare är tillgänglig
            if self.prompt_manager and result:
                formatted_prompt = prompt_template.format(text=text)
                self.prompt_manager.cache_response(formatted_prompt, result)
            
            return result
        else:
            # Bearbeta hela texten på en gång
            prompt = prompt_template.format(text=text)
            response = self.get_completion(prompt)
            
            if response.successful:
                # Tolka svaret baserat på typ
                if result_type == "combined":
                    # För kombinerad extraktion, använd generell JSON-extrahering
                    result = self.response_parser.extract_json(response.text)
                elif result_type == "compatibility":
                    result = self.response_parser.parse_compatibility_data(response.text)
                elif result_type == "technical":
                    result = self.response_parser.parse_technical_specs(response.text)
                else:
                    # För andra typer, använd generell JSON-extrahering
                    result = self.response_parser.extract_json(response.text)
                
                # Cacha svaret om prompthanterare är tillgänglig
                if self.prompt_manager and result:
                    self.prompt_manager.cache_response(prompt, result)
                
                return result
            else:
                self.logger.error(f"Kunde inte extrahera {result_type}-information")
                return {} if result_type == "combined" else {"error": response.error}
    
    def extract_combined_data(self, text: str, prompt_template: PromptTemplate = None) -> Dict[str, Any]:
        """
        Extraherar kombinerad information (produkt, kompatibilitet, teknisk, etc.) från text
        
        Args:
            text: Text att extrahera information från
            prompt_template: Mall för prompten (om None används standardmallen)
            
        Returns:
            Dict[str, Any]: Extraherad kombinerad information
        """
        # Använd standardmall om ingen angavs
        if not prompt_template:
            from prompts.default_prompts import default_combined_template
            prompt_template = default_combined_template
        
        return self.extract_with_template(text, prompt_template, "combined")
    
    def extract_compatibility_info(self, text: str, prompt_template: PromptTemplate = None) -> Dict[str, Any]:
        """
        Extraherar kompatibilitetsinformation från text med hjälp av LLM
        
        Args:
            text: Text att extrahera information från
            prompt_template: Mall för prompten (om None används standardmallen)
            
        Returns:
            Dict[str, Any]: Extraherad kompatibilitetsinformation
        """
        # Använd standardmall om ingen angavs
        if not prompt_template:
            from prompts.default_prompts import default_compatibility_template
            prompt_template = default_compatibility_template
        
        return self.extract_with_template(text, prompt_template, "compatibility")
    
    def extract_technical_specs(self, text: str, prompt_template: PromptTemplate = None) -> Dict[str, Any]:
        """
        Extraherar tekniska specifikationer från text med hjälp av LLM
        
        Args:
            text: Text att extrahera information från
            prompt_template: Mall för prompten (om None används standardmallen)
            
        Returns:
            Dict[str, Any]: Extraherade tekniska specifikationer
        """
        # Använd standardmall om ingen angavs
        if not prompt_template:
            from prompts.default_prompts import default_technical_template
            prompt_template = default_technical_template
        
        return self.extract_with_template(text, prompt_template, "technical")
    
    def _merge_combined_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Specialiserad metod för att sammanfoga resultat från kombinerad extraktion
        
        Args:
            results: Lista med resultat att sammanfoga
            
        Returns:
            Dict[str, Any]: Sammanfogat resultat
        """
        if not results:
            return {}
        
        # Sammanfogat resultat
        merged_result = {}
        
        # Kombinera produktinformation
        # Välj den fullständigaste produktinformationen
        if any("product" in result for result in results):
            best_product_info = None
            max_product_fields = 0
            
            for result in results:
                if "product" in result:
                    product = result["product"]
                    field_count = len(product.keys())
                    
                    if field_count > max_product_fields:
                        max_product_fields = field_count
                        best_product_info = product
            
            if best_product_info:
                merged_result["product"] = best_product_info
        
        # Kombinera kompatibilitetsrelationer
        all_relations = []
        for result in results:
            if "relations" in result and isinstance(result["relations"], list):
                all_relations.extend(result["relations"])
        
        if all_relations:
            # Ta bort eventuella dubbletter baserat på relationstyp och produkt
            unique_relations = {}
            for relation in all_relations:
                # Skapa en nyckel baserad på relation och produkt
                related_name = ""
                if isinstance(relation.get("related_product"), dict):
                    related_name = relation["related_product"].get("name", "").lower()
                else:
                    related_name = str(relation.get("related_product", "")).lower()
                
                key = f"{relation.get('relation_type', '').lower()}-{related_name}"
                
                # Om relationen inte finns i uniques eller har mer information, lägg till den
                if key not in unique_relations:
                    unique_relations[key] = relation
                else:
                    # Om den befintliga relationen inte har artikel/EAN men den nya har det, uppdatera
                    existing = unique_relations[key]
                    if isinstance(relation.get("related_product"), dict) and isinstance(existing.get("related_product"), dict):
                        # Uppdatera med komplett information om den nya har mer data
                        if ("article_number" in relation["related_product"] and "article_number" not in existing["related_product"]) or \
                           ("ean" in relation["related_product"] and "ean" not in existing["related_product"]):
                            unique_relations[key] = relation
            
            if unique_relations:
                merged_result["relations"] = list(unique_relations.values())
        
        # Kombinera tekniska specifikationer
        all_specs = []
        for result in results:
            if "specifications" in result and isinstance(result["specifications"], list):
                all_specs.extend(result["specifications"])
        
        if all_specs:
            # Ta bort dubbletter baserat på kategori och namn
            unique_specs = {}
            for spec in all_specs:
                key = f"{spec.get('category', '').lower()}-{spec.get('name', '').lower()}"
                
                # Om specifikationen inte finns i uniques eller har mer information, lägg till den
                if key not in unique_specs:
                    unique_specs[key] = spec
                else:
                    # Om den befintliga inte har unit/value men den nya har det, uppdatera
                    existing = unique_specs[key]
                    if "unit" in spec and "unit" not in existing or \
                       "value" in spec and "value" not in existing:
                        unique_specs[key] = spec
            
            if unique_specs:
                merged_result["specifications"] = list(unique_specs.values())
        
        # Kombinera datatabeller
        all_tables = []
        for result in results:
            if "data_tables" in result and isinstance(result["data_tables"], list):
                all_tables.extend(result["data_tables"])
        
        if all_tables:
            # Ta bort dubbletter baserat på titel
            unique_tables = {}
            for table in all_tables:
                key = table.get("title", "").lower()
                
                # Om tabellen inte finns i uniques eller har fler rader, lägg till den
                if key not in unique_tables:
                    unique_tables[key] = table
                elif "rows" in table and "rows" in unique_tables[key]:
                    # Om den nya tabellen har fler rader, använd den istället
                    if len(table["rows"]) > len(unique_tables[key]["rows"]):
                        unique_tables[key] = table
            
            if unique_tables:
                merged_result["data_tables"] = list(unique_tables.values())
        
        return merged_result
    
    def verify_extraction_format(self, data: Dict[str, Any], data_type: str) -> bool:
        """
        Verifierar att extraherad data har rätt format
        
        Args:
            data: Data att verifiera
            data_type: Typ av data ("combined", "compatibility" eller "technical")
            
        Returns:
            bool: True om formatet är korrekt, annars False
        """
        if data_type == "combined":
            # Kontrollera kombinerad data
            # Här behöver vi endast kontrollera grundläggande struktur eftersom
            # olika delar kan vara tomma beroende på vad som hittades
            if not isinstance(data, dict):
                self.logger.error("Ogiltig datastruktur: inte ett objekt")
                return False
            
            # Kontrollera produktinformation om den finns
            if "product" in data:
                if not isinstance(data["product"], dict):
                    self.logger.error("Ogiltig produktinformation: inte ett objekt")
                    return False
                
                if "title" not in data["product"]:
                    self.logger.warning("Produktinformation saknar 'title'-fältet")
            
            # Kontrollera kompatibilitetsrelationer om de finns
            if "relations" in data:
                if not isinstance(data["relations"], list):
                    self.logger.error("Ogiltiga relationer: inte en lista")
                    return False
                
                for i, relation in enumerate(data["relations"]):
                    if not isinstance(relation, dict):
                        self.logger.error(f"Ogiltig relation {i}: inte ett objekt")
                        return False
                    
                    if "relation_type" not in relation:
                        self.logger.error(f"Ogiltig relation {i}: saknar 'relation_type'-fältet")
                        return False
                    
                    if "related_product" not in relation:
                        self.logger.error(f"Ogiltig relation {i}: saknar 'related_product'-fältet")
                        return False
                    
                    # Om related_product är ett objekt, kontrollera name-fältet
                    related_product = relation["related_product"]
                    if isinstance(related_product, dict) and "name" not in related_product:
                        self.logger.error(f"Ogiltig related_product för relation {i}: saknar 'name'-fältet")
                        return False
            
            # Kontrollera tekniska specifikationer om de finns
            if "specifications" in data:
                if not isinstance(data["specifications"], list):
                    self.logger.error("Ogiltiga specifikationer: inte en lista")
                    return False
                
                for i, spec in enumerate(data["specifications"]):
                    if not isinstance(spec, dict):
                        self.logger.error(f"Ogiltig specifikation {i}: inte ett objekt")
                        return False
                    
                    required_fields = ["category", "name", "raw_value"]
                    for field in required_fields:
                        if field not in spec:
                            self.logger.error(f"Ogiltig specifikation {i}: saknar fältet '{field}'")
                            return False
            
            # Kontrollera datatabeller om de finns
            if "data_tables" in data:
                if not isinstance(data["data_tables"], list):
                    self.logger.error("Ogiltiga datatabeller: inte en lista")
                    return False
                
                for i, table in enumerate(data["data_tables"]):
                    if not isinstance(table, dict):
                        self.logger.error(f"Ogiltig datatabell {i}: inte ett objekt")
                        return False
                    
                    if "title" not in table:
                        self.logger.error(f"Ogiltig datatabell {i}: saknar 'title'-fältet")
                        return False
                    
                    if "rows" not in table or not isinstance(table["rows"], list):
                        self.logger.error(f"Ogiltig datatabell {i}: saknar 'rows'-fältet eller det är inte en lista")
                        return False
            
            return True
            
        elif data_type == "compatibility":
            # Kontrollera kompatibilitetsformat
            if "relations" not in data or not isinstance(data["relations"], list):
                self.logger.error("Ogiltig datastruktur: saknar 'relations'-listan")
                return False
            
            # Kontrollera varje relation
            for i, relation in enumerate(data["relations"]):
                if not isinstance(relation, dict):
                    self.logger.error(f"Ogiltig relation {i}: inte ett objekt")
                    return False
                
                # Kontrollera obligatoriska fält
                required_fields = ["relation_type", "related_product", "context"]
                for field in required_fields:
                    if field not in relation:
                        self.logger.error(f"Ogiltig relation {i}: saknar fältet '{field}'")
                        return False
            
            return True
            
        elif data_type == "technical":
            # Kontrollera tekniskt specifikationsformat
            if "specifications" not in data or not isinstance(data["specifications"], list):
                self.logger.error("Ogiltig datastruktur: saknar 'specifications'-listan")
                return False
            
            # Kontrollera varje specifikation
            for i, spec in enumerate(data["specifications"]):
                if not isinstance(spec, dict):
                    self.logger.error(f"Ogiltig specifikation {i}: inte ett objekt")
                    return False
                
                # Kontrollera obligatoriska fält
                required_fields = ["category", "name", "raw_value"]
                for field in required_fields:
                    if field not in spec:
                        self.logger.error(f"Ogiltig specifikation {i}: saknar fältet '{field}'")
                        return False
            
            return True
            
        else:
            self.logger.error(f"Okänd datatyp: {data_type}")
            return False
    
    def retry_with_correction_prompt(self, initial_response: str, data_type: str, errors: List[str]) -> Dict[str, Any]:
        """
        Försöker igen med en korrigeringsprompt när initial-extraktionen misslyckas
        
        Args:
            initial_response: Det ursprungliga LLM-svaret
            data_type: Typ av data ("combined", "compatibility" eller "technical")
            errors: Lista med fel som behöver korrigeras
            
        Returns:
            Dict[str, Any]: Korrigerad data
        """
        # Skapa en prompt för att korrigera felen
        if data_type == "combined":
            from prompts.default_prompts import combined_correction_template
            correction_prompt = combined_correction_template.format(
                original_response=initial_response,
                errors="\n".join([f"- {error}" for error in errors])
            )
        elif data_type == "compatibility":
            from prompts.default_prompts import compatibility_correction_template
            correction_prompt = compatibility_correction_template.format(
                original_response=initial_response,
                errors="\n".join([f"- {error}" for error in errors])
            )
        elif data_type == "technical":
            from prompts.default_prompts import technical_correction_template
            correction_prompt = technical_correction_template.format(
                original_response=initial_response,
                errors="\n".join([f"- {error}" for error in errors])
            )
        else:
            self.logger.error(f"Okänd datatyp för korrigering: {data_type}")
            return {}
        
        # Hämta korrigerat svar
        self.logger.workflow("Försöker korrigera extraktion med specifik prompt")
        response = self.get_completion(correction_prompt)
        
        if response.successful:
            # Tolka det korrigerade svaret
            if data_type == "compatibility":
                return self.response_parser.parse_compatibility_data(response.text)
            else:
                return self.response_parser.parse_technical_specs(response.text)
        else:
            self.logger.error("Kunde inte korrigera extraktion")
            return {} if data_type == "compatibility" else {"specifications": []}



