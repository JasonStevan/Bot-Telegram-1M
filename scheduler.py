import logging
import threading
import time
from datetime import datetime

class PostScheduler:
    def __init__(self, bot_handler, data_manager):
        """Inicializa o agendador de posts"""
        self.bot_handler = bot_handler
        self.data_manager = data_manager
        self.running = False
        self.thread = None
        
        # Configuração de logging
        self.logger = logging.getLogger("PostScheduler")
    
    def start(self):
        """Inicia o agendador em uma thread separada"""
        if self.running:
            self.logger.warning("Tentativa de iniciar agendador que já está ativo")
            return True
        
        try:
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop)
            self.thread.daemon = True  # Thread será encerrada quando o programa principal terminar
            self.thread.start()
            
            self.logger.info("Agendador iniciado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao iniciar agendador: {str(e)}")
            self.running = False
            return False
    
    def stop(self):
        """Para o agendador"""
        if not self.running:
            self.logger.debug("Tentativa de parar agendador que já está inativo")
            return False
        
        try:
            self.logger.info("Parando agendador de posts...")
            
            # Marca como inativo para que o loop principal do agendador termine
            self.running = False
            
            # Aguarda a thread terminar com timeout
            if self.thread and self.thread.is_alive():
                self.logger.debug("Aguardando a thread do agendador terminar...")
                self.thread.join(timeout=5)
                
                # Verifica se a thread terminou no tempo esperado
                if self.thread.is_alive():
                    self.logger.warning("A thread do agendador não terminou dentro do timeout, mas será abandonada")
            
            # Limpa as referências para ajudar o garbage collector
            self.thread = None
            
            self.logger.info("Agendador parado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao parar agendador: {str(e)}")
            # Garante que fique marcado como inativo mesmo com erro
            self.running = False
            return False
    
    def is_running(self):
        """Verifica se o agendador está em execução"""
        return self.running and self.thread and self.thread.is_alive()
    
    def _scheduler_loop(self):
        """Loop principal do agendador"""
        last_post_time = datetime.now()
        
        while self.running:
            try:
                # Obtém o intervalo atual
                config = self.data_manager.get_bot_config()
                interval_minutes = config.get('interval', 10)
                
                # Converte para segundos
                interval_seconds = interval_minutes * 60
                
                # Verifica se já passou o tempo necessário desde o último post
                current_time = datetime.now()
                elapsed_seconds = (current_time - last_post_time).total_seconds()
                
                # Calcula quanto tempo falta para o próximo post
                time_to_next_post = max(0, interval_seconds - elapsed_seconds)
                
                if time_to_next_post <= 0:
                    # Hora de enviar um novo post
                    self.logger.info(f"Enviando post programado (intervalo: {interval_minutes} minutos)")
                    self._send_random_post()
                    last_post_time = datetime.now()  # Usa o tempo atual após o envio para maior precisão
                    
                    # Recalcula o tempo para o próximo post
                    time_to_next_post = interval_seconds
                
                # Dorme pelo tempo exato necessário, mas verifica a cada 15 segundos para 
                # responder mais rapidamente às mudanças de configuração
                sleep_time = min(15, time_to_next_post)
                self.logger.debug(f"Próximo post em {time_to_next_post/60:.1f} minutos. Dormindo por {sleep_time} segundos.")
                time.sleep(sleep_time)
            except Exception as e:
                self.logger.error(f"Erro no loop do agendador: {str(e)}")
                time.sleep(30)  # Em caso de erro, espera um pouco antes de tentar novamente
    
    def _send_random_post(self):
        """Envia o próximo post sequencial para o grupo (nome mantido por compatibilidade)"""
        try:
            # Obtém o próximo post sequencial
            post = self.data_manager.get_next_sequential_post()
            
            if not post:
                self.logger.warning("Não há posts promocionais para enviar")
                return False
            
            # Envia o post
            success = self.bot_handler.send_promotional_post(post)
            
            if success:
                self.logger.info(f"Post promocional sequencial enviado com sucesso: {post['title']}")
            else:
                self.logger.error(f"Falha ao enviar post promocional: {post['title']}")
                
            return success
        except Exception as e:
            self.logger.error(f"Erro ao enviar post sequencial: {str(e)}")
            return False
