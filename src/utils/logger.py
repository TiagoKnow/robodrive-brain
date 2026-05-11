import logging
import sys
from datetime import datetime
from pathlib import Path

# Cria diretório de logs
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


# Configuração do logger principal
def setup_logger(name: str, level=logging.DEBUG):
    """Configura logger com handlers para arquivo e console"""

    # Formato detalhado para debug
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Formato mais simples para console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Handler para arquivo (tudo)
    file_handler = logging.FileHandler(
        log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Handler para console (apenas INFO e acima)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Handler para debug (WARNING e acima em arquivo separado)
    error_handler = logging.FileHandler(
        log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.WARNING)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(error_handler)

    return logger


# Logger principal do sistema
system_logger = setup_logger("robodrive")

# Logger específico para LLM
llm_logger = setup_logger("llm", level=logging.DEBUG)

# Logger para conversas
conversation_logger = setup_logger("conversation", level=logging.INFO)


def log_prompt(prompt: str, context: list = None, knowledge: str = ""):
    """Log especial para prompts da LLM"""
    llm_logger.debug("=" * 80)
    llm_logger.debug("📤 PROMPT ENVIADO PARA LLM")
    llm_logger.debug("=" * 80)

    if context:
        llm_logger.debug(f"📚 CONTEXTO ({len(context)} mensagens):")
        for msg in context[-5:]:
            llm_logger.debug(f"   {msg['role']}: {msg['content'][:100]}...")
        llm_logger.debug("-" * 40)

    if knowledge:
        llm_logger.debug(f"🧠 CONHECIMENTO:\n{knowledge[:500]}")
        llm_logger.debug("-" * 40)

    llm_logger.debug(f"💬 PROMPT FINAL:\n{prompt[:1000]}")
    llm_logger.debug("=" * 80)


def log_response(response: str, duration: float):
    """Log da resposta da LLM"""
    llm_logger.debug("=" * 80)
    llm_logger.debug("📥 RESPOSTA DA LLM")
    llm_logger.debug(f"⏱️  Tempo: {duration:.2f}s")
    llm_logger.debug(f"💬 Resposta: {response[:500]}")
    llm_logger.debug("=" * 80)