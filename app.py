import os
import logging
import time
import sys
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from auth import check_auth, authenticate_user
from data_manager import DataManager

# Configurar logger
logger = logging.getLogger(__name__)

# Verificar se podemos importar os módulos relacionados ao Telegram
TELEGRAM_AVAILABLE = True
try:
    from bot_handler import TelegramBotHandler
    from scheduler import PostScheduler
except ImportError as e:
    TELEGRAM_AVAILABLE = False
    logger.error(f"Erro ao importar módulos do Telegram: {str(e)}")
    # Criar classes mock para manter a compatibilidade
    class MockBotHandler:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger('MockBotHandler')
            self.logger.warning("Usando MockBotHandler - funcionalidade do bot limitada")
            
        def start(self):
            return False
            
        def stop(self):
            return False
            
        def is_running(self):
            return False
            
        def send_promotional_post(self, post):
            return False
            
        def test_welcome_message(self):
            return False
            
        def get_stats(self):
            return {
                'welcome_messages_sent': 0,
                'promo_messages_sent': 0,
                'last_restarted': None
            }
    
    class MockScheduler:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger('MockScheduler')
            self.logger.warning("Usando MockScheduler - funcionalidade de agendamento limitada")
            
        def start(self):
            return False
            
        def stop(self):
            return False
            
        def is_running(self):
            return False
    
    # Mostra um erro explicando que a biblioteca está faltando
    logger.error("IMPORTANTE: A biblioteca python-telegram-bot não está instalada. O painel administrativo vai funcionar, mas as funcionalidades de bot estarão desabilitadas.")
    logger.error("Para resolver: pip install python-telegram-bot==13.15")
    
    # Substituir as classes reais por mocks
    TelegramBotHandler = MockBotHandler
    PostScheduler = MockScheduler

# Configuração do logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='bot_admin.log',
                    filemode='a')

# Inicialização da aplicação Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "chave_secreta_fixa_para_producao_theblackwolf")

# Garante que o diretório de dados exista
data_dir = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_dir):
    try:
        os.makedirs(data_dir)
        logging.info(f"Diretório de dados criado: {data_dir}")
    except Exception as e:
        logging.error(f"Não foi possível criar o diretório de dados: {str(e)}")

# Inicialização do gerenciador de dados
data_manager = DataManager()

# Variáveis globais para bot e scheduler
bot_handler = None
scheduler = None

# Função para garantir que apenas uma instância do bot esteja rodando
def initialize_bot(force_restart=False):
    global bot_handler, scheduler
    
    # Se já tiver instâncias rodando e force_restart for True, para elas
    if force_restart and bot_handler:
        logging.info("Forçando parada de instâncias anteriores do bot")
        bot_handler.stop()
        if scheduler:
            scheduler.stop()
        # Aguarda para garantir que os recursos foram liberados
        time.sleep(2)
    
    try:
        # Obter configurações atuais
        config = data_manager.get_bot_config()
        bot_token = config.get('token', '')
        group_id = config.get('group_id', '')
        bot_active = config.get('active', False)
        
        if not bot_token or not group_id:
            logging.warning("Bot não inicializado: Token ou ID do grupo não configurados")
            bot_handler = None
            scheduler = None
            return False
            
        # Cria novas instâncias
        logging.info(f"Inicializando bot com token={bot_token[:5]}... e grupo={group_id}")
        bot_handler = TelegramBotHandler(bot_token, group_id, data_manager)
        scheduler = PostScheduler(bot_handler, data_manager)
        
        # Inicia se estiver configurado como ativo
        if bot_active:
            bot_handler.start()
            scheduler.start()
            logging.info("Bot iniciado automaticamente: configuração 'active' = True")
            return True
        else:
            logging.info("Bot inicializado mas não iniciado: configuração 'active' = False")
            return True
            
    except Exception as e:
        logging.error(f"Erro ao inicializar o bot: {str(e)}")
        bot_handler = None
        scheduler = None
        return False

# Inicializa o bot na inicialização do app
initialize_bot(force_restart=True)

