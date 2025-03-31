import sys
import keyboard
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QRadioButton, QPushButton, 
                            QTextEdit, QSystemTrayIcon, QMenu, QScrollArea,
                            QFrame, QSizePolicy, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QFont
import pyperclip
import os
from dotenv import load_dotenv
import requests
from audio_recorder import AudioRecorder
import time
from config_manager import ConfigManager

class CardWidget(QFrame):
    def __init__(self, title, id, parent=None):
        super().__init__(parent)
        self.id = id
        self.title = title
        self.selected = False
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            CardWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
            CardWidget[selected="true"] {
                border: 2px solid #007bff;
                background-color: #f0f7ff;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 2px;
                margin: 0px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton#editButton {
                color: #6c757d;
                font-size: 14px;
            }
            QPushButton#editButton:hover {
                background-color: #f8f9fa;
                border-radius: 12px;
            }
            QPushButton#saveButton {
                color: white;
                background-color: #28a745;
                border-radius: 12px;
                font-size: 14px;
            }
            QPushButton#saveButton:hover {
                background-color: #218838;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Container para título
        title_container = QHBoxLayout()
        title_container.setSpacing(5)
        
        # Label do título
        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)
        title_container.addWidget(self.title_label, stretch=1)
        
        # Container para botões
        buttons_container = QHBoxLayout()
        buttons_container.setSpacing(2)
        
        # Botão de editar título
        self.edit_button = QPushButton("✎")
        self.edit_button.setObjectName("editButton")
        self.edit_button.setToolTip("Editar título")
        self.edit_button.clicked.connect(self.start_title_edit)
        buttons_container.addWidget(self.edit_button)
        
        # Botão de salvar (inicialmente escondido)
        self.save_button = QPushButton("✓")
        self.save_button.setObjectName("saveButton")
        self.save_button.setToolTip("Salvar título")
        self.save_button.clicked.connect(self.save_title_edit)
        self.save_button.hide()
        buttons_container.addWidget(self.save_button)
        
        title_container.addLayout(buttons_container)
        layout.addLayout(title_container)
        
    def start_title_edit(self):
        # Criar um QLineEdit com o título atual
        self.title_edit = QLineEdit(self.title)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #007bff;
                border-radius: 3px;
                padding: 3px;
                background-color: white;
            }
        """)
        
        # Esconder label e mostrar edit
        self.title_label.hide()
        self.edit_button.hide()
        self.save_button.show()
        
        # Inserir o QLineEdit no layout
        layout = self.layout()
        layout.insertWidget(0, self.title_edit)
        
        self.title_edit.setFocus()
        self.title_edit.selectAll()
        
    def save_title_edit(self):
        new_title = self.title_edit.text()
        if new_title:
            self.title = new_title
            self.title_label.setText(new_title)
            
            # Notificar a janela principal sobre a mudança
            window = self.window()
            if isinstance(window, WhisperApp):
                window.update_item_title(self)
        
        # Limpar o modo de edição
        self.title_edit.deleteLater()
        self.title_label.show()
        self.edit_button.show()
        self.save_button.hide()
        
    def set_selected(self, selected):
        self.selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

class ScrollableCardList(QScrollArea):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setup_ui(title)
        
    def setup_ui(self, title):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(200)
        
        container = QWidget()
        self.layout = QVBoxLayout(container)
        
        # Título da lista
        title_label = QLabel(title)
        title_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        self.layout.addWidget(title_label)
        
        # Container para os cards
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.addStretch()
        self.layout.addWidget(self.cards_container)
        
        self.setWidget(container)
        
    def add_card(self, card):
        # Insere o card antes do stretch
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

class WhisperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.recorder = AudioRecorder(self.config)
        self.current_editing = None  # Armazena o card atualmente em edição
        
        # Carregar variáveis de ambiente
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("API Key não encontrada no arquivo .env")
            sys.exit(1)
            
        print("Usando API OpenAI para transcrição...")
        
        self.setup_ui()
        self.setup_global_hotkeys()
        self.minimized_mode = False
        
    def setup_ui(self):
        self.setWindowTitle("Whisper Transcriber")
        self.setGeometry(100, 100, 1000, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Container esquerdo para as listas
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_container.setMaximumWidth(300)
        
        # Lista de Textos Rápidos
        self.quick_texts_list = ScrollableCardList("Textos Rápidos")
        left_layout.addWidget(self.quick_texts_list)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator)
        
        # Lista de Instruções
        self.instructions_list = ScrollableCardList("Instruções")
        left_layout.addWidget(self.instructions_list)
        
        # Botões de adicionar
        add_buttons_layout = QHBoxLayout()
        add_quick_text = QPushButton("+ Texto")
        add_instruction = QPushButton("+ Instrução")
        add_quick_text.clicked.connect(lambda: self.add_new_item("quick_text"))
        add_instruction.clicked.connect(lambda: self.add_new_item("instruction"))
        add_buttons_layout.addWidget(add_quick_text)
        add_buttons_layout.addWidget(add_instruction)
        left_layout.addLayout(add_buttons_layout)
        
        # Botão para alternar modo
        toggle_button = QPushButton("Modo Botão")
        toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        toggle_button.clicked.connect(self.toggle_mode)
        left_layout.addWidget(toggle_button)
        
        main_layout.addWidget(left_container)
        
        # Container direito para edição
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        # Área de edição
        self.edit_area = QTextEdit()
        self.edit_area.setReadOnly(True)
        self.edit_area.setPlaceholderText("Selecione um item para visualizar ou editar")
        
        # Barra de ferramentas de edição
        toolbar = QHBoxLayout()
        self.edit_button = QPushButton("✎ Editar")
        self.save_button = QPushButton("✓ Salvar")
        self.save_button.setEnabled(False)
        
        self.edit_button.clicked.connect(self.start_editing)
        self.save_button.clicked.connect(self.save_editing)
        
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.save_button)
        toolbar.addStretch()
        
        right_layout.addLayout(toolbar)
        right_layout.addWidget(self.edit_area)
        
        main_layout.addWidget(right_container)
        
        # Carregar itens existentes
        self.load_existing_items()
        
        # Timer para atualizar o tempo quando estiver gravando
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Atualiza a cada segundo
        
    def load_existing_items(self):
        # Carregar textos rápidos
        for id, data in self.config.get_all_quick_texts().items():
            card = CardWidget(data["title"], id)
            card.mousePressEvent = lambda e, c=card: self.select_quick_text(c)
            self.quick_texts_list.add_card(card)
            
        # Carregar instruções
        selected_id = self.config.config.get("selected_instruction")
        for id, data in self.config.get_all_instructions().items():
            card = CardWidget(data["title"], id)
            card.mousePressEvent = lambda e, c=card: self.select_instruction(c)
            self.instructions_list.add_card(card)
            # Se esta é a instrução selecionada, marca visualmente
            if id == selected_id:
                card.set_selected(True)
                self.current_editing = ("instruction", card)
                self.edit_area.setText(data["content"])
    
    def add_new_item(self, item_type):
        if item_type == "quick_text":
            id = self.config.add_new_quick_text()
            card = CardWidget("Novo Texto", id)
            card.mousePressEvent = lambda e, c=card: self.select_quick_text(c)
            self.quick_texts_list.add_card(card)
        else:  # instruction
            id = self.config.add_new_instruction()
            card = CardWidget("Nova Instrução", id)
            card.mousePressEvent = lambda e, c=card: self.select_instruction(c)
            self.instructions_list.add_card(card)
    
    def select_quick_text(self, card):
        # Desseleciona todos os cards
        self.unselect_all_cards()
        
        # Seleciona o card atual
        card.set_selected(True)
        self.current_editing = ("quick_text", card)
        
        # Mostra o conteúdo
        text = self.config.get_quick_text(card.id)
        if text:
            self.edit_area.setText(text["content"])
        
        # Reset botões
        self.edit_area.setReadOnly(True)
        self.edit_button.setEnabled(True)
        self.save_button.setEnabled(False)
    
    def select_instruction(self, card):
        # Desseleciona todos os cards
        self.unselect_all_cards()
        
        # Seleciona o card atual
        card.set_selected(True)
        self.current_editing = ("instruction", card)
        
        # Mostra o conteúdo
        instruction = self.config.get_instruction(card.id)
        if instruction:
            self.edit_area.setText(instruction["content"])
            # Define esta instrução como a selecionada para transcrição
            self.config.set_selected_instruction(card.id)
            
        # Reset botões
        self.edit_area.setReadOnly(True)
        self.edit_button.setEnabled(True)
        self.save_button.setEnabled(False)
    
    def unselect_all_cards(self):
        # Percorre todos os cards e remove a seleção
        for i in range(self.quick_texts_list.cards_layout.count() - 1):
            widget = self.quick_texts_list.cards_layout.itemAt(i).widget()
            if isinstance(widget, CardWidget):
                widget.set_selected(False)
                
        for i in range(self.instructions_list.cards_layout.count() - 1):
            widget = self.instructions_list.cards_layout.itemAt(i).widget()
            if isinstance(widget, CardWidget):
                widget.set_selected(False)
    
    def start_editing(self):
        if self.current_editing:
            self.edit_area.setReadOnly(False)
            self.edit_button.setEnabled(False)
            self.save_button.setEnabled(True)
    
    def save_editing(self):
        if not self.current_editing:
            return
            
        item_type, card = self.current_editing
        content = self.edit_area.toPlainText()
        
        if item_type == "quick_text":
            text = self.config.get_quick_text(card.id)
            if text:
                self.config.set_quick_text(card.id, text["title"], content)
        else:  # instruction
            instruction = self.config.get_instruction(card.id)
            if instruction:
                self.config.set_instruction(card.id, instruction["title"], content)
                # Se esta instrução estiver selecionada, atualiza
                if card.id == self.config.config.get("selected_instruction"):
                    self.config.set_selected_instruction(card.id)
        
        self.edit_area.setReadOnly(True)
        self.edit_button.setEnabled(True)
        self.save_button.setEnabled(False)

    def setup_global_hotkeys(self):
        keyboard.add_hotkey('ctrl+alt+1', self.toggle_recording)
        keyboard.add_hotkey('ctrl+alt+2', self.toggle_pause)
        keyboard.add_hotkey('ctrl+alt+3', self.cancel_recording)
        
        # Atalhos para textos rápidos (agora começando do 4)
        for i in range(4, 10):
            keyboard.add_hotkey(f'ctrl+alt+{i}', lambda i=i: self.send_quick_text(i))

    def toggle_mode(self):
        """Alterna entre modo normal e modo botão"""
        if self.minimized_mode:
            self.showNormal()
            self.minimized_mode = False
        else:
            self.hide()
            self.minimized_mode = True
            self.show_minimized_window()

    def show_minimized_window(self):
        """Mostra a janela minimizada"""
        if not hasattr(self, 'mini_window'):
            self.mini_window = MinimizedWindow(self)
        self.mini_window.show()

    def update_time(self):
        """Atualiza o tempo na janela minimizada"""
        if hasattr(self, 'mini_window') and self.recorder.recording:
            self.mini_window.update_time(self.recorder.get_elapsed_time())

    def toggle_recording(self):
        if not self.recorder.recording:
            self.recorder.start_recording()
            if hasattr(self, 'mini_window'):
                self.mini_window.status_label.setStyleSheet("color: red;")
        else:
            if hasattr(self, 'mini_window'):
                self.mini_window.status_label.setText("⌛")
                self.mini_window.status_label.setStyleSheet("color: orange;")
                QApplication.processEvents()
                
            audio_file = self.recorder.stop_recording()
            if audio_file:
                try:
                    text = self.transcribe_audio(audio_file)
                    if text:
                        pyperclip.copy(text)
                        keyboard.press_and_release('ctrl+v')
                except Exception as e:
                    print(f"Erro na transcrição: {e}")
                
                try:
                    os.remove(audio_file)
                except:
                    pass
            
            if hasattr(self, 'mini_window'):
                self.mini_window.status_label.setText("━━━")
                self.mini_window.status_label.setStyleSheet("")

    def toggle_pause(self):
        if self.recorder.recording:
            if self.recorder.paused:
                self.recorder.resume_recording()
                if hasattr(self, 'mini_window'):
                    self.mini_window.status_label.setStyleSheet("color: red;")
            else:
                self.recorder.pause_recording()
                if hasattr(self, 'mini_window'):
                    self.mini_window.status_label.setStyleSheet("color: orange;")

    def cancel_recording(self):
        if self.recorder.cancel_recording():
            if hasattr(self, 'mini_window'):
                self.mini_window.status_label.setText("━━━")
                self.mini_window.status_label.setStyleSheet("")

    def send_quick_text(self, number):
        text = self.config.get_quick_text(number)
        if text and text["content"]:
            pyperclip.copy(text["content"])
            time.sleep(0.1)
            keyboard.write(text["content"])

    def transcribe_audio(self, audio_file):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Obtém a instrução selecionada
            instruction = self.config.get_selected_instruction()
            prompt = instruction["content"] if instruction else None
            
            log_text = "\n=== Detalhes da Transcrição ===\n"
            log_text += f"Instrução selecionada: {instruction['title'] if instruction else 'Nenhuma'}\n"
            log_text += f"Prompt sendo enviado: {prompt}\n"
            
            with open(audio_file, "rb") as audio:
                files = {
                    "file": ("audio.wav", audio, "audio/wav"),
                    "model": (None, "gpt-4o-mini-transcribe")
                }
                
                if prompt:
                    files["prompt"] = (None, prompt)
                    
                log_text += "\nParâmetros da requisição:\n"
                log_text += f"Files: {[k for k in files.keys()]}\n"
                
                response = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers,
                    files=files
                )
                
            if response.status_code == 200:
                # Logar resposta completa da API
                log_text += "\nResposta da API (raw):\n"
                log_text += f"{response.text}\n"
                
                text = response.json()["text"]
                log_text += f"\nTranscrição extraída: {text}\n"
                
                # Salva o log
                with open("transcription_log.txt", "a", encoding='utf-8') as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                    f.write(log_text)
                
                return text
            else:
                error_msg = f"\nErro na API: {response.status_code} - {response.text}\n"
                log_text += error_msg
                
                # Salva o log
                with open("transcription_log.txt", "a", encoding='utf-8') as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                    f.write(log_text)
                
                return ""
        except Exception as e:
            error_msg = f"\nErro na transcrição: {str(e)}\n"
            
            # Salva o log
            with open("transcription_log.txt", "a", encoding='utf-8') as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(error_msg)
            
            return ""

    def update_item_title(self, card):
        """Atualiza o título de um item no ConfigManager"""
        if not hasattr(card, 'id') or not hasattr(card, 'title'):
            return
            
        item_type = None
        # Determina o tipo do item baseado em qual lista contém o card
        for i in range(self.quick_texts_list.cards_layout.count() - 1):
            if self.quick_texts_list.cards_layout.itemAt(i).widget() == card:
                item_type = "quick_text"
                break
                
        if not item_type:
            for i in range(self.instructions_list.cards_layout.count() - 1):
                if self.instructions_list.cards_layout.itemAt(i).widget() == card:
                    item_type = "instruction"
                    break
        
        if item_type == "quick_text":
            text = self.config.get_quick_text(card.id)
            if text:
                self.config.set_quick_text(card.id, card.title, text["content"])
        elif item_type == "instruction":
            instruction = self.config.get_instruction(card.id)
            if instruction:
                self.config.set_instruction(card.id, card.title, instruction["content"])

class MinimizedWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(100, 100, 250, 50)
        
        # Estilo para o botão chevron e janela
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
            QPushButton#chevron {
                border: none;
                color: #6c757d;
                font-size: 16px;
                padding: 5px;
                margin: 0px;
                border-radius: 4px;
            }
            QPushButton#chevron:hover {
                color: #343a40;
                background-color: rgba(0, 0, 0, 0.1);
            }
            QLabel {
                border: none;
                background: transparent;
                color: #495057;
                font-family: Arial;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Timer
        self.time_label = QLabel("00:00")
        self.time_label.setFont(QFont("Arial", 12))
        
        # Indicador de gravação
        self.status_label = QLabel("━━━")
        self.status_label.setFont(QFont("Arial", 12))
        
        # Botão chevron para expandir
        self.expand_button = QPushButton("▼")
        self.expand_button.setObjectName("chevron")
        self.expand_button.setFixedSize(30, 30)
        self.expand_button.clicked.connect(self.expand_to_full)
        
        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.expand_button)
    
    def expand_to_full(self):
        """Expande para o modo normal"""
        self.hide()
        self.main_window.showNormal()
        self.main_window.minimized_mode = False
    
    def update_time(self, time_str):
        """Atualiza o tempo mostrado"""
        self.time_label.setText(time_str)
        # Alternar entre diferentes caracteres para criar animação
        current = self.status_label.text()
        if current == "━━━":
            self.status_label.setText("═══")
        else:
            self.status_label.setText("━━━")

    def mousePressEvent(self, event):
        """Permite arrastar a janela"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Ignorar cliques no botão chevron
            if self.expand_button.geometry().contains(event.pos()):
                return
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Implementa o arrastar da janela"""
        if hasattr(self, 'old_pos'):
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

def main():
    app = QApplication(sys.argv)
    window = WhisperApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
