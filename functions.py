import json
import requests
import re
import os
import random
def generate_chat_id():
    return random.randint(100000, 999999)  # Генерация ID от 100000 до 999999

from openai import OpenAI
from prompts import formatter_prompt, assistant_instructions

# Загрузка переменных окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

# Проверка загрузки API-ключа
print(f"AIRTABLE_API_KEY: {AIRTABLE_API_KEY}")

# Проверка наличия API-ключей
if not OPENAI_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения OPENAI_API_KEY не найдена!")
if not AIRTABLE_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения AIRTABLE_API_KEY не найдена!")

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
AIRTABLE_BASE_ID = "YOUR_BASE_ID"  # Укажите реальный Base ID
AIRTABLE_TABLE_NAME = "YOUR_TABLE_NAME"  # Укажите точное название таблицы

# Функция обработки контактных данных
def process_contact_data(data):
    name_pattern = r"[А-Яа-яA-Za-z]+(?:\s[А-Яа-яA-Za-z]+)?"
    phone_pattern = r"\+?\d{10,15}"
    service_pattern = r"(?:букет|цветы|композиция|повод|свадьба|юбилей).*?"
    amount_pattern = r"\b\d{3,8}\b"

    name = re.search(name_pattern, data)
    phone = re.search(phone_pattern, data)
    service = re.search(service_pattern, data)
    amount = re.search(amount_pattern, data)

    return (
        name.group(0) if name else "Неизвестно",
        phone.group(0) if phone else "Не указан",
        service.group(0) if service else "Не указано",
        int(amount.group(0)) if amount else 0
    )

# Функция создания лида в Airtable
def create_lead(name, phone, service, amount):
    chat_id = generate_chat_id()  # Генерация ID для клиента
    print(f"📦 Данные для Airtable: {chat_id}, {name}, {phone}, {service}, {amount}")  # Проверка данных
    url = f"https://api.airtable.com/v0/appVoeCexAh2D0WmI/Table%201"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "fields": {
            "chat_id": str(chat_id),
            "Name": name,
            "Phone": phone,
            "Service": service,
            "Amount of money": amount
        }
    }

    print(f"📤 Отправляем в Airtable: {json.dumps(data, indent=2, ensure_ascii=False)}")  # Проверка JSON
    
    response = requests.post(url, json=data, headers=headers)
    print(f"🔍 Статус ответа: {response.status_code}")
    print(f"🔍 Тело ответа: {response.text}")
    if response.status_code in [200, 201]:  # Исправлено для учёта успешного кода 201
        print("✅ Лид успешно добавлен в Airtable!")
    else:
        print(f"❌ Ошибка при добавлении: {response.text}")
    return response.json()

# Функция создания ассистента
def create_assistant(client):
    assistant_file_path = 'assistant.json'
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            return assistant_data[asst_si51TxBCRS5x5zenOIzZGViv]

    knowledge_base_files = ["VmestoSlov_bot_baze.docx"]
    file_ids = []
    for file_path in knowledge_base_files:
        with open(file_path, "rb") as f:  # Исправлено на безопасное открытие файлов
            file = client.files.create(file=f, purpose='assistants')
            file_ids.append(file.id)

    vector_store = client.beta.vector_stores.create(
        name="Vmesto_slov_Vector_store", file_ids=file_ids
    )

    # Создание ассистента
    # ✅ Используем конкретный ассистент
    assistant_id = "asst_si51TxBCRS5x5zenOIzZGViv"  # ← Вставь сюда свой настоящий ID ассистента
    print(f"✅ Используем ассистента с ID: {assistant_id}")
    return assistant_id

