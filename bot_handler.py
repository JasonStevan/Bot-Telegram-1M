import logging
import threading
import time
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

class TelegramBotHandler:
    def __init__(self, token, group_id, data_manager):
        """Inicializa o handler do bot do Telegram"""
        self.token = token
        self.group_id = group_id
        self.data_manager = data_manager
        self.bot = None
        self.updater = None
        self.thread = None
        self.is_active = False
        
        # Configuração de logging
        self.logger = logging.getLogger("TelegramBotHandler")
        
        # Tenta inicializar o bot
        try:
            self.bot = Bot(token=token)
            # Verifica se o token é válido tentando chamar getMe
            me = self.bot.get_me()
            self.logger.info(f"Bot inicializado com sucesso: {me.first_name} (@{me.username})")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar bot: {str(e)}")
            self.bot = None
    
    def start(self):
        """Inicia o bot"""
        if self.is_active:
            self.logger.warning("Tentativa de iniciar bot que já está ativo")
            return True
        
        if not self.bot:
            self.logger.error("Bot não está inicializado corretamente")
            return False
        
        try:
            # Cria um updater
            self.updater = Updater(self.token, use_context=True)
            dispatcher = self.updater.dispatcher
            
            # Adiciona handlers
            dispatcher.add_handler(CommandHandler("start", self._start_command))
            
            # Handler para novos membros
            dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, self._welcome_new_member))
            
            # Inicia o polling em uma thread separada
            self.thread = threading.Thread(target=self._start_polling)
            self.thread.daemon = True  # Thread será encerrada quando o programa principal terminar
            self.thread.start()
            
            self.is_active = True
            self.logger.info("Bot iniciado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao iniciar bot: {str(e)}")
            self.is_active = False
            return False
    
    def _start_polling(self):
        """Função para executar o polling em uma thread separada"""
        try:
            self.updater.start_polling()
            self.updater.idle()
        except Exception as e:
            self.logger.error(f"Erro no polling do bot: {str(e)}")
            self.is_active = False
    
    def stop(self):
        """Para o bot"""
        if not self.is_active:
            self.logger.debug("Tentativa de parar bot que já está inativo")
            return False
        
        try:
            self.logger.info("Parando o bot do Telegram...")
            
            # Define como inativo primeiro para evitar que outras threads tentem acessá-lo
            self.is_active = False
            
            if self.updater:
                try:
                    # Tenta parar o updater com timeout
                    self.updater.stop()
                    self.logger.info("Updater parado com sucesso")
                except Exception as updater_error:
                    self.logger.error(f"Erro ao parar updater: {str(updater_error)}")
            
            # Espera a thread principal terminar com timeout
            if self.thread and self.thread.is_alive():
                self.logger.info("Aguardando término da thread de polling...")
                self.thread.join(timeout=5)
                
                # Verifica se ainda está viva após o timeout
                if self.thread.is_alive():
                    self.logger.warning("A thread do bot não terminou dentro do timeout, mas será abandonada")
            
            # Limpa as referências para ajudar o garbage collector
            self.thread = None
            
            self.logger.info("Bot parado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao parar bot: {str(e)}")
            # Garante que fique marcado como inativo mesmo com erro
            self.is_active = False
            return False
    
    def is_running(self):
        """Verifica se o bot está em execução"""
        # Verifica se o bot está ativo e se a thread está em execução
        return self.is_active and self.thread and self.thread.is_alive()
    
    def _start_command(self, update, context):
        """Handler para o comando /start"""
        update.message.reply_text("Olá! Sou um bot de administração de grupo.")
    
    def _welcome_new_member(self, update, context):
        """Handler para novos membros no grupo"""
        # Verifica se há um novo ID de chat (migração de grupo para supergrupo)
        if update.effective_chat and update.effective_chat.id != int(self.group_id) and str(update.effective_chat.id).startswith("-"):
            self.logger.info(f"Detectada possível migração de grupo. ID atual: {self.group_id}, ID da mensagem: {update.effective_chat.id}")
            new_group_id = str(update.effective_chat.id)
            # Atualiza o ID do grupo
            self.group_id = new_group_id
            self.data_manager.update_bot_config(self.token, new_group_id)
            self.logger.info(f"ID do grupo atualizado para: {new_group_id}")
        
        welcome_config = self.data_manager.get_welcome_config()
        
        if not welcome_config.get('enabled', True):
            return
        
        for new_member in update.message.new_chat_members:
            # Ignora se o novo membro for o próprio bot
            if new_member.id == context.bot.id:
                continue
            
            # Prepara a mensagem de boas-vindas
            message = welcome_config.get('message', "Olá! Bem-vindo(a) ao grupo!")
            
            # Substitui as variáveis na mensagem
            first_name = new_member.first_name or ""
            last_name = new_member.last_name or ""
            username = new_member.username or ""
            
            message = message.replace("{first_name}", first_name)
            message = message.replace("{last_name}", last_name)
            message = message.replace("{username}", username if username else first_name)
            
            try:
                # Envia a mensagem para o grupo
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode="HTML"
                )
                
                # Incrementa estatísticas
                self.data_manager.increment_welcome_messages_stat()
                
                self.logger.info(f"Mensagem de boas-vindas enviada para {first_name} {last_name}")
            except Exception as e:
                self.logger.error(f"Erro ao enviar mensagem de boas-vindas: {str(e)}")
    
    def send_promotional_post(self, post):
        """Envia um post promocional para o grupo"""
        if not self.is_active or not post:
            self.logger.warning("Tentativa de enviar post quando bot está inativo ou post é nulo")
            return False
        
        try:
            # Verifica se o post tem os campos necessários
            if 'title' not in post or 'content' not in post:
                self.logger.error(f"Post com formato inválido: {post}")
                return False
                
            # Loga o post que está sendo enviado para debug
            self.logger.info(f"Enviando post: {post}")
            
            message = f"<b>{post['title']}</b>\n\n{post['content']}"
            
            # Adiciona o link externo, se houver
            if post.get('external_link'):
                message += f"\n\n🔗 <b><a href='{post['external_link']}'>👉 ACESSE AQUI</a></b> 🔗"
            
            # Verifica se o group_id está configurado corretamente
            if not self.group_id:
                self.logger.error("ID do grupo não configurado")
                return False
            
            # Função para lidar com o erro de migração de grupo
            def handle_group_migration(error_message):
                # Verifica se o erro é por causa de migração de grupo
                if "Group migrated to supergroup" in str(error_message):
                    # Extrai o novo ID do supergrupo da mensagem de erro
                    import re
                    match = re.search(r'New chat id: (-\d+)', str(error_message))
                    if match:
                        new_group_id = match.group(1)
                        self.logger.info(f"Grupo migrado para supergrupo. Atualizando ID de {self.group_id} para {new_group_id}")
                        # Atualiza o ID do grupo na instância e no data_manager
                        self.group_id = new_group_id
                        self.data_manager.update_bot_config(self.token, new_group_id)
                        return True
                return False
                
            # Se tiver imagem e bot está inicializado, envia com a imagem
            if post.get('image_url') and self.bot:
                try:
                    self.logger.info(f"Enviando post com imagem: {post['image_url']}")
                    self.bot.send_photo(
                        chat_id=self.group_id,
                        photo=post['image_url'],
                        caption=message,
                        parse_mode="HTML" # Usando string direta para evitar erros de referência
                    )
                except Exception as img_error:
                    # Verifica se o erro é por migração de grupo
                    if handle_group_migration(img_error):
                        # Tenta novamente com o novo ID do grupo
                        try:
                            self.bot.send_photo(
                                chat_id=self.group_id,
                                photo=post['image_url'],
                                caption=message,
                                parse_mode="HTML"
                            )
                        except Exception as retry_error:
                            self.logger.error(f"Erro ao enviar imagem mesmo após atualização do ID do grupo: {str(retry_error)}")
                            # Tenta enviar apenas o texto como último recurso
                            if self.bot:
                                try:
                                    self.bot.send_message(
                                        chat_id=self.group_id,
                                        text=message,
                                        parse_mode="HTML"
                                    )
                                except Exception as text_error:
                                    self.logger.error(f"Erro ao enviar texto após falha com imagem: {str(text_error)}")
                                    return False
                    else:
                        self.logger.error(f"Erro ao enviar imagem. Tentando enviar apenas texto: {str(img_error)}")
                        # Se falhar ao enviar com imagem, tenta enviar apenas o texto
                        if self.bot:
                            try:
                                self.bot.send_message(
                                    chat_id=self.group_id,
                                    text=message,
                                    parse_mode="HTML"
                                )
                            except Exception as text_error:
                                # Última tentativa - verificar migração no erro de texto
                                if handle_group_migration(text_error):
                                    try:
                                        self.bot.send_message(
                                            chat_id=self.group_id,
                                            text=message,
                                            parse_mode="HTML"
                                        )
                                    except Exception as final_error:
                                        self.logger.error(f"Erro final ao enviar mensagem: {str(final_error)}")
                                        return False
                                else:
                                    self.logger.error(f"Erro ao enviar mensagem de texto: {str(text_error)}")
                                    return False
            else:
                # Senão, envia só o texto
                if self.bot:
                    try:
                        self.logger.info("Enviando post apenas com texto")
                        self.bot.send_message(
                            chat_id=self.group_id,
                            text=message,
                            parse_mode="HTML"
                        )
                    except Exception as text_error:
                        # Verifica se o erro é por migração de grupo
                        if handle_group_migration(text_error):
                            # Tenta novamente com o novo ID do grupo
                            try:
                                self.bot.send_message(
                                    chat_id=self.group_id,
                                    text=message,
                                    parse_mode="HTML"
                                )
                            except Exception as retry_error:
                                self.logger.error(f"Erro ao enviar texto mesmo após atualização do ID do grupo: {str(retry_error)}")
                                return False
                        else:
                            self.logger.error(f"Erro ao enviar texto: {str(text_error)}")
                            return False
                else:
                    self.logger.error("Bot não inicializado")
                    return False
            
            # Incrementa estatísticas
            success = self.data_manager.increment_promo_messages_stat()
            if not success:
                self.logger.warning("Não foi possível incrementar estatísticas")
            
            self.logger.info(f"Post promocional enviado com sucesso: {post['title']}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar post promocional: {str(e)}")
            return False
    
    def test_welcome_message(self):
        """Testa o envio da mensagem de boas-vindas"""
        try:
            welcome_config = self.data_manager.get_welcome_config()
            message = welcome_config.get('message', "Olá! Bem-vindo(a) ao grupo!")
            
            # Substitui as variáveis na mensagem com valores de teste
            message = message.replace("{first_name}", "Usuário")
            message = message.replace("{last_name}", "Teste")
            message = message.replace("{username}", "usuario_teste")
            
            # Função para lidar com o erro de migração de grupo
            def handle_group_migration(error_message):
                # Verifica se o erro é por causa de migração de grupo
                if "Group migrated to supergroup" in str(error_message):
                    # Extrai o novo ID do supergrupo da mensagem de erro
                    import re
                    match = re.search(r'New chat id: (-\d+)', str(error_message))
                    if match:
                        new_group_id = match.group(1)
                        self.logger.info(f"Grupo migrado para supergrupo. Atualizando ID de {self.group_id} para {new_group_id}")
                        # Atualiza o ID do grupo na instância e no data_manager
                        self.group_id = new_group_id
                        self.data_manager.update_bot_config(self.token, new_group_id)
                        return True
                return False
            
            # Envia a mensagem para o grupo
            if self.bot:
                try:
                    self.bot.send_message(
                        chat_id=self.group_id,
                        text=f"[TESTE] {message}",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    # Verifica se o erro é por migração de grupo
                    if handle_group_migration(e):
                        # Tenta novamente com o novo ID do grupo
                        try:
                            self.bot.send_message(
                                chat_id=self.group_id,
                                text=f"[TESTE] {message}",
                                parse_mode="HTML"
                            )
                        except Exception as retry_error:
                            self.logger.error(f"Erro ao enviar mensagem de teste mesmo após atualização do ID do grupo: {str(retry_error)}")
                            return False
                    else:
                        self.logger.error(f"Erro ao enviar mensagem de boas-vindas de teste: {str(e)}")
                        return False
            else:
                self.logger.error("Bot não inicializado")
                return False
            
            self.logger.info("Mensagem de boas-vindas de teste enviada")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagem de boas-vindas de teste: {str(e)}")
            return False
    
    def get_stats(self):
        """Retorna estatísticas do bot"""
        stats = self.data_manager.get_stats()
        
        # Adiciona informações atuais
        stats['online'] = self.is_running()
        
        return stats
