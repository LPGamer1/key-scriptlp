from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
import random
import string
import os
import requests

app = Flask(__name__)

# Conexão com MongoDB (Pega a URL das variáveis de ambiente do Render)
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
# Conecta ao banco de dados chamado 'Scriptkey'
db = client['Scriptkey']
keys_collection = db.keys

def generate_segment():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

def generate_key():
    # Formato: LP-5M7-10K
    return f"LP-{generate_segment()}-{generate_segment()}"

@app.route('/', methods=['GET', 'POST'])
def index():
    new_key = None
    if request.method == 'POST':
        webhook_url = request.form.get('webhook')
        if webhook_url and "discord" in webhook_url:
            key = generate_key()
            # Salva no banco de dados
            keys_collection.insert_one({
                "key": key,
                "webhook": webhook_url
            })
            new_key = key
    
    return render_template('index.html', key=new_key)

@app.route('/api/execute', methods=['POST'])
def execute_proxy():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
        
    user_key = data.get('key')
    payload = data.get('content') # O conteúdo que o script Roblox enviou
    
    # Procura a Webhook associada à chave
    record = keys_collection.find_one({"key": user_key})
    
    if record:
        webhook_url = record['webhook']
        # Envia para o Discord
        try:
            response = requests.post(webhook_url, json=payload)
            return jsonify({"status": "sent", "discord_code": response.status_code})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Invalid Key"}), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
