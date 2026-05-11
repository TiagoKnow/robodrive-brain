import requests
import json
import logging
import time
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente para Ollama com suporte a múltiplos modelos"""

    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = os.getenv('MODEL_NAME', 'llama3:latest')
        self.api_url = f"{self.ollama_host}/api/generate"
        self.list_url = f"{self.ollama_host}/api/tags"

        logger.info(f"LLM Client inicializado - Host: {self.ollama_host}, Modelo: {self.model}")

    def list_models(self) -> List[str]:
        """Lista modelos disponíveis no servidor"""
        try:
            response = requests.get(self.list_url, timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
            return []
        except Exception as e:
            logger.error(f"Erro ao listar modelos: {e}")
            return []

    def change_model(self, model_name: str) -> bool:
        """Muda o modelo atual"""
        try:
            # Verifica se o modelo existe
            models = self.list_models()
            if model_name in models:
                self.model = model_name
                logger.info(f"Modelo alterado para: {model_name}")
                return True
            else:
                logger.warning(f"Modelo {model_name} não encontrado")
                return False
        except Exception as e:
            logger.error(f"Erro ao mudar modelo: {e}")
            return False

    def chat(self, prompt: str, context: List[Dict] = None, knowledge: str = "") -> str:
        """Envia prompt para a LLM e retorna resposta"""
        try:
            full_prompt = self._build_prompt(prompt, context, knowledge)

            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }

            start_time = time.time()
            response = requests.post(self.api_url, json=payload, timeout=60)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', 'Desculpe, não consegui processar.')
                logger.info(f"LLM respondeu em {elapsed:.2f}s")
                return llm_response
            else:
                logger.error(f"Erro LLM: Status {response.status_code}")
                return "Desculpe, tive um problema técnico."

        except requests.exceptions.Timeout:
            logger.error("Timeout na LLM")
            return "Demorou muito para processar. Pode repetir?"
        except Exception as e:
            logger.error(f"Erro no cliente LLM: {e}")
            return "Erro na comunicação com o servidor de IA."

    def _build_prompt(self, user_message: str, context: List[Dict] = None, knowledge: str = "") -> str:
        """Constrói o prompt com contexto e conhecimento"""
        base_prompt = f"""Você é o RoboDrive, um robô assistente amigável.
Você foi criado por Tiago e mora na casa dele.
Responda em português brasileiro, de forma natural e conversacional.

{knowledge}

"""

        if context:
            context_str = "\nHistórico da conversa:\n"
            for msg in context[-5:]:
                context_str += f"{msg['role']}: {msg['content']}\n"
            base_prompt += context_str + "\n"

        base_prompt += f"Usuário: {user_message}\nRoboDrive:"
        return base_prompt