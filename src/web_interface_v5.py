from flask import Flask, render_template_string, request, Response, jsonify
from flask_cors import CORS
import json
import tempfile
import os
import re
import logging
from dotenv import load_dotenv
from brain.llm_client import LLMClient
from brain.memory import MemorySystem
from audio.tts_pro import ModernTTS

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Inicializa componentes
llm = LLMClient()
memory = MemorySystem()
tts = ModernTTS(
    voice=os.getenv('DEFAULT_VOICE', 'offline_feminino'),
    rate=int(os.getenv('TTS_RATE', 0))
)

audio_cache = {}


def extract_knowledge(text):
    knowledge = {'persons': [], 'facts': []}

    name_patterns = [
        r'(?:eu sou|me chamo|meu nome é|aqui é|sou o|sou a) (\w+(?:\s+\w+)?)',
    ]
    fact_patterns = [
        r'(?:gosto de|adoro|curto|detesto|não gosto de) (.+?)(?:\.|$)',
        r'(?:tenho|possuo|comprei|ganhei) (?:um|uma) (.+?)(?:\.|$)'
    ]

    for pattern in name_patterns:
        matches = re.findall(pattern, text.lower())
        for match in matches:
            name = match if isinstance(match, str) else match[0]
            if len(name) > 2 and name not in ['eu', 'você', 'ele', 'ela']:
                knowledge['persons'].append(name.title())

    for pattern in fact_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            fact = match.strip()
            if len(fact) > 5:
                knowledge['facts'].append(fact)

    return knowledge


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/chat', methods=['POST'])
def chat():
    message = request.json['message']
    learned_items = []

    knowledge = extract_knowledge(message)

    for person in knowledge['persons']:
        memory.learn_person(person, f"Conhecido via conversa", "amigo")
        learned_items.append(f"conheci {person}")

    for fact in knowledge['facts']:
        memory.learn_fact(fact[:200], "aprendizado_automatico")
        learned_items.append(f"aprendi {fact[:50]}...")

    context = memory.get_recent_context(limit=10)
    persons = memory.get_known_persons()
    facts = memory.get_all_facts()

    knowledge_prompt = ""
    if persons:
        knowledge_prompt += f"\nPessoas na casa: {', '.join(persons.keys())}"
    if facts:
        knowledge_prompt += f"\nFatos conhecidos: {'; '.join(facts[-5:])}"

    response = llm.chat(message, context, knowledge_prompt)
    memory.save_conversation(message, response)

    return jsonify({'response': response, 'learned': ' | '.join(learned_items) if learned_items else None})


@app.route('/speak', methods=['POST'])
def speak():
    if not tts.enabled:
        return Response(b'', mimetype='audio/mp3')

    text = request.json['text']

    if text in audio_cache:
        return Response(audio_cache[text], mimetype='audio/mp3')

    audio_path = tts.speak(text)

    if audio_path and os.path.exists(audio_path):
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        audio_cache[text] = audio_data
        os.unlink(audio_path)
        return Response(audio_data, mimetype='audio/mp3')

    return Response(b'', mimetype='audio/mp3')


@app.route('/models', methods=['GET'])
def get_models():
    """Retorna lista de modelos disponíveis"""
    models = llm.list_models()
    current = llm.model
    return jsonify({'models': models, 'current': current})


@app.route('/model', methods=['POST'])
def change_model():
    """Muda o modelo ativo"""
    model_name = request.json['model']
    if llm.change_model(model_name):
        return jsonify({'status': 'ok', 'model': model_name})
    return jsonify({'status': 'error', 'message': 'Modelo não encontrado'}), 400


@app.route('/voices', methods=['GET'])
def get_voices():
    """Retorna lista de vozes disponíveis"""
    voices = tts.get_available_voices()
    current = tts.current_voice
    return jsonify({'voices': voices, 'current': current})


@app.route('/voice', methods=['POST'])
def change_voice():
    """Muda a voz ativa"""
    voice_name = request.json['voice']
    if tts.change_voice(voice_name):
        return jsonify({'status': 'ok', 'voice': voice_name})
    return jsonify({'status': 'error', 'message': 'Voz não encontrada'}), 400


