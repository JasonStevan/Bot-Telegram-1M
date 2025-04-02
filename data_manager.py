import os
import json
import logging
import datetime
from config import DEFAULT_POST_INTERVAL

class DataManager:
    def __init__(self):
        """Inicializa o gerenciador de dados"""
        self.logger = logging.getLogger(__name__)
        self.data_dir = 'data'
        
        # Nomes dos arquivos de dados
        self.bot_config_file = os.path.join(self.data_dir, 'bot_config.json')
        self.users_file = os.path.join(self.data_dir, 'users.json')
        self.posts_file = os.path.join(self.data_dir, 'promotional_posts.json')
        self.welcome_config_file = os.path.join(self.data_dir, 'welcome_config.json')
        self.stats_file = os.path.join(self.data_dir, 'stats.json')
        self.last_post_index_file = os.path.join(self.data_dir, 'last_post_index.json')
        
        # Garantir que os arquivos de dados existam
        self._ensure_data_files_exist()
    
    def _ensure_data_files_exist(self):
        """Garante que os arquivos de dados existam"""
        # Cria o diretório de dados se não existir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # Verifica e cria o arquivo de configuração do bot se não existir
        if not os.path.exists(self.bot_config_file):
            with open(self.bot_config_file, 'w') as f:
                json.dump({
                    'token': '',
                    'group_id': '',
                    'active': False,
                    'interval': DEFAULT_POST_INTERVAL
                }, f, indent=4)
        
        # Verifica e cria o arquivo de usuários se não existir
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump([], f, indent=4)
        
        # Verifica e cria o arquivo de posts promocionais se não existir
        if not os.path.exists(self.posts_file):
            with open(self.posts_file, 'w') as f:
                json.dump([], f, indent=4)
        
        # Verifica e cria o arquivo de configuração de boas-vindas se não existir
        if not os.path.exists(self.welcome_config_file):
            with open(self.welcome_config_file, 'w') as f:
                json.dump({
                    'message': 'Olá {first_name}! Bem-vindo(a) ao nosso grupo!',
                    'enabled': True
                }, f, indent=4)
        
        # Verifica e cria o arquivo de estatísticas se não existir
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, 'w') as f:
                json.dump({
                    'welcome_messages_sent': 0,
                    'promo_messages_sent': 0,
                    'last_restarted': None
                }, f, indent=4)
        
        # Verifica e cria o arquivo de índice do último post enviado se não existir
        if not os.path.exists(self.last_post_index_file):
            with open(self.last_post_index_file, 'w') as f:
                json.dump({
                    'index': -1  # -1 indica que nenhum post foi enviado ainda
                }, f, indent=4)
    
    def get_bot_config(self):
        """Retorna a configuração atual do bot"""
        try:
            with open(self.bot_config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração do bot: {str(e)}")
            return {
                'token': '',
                'group_id': '',
                'active': False,
                'interval': DEFAULT_POST_INTERVAL
            }
    
    def update_bot_config(self, token, group_id, interval=DEFAULT_POST_INTERVAL):
        """Atualiza a configuração do bot"""
        try:
            # Carrega configuração atual para manter o status 'active'
            current_config = self.get_bot_config()
            active = current_config.get('active', False)
            
            config = {
                'token': token,
                'group_id': group_id,
                'active': active,
                'interval': interval
            }
            
            with open(self.bot_config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            self.logger.info(f"Configuração do bot atualizada: token={token[:5]}..., group_id={group_id}, interval={interval}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar configuração do bot: {str(e)}")
            return False
    
    def update_bot_status(self, active):
        """Atualiza o status de ativação do bot"""
        try:
            config = self.get_bot_config()
            config['active'] = active
            
            with open(self.bot_config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            self.logger.info(f"Status do bot atualizado: active={active}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do bot: {str(e)}")
            return False
    
    def get_promotional_posts(self):
        """Retorna todos os posts promocionais"""
        try:
            with open(self.posts_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar posts promocionais: {str(e)}")
            return []
    
    def get_promotional_post(self, post_id):
        """Retorna um post promocional específico por ID"""
        posts = self.get_promotional_posts()
        for post in posts:
            if str(post.get('id')) == str(post_id):
                return post
        return None
    
    def add_promotional_post(self, title, content, image_url="", external_link=""):
        """Adiciona um novo post promocional"""
        try:
            posts = self.get_promotional_posts()
            
            # Gera um novo ID
            new_id = 1
            if posts:
                new_id = max([int(post.get('id', 0)) for post in posts]) + 1
            
            # Cria o novo post
            new_post = {
                'id': new_id,
                'title': title,
                'content': content,
                'image_url': image_url,
                'external_link': external_link,
                'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Adiciona o post à lista
            posts.append(new_post)
            
            # Salva a lista atualizada
            with open(self.posts_file, 'w') as f:
                json.dump(posts, f, indent=4)
            
            self.logger.info(f"Post promocional adicionado: {title}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao adicionar post promocional: {str(e)}")
            return False
    
    def update_promotional_post(self, post_id, title, content, image_url="", external_link=""):
        """Atualiza um post promocional existente"""
        try:
            posts = self.get_promotional_posts()
            
            # Encontra o post pelo ID
            for i, post in enumerate(posts):
                if str(post.get('id')) == str(post_id):
                    # Atualiza o post
                    posts[i]['title'] = title
                    posts[i]['content'] = content
                    posts[i]['image_url'] = image_url
                    posts[i]['external_link'] = external_link
                    
                    # Salva a lista atualizada
                    with open(self.posts_file, 'w') as f:
                        json.dump(posts, f, indent=4)
                    
                    self.logger.info(f"Post promocional atualizado: {title}")
                    return True
            
            self.logger.warning(f"Post promocional não encontrado para atualização: ID {post_id}")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao atualizar post promocional: {str(e)}")
            return False
    
    def delete_promotional_post(self, post_id):
        """Exclui um post promocional"""
        try:
            posts = self.get_promotional_posts()
            
            # Encontra o post pelo ID
            for i, post in enumerate(posts):
                if str(post.get('id')) == str(post_id):
                    # Remove o post
                    del posts[i]
                    
                    # Salva a lista atualizada
                    with open(self.posts_file, 'w') as f:
                        json.dump(posts, f, indent=4)
                    
                    self.logger.info(f"Post promocional excluído: ID {post_id}")
                    
                    # Atualiza o índice do último post enviado se necessário
                    self._update_last_post_index_after_delete(post_id)
                    
                    return True
            
            self.logger.warning(f"Post promocional não encontrado para exclusão: ID {post_id}")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao excluir post promocional: {str(e)}")
            return False
    
    def _update_last_post_index_after_delete(self, deleted_post_id):
        """Atualiza o índice após a exclusão de um post"""
        try:
            # Carrega o índice atual
            with open(self.last_post_index_file, 'r') as f:
                index_data = json.load(f)
            
            current_index = index_data.get('index', -1)
            
            # Se o post excluído tiver um ID maior que o índice atual, não é necessário atualizar
            if int(deleted_post_id) > current_index:
                return
            
            # Se o post excluído tiver o mesmo ID que o índice atual, decrementamos o índice
            if int(deleted_post_id) == current_index:
                new_index = max(current_index - 1, -1)
            else:
                # Se o post excluído tiver um ID menor que o índice atual, decrementamos o índice
                new_index = max(current_index - 1, -1)
            
            # Salva o novo índice
            with open(self.last_post_index_file, 'w') as f:
                json.dump({'index': new_index}, f, indent=4)
            
            self.logger.info(f"Índice do último post atualizado após exclusão: {new_index}")
        except Exception as e:
            self.logger.error(f"Erro ao atualizar índice após exclusão: {str(e)}")
    
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
                self.logger.warning("Não há posts promocionais cadastrados")
                return None
            
            # Ordena os posts por ID (que reflete a ordem de criação)
            sorted_posts = sorted(posts, key=lambda x: int(x.get('id', 0)))
            
            # Carrega o índice do último post enviado
            try:
                with open(self.last_post_index_file, 'r') as f:
                    index_data = json.load(f)
                
                last_index = index_data.get('index', -1)
            except Exception as e:
                self.logger.error(f"Erro ao carregar índice do último post: {str(e)}. Usando -1 como padrão.")
                last_index = -1
            
            # Encontra o ID do post com o índice mais próximo e maior que o último enviado
            next_post = None
            for post in sorted_posts:
                post_id = int(post.get('id', 0))
                if post_id > last_index:
                    next_post = post
                    break
            
            # Se não encontrou um post com ID maior, volta para o início do ciclo
            if next_post is None and sorted_posts:
                next_post = sorted_posts[0]
                self.logger.info("Reiniciando ciclo de posts promocionais")
            
            # Salva o novo índice (o ID do post que será enviado)
            if next_post:
                with open(self.last_post_index_file, 'w') as f:
                    json.dump({'index': int(next_post.get('id', 0))}, f, indent=4)
                
                self.logger.info(f"Próximo post sequencial selecionado: ID {next_post.get('id')}, Título: {next_post.get('title')}")
            
            return next_post
        except Exception as e:
            self.logger.error(f"Erro ao selecionar próximo post sequencial: {str(e)}")
            return None
    
    def get_welcome_config(self):
        """Retorna a configuração de boas-vindas"""
        try:
            with open(self.welcome_config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração de boas-vindas: {str(e)}")
            return {
                'message': 'Olá {first_name}! Bem-vindo(a) ao nosso grupo!',
                'enabled': True
            }
    
    def update_welcome_config(self, message, enabled=True):
        """Atualiza a configuração de boas-vindas"""
        try:
            config = {
                'message': message,
                'enabled': enabled
            }
            
            with open(self.welcome_config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            self.logger.info(f"Configuração de boas-vindas atualizada: enabled={enabled}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar configuração de boas-vindas: {str(e)}")
            return False
    
    def get_stats(self):
        """Retorna as estatísticas do bot"""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar estatísticas: {str(e)}")
            return {
                'welcome_messages_sent': 0,
                'promo_messages_sent': 0,
                'last_restarted': None
            }
    
    def increment_welcome_messages_stat(self):
        """Incrementa o contador de mensagens de boas-vindas enviadas"""
        try:
            stats = self.get_stats()
            stats['welcome_messages_sent'] = stats.get('welcome_messages_sent', 0) + 1
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=4)
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao incrementar estatística de mensagens de boas-vindas: {str(e)}")
            return False
    
    def increment_promo_messages_stat(self):
        """Incrementa o contador de mensagens promocionais enviadas"""
        try:
            stats = self.get_stats()
            stats['promo_messages_sent'] = stats.get('promo_messages_sent', 0) + 1
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=4)
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao incrementar estatística de mensagens promocionais: {str(e)}")
            return False
    
    def update_restart_time(self):
        """Atualiza o horário do último reinício do bot"""
        try:
            stats = self.get_stats()
            stats['last_restarted'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=4)
            
            self.logger.info("Horário de reinício do bot atualizado")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar horário de reinício: {str(e)}")
            return False
