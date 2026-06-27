import subprocess
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

subprocess.Popen(
    [r"venv\Scripts\python.exe", "manage.py", "runserver"],
    cwd=BASE_DIR
)

time.sleep(5)

os.system("start http://127.0.0.1:8000")