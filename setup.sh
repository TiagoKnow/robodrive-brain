#!/bin/bash

echo "🤖 Configurando RoboDrive Brain..."

# Cria ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Atualiza pip e ferramentas base
pip install --upgrade pip setuptools wheel

# Instala dependências
pip install -r requirements.txt

# Cria diretórios necessários
mkdir -p data logs

# Configura arquivo .env se não existe
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || cat > .env << EOF
# LLM Configuration
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=deepseek-coder:6.7b

# Audio Configuration
WAKE_WORD=robodrive
STT_ENGINE=google
TTS_ENGINE=pyttsx3

# Persona
ROBOT_NAME=RoboDrive
CREATOR_NAME=Tiago
LOCATION=Casa do Tiago

# Memory
MEMORY_RETENTION_DAYS=30
MAX_CONTEXT_MESSAGES=10
EOF
fi

echo "✅ Instalação concluída!"
echo ""
echo "Para iniciar:"
echo "  source venv/bin/activate"
echo "  python cli.py"
echo "  python src/web_interface.py"