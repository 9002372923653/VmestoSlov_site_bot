import json
import requests
import re
import os
import uuid  # 🆕 Для генерации уникального client_id
from openai import OpenAI
from prompts import formatter_prompt, assistant_instructions

# Загрузка API-ключей
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения OPENAI_API_KEY не найдена!")

if not AIRTABLE_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения AIRTABLE_API_KEY не найдена!")

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Инициализация API Airtable
AIRTABLE_BASE_ID = "appVoeCexAh2D0WmI"  # ✅ Взято из твоего кода
AIRTABLE_TABLE_NAME = "Table 1"  # ✅ Взято из твоего кода

# 🔍 **Функция поиска существующего лида**
def find_existing_lead(client_id, phone=None):
    """Ищет лид в Airtable по client_id или номеру телефона"""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        records = response.json().get("records", [])
        for record in records:
            fields = record.get("fields", {})
            if fields.get("Client ID") == client_id or (phone and fields.get("Phone") == phone):
                return record["id"]  # Возвращаем ID найденной записи

    return None  # Если не найдено

# ✏ **Функция обновления существующего лида**
def update_lead(record_id, fields):
    """Обновляет существующую запись в Airtable"""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}/{record_id}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.patch(url, json={"fields": fields}, headers=headers)
    if response.status_code in [200, 201]:
        print("✅ Лид успешно обновлен в Airtable!")
    else:
        print(f"❌ Ошибка при обновлении: {response.text}")

# ✅ **Функция `create_lead()` с поддержкой client_id**
def create_lead(name, phone, service, amount, client_id=None):
    """Создает или обновляет лид в Airtable"""

    if client_id is None:
        client_id = str(uuid.uuid4())[:8]  # 🆕 Генерируем уникальный client_id (первые 8 символов)

    existing_record_id = find_existing_lead(client_id, phone)  # 🆕 Проверяем, есть ли уже запись

    fields = {
        "Client ID": client_id,  # 🆕 Теперь у каждого клиента есть уникальный ID
        "Name": name if name != "Неизвестно" else None,
        "Phone": phone if phone != "Не указан" else None,
        "Service": service if service != "Не указано" else None,
        "Amount of money": amount if amount > 0 else None
    }

    # Убираем пустые поля, чтобы не затирать уже существующие данные
    fields = {k: v for k, v in fields.items() if v is not None}

    if existing_record_id:
        print(f"🔄 Обновляем существующего лида: {existing_record_id}")
        update_lead(existing_record_id, fields)
    else:
        print("📤 Создаем нового лида в Airtable")
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json={"fields": fields}, headers=headers)

        if response.status_code in [200, 201]:
            print("✅ Лид успешно добавлен в Airtable!")
        else:
            print(f"❌ Ошибка при добавлении: {response.text}")

    return client_id  # 🆕 Возвращаем client_id, чтобы использовать его в следующих запросах

# ✅ **Функция создания ассистента**
def create_assistant(client):
    assistant_file_path = 'assistant.json'

    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            print("✅ Загружен существующий ID ассистента:", assistant_id)
            return assistant_id

    assistant = client.beta.assistants.create(
        instructions="Ты — виртуальный ассистент цветочного салона. Твоя задача — помочь клиенту подобрать букет и оформить заказ.",
        model="gpt-4o",
        tools=[
            {
                "type": "file_search"
            },
            {
                "type": "code_interpreter"
            },
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Записывает заказ клиента в Airtable.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Имя клиента."},
                            "phone": {"type": "string", "description": "Номер телефона клиента."},
                            "service": {"type": "string", "description": "Тип заказа (букет, оформление события)."},
                            "amount": {"type": "integer", "description": "Бюджет заказа в рублях."}
                        },
                        "required": ["name", "phone", "service", "amount"]
                    }
                }
            }
        ]
    )

    with open(assistant_file_path, 'w') as file:
        json.dump({'assistant_id': assistant.id}, file)
        print("✅ Создан новый ассистент и сохранен ID:", assistant.id)

    return assistant.id
