import json
import os

class ConfigManager:
    def __init__(self):
        # Diretórios do projeto
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.temp_dir = os.path.join(self.base_dir, 'temp')
        self.models_dir = os.path.join(self.base_dir, 'models')
        
        # Criar diretórios se não existirem
        for dir_path in [self.data_dir, self.temp_dir, self.models_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        # Arquivo de configuração dentro da pasta data
        self.config_file = os.path.join(self.data_dir, "config.json")
        
        self.default_config = {
            "models_dir": "models",
            "quick_texts": {},
            "instructions": {
                "1": {
                    "title": "Desenvolvimento de Software",
                    "content": "O usuário está desenvolvendo um aplicativo e conversando com um agente de desenvolvimento. A conversa inclui termos técnicos comuns de programação como Next.js, TypeScript, React, APIs, e outros termos da área de desenvolvimento de software. Por favor, transcreva considerando este contexto técnico."
                }
            },
            "audio_source": "microphone",  # ou "system"
            "selected_instruction": "1"  # ID da instrução selecionada para transcrição
        }
        self.load_config()

    def get_temp_path(self, filename):
        """Retorna o caminho completo para um arquivo temporário"""
        return os.path.join(self.temp_dir, filename)

    def get_model_path(self, model_name):
        """Retorna o caminho completo para um arquivo de modelo"""
        return os.path.join(self.models_dir, model_name)

    def load_config(self):
        """Carrega ou cria a configuração"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Garante que todos os campos necessários existam
                    for key, value in self.default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    self.config = loaded_config
            except:
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
        self.save_config()

    def save_config(self):
        """Salva a configuração atual"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get_audio_source(self):
        return self.config.get('audio_source', 'microphone')

    def set_audio_source(self, source):
        if source in ['microphone', 'system']:
            self.config['audio_source'] = source
            self.save_config()

    def get_quick_text(self, number):
        return self.config['quick_texts'].get(str(number))

    def set_quick_text(self, number, title, content):
        self.config['quick_texts'][str(number)] = {
            "title": title,
            "content": content
        }
        self.save_config()

    def get_all_quick_texts(self):
        return self.config['quick_texts']

    def get_instruction(self, id):
        return self.config["instructions"].get(str(id))

    def set_instruction(self, id, title, content):
        self.config["instructions"][str(id)] = {"title": title, "content": content}
        self.save_config()

    def get_all_instructions(self):
        if "instructions" not in self.config:
            self.config["instructions"] = self.default_config["instructions"]
            self.save_config()
        return self.config["instructions"]

    def get_selected_instruction(self):
        instruction_id = self.config.get("selected_instruction")
        if instruction_id:
            return self.get_instruction(instruction_id)
        return None

    def set_selected_instruction(self, instruction_id):
        self.config["selected_instruction"] = str(instruction_id)
        self.save_config()

    def add_new_instruction(self, title="Nova Instrução", content=""):
        # Encontra o próximo ID disponível
        existing_ids = [int(x) for x in self.get_all_instructions().keys()]
        new_id = "1" if not existing_ids else str(max(existing_ids) + 1)
        self.set_instruction(new_id, title, content)
        return new_id

    def add_new_quick_text(self, title="Novo Texto", content=""):
        # Encontra o próximo ID disponível
        existing_ids = [int(x) for x in self.get_all_quick_texts().keys()]
        new_id = "4" if not existing_ids else str(max(existing_ids) + 1)
        self.set_quick_text(new_id, title, content)
        return new_id
