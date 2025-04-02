import os
import json
import logging
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps

# Configuração de log para melhor depuração
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_admin.log')
    ]
)

# Configuração do Flask
app = Flask(__name__)
# Chave secreta para sessões
app.secret_key = os.environ.get("SESSION_SECRET", "um_segredo_muito_secreto_para_sessoes")

# Importações condicionais para permitir execução mesmo sem o módulo telegram
try:
    from bot_handler import TelegramBotHandler
    from scheduler import PostScheduler
    TELEGRAM_AVAILABLE = True
    logging.info("Módulo Telegram disponível. Recursos de bot habilitados.")
except ImportError:
    logging.warning("Módulo Telegram não disponível. Recursos de bot desabilitados.")
    TELEGRAM_AVAILABLE = False

# Importar gerenciador de dados e autenticação
from data_manager import DataManager
from auth import authenticate_user, create_default_user

# Criar instâncias globais
data_manager = DataManager()
bot_handler = None
scheduler = None

# Inicializar usuário padrão
create_default_user()

# Classes mock para quando o Telegram não está disponível
if not TELEGRAM_AVAILABLE:
    class MockBotHandler:
        def __init__(self, *args, **kwargs):
            pass
        
        def start(self):
            logging.info("MockBotHandler: start chamado")
            return True
        
        def stop(self):
            logging.info("MockBotHandler: stop chamado")
            return True
        
        def is_running(self):
            return False
        
        def send_promotional_post(self, post):
            logging.info(f"MockBotHandler: send_promotional_post chamado com {post.get('title', 'unknown')}")
            return False
        
        def test_welcome_message(self):
            logging.info("MockBotHandler: test_welcome_message chamado")
            return False
        
        def get_stats(self):
            return {"error": "Telegram não disponível"}
    
    class MockScheduler:
        def __init__(self, *args, **kwargs):
            pass
        
        def start(self):
            logging.info("MockScheduler: start chamado")
            return True
        
        def stop(self):
            logging.info("MockScheduler: stop chamado")
            return True
        
        def is_running(self):
            return False

def initialize_bot(force_restart=False):
    """Inicializa o bot com base na configuração salva"""
    global bot_handler, scheduler
    
    if not TELEGRAM_AVAILABLE:
        logging.warning("Não é possível inicializar o bot: Módulo Telegram não disponível")
        bot_handler = MockBotHandler(None, None, data_manager)
        scheduler = MockScheduler(bot_handler, data_manager)
        return False
    
    try:
        # Obter configuração
        config = data_manager.get_bot_config()
        
        # Verificar se o bot deve estar ativo
        if not config.get("active", False) and not force_restart:
            logging.info("Bot não está configurado para iniciar automaticamente")
            return False
        
        token = config.get("token", "")
        group_id = config.get("group_id", "")
        
        # Verificar se token e group_id estão configurados
        if not token or not group_id:
            logging.warning("Token ou ID do grupo não configurados")
            return False
        
        # Se o bot já estiver inicializado e não for forçado a reiniciar, retorna
        if bot_handler and bot_handler.is_running() and not force_restart:
            logging.info("Bot já está em execução")
            return True
            
        # Parar instâncias existentes se necessário
        if bot_handler:
            bot_handler.stop()
        if scheduler:
            scheduler.stop()
            
        # Iniciar novas instâncias
        bot_handler = TelegramBotHandler(token, group_id, data_manager)
        scheduler = PostScheduler(bot_handler, data_manager)
        
        # Iniciar o bot e o agendador
        bot_started = bot_handler.start()
        scheduler_started = scheduler.start()
        
        # Atualizar o horário de reinício
        data_manager.update_restart_time()
        
        if bot_started and scheduler_started:
            logging.info("Bot e agendador inicializados com sucesso")
            return True
        else:
            logging.error("Falha ao inicializar bot ou agendador")
            return False
            
    except Exception as e:
        logging.error(f"Erro ao inicializar bot: {str(e)}")
        # Usar versões de mock em caso de erro
        bot_handler = MockBotHandler(None, None, data_manager)
        scheduler = MockScheduler(bot_handler, data_manager)
        return False

# Inicializar o bot na inicialização do aplicativo
initialize_bot()

