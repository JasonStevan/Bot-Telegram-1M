# Este arquivo contém a configuração WSGI para o PythonAnywhere
import sys
import os

# Adicione o caminho do seu projeto ao path do Python
path = '/home/TheBlackWolf/mysite'
if path not in sys.path:
    sys.path.append(path)

# Importe a aplicação Flask do seu projeto
from app import app as application

# Certifique-se de que a pasta de logs existe
log_dir = os.path.join(path, 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# O PythonAnywhere procura por uma variável chamada 'application'
# que aponta para sua aplicação Flask
