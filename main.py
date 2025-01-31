import json
import os
import time
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
import functions
import uuid

from packaging import version

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
if current_version < required_version:
    raise ValueError(f"Ошибка: версия OpenAI {openai.__version__} меньше требуемой версии 1.1.1")
else:
    print("Версия OpenAI совместима.")

app = Flask(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)
assistant_id = functions.create_assistant(client)

@app.route('/start', methods=['GET'])
def start_conversation():
    client_id = str(uuid.uuid4())[:8]
    print(f"Начинается новая беседа... Присвоен client_id: {client_id}")
    thread = client.beta.threads.create()
    return jsonify({"thread_id": thread.id, "client_id": client_id})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    thread_id = data.get('thread_id')
    client_id = data.get('client_id')
    user_input = data.get('message', '')

    if not thread_id:
        return jsonify({"error": "Отсутствует thread_id"}), 400

    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)

    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)

    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        if run_status.status == 'completed':
            break
        elif run_status.status == 'requires_action':
            print("🔄 Требуется действие!")
            time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response_text = messages.data[0].content[0].text.value if messages.data else "Ошибка: сообщение пустое"

    return jsonify({"response": response_text, "client_id": client_id})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
