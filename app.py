from flask import Flask, request, render_template, redirect, url_for
from pymongo import MongoClient
import random
import string
import os
import requests

app = Flask(__name__)

# CONFIGURAÇÃO DO MONGODB
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['Scriptkey']
keys_collection = db.keys
ips_collection = db.verified_ips  # Nova coleção para salvar os IPs

# Função para pegar o IP real (mesmo usando Render/Proxy)
def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    return request.remote_addr

def generate_key():
    segment1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    segment2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"LP-{segment1}-{segment2}"

@app.route('/', methods=['GET', 'POST'])
def index():
    user_ip = get_client_ip()
    
    # Verifica se o IP já está salvo no banco
    is_verified = ips_collection.find_one({"ip": user_ip}) is not None

    new_key = None
    
    if request.method == 'POST':
        # Segurança extra: se tentar burlar o HTML e postar sem verificar
        if not is_verified:
            return "Verificação Necessária", 403

        webhook_url = request.form.get('webhook')
        if webhook_url and "http" in webhook_url:
            key = generate_key()
            keys_collection.insert_one({
                "key": key,
                "webhook": webhook_url,
                "created_by": user_ip
            })
            new_key = key
    
    # Envia a variável 'is_verified' para o HTML decidir o que mostrar
    return render_template('index.html', key=new_key, is_verified=is_verified)

# ROTA DE SUCESSO (Onde o bot manda o usuário de volta)
@app.route('/sucess')
def sucess_route():
    user_ip = get_client_ip()
    
    # Salva o IP no banco de dados (upsert=True evita duplicatas)
    ips_collection.update_one(
        {"ip": user_ip}, 
        {"$set": {"ip": user_ip, "status": "verified"}}, 
        upsert=True
    
    )
    # Redireciona de volta para a home (que agora estará liberada)
    return redirect('/')

# API que o script Lua chama
@app.route('/api/execute', methods=['POST'])
def execute_proxy():
    data = request.json
    if not data: return {"error": "No data"}, 400
        
    user_key = data.get('key')
    payload = data.get('content') 
    
    record = keys_collection.find_one({"key": user_key})
    
    if record:
        try:
            requests.post(record['webhook'], json=payload)
            return {"status": "sent"}
        except:
            return {"error": "Failed to send"}, 500
    else:
        return {"error": "Invalid Key"}, 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
