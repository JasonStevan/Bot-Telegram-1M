import logging
import threading
import time
from typing import Optional, List, Dict, Any, Union

# Configurar logging
logger = logging.getLogger(__name__)

try:
    import telegram
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
    from telegram import Update, Bot, ParseMode, TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    logger.warning("Módulo python-telegram-bot não está instalado. Funcionalidade limitada.")
    TELEGRAM_AVAILABLE = False

class TelegramBotHandler:
    def __init__(self, token: str, group_id: str, data_manager):
        """
        Inicializa o manipulador do bot do Telegram.
        
        Args:
            token: Token de API do bot Telegram
            group_id: ID do grupo ou supergrupo
            data_manager: Instância do gerenciador de dados
        """
        self.token = token
        self.group_id = group_id
        self.data_manager = data_manager
        self.bot = None
        self.updater = None
        self.running = False
        self.thread = None
    
    def setup(self) -> bool:
        """
        Configura o bot e registra handlers.
        
        Returns:
            bool: True se a configuração foi bem-sucedida, False caso contrário.
        """
        try:
            if not TELEGRAM_AVAILABLE:
                logger.error("Módulo python-telegram-bot não está instalado. Não é possível configurar o bot.")
                return False
            
            # Criar instância do bot
            self.bot = Bot(token=self.token)
            
            # Verificar se o token é válido
            try:
                bot_info = self.bot.get_me()
                logger.info(f"Bot configurado: {bot_info.first_name} (@{bot_info.username})")
            except TelegramError as e:
                logger.error(f"Token inválido ou erro ao conectar ao Telegram: {str(e)}")
                self.bot = None
                return False
            
            # Criar updater
            self.updater = Updater(bot=self.bot, use_context=True)
            dispatcher = self.updater.dispatcher
            
            # Registrar handlers
            dispatcher.add_handler(CommandHandler("start", self._start_command))
            dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, self._welcome_new_member))
            
            # Registrar handler de erro
            dispatcher.add_error_handler(self._error_handler)
            
            logger.info("Bot configurado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar bot: {str(e)}")
            self.bot = None
            self.updater = None
            return False
    
    def start(self) -> bool:
        """
        Inicia o bot em segundo plano.
        
        Returns:
            bool: True se o bot foi iniciado com sucesso, False caso contrário.
        """
        try:
            if not self.bot or not self.updater:
                logger.error("Bot não configurado. Execute setup() primeiro.")
                return False
            
            if self.running:
                logger.info("Bot já está em execução.")
                return True
            
            # Iniciar polling em uma thread separada
            self.thread = threading.Thread(target=self._start_polling)
            self.thread.daemon = True
            self.thread.start()
            
            # Esperar um momento para verificar se o polling iniciou corretamente
            time.sleep(1)
            
            if self.running:
                logger.info("Bot iniciado com sucesso.")
                return True
            else:
                logger.error("Falha ao iniciar bot.")
                return False
        except Exception as e:
            logger.error(f"Erro ao iniciar bot: {str(e)}")
            return False
    
    def _start_polling(self):
        """Inicia o polling em uma thread separada."""
        try:
            self.running = True
            logger.info("Iniciando polling para o bot...")
            self.updater.start_polling()
            self.updater.idle()
        except Exception as e:
            logger.error(f"Erro no polling do bot: {str(e)}")
        finally:
            self.running = False
            logger.info("Polling do bot encerrado.")
    
    def stop(self) -> bool:
        """
        Para o bot.
        
        Returns:
            bool: True se o bot foi parado com sucesso, False caso contrário.
        """
        try:
            if not self.running:
                logger.info("Bot não está em execução.")
                return True
            
            if self.updater:
                logger.info("Parando bot...")
                self.updater.stop()
                if self.thread:
                    self.thread.join(timeout=5)
                self.running = False
                logger.info("Bot parado com sucesso.")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao parar bot: {str(e)}")
            self.running = False
            return False
    
    def is_running(self) -> bool:
        """
        Verifica se o bot está em execução.
        
        Returns:
            bool: True se o bot está em execução, False caso contrário.
        """
        return self.running
    
    def _start_command(self, update: Update, context: CallbackContext):
        """Handler para o comando /start."""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Verificar se é uma mensagem privada
            if chat_id == int(self.group_id):
                return
            
            message = f"Olá {user.first_name}! Eu sou um bot de gerenciamento de grupo."
            
            update.message.reply_text(message)
            logger.info(f"Comando /start de {user.first_name} (ID: {user.id})")
        except Exception as e:
            logger.error(f"Erro ao processar comando /start: {str(e)}")
    
    def _welcome_new_member(self, update: Update, context: CallbackContext):
        """Handler para novos membros no grupo."""
        try:
            # Obter mensagem de boas-vindas das configurações
            welcome_message = self.data_manager.get_welcome_message()
            
            # Verificar se o evento é do grupo correto
            chat_id = update.effective_chat.id
            if str(chat_id) != str(self.group_id):
                logger.debug(f"Evento de novo membro em grupo diferente: {chat_id} vs {self.group_id}")
                return
            
            # Processar novos membros
            for new_member in update.message.new_chat_members:
                # Ignorar se for o próprio bot
                if new_member.id == context.bot.id:
                    continue
                
                # Formatar mensagem de boas-vindas
                formatted_message = welcome_message.replace("{name}", new_member.first_name)
                
                # Enviar mensagem
                context.bot.send_message(
                    chat_id=chat_id,
                    text=formatted_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                logger.info(f"Mensagem de boas-vindas enviada para {new_member.first_name} no grupo {chat_id}")
                
                # Incrementar estatística
                self.data_manager.increment_welcome_messages_stat()
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de boas-vindas: {str(e)}")
    
    def _error_handler(self, update: object, context: CallbackContext):
        """Handler para erros do Telegram."""
        try:
            logger.error(f"Erro do Telegram: {context.error}")
            
            # Verificar se é um erro de grupo migrado
            if isinstance(context.error, TelegramError) and "migrated to chat id" in str(context.error).lower():
                self._handle_group_migration(str(context.error))
        except Exception as e:
            logger.error(f"Erro ao processar erro do Telegram: {str(e)}")
    
    def _handle_group_migration(self, error_message: str):
        """
        Processa mensagem de erro de migração de grupo.
        
        Args:
            error_message: Mensagem de erro contendo o novo ID do grupo
        """
        try:
            # Extrair novo ID do grupo
            import re
            match = re.search(r"migrated to chat id (-\d+)", error_message.lower())
            if match:
                new_group_id = match.group(1)
                logger.info(f"Grupo migrado para novo ID: {new_group_id}")
                
                # Atualizar ID do grupo
                self.data_manager.set_group_id(new_group_id)
                self.group_id = new_group_id
        except Exception as e:
            logger.error(f"Erro ao processar migração de grupo: {str(e)}")
    
    def send_message(self, text: str) -> bool:
        """
        Envia uma mensagem de texto para o grupo.
        
        Args:
            text: Texto da mensagem
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário.
        """
        try:
            if not self.bot or not self.group_id:
                logger.error("Bot não configurado para enviar mensagens.")
                return False
            
            # Verificar se o texto está vazio
            if not text:
                logger.error("Texto da mensagem está vazio.")
                return False
            
            # Tentar enviar a mensagem
            self.bot.send_message(
                chat_id=self.group_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Mensagem enviada com sucesso: {text[:30]}...")
            return True
        except TelegramError as te:
            # Verificar se é um erro de grupo migrado
            if "migrated to chat id" in str(te).lower():
                self._handle_group_migration(str(te))
                # Tentar novamente com o novo ID
                try:
                    self.bot.send_message(
                        chat_id=self.group_id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.info(f"Mensagem enviada com sucesso após migração: {text[:30]}...")
                    return True
                except Exception as e:
                    logger.error(f"Erro ao enviar mensagem após migração: {str(e)}")
                    return False
            else:
                logger.error(f"Erro do Telegram ao enviar mensagem: {str(te)}")
                return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return False
    
    def send_photo(self, photo_url: str, caption: Optional[str] = None) -> bool:
        """
        Envia uma foto com legenda opcional para o grupo.
        
        Args:
            photo_url: URL da imagem
            caption: Texto da legenda (opcional)
            
        Returns:
            bool: True se a foto foi enviada com sucesso, False caso contrário.
        """
        try:
            if not self.bot or not self.group_id:
                logger.error("Bot não configurado para enviar fotos.")
                return False
            
            # Verificar se a URL está vazia
            if not photo_url:
                logger.error("URL da foto está vazia.")
                return False
            
            # Tentar enviar a foto
            self.bot.send_photo(
                chat_id=self.group_id,
                photo=photo_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Foto enviada com sucesso: {photo_url}")
            return True
        except TelegramError as te:
            # Verificar se é um erro de grupo migrado
            if "migrated to chat id" in str(te).lower():
                self._handle_group_migration(str(te))
                # Tentar novamente com o novo ID
                try:
                    self.bot.send_photo(
                        chat_id=self.group_id,
                        photo=photo_url,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.info(f"Foto enviada com sucesso após migração: {photo_url}")
                    return True
                except Exception as e:
                    logger.error(f"Erro ao enviar foto após migração: {str(e)}")
                    return False
            else:
                logger.error(f"Erro do Telegram ao enviar foto: {str(te)}")
                return False
        except Exception as e:
            logger.error(f"Erro ao enviar foto: {str(e)}")
            return False
    
    def test_welcome_message(self) -> bool:
        """
        Testa o envio da mensagem de boas-vindas para o grupo.
        
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário.
        """
        try:
            welcome_message = self.data_manager.get_welcome_message()
            test_message = f"🧪 TESTE DE MENSAGEM DE BOAS-VINDAS 🧪\n\n{welcome_message}"
            
            # Substituir placeholder
            test_message = test_message.replace("{name}", "Usuário")
            
            return self.send_message(test_message)
        except Exception as e:
            logger.error(f"Erro ao testar mensagem de boas-vindas: {str(e)}")
            return False
