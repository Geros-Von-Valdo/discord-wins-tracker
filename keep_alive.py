from flask import Flask
from threading import Thread

app = Flask("")

@app.route('/')
def home():
    return "Servidor do Bot está rodando!"

def run():
    # Roda o Flask na porta 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # Inicia a thread em background
    t = Thread(target=run)
    t.start()