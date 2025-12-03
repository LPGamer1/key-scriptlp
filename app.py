from flask import Flask, request, render_template
from pymongo import MongoClient
import random
import string
import os
import requests

app = Flask(__name__)

MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['Scriptkey']
keys_collection = db.keys

def generate_key():
    s1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    s2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"LP-{s1}-{s2}"

@app.route('/', methods=['GET', 'POST'])
def index():
    new_key = None
    if request.method == 'POST':
        webhook = request.form.get('webhook')
        if webhook and "http" in webhook:
            key = generate_key()
            keys_collection.insert_one({"key": key, "webhook": webhook})
            new_key = key
    return render_template('index.html', key=new_key)

@app.route('/api/execute', methods=['POST'])
def execute_proxy():
    data = request.json
    if not data: return {"error": "No data"}, 400
    record = keys_collection.find_one({"key": data.get('key')})
    if record:
        try:
            requests.post(record['webhook'], json=data.get('content'))
            return {"status": "sent"}
        except: return {"error": "Failed"}, 500
    return {"error": "Invalid"}, 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
