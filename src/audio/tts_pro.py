import asyncio
import edge_tts
import tempfile
import os
import logging
from typing import Optional
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModernTTS:
    """Sistema de TTS com múltiplos provedores"""

    VOZES = {
        # Edge TTS (Melhor qualidade, requer internet)
        "antonio": {"provider": "edge", "name": "pt-BR-AntonioNeural", "gender": "masculino",
                    "description": "Edge TTS - Antonio (Masculino)"},
        "francisca": {"provider": "edge", "name": "pt-BR-FranciscaNeural", "gender": "feminino",
                      "description": "Edge TTS - Francisca (Feminino)"},
        "thalita": {"provider": "edge", "name": "pt-BR-ThalitaNeural", "gender": "feminino",
                    "description": "Edge TTS - Thalita (Feminino)"},
        "brenda": {"provider": "edge", "name": "pt-BR-BrendaNeural", "gender": "feminino",
                   "description": "Edge TTS - Brenda (Feminino)"},
        "donato": {"provider": "edge", "name": "pt-BR-DonatoNeural", "gender": "masculino",
                   "description": "Edge TTS - Donato (Masculino)"},
        "elza": {"provider": "edge", "name": "pt-BR-ElzaNeural", "gender": "feminino",
                 "description": "Edge TTS - Elza (Feminino)"},

        # gTTS (Boa qualidade, fallback)
        "gtts_feminino": {"provider": "gtts", "name": "pt", "gender": "feminino",
                          "description": "Google TTS - Feminino"},
        "gtts_masculino": {"provider": "gtts", "name": "pt", "gender": "masculino",
                           "description": "Google TTS - Masculino"},

        # pyttsx3 (Offline, qualidade básica)
        "offline_feminino": {"provider": "offline", "name": "feminino", "gender": "feminino",
                             "description": "Offline - Feminino (espeak)"},
        "offline_masculino": {"provider": "offline", "name": "masculino", "gender": "masculino",
                              "description": "Offline - Masculino (espeak)"},
    }

    def __init__(self, voice: str = "offline_feminino", rate: int = 0):
        self.current_voice = voice
        self.rate = rate
        self.enabled = True
        self._init_fallback()

        logger.info(f"🎤 TTS inicializado com voz: {voice}")

    def _init_fallback(self):
        """Inicializa fallbacks"""
        try:
            from gtts import gTTS
            self.gtts = gTTS
            logger.debug("✅ gTTS disponível")
        except ImportError:
            self.gtts = None

        try:
            import pyttsx3
            self.offline_engine = pyttsx3.init()
            voices = self.offline_engine.getProperty('voices')
            self.offline_voice_feminino = None
            self.offline_voice_masculino = None

            for voice in voices:
                if 'brazil' in voice.name.lower() or 'portuguese' in voice.name.lower():
                    if not self.offline_voice_feminino:
                        self.offline_voice_feminino = voice.id
                    self.offline_voice_masculino = voice.id

            self.offline_engine.setProperty('rate', 170)
            logger.debug("✅ TTS offline disponível")
        except Exception as e:
            self.offline_engine = None
            logger.debug(f"TTS offline não disponível")

    def speak(self, text: str) -> Optional[str]:
        """Gera áudio e retorna caminho do arquivo"""
        if not self.enabled:
            return None

        voice_config = self.VOZES.get(self.current_voice, self.VOZES["offline_feminino"])

        try:
            if voice_config["provider"] == "edge":
                return self._speak_edge(text, voice_config["name"])
            elif voice_config["provider"] == "gtts" and self.gtts:
                return self._speak_gtts(text)
            elif voice_config["provider"] == "offline" and self.offline_engine:
                return self._speak_offline(text)
            else:
                logger.warning(f"Provedor não disponível, usando modo texto")
                return None

        except Exception as e:
            logger.error(f"Erro no TTS: {e}")
            return None

    def _speak_edge(self, text: str, voice_name: str) -> str:
        """Edge TTS (melhor qualidade)"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_path = temp_file.name
        temp_file.close()

        rate_str = f"+{self.rate}%" if self.rate >= 0 else f"{self.rate}%"
        if self.rate == 0:
            rate_str = "+0%"

        communicate = edge_tts.Communicate(text, voice_name, rate=rate_str)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(communicate.save(temp_path))
            loop.close()
        except RuntimeError:
            asyncio.get_event_loop().run_until_complete(communicate.save(temp_path))

        return temp_path

    def _speak_gtts(self, text: str) -> str:
        """gTTS (fallback de boa qualidade)"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_path = temp_file.name
        temp_file.close()

        tts = self.gtts(text, lang='pt', slow=False)
        tts.save(temp_path)
        return temp_path

    def _speak_offline(self, text: str) -> str:
        """TTS offline (pyttsx3)"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_path = temp_file.name
        temp_file.close()

        self.offline_engine.save_to_file(text, temp_path)
        self.offline_engine.runAndWait()
        return temp_path

    def change_voice(self, voice_name: str) -> bool:
        """Muda a voz dinamicamente"""
        if voice_name in self.VOZES:
            self.current_voice = voice_name
            logger.info(f"Voz alterada para: {voice_name}")
            return True
        return False

    def set_enabled(self, enabled: bool):
        """Habilita/desabilita TTS"""
        self.enabled = enabled
        logger.info(f"TTS {'habilitado' if enabled else 'desabilitado'}")

    @staticmethod
    def get_available_voices():
        """Retorna lista de vozes disponíveis"""
        return {k: v["description"] for k, v in ModernTTS.VOZES.items()}