# Decorator para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if authenticate_user(username, password):
            session['username'] = username
            
            # Redirecionar para 'next' se existir, ou para dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Nome de usuário ou senha incorretos!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    global bot_handler
    
    # Estatísticas básicas
    stats = data_manager.get_stats()
    
    # Verifica se o bot está em execução
    bot_running = False
    if bot_handler:
        try:
            bot_running = bot_handler.is_running()
        except Exception as e:
            logging.error(f"Erro ao verificar status do bot: {str(e)}")
    
    # Carrega a configuração do bot
    bot_config = data_manager.get_bot_config()
    
    # Contagem de posts promocionais
    posts = data_manager.get_promotional_posts()
    post_count = len(posts)
    
    # Verifica se o módulo telegram está disponível
    telegram_warning = not TELEGRAM_AVAILABLE
    
    return render_template(
        'dashboard.html', 
        stats=stats, 
        bot_running=bot_running, 
        bot_config=bot_config,
        post_count=post_count,
        telegram_warning=telegram_warning
    )

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
                return redirect(url_for('promotional_posts'))
            else:
                try:
                    if action == 'create':
                        result = data_manager.add_promotional_post(title, content, image_url, external_link)
                        if result:
                            flash('Post promocional criado com sucesso!', 'success')
                        else:
                            flash('Erro ao criar post promocional. Verifique os logs para mais informações.', 'danger')
                    else:
                        result = data_manager.update_promotional_post(post_id, title, content, image_url, external_link)
                        if result:
                            flash('Post promocional atualizado com sucesso!', 'success')
                        else:
                            flash('Erro ao atualizar post promocional. Verifique os logs para mais informações.', 'danger')
                except Exception as e:
                    logging.error(f"Erro ao manipular post promocional: {str(e)}")
                    flash(f'Erro ao processar solicitação: {str(e)}', 'danger')
        
        elif action == 'delete':
            post_id = request.form.get('post_id')
            if post_id:
                try:
                    result = data_manager.delete_promotional_post(post_id)
                    if result:
                        flash('Post promocional excluído com sucesso!', 'success')
                    else:
                        flash('Erro ao excluir post promocional. Verifique os logs para mais informações.', 'danger')
                except Exception as e:
                    logging.error(f"Erro ao excluir post promocional: {str(e)}")
                    flash(f'Erro ao excluir post: {str(e)}', 'danger')
        
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
            
            try:
                success = data_manager.update_welcome_config(welcome_message, enabled)
                if success:
                    flash('Configuração de boas-vindas atualizada com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar configuração de boas-vindas. Verifique os logs para mais informações.', 'danger')
            except Exception as e:
                logging.error(f"Erro ao atualizar configuração de boas-vindas: {str(e)}")
                flash(f'Erro ao atualizar configuração: {str(e)}', 'danger')
        
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
            
            try:
                success = data_manager.update_bot_config(token, group_id, interval)
                if success:
                    flash('Configurações atualizadas com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar configurações. Verifique os logs para mais informações.', 'danger')
            except Exception as e:
                logging.error(f"Erro ao atualizar configurações do bot: {str(e)}")
                flash(f'Erro ao atualizar configurações: {str(e)}', 'danger')
            
        elif action == 'toggle_bot':
            new_status = request.form.get('status') == 'true'
            logging.info(f"Solicitação para {'ativar' if new_status else 'desativar'} o bot")
            
            # Verifica se o módulo Telegram está disponível
            if new_status and not TELEGRAM_AVAILABLE:
                flash('Não é possível ativar o bot: Módulo Telegram não disponível. Instale python-telegram-bot.', 'warning')
                try:
                    success = data_manager.update_bot_status(False)  # Força o status como desativado
                    if not success:
                        logging.error("Erro ao forçar status do bot como desativado")
                        flash('Erro ao atualizar status do bot. Verifique os logs para mais detalhes.', 'danger')
                except Exception as e:
                    logging.error(f"Erro ao forçar status do bot como desativado: {str(e)}")
                    flash(f'Erro ao atualizar status do bot: {str(e)}', 'danger')
                return redirect(url_for('settings'))
            
            # Salva o novo status na configuração
            try:
                success = data_manager.update_bot_status(new_status)
                if not success:
                    logging.error("Erro ao atualizar status do bot")
                    flash('Erro ao atualizar status do bot. Verifique os logs para mais detalhes.', 'danger')
                    return redirect(url_for('settings'))
            except Exception as e:
                logging.error(f"Erro ao atualizar status do bot: {str(e)}")
                flash(f'Erro ao atualizar status do bot: {str(e)}', 'danger')
                return redirect(url_for('settings'))
            
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
        
        # Registra o tempo de processamento
        end_time = datetime.now()
        time_diff = (end_time - start_time).total_seconds()
        logging.info(f"Tempo para processar página de configurações: {time_diff} segundos")
        
        # Verifica se o módulo telegram está disponível
        telegram_warning = not TELEGRAM_AVAILABLE
        
        # Renderiza a página com os dados mínimos necessários
        return render_template('settings.html', config=config, telegram_warning=telegram_warning)
    except Exception as e:
        logging.error(f"Erro ao renderizar página de configurações: {str(e)}")
        flash(f'Erro ao carregar configurações: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/logs')
@login_required
def logs():
    global bot_handler, scheduler
    
    # Lê os últimos 100 logs
    logs = []
    try:
        with open('bot_admin.log', 'r') as log_file:
            logs = log_file.readlines()[-100:]
    except Exception as e:
        logging.error(f"Erro ao ler logs: {str(e)}")
        flash(f'Erro ao ler logs: {str(e)}', 'danger')
    
    # Diagnóstico básico
    diagnostic = {}
    
    # Verifica se o token está configurado
    config = data_manager.get_bot_config()
    diagnostic['token_configured'] = bool(config.get('token', ''))
    diagnostic['group_configured'] = bool(config.get('group_id', ''))
    
    # Verifica se o bot está online
    diagnostic['bot_online'] = False
    if bot_handler:
        try:
            diagnostic['bot_online'] = bot_handler.is_running()
        except Exception as e:
            logging.error(f"Erro ao verificar status do bot: {str(e)}")
    
    # Verifica se há posts promocionais configurados
    posts = data_manager.get_promotional_posts()
    diagnostic['posts_configured'] = len(posts) > 0
    
    # Verifica se há mensagem de boas-vindas configurada
    welcome_config = data_manager.get_welcome_config()
    diagnostic['welcome_configured'] = bool(welcome_config.get('message', ''))
    
    # Verifica se o módulo telegram está disponível
    telegram_warning = not TELEGRAM_AVAILABLE
    
    # Adiciona informação de módulos disponíveis ao diagnóstico
    diagnostic['telegram_module'] = TELEGRAM_AVAILABLE
    
    return render_template('logs.html', logs=logs, diagnostic=diagnostic, telegram_warning=telegram_warning)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
