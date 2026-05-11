#!/usr/bin/env python3
"""
RoboDrive CLI - Interface de Linha de Comando
Usa configurações padrão do .env e TTS offline
"""

import os
import sys
import readline
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

# Adiciona src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.brain.llm_client import LLMClient
from src.brain.memory import MemorySystem
from src.audio.tts_pro import ModernTTS

load_dotenv()
console = Console()


class RoboDriveCLI:
    """Interface de linha de comando do RoboDrive"""

    def __init__(self):
        console.print(Panel.fit(
            "[bold cyan]🤖 RoboDrive CLI v5.0[/bold cyan]\n"
            "[dim]Agente Autônomo com Memória Persistente[/dim]",
            border_style="cyan"
        ))

        self.llm = LLMClient()
        self.memory = MemorySystem()
        self.tts = ModernTTS(
            voice=os.getenv('DEFAULT_VOICE', 'offline_feminino'),
            rate=int(os.getenv('TTS_RATE', 0))
        )

        self.running = True
        self.show_info()

    def show_info(self):
        """Mostra informações iniciais"""
        table = Table(title="⚙️ Configuração Atual", style="cyan")
        table.add_column("Item", style="bold")
        table.add_column("Valor", style="green")

        table.add_row("🎯 Modelo LLM", self.llm.model)
        table.add_row("🎤 Voz TTS", self.tts.current_voice)
        table.add_row("🔊 Áudio", "✅ Ativado" if self.tts.enabled else "❌ Desativado")
        table.add_row("💾 Memória", f"📊 SQLite ativo")

        persons = self.memory.get_known_persons()
        table.add_row("👥 Pessoas conhecidas", str(len(persons)))

        facts = self.memory.get_all_facts()
        table.add_row("💡 Fatos aprendidos", str(len(facts)))

        console.print(table)
        console.print("\n[dim]Comandos especiais:[/dim]")
        console.print("  [yellow]/ajuda[/yellow] - Mostrar ajuda")
        console.print("  [yellow]/memoria[/yellow] - Ver histórico")
        console.print("  [yellow]/pessoas[/yellow] - Listar pessoas")
        console.print("  [yellow]/fatos[/yellow] - Listar fatos")
        console.print("  [yellow]/audio[/yellow] - Ligar/desligar TTS")
        console.print("  [yellow]/voz [nome][/yellow] - Mudar voz")
        console.print("  [yellow]/modelo [nome][/yellow] - Mudar modelo")
        console.print("  [yellow]/sair[/yellow] - Encerrar\n")

    def process_command(self, command: str) -> bool:
        """Processa comandos especiais"""
        if command == '/ajuda':
            self.show_help()
            return True
        elif command == '/memoria':
            self.show_memory()
            return True
        elif command == '/pessoas':
            self.show_persons()
            return True
        elif command == '/fatos':
            self.show_facts()
            return True
        elif command == '/audio':
            self.tts.set_enabled(not self.tts.enabled)
            status = "ativado" if self.tts.enabled else "desativado"
            console.print(f"[green]🔊 Áudio {status}[/green]")
            return True
        elif command.startswith('/voz '):
            voice = command.split(' ')[1]
            if self.tts.change_voice(voice):
                console.print(f"[green]✅ Voz alterada para: {voice}[/green]")
            else:
                console.print(f"[red]❌ Voz '{voice}' não encontrada[/red]")
                self.show_available_voices()
            return True
        elif command.startswith('/modelo '):
            model = command.split(' ')[1]
            if self.llm.change_model(model):
                console.print(f"[green]✅ Modelo alterado para: {model}[/green]")
            else:
                console.print(f"[red]❌ Modelo '{model}' não encontrado[/red]")
                self.show_available_models()
            return True
        elif command == '/sair':
            self.running = False
            return True
        return False

    def show_help(self):
        """Mostra ajuda detalhada"""
        help_text = """
## 📚 Comandos Disponíveis

### 💬 Conversação
- **Qualquer texto** - Converse normalmente com o RoboDrive

### 🧠 Memória
- `/memoria` - Ver histórico das últimas conversas
- `/pessoas` - Listar todas as pessoas conhecidas
- `/fatos` - Listar fatos aprendidos

### 🔊 Áudio
- `/audio` - Ligar/desligar respostas em áudio
- `/voz francisca` - Mudar para voz Francisca (Edge TTS)
- `/voz offline_feminino` - Mudar para voz offline feminina

### 🤖 Modelos de IA
- `/modelo llama3:latest` - Mudar modelo LLM
- `/modelo qwen3:1.7b` - Mudar para Qwen3

### 🎮 Sistema
- `/ajuda` - Mostrar esta ajuda
- `/sair` - Encerrar o programa

### 💡 Dicas
- Você pode ensinar seu nome: "Meu nome é Tiago"
- Pode ensinar fatos: "Saiba que gosto de café"
- O robô aprende automaticamente com todas as conversas
"""
        console.print(Markdown(help_text))

    def show_memory(self):
        """Mostra memória recente"""
        context = self.memory.get_recent_context(10)
        if context:
            table = Table(title="📚 Histórico de Conversas", style="cyan")
            table.add_column("Role", style="bold")
            table.add_column("Mensagem", style="white")

            for msg in context[-10:]:
                role = "👤 Você" if msg['role'] == 'user' else "🤖 RoboDrive"
                table.add_row(role, msg['content'][:100] + ("..." if len(msg['content']) > 100 else ""))

            console.print(table)
        else:
            console.print("[yellow]Nenhuma conversa registrada ainda[/yellow]")

    def show_persons(self):
        """Mostra pessoas conhecidas"""
        persons = self.memory.get_known_persons()
        if persons:
            table = Table(title="👥 Pessoas Conhecidas", style="green")
            table.add_column("Nome", style="bold")
            table.add_column("Relação", style="cyan")
            table.add_column("Características", style="white")

            for name, info in persons.items():
                table.add_row(name, info.get('role', 'amigo'), info.get('characteristics', '-'))

            console.print(table)
        else:
            console.print("[yellow]Ainda não conheço ninguém[/yellow]")

    def show_facts(self):
        """Mostra fatos aprendidos"""
        facts = self.memory.get_all_facts()
        if facts:
            console.print("[bold green]💡 Fatos que aprendi:[/bold green]")
            for i, fact in enumerate(facts[-20:], 1):
                console.print(f"  {i}. {fact}")
        else:
            console.print("[yellow]Ainda não aprendi nenhum fato[/yellow]")

    def show_available_voices(self):
        """Mostra vozes disponíveis"""
        voices = self.tts.get_available_voices()
        console.print("[cyan]🎤 Vozes disponíveis:[/cyan]")
        for voice, desc in voices.items():
            current = " ✅" if voice == self.tts.current_voice else ""
            console.print(f"  • {voice}: {desc}{current}")

    def show_available_models(self):
        """Mostra modelos disponíveis"""
        models = self.llm.list_models()
        console.print("[cyan]🧠 Modelos disponíveis:[/cyan]")
        for model in models:
            current = " ✅" if model == self.llm.model else ""
            console.print(f"  • {model}{current}")

    def process_message(self, text: str):
        """Processa mensagem do usuário"""
        with console.status("[bold cyan]🤔 Pensando...[/bold cyan]", spinner="dots"):
            context = self.memory.get_recent_context(limit=5)
            persons = self.memory.get_known_persons()
            facts = self.memory.get_all_facts()

            knowledge_prompt = ""
            if persons:
                knowledge_prompt += f"\nPessoas na casa: {', '.join(persons.keys())}"
            if facts:
                knowledge_prompt += f"\nFatos conhecidos: {'; '.join(facts[-5:])}"

            response = self.llm.chat(text, context, knowledge_prompt)

        # Mostra resposta formatada
        console.print(Panel(
            response,
            title="🤖 RoboDrive",
            border_style="green",
            padding=(0, 2)
        ))

        # Gera áudio se habilitado
        if self.tts.enabled:
            with console.status("[bold blue]🔊 Gerando áudio...[/bold blue]", spinner="dots"):
                audio_file = self.tts.speak(response)
                if audio_file:
                    try:
                        if sys.platform == "linux":
                            os.system(f"play {audio_file} > /dev/null 2>&1 &")
                        elif sys.platform == "darwin":
                            os.system(f"afplay {audio_file} &")
                        elif sys.platform == "win32":
                            os.system(f"start {audio_file}")
                    except:
                        pass

        # Salva conversa
        self.memory.save_conversation(text, response)

        # Aprendizado automático
        import re
        if "meu nome é" in text.lower():
            name_match = re.search(r'meu nome é (\w+)', text.lower())
            if name_match:
                name = name_match.group(1).title()
                self.memory.learn_person(name, f"Apresentou-se como {name}", "amigo")
                console.print(f"[green]🧠 Aprendi seu nome: {name}![/green]")

    def run(self):
        """Loop principal do CLI"""
        while self.running:
            try:
                user_input = Prompt.ask("\n[bold cyan]👤 Você[/bold cyan]")

                if not user_input:
                    continue

                if user_input.startswith('/'):
                    self.process_command(user_input)
                else:
                    self.process_message(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]👋 Encerrando...[/yellow]")
                break
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]❌ Erro: {e}[/red]")

        console.print("\n[bold green]✅ RoboDrive CLI encerrado! Até logo! 🚀[/bold green]")


def main():
    cli = RoboDriveCLI()
    cli.run()


if __name__ == "__main__":
    main()