@app.route('/audio/toggle', methods=['POST'])
def toggle_audio():
    """Habilita/desabilita áudio"""
    enabled = request.json.get('enabled', True)
    tts.set_enabled(enabled)
    return jsonify({'status': 'ok', 'enabled': enabled})


@app.route('/knowledge')
def get_knowledge():
    persons = memory.get_known_persons()
    facts = memory.get_all_facts()
    return jsonify({'persons': persons, 'facts': facts})


@app.route('/memory')
def get_memory():
    context = memory.get_recent_context(10)
    context_str = "Últimas conversas:\n" + "\n".join([f"{c['role']}: {c['content'][:100]}" for c in context])
    return jsonify({'context': context_str})


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RoboDrive v5.0 - IA</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
        }

        .chat-area {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 85vh;
        }

        .sidebar {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 20px;
            height: 85vh;
            overflow-y: auto;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }

        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { font-size: 12px; opacity: 0.9; }

        #chat {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f9f9f9;
        }

        .message { margin-bottom: 15px; animation: fadeIn 0.3s ease-in; }
        .user-message { text-align: right; }
        .bot-message { text-align: left; }

        .user-message .content {
            background: #667eea;
            color: white;
            display: inline-block;
            padding: 10px 15px;
            border-radius: 20px 20px 5px 20px;
            max-width: 70%;
        }

        .bot-message .content {
            background: #e0e0e0;
            color: #333;
            display: inline-block;
            padding: 10px 15px;
            border-radius: 20px 20px 20px 5px;
            max-width: 70%;
        }

        .input-area {
            padding: 20px;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
            background: white;
        }

        #input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
        }

        #input:focus { border-color: #667eea; }

        button {
            padding: 12px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            transition: transform 0.2s;
        }

        button:hover { transform: translateY(-2px); }
        .voice-btn { background: #48bb78; }
        .clear-btn { background: #f56565; }

        .status {
            text-align: center;
            padding: 10px;
            font-size: 12px;
            color: #666;
            background: white;
            border-top: 1px solid #e0e0e0;
        }

        .sidebar h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 16px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 5px;
        }

        .sidebar-section { margin-bottom: 25px; }

        .person-item, .fact-item {
            background: #f0f0f0;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 10px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .person-item:hover, .fact-item:hover { background: #e0e0e0; }
        .person-name { font-weight: bold; color: #667eea; }
        .fact-text { color: #555; }

        select {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            margin-bottom: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            outline: none;
            cursor: pointer;
        }

        .toggle-switch {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }

        .switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: 0.3s;
            border-radius: 24px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background-color: #48bb78;
        }

        input:checked + .slider:before {
            transform: translateX(26px);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .badge {
            display: inline-block;
            padding: 2px 8px;
            background: #48bb78;
            color: white;
            border-radius: 10px;
            font-size: 10px;
            margin-left: 5px;
        }

        .current-indicator {
            font-size: 11px;
            color: #888;
            margin-top: 5px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="chat-area">
            <div class="header">
                <h1>🧠 RoboDrive v5.0 - IA</h1>
                <p>Modelos de IA | Vozes | Aprendizado Contínuo</p>
            </div>

            <div id="chat"></div>

            <div class="input-area">
                <input type="text" id="input" placeholder="Converse comigo...">
                <button onclick="sendMessage()">📝 Enviar</button>
                <button class="voice-btn" onclick="startVoice()">🎤 Falar</button>
            </div>
            <div class="status" id="status">✅ Pronto para conversar</div>
        </div>

        <div class="sidebar">
            <div class="sidebar-section">
                <h3>🧠 Modelo de IA</h3>
                <select id="model-select" onchange="changeModel()">
                    <option>Carregando modelos...</option>
                </select>
                <div class="current-indicator" id="current-model"></div>
            </div>

            <div class="sidebar-section">
                <h3>🔊 Áudio</h3>
                <div class="toggle-switch">
                    <span>🗣️ Voz do Robô</span>
                    <label class="switch">
                        <input type="checkbox" id="audio-toggle" checked onchange="toggleAudio()">
                        <span class="slider"></span>
                    </label>
                </div>
                <select id="voice-select" onchange="changeVoice()">
                    <option>Carregando vozes...</option>
                </select>
            </div>

            <div class="sidebar-section">
                <h3>👥 Pessoas que Conheço</h3>
                <div id="persons-list">Carregando...</div>
            </div>

            <div class="sidebar-section">
                <h3>💡 Fatos que Aprendi</h3>
                <div id="facts-list">Carregando...</div>
            </div>

            <div class="sidebar-section">
                <h3>🎮 Comandos</h3>
                <button onclick="showMemory()">📚 Ver Memória</button>
                <button class="clear-btn" onclick="clearChat()">🗑️ Limpar Chat</button>
            </div>
        </div>
    </div>

    <script>
        let currentAudio = null;

        async function loadModels() {
            const response = await fetch('/models');
            const data = await response.json();
            const select = document.getElementById('model-select');
            const currentModelSpan = document.getElementById('current-model');

            select.innerHTML = '';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === data.current) {
                    option.selected = true;
                }
                select.appendChild(option);
            });

            currentModelSpan.innerHTML = `📌 Atual: ${data.current}`;
        }

        async function loadVoices() {
            const response = await fetch('/voices');
            const data = await response.json();
            const select = document.getElementById('voice-select');

            select.innerHTML = '';
            for (const [voice, description] of Object.entries(data.voices)) {
                const option = document.createElement('option');
                option.value = voice;
                option.textContent = description;
                if (voice === data.current) {
                    option.selected = true;
                }
                select.appendChild(option);
            }
        }

        async function changeModel() {
            const select = document.getElementById('model-select');
            const model = select.value;

            const response = await fetch('/model', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model: model})
            });

            const data = await response.json();
            if (data.status === 'ok') {
                const status = document.getElementById('status');
                status.innerHTML = `🧠 Modelo alterado para: ${model}`;
                setTimeout(() => {
                    status.innerHTML = '✅ Pronto para conversar';
                }, 2000);
                loadModels();
            }
        }

        async function changeVoice() {
            const select = document.getElementById('voice-select');
            const voice = select.value;

            const response = await fetch('/voice', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({voice: voice})
            });

            const data = await response.json();
            if (data.status === 'ok') {
                const status = document.getElementById('status');
                status.innerHTML = `🗣️ Voz alterada: ${voice}`;
                setTimeout(() => {
                    status.innerHTML = '✅ Pronto para conversar';
                }, 2000);
            }
        }

        async function toggleAudio() {
            const enabled = document.getElementById('audio-toggle').checked;

            const response = await fetch('/audio/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: enabled})
            });

            const status = document.getElementById('status');
            status.innerHTML = enabled ? '🔊 Áudio habilitado' : '🔇 Áudio desabilitado';
            setTimeout(() => {
                status.innerHTML = '✅ Pronto para conversar';
            }, 2000);
        }

        function addMessage(text, isUser, isThinking = false) {
            const chat = document.getElementById('chat');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user-message' : 'bot-message');

            const content = document.createElement('div');
            content.className = 'content';

            if (isThinking) {
                content.innerHTML = '<span style="background:#fff3cd;color:#856404;padding:10px;border-radius:10px;display:inline-block;">🤔 ' + text + '</span>';
            } else {
                content.textContent = text;
            }

            messageDiv.appendChild(content);
            chat.appendChild(messageDiv);
            chat.scrollTop = chat.scrollHeight;
            return messageDiv;
        }

        async function sendMessage() {
            const input = document.getElementById('input');
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, true);
            input.value = '';
            input.disabled = true;

            const thinkingMsg = addMessage('Pensando...', false, true);

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: text})
                });

                const data = await response.json();
                thinkingMsg.remove();

                addMessage(data.response, false);

                if (document.getElementById('audio-toggle').checked) {
                    await playAudio(data.response);
                }

                await loadKnowledge();

                if (data.learned) {
                    const status = document.getElementById('status');
                    status.innerHTML = '🧠 ' + data.learned;
                    setTimeout(() => {
                        status.innerHTML = '✅ Pronto para conversar';
                    }, 3000);
                }

            } catch (error) {
                thinkingMsg.remove();
                addMessage('❌ Erro de conexão!', false);
            } finally {
                input.disabled = false;
                input.focus();
            }
        }

        async function playAudio(text) {
            const status = document.getElementById('status');
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }

            status.innerHTML = '🔊 Gerando áudio...';

            try {
                const response = await fetch('/speak', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });

                const audioBlob = await response.blob();
                if (audioBlob.size === 0) return;

                const audioUrl = URL.createObjectURL(audioBlob);
                currentAudio = new Audio(audioUrl);

                currentAudio.onplay = () => status.innerHTML = '🗣️ RoboDrive está falando...';
                currentAudio.onended = () => {
                    status.innerHTML = '✅ Pronto para conversar';
                    URL.revokeObjectURL(audioUrl);
                    currentAudio = null;
                };

                await currentAudio.play();
            } catch (error) {
                status.innerHTML = '✅ Pronto para conversar';
            }
        }

        async function loadKnowledge() {
            try {
                const response = await fetch('/knowledge');
                const data = await response.json();

                const personsDiv = document.getElementById('persons-list');
                if (data.persons && Object.keys(data.persons).length > 0) {
                    personsDiv.innerHTML = '';
                    for (const [name, info] of Object.entries(data.persons)) {
                        personsDiv.innerHTML += `
                            <div class="person-item">
                                <div class="person-name">${name}</div>
                                <div>👤 ${info.role || 'amigo'}</div>
                            </div>
                        `;
                    }
                } else {
                    personsDiv.innerHTML = '<div style="color: #888;">Ainda não conheço ninguém.</div>';
                }

                const factsDiv = document.getElementById('facts-list');
                if (data.facts && data.facts.length > 0) {
                    factsDiv.innerHTML = '';
                    data.facts.slice(0, 10).forEach(fact => {
                        factsDiv.innerHTML += `
                            <div class="fact-item">
                                <div class="fact-text">💡 ${fact}</div>
                            </div>
                        `;
                    });
                } else {
                    factsDiv.innerHTML = '<div style="color: #888;">Ainda não aprendi fatos.</div>';
                }
            } catch (error) {
                console.error('Erro:', error);
            }
        }

        async function showMemory() {
            const response = await fetch('/memory');
            const data = await response.json();
            addMessage(data.context, false);
        }

        function clearChat() {
            document.getElementById('chat').innerHTML = '';
            addMessage("🧹 Chat limpo! Continuo lembrando de tudo.", false);
        }

        function startVoice() {
            if (!('webkitSpeechRecognition' in window)) {
                alert('Seu navegador não suporta reconhecimento de voz');
                return;
            }

            const recognition = new webkitSpeechRecognition();
            recognition.lang = 'pt-BR';
            recognition.continuous = false;
            recognition.interimResults = true;

            const status = document.getElementById('status');
            status.innerHTML = '🎤 Ouvindo... Fale agora';
            recognition.start();

            recognition.onresult = function(event) {
                let final = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    }
                }

                if (final) {
                    document.getElementById('input').value = final;
                    status.innerHTML = '🎤 Reconhecido: ' + final;
                    sendMessage();
                }
            };
        }

        loadModels();
        loadVoices();
        loadKnowledge();
        setInterval(loadKnowledge, 10000);
        document.getElementById('input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🧠 RoboDrive v5.0 - Interface Web Completa")
    print("=" * 60)
    print("\n✨ Funcionalidades:")
    print("   • Seleção de modelos LLM do servidor")
    print("   • 10 vozes diferentes (online e offline)")
    print("   • Áudio liga/desliga com um clique")
    print("   • Reconhecimento de voz no navegador")
    print("   • Aprendizado contínuo")
    print("\n📍 Acesse: http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)