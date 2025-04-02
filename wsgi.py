"""
Arquivo de configuração WSGI para o PythonAnywhere
Este arquivo permite que o PythonAnywhere execute a aplicação Flask
"""
import sys
import os

# Adicione o caminho do seu projeto ao path do Python
# Este caminho deve apontar para a pasta raiz do seu projeto
path = '/home/TheBlackWolf/mysite'
if path not in sys.path:
    sys.path.append(path)

# Certifique-se de que os diretórios necessários existam
# Isso evita erros quando a aplicação tenta acessar esses diretórios
for directory in ['data', 'static', 'templates']:
    dir_path = os.path.join(path, directory)
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except Exception:
            pass  # Ignora erros, aplicação lidará com isso

# Configura o logging para capturar erros de inicialização
import logging
log_path = os.path.join(path, 'wsgi_startup.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    # Importa a aplicação Flask como 'application'
    # Isso é o que o servidor WSGI espera encontrar
    from app import app as application
    logging.info("Aplicação Flask carregada com sucesso")
except Exception as e:
    logging.error(f"Erro ao carregar a aplicação Flask: {str(e)}")
    # Re-lança a exceção para que o servidor WSGI possa reportá-la
    raise
