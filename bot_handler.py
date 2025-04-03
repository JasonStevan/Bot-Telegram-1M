import logging
import threading
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

# Configurar logging
logger = logging.getLogger(__name__)

class MessageScheduler:
    def __init__(self, bot_handler, data_manager):
        """
        Inicializa o agendador de mensagens.
        
        Args:
            bot_handler: Instância do manipulador do bot
            data_manager: Instância do gerenciador de dados
        """
        self.bot_handler = bot_handler
        self.data_manager = data_manager
        self.thread = None
        self.running = False
        self.last_sent = 0  # Timestamp do último envio
    
    def start(self) -> bool:
        """
        Inicia o agendador em segundo plano.
        
        Returns:
            bool: True se o agendador foi iniciado com sucesso, False caso contrário.
        """
        try:
            if self.running:
                logger.info("Agendador já está em execução.")
                return True
            
            # Iniciar thread do agendador
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop)
            self.thread.daemon = True
            self.thread.start()
            
            logger.info("Agendador de mensagens iniciado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao iniciar agendador: {str(e)}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """
        Para o agendador.
        
        Returns:
            bool: True se o agendador foi parado com sucesso, False caso contrário.
        """
        try:
            if not self.running:
                logger.info("Agendador não está em execução.")
                return True
            
            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            
            logger.info("Agendador de mensagens parado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao parar agendador: {str(e)}")
            return False
    
    def is_running(self) -> bool:
        """
        Verifica se o agendador está em execução.
        
        Returns:
            bool: True se o agendador está em execução, False caso contrário.
        """
        return self.running
    
    def update_interval(self, interval: int) -> bool:
        """
        Atualiza o intervalo entre mensagens.
        
        Args:
            interval: Novo intervalo em minutos
            
        Returns:
            bool: True se o intervalo foi atualizado com sucesso, False caso contrário.
        """
        try:
            # Não precisa fazer nada especial, pois o intervalo é obtido
            # diretamente do data_manager a cada iteração
            logger.info(f"Intervalo atualizado para: {interval} minutos")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar intervalo: {str(e)}")
            return False
    
    def _scheduler_loop(self):
        """Loop principal do agendador."""
        logger.info("Loop do agendador iniciado.")
        
        while self.running:
            try:
                # Verificar se o bot está ativo
                if not self.data_manager.get_bot_status():
                    time.sleep(10)  # Esperar 10 segundos antes de verificar novamente
                    continue
                
                # Obter intervalo atual (em minutos)
                interval = self.data_manager.get_interval()
                if interval < 1:
                    interval = 1  # Mínimo de 1 minuto
                
                # Converter para segundos
                interval_seconds = interval * 60
                
                # Verificar se é hora de enviar uma nova mensagem
                current_time = time.time()
                if current_time - self.last_sent >= interval_seconds:
                    # Enviar mensagem
                    if self.send_scheduled_post():
                        self.last_sent = current_time
                    
                # Dormir por um curto período para não sobrecarregar a CPU
                time.sleep(5)
            except Exception as e:
                logger.error(f"Erro no loop do agendador: {str(e)}")
                time.sleep(10)  # Esperar um pouco antes de tentar novamente
    
    def send_scheduled_post(self) -> bool:
        """
        Envia um post promocional programado.
        
        Returns:
            bool: True se o post foi enviado com sucesso, False caso contrário.
        """
        try:
            # Verificar se o bot está ativo
            if not self.data_manager.get_bot_status():
                logger.info("Bot está desativado. Nenhum post será enviado.")
                return False

            # Obter o próximo post
            next_post = self.data_manager.get_next_post()
            if not next_post:
                logger.warning("Não há posts para enviar.")
                return False
            
            # Tentar enviar a mensagem com tratamento de erro robusto
            try:
                # Extrair texto e imagem do post
                text = next_post.get('text', '')
                image_url = next_post.get('image_url', '')
                external_link = next_post.get('external_link', '')
                
                # Construir o texto da mensagem
                message_text = text
                if external_link:
                    message_text += f"\n\n{external_link}"
                
                # Enviar mensagem
                result = False
                if image_url:
                    # Mensagem com imagem
                    try:
                        result = self.bot_handler.send_photo(image_url, message_text)
                    except Exception as e:
                        logger.error(f"Erro ao enviar mensagem com imagem: {str(e)}")
                        # Tentar enviar apenas o texto como fallback
                        result = self.bot_handler.send_message(message_text)
                else:
                    # Mensagem de texto simples
                    result = self.bot_handler.send_message(message_text)
                
                if result:
                    # Incrementar estatística
                    self.data_manager.increment_promo_messages_stat()
                    logger.info(f"Post promocional enviado com sucesso: {text[:30]}...")
                    return True
                else:
                    logger.error("Falha ao enviar post promocional.")
                    return False
            except Exception as e:
                logger.error(f"Erro ao processar e enviar post: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar post programado: {str(e)}")
            return False
