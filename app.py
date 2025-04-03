import logging
import os
import json
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort

# Configuração de logs
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.StreamHandler(),
                       logging.FileHandler('app.log')
                   ])
logger = logging.getLogger(__name__)

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sua_chave_secreta_aqui")

try:
    from bot_handler_new import TelegramBotHandler
    from data_manager import DataManager
    from scheduler import MessageScheduler

    # Inicialização dos componentes
    data_manager = DataManager()
    data_manager.init()

    # Verificar se existe um token nos env vars e usar como padrão se não existir no data_manager
    env_token = os.environ.get("TELEGRAM_TOKEN", "")
    if env_token and not data_manager.get_telegram_token():
        data_manager.set_telegram_token(env_token)

    # Verificar se existe um group_id nos env vars e usar como padrão se não existir no data_manager
    env_group_id = os.environ.get("GROUP_ID", "")
    if env_group_id and not data_manager.get_group_id():
        data_manager.set_group_id(env_group_id)

    # Inicializa o bot com os valores do data_manager
    token = data_manager.get_telegram_token()
    group_id = data_manager.get_group_id()

    bot_handler = None
    scheduler = None

    if token and group_id:
        try:
            bot_handler = TelegramBotHandler(token, group_id, data_manager)
            bot_handler.setup()
            
            scheduler = MessageScheduler(bot_handler, data_manager)
            scheduler.start()
        except Exception as e:
            logger.error(f"Erro ao inicializar bot ou agendador: {str(e)}")
    else:
        logger.warning("Token ou ID do grupo não configurados. O bot não será inicializado.")
except Exception as e:
    logger.error(f"Erro durante a inicialização da aplicação: {str(e)}")
    data_manager = None
    bot_handler = None
    scheduler = None

