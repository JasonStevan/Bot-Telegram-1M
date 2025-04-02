import os
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import User, PromotionalPost, WelcomeConfig, BotConfig, Stats
from auth import authenticate_user, create_default_user
from data_manager import DataManager
from bot_handler import TelegramBotHandler
from scheduler import PostScheduler

# Configuração do logging
logging.basicConfig(
    filename='bot_admin.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "sua_chave_secreta_aqui")

# Inicialização do gerenciador de dados
data_manager = DataManager()

# Variáveis globais para instâncias do bot e do agendador
bot_handler = None
scheduler = None

# Função para inicializar o bot
def initialize_bot(force_restart=False):
    global bot_handler, scheduler
    
    # Obtém a configuração atual do bot
    config = data_manager.get_bot_config()
    token = config.get('token')
    group_id = config.get('group_id')
    active = config.get('active', False)
    
    # Verifica se tem configurações básicas
    if not token or not group_id:
        logging.warning("Bot não inicializado: token ou ID do grupo não configurados")
        return False
    
    try:
        # Se já existe uma instância ativa e não é um reinício forçado, retorna
        if bot_handler and bot_handler.is_running() and not force_restart:
            logging.info("Bot já está em execução")
            return True
        
        # Se estiver rodando e for um reinício forçado, desliga primeiro
        if bot_handler and bot_handler.is_running():
            logging.info("Desligando instância atual do bot para reinício forçado")
            if scheduler and scheduler.is_running():
                scheduler.stop()
            bot_handler.stop()
        
        # Cria uma nova instância
        new_bot_handler = TelegramBotHandler(token, group_id, data_manager)
        
        # Inicia o bot se 'active' for True
        if active:
            if new_bot_handler.start():
                # Atualiza a variável global
                bot_handler = new_bot_handler
                
                # Inicia o agendador se o bot foi iniciado com sucesso
                new_scheduler = PostScheduler(bot_handler, data_manager)
                if new_scheduler.start():
                    # Atualiza a variável global do agendador
                    scheduler = new_scheduler
                    # Atualiza o horário de reinício
                    data_manager.update_restart_time()
                    logging.info(f"Bot iniciado automaticamente: configuração 'active' = {active}")
                    return True
                else:
                    logging.error("Falha ao iniciar o agendador de posts")
                    bot_handler.stop()
                    return False
            else:
                logging.error("Falha ao iniciar o bot")
                return False
        else:
            # Apenas atualiza a variável global, mas não inicia o bot
            bot_handler = new_bot_handler
            logging.info(f"Bot inicializado mas não ativado: configuração 'active' = {active}")
            return True
    except Exception as e:
        logging.error(f"Erro ao inicializar bot: {str(e)}")
        return False

# Decorator para verificar autenticação
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Cria usuário padrão se não existir
create_default_user()

# Inicializa o bot na inicialização da aplicação
initialize_bot()

# Rota para login
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if authenticate_user(username, password):
            session['user'] = username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Credenciais inválidas. Tente novamente.'
    
    return render_template('login.html', error=error)

# Rota para logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

# Rota para o dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Obtém estatísticas
    stats = {}
    if bot_handler:
        stats = bot_handler.get_stats()
    
    # Obtém a configuração atual
    config = data_manager.get_bot_config()
    
    # Formata o horário do último reinício
    last_restarted = stats.get('last_restarted')
    if last_restarted:
        try:
            # Converte para datetime se for string
            if isinstance(last_restarted, str):
                last_restarted = datetime.datetime.strptime(last_restarted, "%Y-%m-%d %H:%M:%S")
            
            # Formata para exibição
            stats['last_restarted_formatted'] = last_restarted.strftime("%d/%m/%Y %H:%M:%S")
        except Exception as e:
            logging.error(f"Erro ao formatar data do último reinício: {str(e)}")
            stats['last_restarted_formatted'] = "Data desconhecida"
    else:
        stats['last_restarted_formatted'] = "Nunca reiniciado"
    
    # Adiciona a configuração atual às estatísticas
    stats['token'] = config.get('token', '')
    stats['group_id'] = config.get('group_id', '')
    stats['interval'] = config.get('interval', 10)
    stats['active'] = config.get('active', False)
    
    return render_template('dashboard.html', stats=stats)

# Rota para posts promocionais
@app.route('/promotional-posts', methods=['GET', 'POST'])
@login_required
def promotional_posts():
    if request.method == 'POST':
        # Verifica a ação
        action = request.form.get('action')
        
        if action == 'add':
            # Adiciona um novo post
            title = request.form.get('title')
            content = request.form.get('content')
            image_url = request.form.get('image_url', '')
            external_link = request.form.get('external_link', '')
            
            if title and content:
                data_manager.add_promotional_post(title, content, image_url, external_link)
                flash('Post promocional adicionado com sucesso!', 'success')
            else:
                flash('Título e conteúdo são obrigatórios!', 'danger')
        
        elif action == 'edit':
            # Edita um post existente
            post_id = request.form.get('post_id')
            title = request.form.get('title')
            content = request.form.get('content')
            image_url = request.form.get('image_url', '')
            external_link = request.form.get('external_link', '')
            
            if post_id and title and content:
                data_manager.update_promotional_post(post_id, title, content, image_url, external_link)
                flash('Post promocional atualizado com sucesso!', 'success')
            else:
                flash('ID, título e conteúdo são obrigatórios!', 'danger')
        
        elif action == 'delete':
            # Exclui um post
            post_id = request.form.get('post_id')
            
            if post_id:
                data_manager.delete_promotional_post(post_id)
                flash('Post promocional excluído com sucesso!', 'success')
            else:
                flash('ID do post é obrigatório!', 'danger')
        
        elif action == 'test':
            # Testa envio de post específico
            post_id = request.form.get('post_id')
            
            if not bot_handler or not bot_handler.is_running():
                flash('Bot não está ativo! Ative-o primeiro no dashboard.', 'warning')
                return redirect(url_for('promotional_posts'))
            
            if post_id:
                post = data_manager.get_promotional_post(post_id)
                if post:
                    if bot_handler.send_promotional_post(post):
                        flash('Post de teste enviado com sucesso!', 'success')
                    else:
                        flash('Erro ao enviar post de teste!', 'danger')
                else:
                    flash('Post não encontrado!', 'danger')
            else:
                flash('ID do post é obrigatório!', 'danger')
    
    # Obtém todos os posts para exibição
    posts = data_manager.get_promotional_posts()
    
    return render_template('promotional_posts.html', posts=posts)

# Rota para mensagens de boas-vindas
@app.route('/welcome-messages', methods=['GET', 'POST'])
@login_required
def welcome_messages():
    if request.method == 'POST':
        # Atualiza configuração de boas-vindas
        welcome_message = request.form.get('welcome_message')
        enabled = 'enabled' in request.form  # Checkbox marcado
        
        if welcome_message is not None:
            data_manager.update_welcome_config(welcome_message, enabled)
            flash('Configuração de boas-vindas atualizada com sucesso!', 'success')
        
        # Verifica se é um teste
        if 'test' in request.form:
            if not bot_handler or not bot_handler.is_running():
                flash('Bot não está ativo! Ative-o primeiro no dashboard.', 'warning')
                return redirect(url_for('welcome_messages'))
            
            if bot_handler.test_welcome_message():
                flash('Mensagem de boas-vindas de teste enviada com sucesso!', 'success')
            else:
                flash('Erro ao enviar mensagem de boas-vindas de teste!', 'danger')
    
    # Obtém configuração atual
    welcome_config = data_manager.get_welcome_config()
    
    return render_template('welcome_messages.html', welcome_config=welcome_config)

# Rota para configurações do bot
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        token = request.form.get('token')
        group_id = request.form.get('group_id')
        interval = request.form.get('interval')
        
        try:
            interval = int(interval) if interval else 10
        except ValueError:
            interval = 10
            flash('Intervalo inválido, usando padrão de 10 minutos.', 'warning')
        
        if token and group_id:
            data_manager.update_bot_config(token, group_id, interval)
            flash('Configurações do bot atualizadas com sucesso!', 'success')
            
            # Reinicia o bot com as novas configurações
            if initialize_bot(force_restart=True):
                flash('Bot reiniciado com as novas configurações!', 'success')
            else:
                flash('Erro ao reiniciar o bot. Verifique os logs.', 'danger')
        else:
            flash('Token e ID do grupo são obrigatórios!', 'danger')
    
    # Obtém configuração atual
    config = data_manager.get_bot_config()
    
    return render_template('settings.html', config=config)

# Rota para alternar status do bot (ativado/desativado)
@app.route('/toggle-bot', methods=['POST'])
@login_required
def toggle_bot():
    global bot_handler, scheduler
    
    try:
        status = request.json.get('status')
        config = data_manager.get_bot_config()
        
        # Atualiza o status na configuração
        data_manager.update_bot_status(status)
        
        if status:
            # Ativa o bot
            if bot_handler and not bot_handler.is_running():
                if bot_handler.start():
                    # Inicia o agendador
                    if scheduler:
                        if not scheduler.is_running():
                            scheduler.start()
                    else:
                        scheduler = PostScheduler(bot_handler, data_manager)
                        scheduler.start()
                    
                    # Atualiza horário de reinício
                    data_manager.update_restart_time()
                    return jsonify({'success': True, 'message': 'Bot ativado com sucesso!'})
                else:
                    return jsonify({'success': False, 'message': 'Falha ao ativar o bot!'})
            elif not bot_handler:
                # Bot não inicializado ainda, tenta inicializar
                if initialize_bot():
                    return jsonify({'success': True, 'message': 'Bot ativado com sucesso!'})
                else:
                    return jsonify({'success': False, 'message': 'Falha ao inicializar o bot! Verifique as configurações.'})
            else:
                # Bot já está rodando
                return jsonify({'success': True, 'message': 'Bot já está ativo!'})
        else:
            # Desativa o bot
            if bot_handler and bot_handler.is_running():
                # Para o agendador primeiro
                if scheduler and scheduler.is_running():
                    scheduler.stop()
                
                # Depois para o bot
                if bot_handler.stop():
                    return jsonify({'success': True, 'message': 'Bot desativado com sucesso!'})
                else:
                    return jsonify({'success': False, 'message': 'Falha ao desativar o bot!'})
            else:
                # Bot já está parado
                return jsonify({'success': True, 'message': 'Bot já está inativo!'})
    except Exception as e:
        logging.error(f"Erro ao alternar status do bot: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

# Rota para logs
@app.route('/logs')
@login_required
def logs():
    try:
        with open('bot_admin.log', 'r') as f:
            log_content = f.readlines()
            
        # Pega as últimas 100 linhas
        log_content = log_content[-100:]
        
        return render_template('logs.html', logs=log_content)
    except Exception as e:
        flash(f'Erro ao ler logs: {str(e)}', 'danger')
        return render_template('logs.html', logs=[])
