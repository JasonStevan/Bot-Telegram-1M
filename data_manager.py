import json
import os
import uuid
import logging
from datetime import datetime
from config import (
    BOT_CONFIG_FILE,
    PROMOTIONAL_POSTS_FILE,
    WELCOME_CONFIG_FILE,
    STATS_FILE,
    DEFAULT_POST_INTERVAL
)

# Diretório de dados
DATA_DIR = 'data'

class DataManager:
    def __init__(self):
        """Inicializa o gerenciador de dados"""
        # Inicializa cache para dados frequentemente acessados
        self._bot_config_cache = None
        self._posts_cache = None
        self._welcome_config_cache = None
        self._stats_cache = None
        
        # Garante que os arquivos necessários existam
        self._ensure_data_files_exist()
    
    def _ensure_data_files_exist(self):
        """Garante que os arquivos de dados existam"""
        # Garantir que o diretório data exista
        try:
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR, exist_ok=True)
                logging.info(f"Diretório de dados criado: {DATA_DIR}")
        except Exception as e:
            logging.error(f"Erro ao criar diretório de dados: {str(e)}")
            
        # Configuração do bot
        try:
            if not os.path.exists(BOT_CONFIG_FILE):
                os.makedirs(os.path.dirname(BOT_CONFIG_FILE), exist_ok=True)
                default_config = {
                    "token": "",
                    "group_id": "",
                    "active": False,
                    "interval": DEFAULT_POST_INTERVAL
                }
                with open(BOT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                logging.info(f"Arquivo de configuração do bot criado: {BOT_CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Erro ao criar arquivo de configuração do bot: {str(e)}")
        
        # Posts promocionais
        try:
            if not os.path.exists(PROMOTIONAL_POSTS_FILE):
                os.makedirs(os.path.dirname(PROMOTIONAL_POSTS_FILE), exist_ok=True)
                with open(PROMOTIONAL_POSTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=4, ensure_ascii=False)
                logging.info(f"Arquivo de posts promocionais criado: {PROMOTIONAL_POSTS_FILE}")
        except Exception as e:
            logging.error(f"Erro ao criar arquivo de posts promocionais: {str(e)}")
        
        # Configuração de boas-vindas
        try:
            if not os.path.exists(WELCOME_CONFIG_FILE):
                os.makedirs(os.path.dirname(WELCOME_CONFIG_FILE), exist_ok=True)
                default_welcome = {
                    "message": "Olá {first_name}! Bem-vindo(a) ao grupo!",
                    "enabled": True
                }
                with open(WELCOME_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_welcome, f, indent=4, ensure_ascii=False)
                logging.info(f"Arquivo de configuração de boas-vindas criado: {WELCOME_CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Erro ao criar arquivo de configuração de boas-vindas: {str(e)}")
        
        # Estatísticas
        try:
            if not os.path.exists(STATS_FILE):
                os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
                default_stats = {
                    "welcome_messages_sent": 0,
                    "promo_messages_sent": 0,
                    "last_restarted": datetime.now().isoformat()
                }
                with open(STATS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_stats, f, indent=4, ensure_ascii=False)
                logging.info(f"Arquivo de estatísticas criado: {STATS_FILE}")
        except Exception as e:
            logging.error(f"Erro ao criar arquivo de estatísticas: {str(e)}")
    
    # Métodos para gerenciar configuração do bot
    def get_bot_config(self):
        """Retorna a configuração atual do bot"""
        # Verifica se há dados no cache
        if self._bot_config_cache is not None:
            return self._bot_config_cache
            
        try:
            # Verifica se o arquivo existe
            if not os.path.exists(BOT_CONFIG_FILE):
                self._ensure_data_files_exist()
                
            with open(BOT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                try:
                    self._bot_config_cache = json.load(f)
                    return self._bot_config_cache
                except json.JSONDecodeError:
                    logging.error("Arquivo de configuração do bot corrompido. Criando um novo.")
                    default_config = {
                        "token": "",
                        "group_id": "",
                        "active": False,
                        "interval": DEFAULT_POST_INTERVAL
                    }
                    with open(BOT_CONFIG_FILE, 'w', encoding='utf-8') as f_write:
                        json.dump(default_config, f_write, indent=4, ensure_ascii=False)
                    self._bot_config_cache = default_config
                    return default_config
        except Exception as e:
            logging.error(f"Erro ao ler configuração do bot: {str(e)}")
            self._bot_config_cache = {
                "token": "",
                "group_id": "",
                "active": False,
                "interval": DEFAULT_POST_INTERVAL
            }
            return self._bot_config_cache
    
    def update_bot_config(self, token, group_id, interval=DEFAULT_POST_INTERVAL):
        """Atualiza a configuração do bot"""
        try:
            # Verificar direitos de acesso ao diretório de dados
            data_dir = os.path.dirname(BOT_CONFIG_FILE)
            if not os.path.exists(data_dir):
                try:
                    os.makedirs(data_dir, exist_ok=True)
                    logging.info(f"Diretório de dados criado: {data_dir}")
                except PermissionError:
                    logging.error(f"Sem permissão para criar diretório de dados: {data_dir}")
                    return False
                except Exception as e:
                    logging.error(f"Erro ao criar diretório de dados: {str(e)}")
                    return False
            elif not os.access(data_dir, os.W_OK):
                logging.error(f"Sem permissão de escrita no diretório de dados: {data_dir}")
                return False
            
            # Verificar se o arquivo existe e pode ser escrito
            if os.path.exists(BOT_CONFIG_FILE) and not os.access(BOT_CONFIG_FILE, os.W_OK):
                logging.error(f"Sem permissão de escrita no arquivo: {BOT_CONFIG_FILE}")
                return False
                
            config = self.get_bot_config()
            
            # Garantir que as strings sejam tratadas corretamente
            if token is None:
                token = ""
            if group_id is None:
                group_id = ""
                
            # Garantir que o intervalo seja um número válido
            try:
                interval = int(interval)
                if interval < 1:
                    logging.warning("Intervalo de post menor que 1, definindo para o valor padrão")
                    interval = DEFAULT_POST_INTERVAL
            except (ValueError, TypeError):
                logging.warning("Intervalo de post inválido, definindo para o valor padrão")
                interval = DEFAULT_POST_INTERVAL
                
            config["token"] = token
            config["group_id"] = group_id
            config["interval"] = interval
            
            # Verificar validade do conteúdo para JSON
            try:
                # Testar se os dados podem ser serializados para JSON
                json.dumps(config)
            except Exception as e:
                logging.error(f"Dados inválidos para serialização JSON: {str(e)}")
                return False
            
            # Salvar no arquivo com tratamento de erros aprimorado
            try:
                with open(BOT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            except PermissionError:
                logging.error(f"Sem permissão para escrever no arquivo: {BOT_CONFIG_FILE}")
                return False
            except IOError as e:
                logging.error(f"Erro de I/O ao escrever no arquivo: {str(e)}")
                return False
                
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(BOT_CONFIG_FILE):
                logging.error("Arquivo de configuração do bot não foi criado")
                return False
            
            # Atualiza o cache
            self._bot_config_cache = config
                
            logging.info("Configurações do bot atualizadas com sucesso")
            return True
        except Exception as e:
            logging.error(f"Erro ao atualizar configuração do bot: {str(e)}")
            return False
    
    def update_bot_status(self, active):
        """Atualiza o status de ativação do bot"""
        try:
            # Verificar direitos de acesso ao diretório de dados
            data_dir = os.path.dirname(BOT_CONFIG_FILE)
            if not os.path.exists(data_dir):
                try:
                    os.makedirs(data_dir, exist_ok=True)
                    logging.info(f"Diretório de dados criado: {data_dir}")
                except PermissionError:
                    logging.error(f"Sem permissão para criar diretório de dados: {data_dir}")
                    return False
                except Exception as e:
                    logging.error(f"Erro ao criar diretório de dados: {str(e)}")
                    return False
            elif not os.access(data_dir, os.W_OK):
                logging.error(f"Sem permissão de escrita no diretório de dados: {data_dir}")
                return False
            
            # Verificar se o arquivo existe e pode ser escrito
            if os.path.exists(BOT_CONFIG_FILE) and not os.access(BOT_CONFIG_FILE, os.W_OK):
                logging.error(f"Sem permissão de escrita no arquivo: {BOT_CONFIG_FILE}")
                return False
                
            config = self.get_bot_config()
            
            # Garantir que o active seja um booleano válido
            try:
                config["active"] = bool(active)
            except Exception as e:
                logging.error(f"Erro ao converter valor de status para booleano: {str(e)}")
                return False
            
            # Salvar no arquivo com tratamento de erros aprimorado
            try:
                with open(BOT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            except PermissionError:
                logging.error(f"Sem permissão para escrever no arquivo: {BOT_CONFIG_FILE}")
                return False
            except IOError as e:
                logging.error(f"Erro de I/O ao escrever no arquivo: {str(e)}")
                return False
                
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(BOT_CONFIG_FILE):
                logging.error("Arquivo de configuração do bot não foi criado após atualização de status")
                return False
            
            # Atualiza o cache    
            self._bot_config_cache = config
            
            logging.info(f"Status do bot atualizado para: {'Ativo' if active else 'Inativo'}")    
            return True
        except Exception as e:
            logging.error(f"Erro ao atualizar status do bot: {str(e)}")
            return False
    
    # Métodos para gerenciar posts promocionais
    def get_promotional_posts(self):
        """Retorna todos os posts promocionais"""
        # Verifica se há dados no cache
        if self._posts_cache is not None:
            return self._posts_cache
            
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(PROMOTIONAL_POSTS_FILE):
                self._ensure_data_files_exist()
                self._posts_cache = []
                return []
                
            with open(PROMOTIONAL_POSTS_FILE, 'r', encoding='utf-8') as f:
                try:
                    self._posts_cache = json.load(f)
                    return self._posts_cache
                except json.JSONDecodeError:
                    logging.error("Arquivo de posts promocionais corrompido. Criando um novo.")
                    os.makedirs(os.path.dirname(PROMOTIONAL_POSTS_FILE), exist_ok=True)
                    with open(PROMOTIONAL_POSTS_FILE, 'w', encoding='utf-8') as f_write:
                        json.dump([], f_write, indent=4, ensure_ascii=False)
                    self._posts_cache = []
                    return []
        except Exception as e:
            logging.error(f"Erro ao ler posts promocionais: {str(e)}")
            self._posts_cache = []
            return self._posts_cache
    
    def get_promotional_post(self, post_id):
        """Retorna um post promocional específico por ID"""
        try:
            posts = self.get_promotional_posts()
            for post in posts:
                if post.get('id') == post_id:
                    return post
            return None
        except Exception as e:
            logging.error(f"Erro ao buscar post promocional: {str(e)}")
            return None
    
    def add_promotional_post(self, title, content, image_url="", external_link=""):
        """Adiciona um novo post promocional"""
        try:
            # Verificar direitos de acesso ao diretório de dados
            data_dir = os.path.dirname(PROMOTIONAL_POSTS_FILE)
            if not os.path.exists(data_dir):
                try:
                    os.makedirs(data_dir, exist_ok=True)
                    logging.info(f"Diretório de dados criado: {data_dir}")
                except PermissionError:
                    logging.error(f"Sem permissão para criar diretório de dados: {data_dir}")
                    return False
                except Exception as e:
                    logging.error(f"Erro ao criar diretório de dados: {str(e)}")
                    return False
            elif not os.access(data_dir, os.W_OK):
                logging.error(f"Sem permissão de escrita no diretório de dados: {data_dir}")
                return False
            
            # Verificar se o arquivo existe e pode ser escrito
            if os.path.exists(PROMOTIONAL_POSTS_FILE) and not os.access(PROMOTIONAL_POSTS_FILE, os.W_OK):
                logging.error(f"Sem permissão de escrita no arquivo: {PROMOTIONAL_POSTS_FILE}")
                return False
            
            # Ler posts existentes ou criar um array vazio
            posts = []
            if os.path.exists(PROMOTIONAL_POSTS_FILE):
                try:
                    with open(PROMOTIONAL_POSTS_FILE, 'r', encoding='utf-8') as f:
                        try:
                            posts = json.load(f)
                        except json.JSONDecodeError:
                            logging.error("Arquivo de posts promocionais corrompido. Criando um novo.")
                            posts = []
                except Exception as e:
                    logging.error(f"Erro ao ler arquivo de posts existente: {str(e)}")
                    posts = []
            
            # Garantir que as strings sejam tratadas corretamente
            if title is None:
                title = ""
            if content is None:
                content = ""
            if image_url is None:
                image_url = ""
            if external_link is None:
                external_link = ""
            
            # Verificar validade do conteúdo para JSON
            try:
                # Testar se os dados podem ser serializados para JSON
                json.dumps({
                    "title": title,
                    "content": content,
                    "image_url": image_url,
                    "external_link": external_link
                })
            except Exception as e:
                logging.error(f"Dados inválidos para serialização JSON: {str(e)}")
                return False
            
            # Criar post
            new_post = {
                "id": str(uuid.uuid4()),
                "title": title,
                "content": content,
                "image_url": image_url,
                "external_link": external_link,
                "created_at": datetime.now().isoformat()
            }
            
            # Adicionar à lista
            posts.append(new_post)
            
            # Salvar no arquivo com tratamento de erros aprimorado
            try:
                os.makedirs(os.path.dirname(PROMOTIONAL_POSTS_FILE), exist_ok=True)
                with open(PROMOTIONAL_POSTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(posts, f, indent=4, ensure_ascii=False)
            except PermissionError:
                logging.error(f"Sem permissão para escrever no arquivo: {PROMOTIONAL_POSTS_FILE}")
                return False
            except IOError as e:
                logging.error(f"Erro de I/O ao escrever no arquivo: {str(e)}")
                return False
            
            # Verificar se o arquivo foi salvo
            if not os.path.exists(PROMOTIONAL_POSTS_FILE):
                logging.error("Arquivo de posts promocionais não foi criado")
                return False
            
            # Atualiza o cache
            self._posts_cache = posts
                
            logging.info(f"Post promocional adicionado com sucesso: {title}")
            return True
        except Exception as e:
            logging.error(f"Erro inesperado ao adicionar post promocional: {str(e)}")
            return False
    
    def update_promotional_post(self, post_id, title, content, image_url="", external_link=""):
        """Atualiza um post promocional existente"""
        try:
            # Verificar direitos de acesso ao diretório de dados
            data_dir = os.path.dirname(PROMOTIONAL_POSTS_FILE)
            if not os.path.exists(data_dir):
                try:
                    os.makedirs(data_dir, exist_ok=True)
                    logging.info(f"Diretório de dados criado: {data_dir}")
                except PermissionError:
                    logging.error(f"Sem permissão para criar diretório de dados: {data_dir}")
                    return False
                except Exception as e:
                    logging.error(f"Erro ao criar diretório de dados: {str(e)}")
                    return False
            elif not os.access(data_dir, os.W_OK):
                logging.error(f"Sem permissão de escrita no diretório de dados: {data_dir}")
                return False
            
            # Verificar se o arquivo existe e pode ser escrito
            if os.path.exists(PROMOTIONAL_POSTS_FILE) and not os.access(PROMOTIONAL_POSTS_FILE, os.W_OK):
                logging.error(f"Sem permissão de escrita no arquivo: {PROMOTIONAL_POSTS_FILE}")
                return False
            
            # Ler posts existentes
            posts = []
            if os.path.exists(PROMOTIONAL_POSTS_FILE):
                try:
                    with open(PROMOTIONAL_POSTS_FILE, 'r', encoding='utf-8') as f:
                        try:
                            posts = json.load(f)
                        except json.JSONDecodeError:
                            logging.error("Arquivo de posts promocionais corrompido. Não foi possível atualizar.")
                            return False
                except Exception as e:
                    logging.error(f"Erro ao ler arquivo de posts: {str(e)}")
                    return False
            else:
                logging.error("Arquivo de posts não encontrado.")
                return False
            
            # Garantir que as strings sejam tratadas corretamente
            if title is None:
                title = ""
            if content is None:
                content = ""
            if image_url is None:
                image_url = ""
            if external_link is None:
                external_link = ""
            
            # Verificar validade do conteúdo para JSON
            try:
                # Testar se os dados podem ser serializados para JSON
                json.dumps({
                    "title": title,
                    "content": content,
                    "image_url": image_url,
                    "external_link": external_link
                })
            except Exception as e:
                logging.error(f"Dados inválidos para serialização JSON: {str(e)}")
                return False
            
            # Buscar e atualizar o post
            post_updated = False
            for post in posts:
                if post.get('id') == post_id:
                    post['title'] = title
                    post['content'] = content
                    post['image_url'] = image_url
                    post['external_link'] = external_link
                    post['updated_at'] = datetime.now().isoformat()
                    post_updated = True
                    break
            
            if not post_updated:
                logging.warning(f"Tentativa de atualizar post não encontrado com ID: {post_id}")
                return False
            
            # Salvar no arquivo com tratamento de erros aprimorado
            try:
                with open(PROMOTIONAL_POSTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(posts, f, indent=4, ensure_ascii=False)
            except PermissionError:
                logging.error(f"Sem permissão para escrever no arquivo: {PROMOTIONAL_POSTS_FILE}")
                return False
            except IOError as e:
                logging.error(f"Erro de I/O ao escrever no arquivo: {str(e)}")
                return False
            
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(PROMOTIONAL_POSTS_FILE):
                logging.error("Arquivo de posts promocionais não foi criado após atualização")
                return False
            
            # Atualiza o cache
            self._posts_cache = posts
            
            logging.info(f"Post promocional atualizado com sucesso: {title}")    
            return True
        except Exception as e:
            logging.error(f"Erro inesperado ao atualizar post promocional: {str(e)}")
            return False
    
    def delete_promotional_post(self, post_id):
        """Exclui um post promocional"""
        try:
            # Verificar direitos de acesso ao diretório de dados
            data_dir = os.path.dirname(PROMOTIONAL_POSTS_FILE)
            if not os.path.exists(data_dir):
                try:
                    os.makedirs(data_dir, exist_ok=True)
                    logging.info(f"Diretório de dados criado: {data_dir}")
                except PermissionError:
                    logging.error(f"Sem permissão para criar diretório de dados: {data_dir}")
                    return False
                except Exception as e:
                    logging.error(f"Erro ao criar diretório de dados: {str(e)}")
                    return False
            elif not os.access(data_dir, os.W_OK):
                logging.error(f"Sem permissão de escrita no diretório de dados: {data_dir}")
                return False
            
            # Verificar se o arquivo existe e pode ser escrito
            if os.path.exists(PROMOTIONAL_POSTS_FILE) and not os.access(PROMOTIONAL_POSTS_FILE, os.W_OK):
                logging.error(f"Sem permissão de escrita no arquivo: {PROMOTIONAL_POSTS_FILE}")
                return False
            
            # Ler posts existentes
            posts = []
            if os.path.exists(PROMOTIONAL_POSTS_FILE):
                try:
                    with open(PROMOTIONAL_POSTS_FILE, 'r', encoding='utf-8') as f:
                        try:
                            posts = json.load(f)
                        except json.JSONDecodeError:
                            logging.error("Arquivo JSON corrompido. Não foi possível excluir o post.")
                            return False
                except Exception as e:
                    logging.error(f"Erro ao ler arquivo de posts: {str(e)}")
                    return False
            else:
                logging.error("Arquivo de posts não encontrado.")
                return False
                
            # Excluir o post
            initial_count = len(posts)
            posts = [post for post in posts if post.get('id') != post_id]
            
            if len(posts) == initial_count:
                logging.warning(f"Tentativa de excluir post não encontrado com ID: {post_id}")
                return False
            
            # Salvar no arquivo com tratamento de erros aprimorado
            try:
                os.makedirs(os.path.dirname(PROMOTIONAL_POSTS_FILE), exist_ok=True)
                with open(PROMOTIONAL_POSTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(posts, f, indent=4, ensure_ascii=False)
            except PermissionError:
                logging.error(f"Sem permissão para escrever no arquivo: {PROMOTIONAL_POSTS_FILE}")
                return False
            except IOError as e:
                logging.error(f"Erro de I/O ao escrever no arquivo: {str(e)}")
                return False
            
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(PROMOTIONAL_POSTS_FILE):
                logging.error("Arquivo de posts promocionais não foi criado após exclusão")
                return False
            
            # Atualiza o cache
            self._posts_cache = posts
            
            logging.info(f"Post promocional excluído com sucesso: ID {post_id}")
            return True
        except Exception as e:
            logging.error(f"Erro inesperado ao excluir post promocional: {str(e)}")
            return False
    
    def get_random_promotional_post(self):
        """
        Função mantida por compatibilidade, mas agora retorna o próximo post
        sequencial em vez de um aleatório
        """
        return self.get_next_sequential_post()
        
    def get_next_sequential_post(self):
        """
        Retorna o próximo post promocional em ordem sequencial (do mais antigo ao mais recente)
        Após enviar todos os posts, reinicia o ciclo
        """
        try:
            posts = self.get_promotional_posts()
            
            if not posts:
                return None
                
            # Ordenar os posts por data de criação (mais antigos primeiro)
            sorted_posts = sorted(posts, key=lambda x: x.get('created_at', ''))
            
            # Ler o último ID enviado do arquivo de estado (se existir)
            last_sent_post_id = None
            stats_file = os.path.join(DATA_DIR, 'last_sent_post.json')
            
            try:
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            last_sent_post_id = data.get('last_sent_post_id')
                        except json.JSONDecodeError:
                            logging.error("Arquivo de último post enviado corrompido.")
                            last_sent_post_id = None
                            os.remove(stats_file)  # Remove para permitir recriação
            except Exception as e:
                logging.error(f"Erro ao ler último post enviado: {str(e)}")
                last_sent_post_id = None
            
            # Se não houver post anterior ou for o último, começar do início
            next_post = sorted_posts[0]
            next_index = 0
            
            # Se tiver um ID de último post enviado, encontrar o próximo
            if last_sent_post_id:
                found = False
                for i, post in enumerate(sorted_posts):
                    if post.get('id') == last_sent_post_id:
                        # Pega o próximo post (ou volta para o início se for o último)
                        next_index = (i + 1) % len(sorted_posts)
                        next_post = sorted_posts[next_index]
                        found = True
                        break
                
                # Se o post anterior não for encontrado (talvez tenha sido excluído), 
                # começa do início
                if not found:
                    next_post = sorted_posts[0]
                    next_index = 0
            
            # Salvar o ID do post que será enviado como o último
            try:
                os.makedirs(os.path.dirname(stats_file), exist_ok=True)
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump({'last_sent_post_id': next_post.get('id')}, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Erro ao salvar último post enviado: {str(e)}")
            
            logging.info(f"Enviando post sequencial {next_index+1}/{len(sorted_posts)}: {next_post.get('title', 'unknown')}")
            return next_post
        except Exception as e:
            logging.error(f"Erro ao obter próximo post sequencial: {str(e)}")
            return None
    
    # Métodos para gerenciar configuração de boas-vindas
    def get_welcome_config(self):
        """Retorna a configuração de boas-vindas"""
        # Verifica se há dados no cache
        if self._welcome_config_cache is not None:
            return self._welcome_config_cache
            
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(WELCOME_CONFIG_FILE):
                self._ensure_data_files_exist()
                
            with open(WELCOME_CONFIG_FILE, 'r', encoding='utf-8') as f:
                try:
                    self._welcome_config_cache = json.load(f)
                    return self._welcome_config_cache
                except json.JSONDecodeError:
                    logging.error("Arquivo de configuração de boas-vindas corrompido. Criando um novo.")
                    default_welcome = {
                        "message": "Olá {first_name}! Bem-vindo(a) ao grupo!",
                        "enabled": True
                    }
                    with open(WELCOME_CONFIG_FILE, 'w', encoding='utf-8') as f_write:
                        json.dump(default_welcome, f_write, indent=4, ensure_ascii=False)
                    self._welcome_config_cache = default_welcome
                    return default_welcome
        except Exception as e:
            logging.error(f"Erro ao ler configuração de boas-vindas: {str(e)}")
            self._welcome_config_cache = {
                "message": "Olá {first_name}! Bem-vindo(a) ao grupo!",
                "enabled": True
            }
            return self._welcome_config_cache
    
    def update_welcome_config(self, message, enabled=True):
        """Atualiza a configuração de boas-vindas"""
        try:
            # Verificar direitos de acesso ao diretório de dados
            data_dir = os.path.dirname(WELCOME_CONFIG_FILE)
            if not os.path.exists(data_dir):
                try:
                    os.makedirs(data_dir, exist_ok=True)
                    logging.info(f"Diretório de dados criado: {data_dir}")
                except PermissionError:
                    logging.error(f"Sem permissão para criar diretório de dados: {data_dir}")
                    return False
                except Exception as e:
                    logging.error(f"Erro ao criar diretório de dados: {str(e)}")
                    return False
            elif not os.access(data_dir, os.W_OK):
                logging.error(f"Sem permissão de escrita no diretório de dados: {data_dir}")
                return False
            
            # Verificar se o arquivo existe e pode ser escrito
            if os.path.exists(WELCOME_CONFIG_FILE) and not os.access(WELCOME_CONFIG_FILE, os.W_OK):
                logging.error(f"Sem permissão de escrita no arquivo: {WELCOME_CONFIG_FILE}")
                return False
            
            # Garantir que a mensagem é uma string
            if message is None:
                message = ""
                
            # Verificar validade do conteúdo para JSON
            try:
                # Testar se os dados podem ser serializados para JSON
                json.dumps({
                    "message": message,
                    "enabled": bool(enabled)
                })
            except Exception as e:
                logging.error(f"Dados inválidos para serialização JSON: {str(e)}")
                return False
                
            welcome_config = {
                "message": message,
                "enabled": bool(enabled)
            }
            
            # Salvar no arquivo com tratamento de erros aprimorado
            try:
                os.makedirs(os.path.dirname(WELCOME_CONFIG_FILE), exist_ok=True)
                with open(WELCOME_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(welcome_config, f, indent=4, ensure_ascii=False)
            except PermissionError:
                logging.error(f"Sem permissão para escrever no arquivo: {WELCOME_CONFIG_FILE}")
                return False
            except IOError as e:
                logging.error(f"Erro de I/O ao escrever no arquivo: {str(e)}")
                return False
                
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(WELCOME_CONFIG_FILE):
                logging.error("Arquivo de configuração de boas-vindas não foi criado")
                return False
            
            # Atualiza o cache
            self._welcome_config_cache = welcome_config
            
            logging.info("Configuração de boas-vindas atualizada com sucesso")    
            return True
        except Exception as e:
            logging.error(f"Erro ao atualizar configuração de boas-vindas: {str(e)}")
            return False
    
    # Métodos para gerenciar estatísticas
    def get_stats(self):
        """Retorna as estatísticas do bot"""
        # Verifica se há dados no cache
        if self._stats_cache is not None:
            return self._stats_cache
            
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(STATS_FILE):
                self._ensure_data_files_exist()
                
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                try:
                    self._stats_cache = json.load(f)
                    return self._stats_cache
                except json.JSONDecodeError:
                    logging.error("Arquivo de estatísticas corrompido. Criando um novo.")
                    default_stats = {
                        "welcome_messages_sent": 0,
                        "promo_messages_sent": 0,
                        "last_restarted": datetime.now().isoformat()
                    }
                    with open(STATS_FILE, 'w', encoding='utf-8') as f_write:
                        json.dump(default_stats, f_write, indent=4, ensure_ascii=False)
                    self._stats_cache = default_stats
                    return default_stats
        except Exception as e:
            logging.error(f"Erro ao ler estatísticas: {str(e)}")
            self._stats_cache = {
                "welcome_messages_sent": 0,
                "promo_messages_sent": 0,
                "last_restarted": datetime.now().isoformat()
            }
            return self._stats_cache
    
    def increment_welcome_messages_stat(self):
        """Incrementa o contador de mensagens de boas-vindas enviadas"""
        try:
            stats = self.get_stats()
            stats["welcome_messages_sent"] = stats.get("welcome_messages_sent", 0) + 1
            
            try:
                os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
                with open(STATS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Erro ao salvar estatísticas de boas-vindas: {str(e)}")
                return False
            
            # Atualiza o cache    
            self._stats_cache = stats
                
            return True
        except Exception as e:
            logging.error(f"Erro ao incrementar estatística de boas-vindas: {str(e)}")
            return False
    
    def increment_promo_messages_stat(self):
        """Incrementa o contador de mensagens promocionais enviadas"""
        try:
            stats = self.get_stats()
            stats["promo_messages_sent"] = stats.get("promo_messages_sent", 0) + 1
            
            try:
                os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
                with open(STATS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Erro ao salvar estatísticas de mensagens promocionais: {str(e)}")
                return False
            
            # Atualiza o cache    
            self._stats_cache = stats
                
            return True
        except Exception as e:
            logging.error(f"Erro ao incrementar estatística de mensagens promocionais: {str(e)}")
            return False
    
    def update_restart_time(self):
        """Atualiza o horário do último reinício do bot"""
        try:
            stats = self.get_stats()
            stats["last_restarted"] = datetime.now().isoformat()
            
            try:
                os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
                with open(STATS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Erro ao salvar horário de reinício: {str(e)}")
                return False
            
            # Atualiza o cache    
            self._stats_cache = stats
            
            logging.info("Horário de reinício do bot atualizado")    
            return True
        except Exception as e:
            logging.error(f"Erro ao atualizar horário de reinício: {str(e)}")
            return False