# Decorator para verificar se o usuário está autenticado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Rotas para a interface web
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if authenticate_user(username, password):
            session['authenticated'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas!', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado!', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    global bot_handler, scheduler
    
    bot_status = {
        'active': False,
        'token_configured': False,
        'group_configured': False,
        'online': False
    }
    
    stats = {
        'total_posts': 0,
        'welcome_messages_sent': 0,
        'promo_messages_sent': 0
    }
    
    config = data_manager.get_bot_config()
    bot_status['active'] = config.get('active', False)
    bot_status['token_configured'] = bool(config.get('token', ''))
    bot_status['group_configured'] = bool(config.get('group_id', ''))
    
    if bot_handler:
        try:
            bot_status['online'] = bot_handler.is_running()
        except Exception as e:
            logging.error(f"Erro ao verificar status do bot: {str(e)}")
            bot_status['online'] = False
        stats = bot_handler.get_stats()
    
    promotional_posts = data_manager.get_promotional_posts()
    stats['total_posts'] = len(promotional_posts)
    
    # Verifica se o módulo telegram está disponível
    telegram_warning = not TELEGRAM_AVAILABLE
    
    return render_template('dashboard.html', 
                          bot_status=bot_status, 
                          stats=stats,
                          config=config,
                          telegram_warning=telegram_warning)

@app.route('/promotional_posts', methods=['GET', 'POST'])
@login_required
def promotional_posts():
    global bot_handler, scheduler
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create' or action == 'edit':
            post_id = request.form.get('post_id', '')
            title = request.form.get('title')
            content = request.form.get('content')
            image_url = request.form.get('image_url', '')
            external_link = request.form.get('external_link', '')
            
            if not title or not content:
                flash('Título e conteúdo são obrigatórios!', 'danger')
            else:
                if action == 'create':
                    data_manager.add_promotional_post(title, content, image_url, external_link)
                    flash('Post promocional criado com sucesso!', 'success')
                else:
                    data_manager.update_promotional_post(post_id, title, content, image_url, external_link)
                    flash('Post promocional atualizado com sucesso!', 'success')
        
        elif action == 'delete':
            post_id = request.form.get('post_id')
            if post_id:
                data_manager.delete_promotional_post(post_id)
                flash('Post promocional excluído com sucesso!', 'success')
        
        elif action == 'test':
            post_id = request.form.get('post_id')
            if not TELEGRAM_AVAILABLE:
                flash('Módulo Telegram não disponível. Instale python-telegram-bot para habilitar esta funcionalidade.', 'warning')
            elif bot_handler and post_id:
                post = data_manager.get_promotional_post(post_id)
                if post:
                    try:
                        success = bot_handler.send_promotional_post(post)
                        if success:
                            flash('Post promocional enviado para teste!', 'success')
                        else:
                            flash('Erro ao enviar post para teste!', 'danger')
                    except Exception as e:
                        logging.error(f"Erro ao enviar post para teste: {str(e)}")
                        flash(f'Erro ao enviar post: {str(e)}', 'danger')
                else:
                    flash('Post não encontrado!', 'danger')
            else:
                flash('Bot não está configurado ou post não encontrado!', 'danger')
                
        return redirect(url_for('promotional_posts'))
    
    posts = data_manager.get_promotional_posts()
    # Verifica se o módulo telegram está disponível
    telegram_warning = not TELEGRAM_AVAILABLE
    return render_template('promotional_posts.html', posts=posts, telegram_warning=telegram_warning)

@app.route('/welcome_messages', methods=['GET', 'POST'])
@login_required
def welcome_messages():
    global bot_handler, scheduler
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'save':
            welcome_message = request.form.get('welcome_message')
            enabled = request.form.get('enabled') == 'on'
            
            data_manager.update_welcome_config(welcome_message, enabled)
            flash('Configuração de boas-vindas atualizada com sucesso!', 'success')
        
        elif action == 'test':
            if not TELEGRAM_AVAILABLE:
                flash('Módulo Telegram não disponível. Instale python-telegram-bot para habilitar esta funcionalidade.', 'warning')
            elif bot_handler:
                welcome_config = data_manager.get_welcome_config()
                try:
                    success = bot_handler.test_welcome_message()
                    if success:
                        flash('Mensagem de boas-vindas enviada para teste!', 'success')
                    else:
                        flash('Erro ao enviar mensagem de boas-vindas para teste!', 'danger')
                except Exception as e:
                    logging.error(f"Erro ao testar mensagem de boas-vindas: {str(e)}")
                    flash(f'Erro ao testar mensagem: {str(e)}', 'danger')
            else:
                flash('Bot não está configurado!', 'danger')
                
        return redirect(url_for('welcome_messages'))
    
    welcome_config = data_manager.get_welcome_config()
    # Verifica se o módulo telegram está disponível
    telegram_warning = not TELEGRAM_AVAILABLE
    return render_template('welcome_messages.html', welcome_config=welcome_config, telegram_warning=telegram_warning)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    global bot_handler, scheduler
    
    logging.info("Acessando página de configurações")
    start_time = datetime.now()
    
    # Para requisições POST, processa separadamente para evitar atrasos na interface
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'save_config':
            token = request.form.get('token')
            group_id = request.form.get('group_id')
            interval = request.form.get('interval')
            
            try:
                interval = int(interval)
                if interval < 1:
                    interval = 10  # Valor padrão
            except:
                interval = 10  # Valor padrão
                
            data_manager.update_bot_config(token, group_id, interval)
            flash('Configurações atualizadas com sucesso!', 'success')
            
        elif action == 'toggle_bot':
            new_status = request.form.get('status') == 'true'
            logging.info(f"Solicitação para {'ativar' if new_status else 'desativar'} o bot")
            
            # Verifica se o módulo Telegram está disponível
            if new_status and not TELEGRAM_AVAILABLE:
                flash('Não é possível ativar o bot: Módulo Telegram não disponível. Instale python-telegram-bot.', 'warning')
                data_manager.update_bot_status(False)  # Força o status como desativado
                return redirect(url_for('settings'))
            
            # Salva o novo status na configuração
            data_manager.update_bot_status(new_status)
            
            if new_status:
                # Ativar o bot usando nossa função centralizada
                try:
                    success = initialize_bot(force_restart=True)
                    if success:
                        flash('Bot ativado com sucesso!', 'success')
                    else:
                        flash('Erro ao ativar o bot. Verifique os logs para mais detalhes.', 'danger')
                except Exception as e:
                    logging.error(f"Erro ao ativar bot: {str(e)}")
                    flash(f'Erro ao ativar bot: {str(e)}', 'danger')
            else:
                # Desativar o bot
                try:
                    if bot_handler:
                        bot_handler.stop()
                    if scheduler:
                        scheduler.stop()
                    logging.info("Bot desativado com sucesso")
                    flash('Bot desativado com sucesso!', 'success')
                except Exception as e:
                    logging.error(f"Erro ao desativar bot: {str(e)}")
                    flash(f'Erro ao desativar bot: {str(e)}', 'danger')
        
        elif action == 'restart_bot':
            logging.info("Solicitação para reiniciar o bot recebida")
            
            # Verifica se o módulo Telegram está disponível
            if not TELEGRAM_AVAILABLE:
                flash('Não é possível reiniciar o bot: Módulo Telegram não disponível. Instale python-telegram-bot.', 'warning')
                return redirect(url_for('settings'))
                
            try:
                # Usa a função centralizada para reiniciar o bot
                if initialize_bot(force_restart=True):
                    flash('Bot reiniciado com sucesso!', 'success')
                else:
                    flash('Erro ao reiniciar o bot. Verifique os logs para mais detalhes.', 'danger')
            except Exception as e:
                logging.error(f"Erro ao reiniciar bot: {str(e)}")
                flash(f'Erro ao reiniciar bot: {str(e)}', 'danger')
                
        return redirect(url_for('settings'))
    
    # Para GET, otimiza ao máximo a performance renderizando a página rapidamente
    try:
        # Carregar somente os dados essenciais para renderizar a página mais rápido
        config = data_manager.get_bot_config()
        telegram_warning = not TELEGRAM_AVAILABLE
            
        return render_template('settings.html', config=config, telegram_warning=telegram_warning)
    except Exception as e:
        # Falha segura em caso de erro
        logging.error(f"Erro ao acessar página de configurações: {str(e)}")
        flash(f"Erro ao carregar configurações: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/logs')
@login_required
def logs():
    # Tempo máximo em milissegundos para ler o arquivo de log
    max_time_ms = 500
    
    # Obter os logs mais recentes
    log_entries = []
    try:
        start_time = datetime.now()
        if os.path.exists('bot_admin.log'):
            with open('bot_admin.log', 'r') as f:
                # Ler as últimas 100 linhas (mais rápido do que ler tudo)
                lines = f.readlines()[-100:]
                for line in lines:
                    # Processar somente se ainda estiver dentro do limite de tempo
                    current_time = datetime.now()
                    elapsed_ms = (current_time - start_time).total_seconds() * 1000
                    if elapsed_ms > max_time_ms:
                        log_entries.append("Carregamento de logs interrompido para evitar timeout...")
                        break
                        
                    log_entries.append(line.strip())
    except Exception as e:
        log_entries.append(f"Erro ao ler logs: {str(e)}")
    
    # Informações de diagnóstico
    diagnostic = {
        'python_version': sys.version,
        'app_path': os.path.abspath(__file__),
        'data_dir_exists': os.path.exists(data_dir),
        'telegram_module': TELEGRAM_AVAILABLE
    }
    
    # Verifica se o módulo telegram está disponível
    telegram_warning = not TELEGRAM_AVAILABLE
    
    # Renderizar o template
    return render_template('logs.html', logs=logs, diagnostic=diagnostic, telegram_warning=telegram_warning)

@app.route('/api/bot/status')
@login_required
def api_bot_status():
    """API para verificar o status do bot (para atualizações em tempo real no dashboard)"""
    if not bot_handler:
        return {'status': 'not_configured', 'active': False, 'running': False}
    
    config = data_manager.get_bot_config()
    active = config.get('active', False)
    
    try:
        running = bot_handler.is_running() if active else False
    except:
        running = False
        
    return {'status': 'ok', 'active': active, 'running': running}

# Tratamento de erros
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Usado para testes locais, não será executado no ambiente de produção
    app.run(host='0.0.0.0', port=5000, debug=True)