@app.route('/')
def index():
    """Página principal do painel administrativo."""
    try:
        if not data_manager:
            flash("Erro no sistema de gerenciamento de dados. Entre em contato com o suporte.", "danger")
            return render_template('error.html', error="Sistema de gerenciamento de dados não disponível"), 500
        
        promo_posts = []
        try:
            promo_posts = data_manager.get_promo_posts() or []
            
            # Ordenar posts do mais recente para o mais antigo
            if promo_posts:
                promo_posts = sorted(promo_posts, key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Erro ao obter posts promocionais: {str(e)}")
            flash(f'Erro ao carregar posts promocionais: {str(e)}', 'danger')
        
        bot_active = False
        try:
            bot_active = data_manager.get_bot_status()
        except Exception as e:
            logger.error(f"Erro ao obter status do bot: {str(e)}")
            flash(f'Erro ao verificar status do bot: {str(e)}', 'warning')
        
        interval = 10  # Valor padrão
        try:
            interval = data_manager.get_interval()
        except Exception as e:
            logger.error(f"Erro ao obter intervalo: {str(e)}")
            flash(f'Erro ao carregar intervalo de posts: {str(e)}', 'warning')
        
        return render_template('index.html', 
                              promo_posts=promo_posts[:3], 
                              bot_active=bot_active,
                              post_count=len(promo_posts),
                              interval=interval)
    except Exception as e:
        logger.error(f"Erro não tratado na rota /: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    """Página de configuração da mensagem de boas-vindas."""
    try:
        if not data_manager:
            flash("Erro no sistema de gerenciamento de dados. Entre em contato com o suporte.", "danger")
            return render_template('error.html', error="Sistema de gerenciamento de dados não disponível"), 500
        
        if request.method == 'POST':
            try:
                welcome_message = request.form.get('welcome_message', '')
                success = data_manager.save_welcome_message(welcome_message)
                if success:
                    flash('Mensagem de boas-vindas atualizada com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar mensagem de boas-vindas. Verifique os logs.', 'danger')
            except Exception as e:
                logger.error(f"Erro ao salvar mensagem de boas-vindas: {str(e)}")
                flash(f'Erro ao atualizar mensagem: {str(e)}', 'danger')
            
            return redirect(url_for('welcome'))
        
        welcome_message = ""
        try:
            welcome_message = data_manager.get_welcome_message()
        except Exception as e:
            logger.error(f"Erro ao obter mensagem de boas-vindas: {str(e)}")
            flash(f'Erro ao carregar mensagem de boas-vindas: {str(e)}', 'danger')
        
        bot_active = False
        try:
            bot_active = data_manager.get_bot_status()
        except Exception as e:
            logger.error(f"Erro ao obter status do bot: {str(e)}")
            flash(f'Erro ao verificar status do bot: {str(e)}', 'warning')
        
        return render_template('welcome.html', 
                              welcome_message=welcome_message,
                              bot_active=bot_active)
    except Exception as e:
        logger.error(f"Erro não tratado na rota /welcome: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/promo', methods=['GET', 'POST'])
def promo():
    """Página de gerenciamento de posts promocionais."""
    try:
        if not data_manager:
            flash("Erro no sistema de gerenciamento de dados. Entre em contato com o suporte.", "danger")
            return render_template('error.html', error="Sistema de gerenciamento de dados não disponível"), 500
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add':
                text = request.form.get('text', '')
                image_url = request.form.get('image_url', '')
                external_link = request.form.get('external_link', '')
                
                if text:
                    try:
                        success = data_manager.add_promo_post(text, image_url, external_link)
                        if success:
                            flash('Post promocional adicionado com sucesso!', 'success')
                        else:
                            flash('Erro ao adicionar post promocional. Verifique os logs.', 'danger')
                    except Exception as e:
                        logger.error(f"Erro ao adicionar post promocional: {str(e)}")
                        flash(f'Erro ao adicionar post: {str(e)}', 'danger')
                else:
                    flash('O texto do post não pode estar vazio!', 'danger')
            
            elif action == 'edit':
                post_id = request.form.get('id')
                text = request.form.get('text', '')
                image_url = request.form.get('image_url', '')
                external_link = request.form.get('external_link', '')
                
                if text and post_id:
                    try:
                        success = data_manager.update_promo_post(post_id, text, image_url, external_link)
                        if success:
                            flash('Post promocional atualizado com sucesso!', 'success')
                        else:
                            flash('Erro ao atualizar post promocional. Verifique os logs.', 'danger')
                    except Exception as e:
                        logger.error(f"Erro ao atualizar post promocional: {str(e)}")
                        flash(f'Erro ao atualizar post: {str(e)}', 'danger')
                else:
                    flash('ID do post ou texto inválido!', 'danger')
            
            elif action == 'delete':
                post_id = request.form.get('id')
                
                if post_id:
                    try:
                        success = data_manager.delete_promo_post(post_id)
                        if success:
                            flash('Post promocional excluído com sucesso!', 'success')
                        else:
                            flash('Erro ao excluir post promocional. Verifique os logs.', 'danger')
                    except Exception as e:
                        logger.error(f"Erro ao excluir post promocional: {str(e)}")
                        flash(f'Erro ao excluir post: {str(e)}', 'danger')
                else:
                    flash('ID do post inválido!', 'danger')
            
            return redirect(url_for('promo'))
        
        # Para requisições GET
        promo_posts = []
        try:
            promo_posts = data_manager.get_promo_posts() or []
            
            # Ordenar posts do mais recente para o mais antigo
            if promo_posts:
                promo_posts = sorted(promo_posts, key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Erro ao obter posts promocionais: {str(e)}")
            flash(f'Erro ao carregar posts: {str(e)}', 'danger')
        
        bot_active = False
        try:
            bot_active = data_manager.get_bot_status()
        except Exception as e:
            logger.error(f"Erro ao obter status do bot: {str(e)}")
            flash(f'Erro ao verificar status do bot: {str(e)}', 'warning')
        
        return render_template('promo.html', 
                              promo_posts=promo_posts,
                              bot_active=bot_active)
    except Exception as e:
        # Log do erro geral
        logger.error(f"Erro não tratado na rota /promo: {str(e)}")
        flash(f'Ocorreu um erro: {str(e)}', 'danger')
        # Retornar uma página de erro em vez de uma tela branca
        return render_template('error.html', error=str(e)), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Página de configurações do bot."""
    try:
        if not data_manager:
            flash("Erro no sistema de gerenciamento de dados. Entre em contato com o suporte.", "danger")
            return render_template('error.html', error="Sistema de gerenciamento de dados não disponível"), 500
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'toggle_status':
                try:
                    current_status = data_manager.get_bot_status()
                    success = data_manager.set_bot_status(not current_status)
                    
                    if success:
                        status_text = "ativado" if not current_status else "desativado"
                        flash(f'Bot {status_text} com sucesso!', 'success')
                    else:
                        flash('Erro ao alterar status do bot. Verifique os logs.', 'danger')
                except Exception as e:
                    logger.error(f"Erro ao alterar status do bot: {str(e)}")
                    flash(f'Erro ao alterar status: {str(e)}', 'danger')
            
            elif action == 'update_interval':
                try:
                    interval = int(request.form.get('interval', 10))
                    if interval < 1:
                        interval = 1
                        
                    success = data_manager.set_interval(interval)
                    
                    if success:
                        try:
                            if scheduler:
                                scheduler.update_interval(interval)
                        except Exception as e:
                            logger.error(f"Erro ao atualizar intervalo no agendador: {str(e)}")
                            # Não mostrar erro ao usuário pois a configuração foi salva
                        
                        flash(f'Intervalo atualizado para {interval} minutos!', 'success')
                    else:
                        flash('Erro ao atualizar intervalo. Verifique os logs.', 'danger')
                except ValueError:
                    flash('Intervalo inválido! Use apenas números.', 'danger')
                except Exception as e:
                    logger.error(f"Erro ao atualizar intervalo: {str(e)}")
                    flash(f'Erro ao atualizar intervalo: {str(e)}', 'danger')
            
            return redirect(url_for('settings'))
        
        # Para requisições GET
        bot_active = False
        try:
            bot_active = data_manager.get_bot_status()
        except Exception as e:
            logger.error(f"Erro ao obter status do bot: {str(e)}")
            flash(f'Erro ao verificar status do bot: {str(e)}', 'warning')
        
        interval = 10  # Valor padrão
        try:
            interval = data_manager.get_interval()
        except Exception as e:
            logger.error(f"Erro ao obter intervalo: {str(e)}")
            flash(f'Erro ao carregar intervalo: {str(e)}', 'warning')
        
        return render_template('settings.html', 
                              bot_active=bot_active,
                              interval=interval)
    except Exception as e:
        logger.error(f"Erro não tratado na rota /settings: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/bot_config', methods=['GET', 'POST'])
def bot_config():
    """Página de configuração do bot."""
    try:
        if not data_manager:
            flash("Erro no sistema de gerenciamento de dados. Entre em contato com o suporte.", "danger")
            return render_template('error.html', error="Sistema de gerenciamento de dados não disponível"), 500
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'update_credentials':
                token = request.form.get('token', '')
                group_id = request.form.get('group_id', '')
                
                try:
                    old_token = data_manager.get_telegram_token()
                    old_group_id = data_manager.get_group_id()
                    
                    token_success = data_manager.set_telegram_token(token)
                    group_success = data_manager.set_group_id(group_id)
                    
                    if not token_success or not group_success:
                        flash('Erro ao salvar credenciais. Verifique os logs.', 'danger')
                        return redirect(url_for('bot_config'))
                    
                    # Se as credenciais mudaram, reinicia o bot
                    if token != old_token or group_id != old_group_id:
                        try:
                            # Para o bot e o agendador existentes
                            if scheduler:
                                scheduler.stop()
                            if bot_handler:
                                bot_handler.stop()
                            
                            global bot_handler, scheduler
                            
                            # Reinicia com as novas credenciais
                            if token and group_id:
                                bot_handler = TelegramBotHandler(token, group_id, data_manager)
                                bot_handler.setup()
                                
                                scheduler = MessageScheduler(bot_handler, data_manager)
                                scheduler.start()
                                
                                flash('Credenciais do bot atualizadas e bot reiniciado!', 'success')
                            else:
                                flash('Credenciais atualizadas, mas bot não iniciado devido a credenciais vazias.', 'warning')
                        except Exception as e:
                            logger.error(f"Erro ao reiniciar bot com novas credenciais: {str(e)}")
                            flash(f'Erro ao reiniciar bot: {str(e)}', 'danger')
                    else:
                        flash('Credenciais do bot atualizadas!', 'success')
                except Exception as e:
                    logger.error(f"Erro ao atualizar credenciais do bot: {str(e)}")
                    flash(f'Erro ao atualizar credenciais: {str(e)}', 'danger')
            
            return redirect(url_for('bot_config'))
        
        # Para requisições GET
        token = ""
        try:
            token = data_manager.get_telegram_token()
        except Exception as e:
            logger.error(f"Erro ao obter token do Telegram: {str(e)}")
            flash(f'Erro ao carregar token: {str(e)}', 'warning')
        
        group_id = ""
        try:
            group_id = data_manager.get_group_id()
        except Exception as e:
            logger.error(f"Erro ao obter ID do grupo: {str(e)}")
            flash(f'Erro ao carregar ID do grupo: {str(e)}', 'warning')
        
        bot_active = False
        try:
            bot_active = data_manager.get_bot_status()
        except Exception as e:
            logger.error(f"Erro ao obter status do bot: {str(e)}")
            flash(f'Erro ao verificar status do bot: {str(e)}', 'warning')
        
        return render_template('bot_config.html', 
                              token=token,
                              group_id=group_id,
                              bot_active=bot_active)
    except Exception as e:
        logger.error(f"Erro não tratado na rota /bot_config: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/toggle_bot', methods=['POST'])
def toggle_bot():
    """Endpoint para ativar/desativar o bot."""
    try:
        if not data_manager:
            return jsonify({'success': False, 'message': 'Sistema de gerenciamento de dados não disponível'})
        
        current_status = data_manager.get_bot_status()
        new_status = not current_status
        
        # Tentar alterar o status
        try:
            success = data_manager.set_bot_status(new_status)
            
            if not success:
                return jsonify({
                    'success': False,
                    'message': 'Erro ao alterar status do bot'
                })
                
            # Se o novo status for ativo, tentar iniciar o bot e o agendador
            if new_status:
                if bot_handler and scheduler:
                    # Iniciar bot e agendador
                    try:
                        bot_handler.setup()
                        scheduler.start()
                    except Exception as e:
                        logger.error(f"Erro ao iniciar bot/agendador: {str(e)}")
                        # Não retornar erro aqui, pois o status foi alterado com sucesso
            else:
                # Se o novo status for inativo, tentar parar o bot e o agendador
                if scheduler:
                    try:
                        scheduler.stop()
                    except Exception as e:
                        logger.error(f"Erro ao parar agendador: {str(e)}")
                
                if bot_handler:
                    try:
                        bot_handler.stop()
                    except Exception as e:
                        logger.error(f"Erro ao parar bot: {str(e)}")
            
            logger.info(f"Status do bot alterado para: {'Ativo' if new_status else 'Inativo'}")
            
            return jsonify({
                'success': True,
                'active': new_status,
                'message': f'Bot {"ativado" if new_status else "desativado"} com sucesso'
            })
        except Exception as e:
            logger.error(f"Erro ao alterar status do bot: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao alterar status: {str(e)}'
            })
    except Exception as e:
        logger.error(f"Erro não tratado ao alterar status do bot: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })

@app.route('/diagnostics')
def diagnostics():
    """Exibe informações de diagnóstico do sistema."""
    try:
        # Inicializar dicionário de diagnóstico
        diag = {
            'bot_status': {
                'configured': False,
                'token_set': False,
                'group_id_set': False,
                'active': False,
                'handler_created': False,
                'scheduler_running': False
            },
            'posts': {
                'count': 0,
                'latest': None
            },
            'welcome': {
                'message_set': False
            },
            'system': {
                'data_dir_exists': False,
                'data_files_ok': False
            },
            'logs': []
        }
        
        # Verificar diretório de dados
        if data_manager:
            diag['system']['data_dir_exists'] = os.path.exists(data_manager.data_dir)
            
            # Verificar arquivos de dados
            config_ok = os.path.exists(data_manager.config_file)
            welcome_ok = os.path.exists(data_manager.welcome_file)
            posts_ok = os.path.exists(data_manager.promo_posts_file)
            
            diag['system']['data_files_ok'] = config_ok and welcome_ok and posts_ok
            
            # Status do bot
            try:
                diag['bot_status']['token_set'] = bool(data_manager.get_telegram_token())
                diag['bot_status']['group_id_set'] = bool(data_manager.get_group_id())
                diag['bot_status']['active'] = data_manager.get_bot_status()
                diag['bot_status']['configured'] = diag['bot_status']['token_set'] and diag['bot_status']['group_id_set']
            except Exception as e:
                logger.error(f"Erro ao verificar status do bot para diagnóstico: {str(e)}")
            
            # Status do manipulador e agendador
            diag['bot_status']['handler_created'] = bot_handler is not None
            diag['bot_status']['scheduler_running'] = scheduler is not None and getattr(scheduler, 'is_running', lambda: False)()
            
            # Informações sobre posts
            try:
                posts = data_manager.get_promo_posts() or []
                diag['posts']['count'] = len(posts)
                
                if posts:
                    # Ordenar por data de criação, mais recente primeiro
                    sorted_posts = sorted(posts, key=lambda x: x.get('created_at', ''), reverse=True)
                    latest = sorted_posts[0]
                    diag['posts']['latest'] = {
                        'id': latest.get('id', ''),
                        'text': latest.get('text', '')[:50] + ('...' if len(latest.get('text', '')) > 50 else ''),
                        'created_at': latest.get('created_at', '')
                    }
            except Exception as e:
                logger.error(f"Erro ao verificar posts para diagnóstico: {str(e)}")
            
            # Informações sobre mensagem de boas-vindas
            try:
                welcome_message = data_manager.get_welcome_message()
                diag['welcome']['message_set'] = bool(welcome_message)
            except Exception as e:
                logger.error(f"Erro ao verificar mensagem de boas-vindas para diagnóstico: {str(e)}")
        
        # Ler logs (últimas 50 linhas)
        log_file = 'app.log'  # Ajuste para o nome correto do seu arquivo de log
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    diag['logs'] = lines[-50:]  # Últimas 50 linhas
        except Exception as e:
            logger.error(f"Erro ao ler arquivo de log: {str(e)}")
            diag['logs'] = [f"Erro ao ler logs: {str(e)}"]
        
        return render_template('diagnostics.html', diag=diag)
    except Exception as e:
        logger.error(f"Erro ao gerar diagnóstico: {str(e)}")
        return render_template('error.html', error=f"Erro ao gerar diagnóstico: {str(e)}"), 500

@app.route('/api/status')
def get_status():
    """Endpoint da API para obter o status atual do bot."""
    try:
        if not data_manager:
            return jsonify({
                'error': 'Sistema de gerenciamento de dados não disponível',
                'active': False,
                'interval': 0
            }), 500
        
        active = False
        try:
            active = data_manager.get_bot_status()
        except Exception as e:
            logger.error(f"Erro ao obter status do bot: {str(e)}")
        
        interval = 10
        try:
            interval = data_manager.get_interval()
        except Exception as e:
            logger.error(f"Erro ao obter intervalo: {str(e)}")
        
        return jsonify({
            'active': active,
            'interval': interval
        })
    except Exception as e:
        logger.error(f"Erro não tratado na rota /api/status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test_send', methods=['GET'])
def test_send():
    """Endpoint para testar o envio de mensagens."""
    try:
        if not data_manager:
            flash("Erro no sistema de gerenciamento de dados. Entre em contato com o suporte.", "danger")
            return redirect(url_for('index'))
        
        if not bot_handler:
            flash("Bot não inicializado. Configure o token e ID do grupo primeiro.", "danger")
            return redirect(url_for('bot_config'))
            
        try:
            success = bot_handler.send_message("Teste de mensagem do painel administrativo!")
            if success:
                flash("Mensagem de teste enviada com sucesso!", "success")
            else:
                flash("Falha ao enviar mensagem de teste. Verifique os logs.", "danger")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de teste: {str(e)}")
            flash(f"Erro ao enviar mensagem: {str(e)}", "danger")
        
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Erro não tratado na rota /test_send: {str(e)}")
        flash(f"Erro: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """Manipulador para página não encontrada."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Manipulador para erro interno do servidor."""
    logger.error(f"Erro 500: {str(e)}")
    return render_template('500.html'), 500

# Limpar recursos ao encerrar a aplicação
import atexit

def cleanup():
    """Função para limpar recursos ao encerrar a aplicação."""
    logger.info("Encerrando aplicação e limpando recursos...")
    try:
        if scheduler:
            scheduler.stop()
        if bot_handler:
            bot_handler.stop()
    except Exception as e:
        logger.error(f"Erro ao limpar recursos: {str(e)}")

atexit.register(cleanup)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
