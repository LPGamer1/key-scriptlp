from flask import Flask, request, render_template, redirect, session
from pymongo import MongoClient
import random
import string
import os
import requests

app = Flask(__name__)

# CONFIGURAÇÃO DE SEGURANÇA (Necessário para usar Sessões)
# Isso criptografa o cookie do usuário
app.secret_key = os.urandom(24)

# CONFIGURAÇÃO DO MONGODB
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['Scriptkey']
keys_collection = db.keys
# A coleção de IPs continua existindo para log, mas não define mais o acesso
ips_collection = db.verified_ips 

def generate_key():
    segment1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    segment2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"LP-{segment1}-{segment2}"

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    return request.remote_addr

@app.route('/', methods=['GET', 'POST'])
def index():
    # VERIFICAÇÃO POR COOKIE (Sessão)
    # Se o navegador tem o cookie 'verified', ele passa.
    is_verified = session.get('verified', False)

    new_key = None
    
    if request.method == 'POST':
        # Segurança: Se tentar postar sem o cookie, bloqueia
        if not is_verified:
            return "Sessão expirada ou inválida. Verifique novamente.", 403

        webhook_url = request.form.get('webhook')
        if webhook_url and "http" in webhook_url:
            key = generate_key()
            
            # Salva no banco quem criou (IP) para seu controle
            keys_collection.insert_one({
                "key": key,
                "webhook": webhook_url,
                "created_by_ip": get_client_ip()
            })
            new_key = key
    
    return render_template('index.html', key=new_key, is_verified=is_verified)

# ROTA DE SUCESSO
@app.route('/sucess')
def sucess_route():
    # 1. Marca este navegador específico como Verificado
    session['verified'] = True
    
    # 2. (Opcional) Ainda salvamos o IP no banco só para você ter um histórico de quem verificou
    user_ip = get_client_ip()
    ips_collection.update_one(
        {"ip": user_ip}, 
        {"$set": {"ip": user_ip, "status": "verified_log"}}, 
        upsert=True
    )

    # 3. Redireciona para a home
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
