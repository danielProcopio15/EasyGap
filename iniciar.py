import os
import subprocess
import sys

# 1. Descobre automaticamente a pasta onde o iniciar.py está salvo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Descobre o caminho do executável do Python que está rodando este script
python_executavel = sys.executable

# 3. Monta o caminho correto para o arquivo manage.py do Django
manage_py = os.path.join(BASE_DIR, "manage.py")

print(f"Iniciando o servidor Django a partir de: {BASE_DIR}")

# 4. Executa o comando 'python manage.py runserver' de forma segura e dinâmica
try:
    subprocess.Popen([python_executavel, manage_py, "runserver"])
    print("Servidor iniciado com sucesso! Acesse http://127.0.0.1:8000/ no seu navegador.")
except Exception as e:
    print(f"Erro ao tentar iniciar o servidor: {e}")