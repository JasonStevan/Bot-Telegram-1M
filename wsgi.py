import sys
import os

# Adicione o caminho do seu projeto ao path do Python
path = '/home/TheBlackWolf/mysite'
if path not in sys.path:
    sys.path.append(path)

# Importe a aplicação Flask do seu projeto
from app import app as application

# O PythonAnywhere procura por uma variável chamada 'application'
# que aponta para sua aplicação Flask
