from flask import Flask, request, render_template
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

def generate_key():
    segment1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    segment2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"LP-{segment1}-{segment2}"

@app.route('/', methods=['GET', 'POST'])
def index():
    new_key = None
    
    if request.method == 'POST':
        webhook_url = request.form.get('webhook')
        # Validação simples
        if webhook_url and "http" in webhook_url:
            key = generate_key()
            
            # Salva no banco
            keys_collection.insert_one({
                "key": key,
                "webhook": webhook_url
            })
            new_key = key
    
    return render_template('index.html', key=new_key)

# API QUE O SCRIPT LUA USA (NÃO APAGUE)
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
