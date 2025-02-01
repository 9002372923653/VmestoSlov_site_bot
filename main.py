import json
import os
import time
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
import functions
from packaging import version  # Для проверки версии OpenAI

# ✅ Проверка совместимости версии OpenAI
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Безопасное получение ключа
if not OPENAI_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения OPENAI_API_KEY не найдена!")

if current_version < required_version:
    raise ValueError(
        f"Ошибка: версия OpenAI {openai.__version__} меньше требуемой версии 1.1.1"
    )
else:
    print("✅ Версия OpenAI совместима.")

# ✅ Инициализация приложения Flask
app = Flask(__name__)

# ✅ Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Создание или загрузка ассистента
assistant_id = functions.create_assistant(client)

# 🚀 Начало новой беседы
@app.route('/start', methods=['GET'])
def start_conversation():
    print("Начинается новая беседа...")
    thread = client.beta.threads.create()
    print(f"✅ Создан новый поток с ID: {thread.id}")
    return jsonify({"thread_id": thread.id})

# 💬 Обработка сообщений от пользователя
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    thread_id = data.get('thread_id')
    user_input = data.get('message', '')

    if not thread_id:
        print("❌ Ошибка: отсутствует thread_id")
        return jsonify({"error": "Отсутствует thread_id"}), 400

    print(f"📩 Получено сообщение: {user_input} для потока с ID: {thread_id}")

    # ✅ Добавление сообщения пользователя в поток
    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=user_input
    )

    # ✅ Запуск помощника
    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )

    # ⏱ Ожидание завершения обработки
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )

        if run_status.status == 'completed':
            break

        elif run_status.status == 'requires_action':
            print("🌀 Ассистент требует выполнения действия.")  # Проверка статуса
            tool_calls = []
            if hasattr(run_status, "required_action") and hasattr(run_status.required_action, "submit_tool_outputs"):
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                print(f"🔧 Tool calls: {tool_calls}")  # Проверка наличия вызова функций

            if not tool_calls:
                print("⚠ Предупреждение: Voiceflow не передал tool_calls!")
            else:
                for tool_call in tool_calls:
                    print(f"🔍 Проверка вызова функции: {tool_call.function.name}")  # Проверка вызова

                    if tool_call.function.name == "create_lead":
                        print("🚀 Сценарий create_lead запущен!")  # Проверка запуска
                        arguments = json.loads(tool_call.function.arguments)
                        print(f"📋 Аргументы для create_lead: {arguments}")  # Проверка аргументов

                        output = functions.create_lead(
                            arguments.get("name", "Неизвестно"),
                            arguments.get("phone", "Не указан"),
                            arguments.get("service", "Не указано"),
                            arguments.get("amount", 0)
                        )

                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=[{
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(output)
                            }]
                        )

        time.sleep(1)  # 💤 Пауза перед повторной проверкой

    # 📤 Получение последнего сообщения от помощника
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response_text = messages.data[0].content[0].text.value if messages.data else "Ошибка: сообщение пустое"

    print(f"📨 Отправляем ответ пользователю: {response_text}")
    return jsonify({"response": response_text})

# 🚀 Запуск Flask-приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
