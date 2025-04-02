import os
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

def hash_password(password):
    """Cria um hash da senha usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_default_user():
    """Cria um usuário padrão se o arquivo de usuários não existir"""
    users_file = 'data/users.json'
    
    # Cria diretório de dados se não existir
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Verifica se o arquivo de usuários existe e tem algum usuário
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
                if users:
                    logger.info("Usuários já existem no sistema")
                    return
        except Exception as e:
            logger.error(f"Erro ao verificar usuários existentes: {str(e)}")
    
    try:
        # Cria um usuário padrão
        default_user = {
            'username': 'admin',
            'password_hash': hash_password('admin123')
        }
        
        # Salva o usuário no arquivo
        with open(users_file, 'w') as f:
            json.dump([default_user], f, indent=4)
        
        logger.info("Usuário padrão criado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar usuário padrão: {str(e)}")

def authenticate_user(username, password):
    """Autentica um usuário"""
    users_file = 'data/users.json'
    
    if not os.path.exists(users_file):
        logger.error("Arquivo de usuários não encontrado")
        return False
    
    try:
        with open(users_file, 'r') as f:
            users = json.load(f)
        
        password_hash = hash_password(password)
        
        for user in users:
            if user.get('username') == username and user.get('password_hash') == password_hash:
                logger.info(f"Usuário autenticado com sucesso: {username}")
                return True
        
        logger.warning(f"Tentativa de autenticação falhou para o usuário: {username}")
        return False
    except Exception as e:
        logger.error(f"Erro ao autenticar usuário: {str(e)}")
        return False

def check_auth(username, password):
    """Verifica se as credenciais são válidas"""
    return authenticate_user(username, password)
