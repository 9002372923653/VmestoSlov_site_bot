import json
import requests
import re
import os
from openai import OpenAI
from prompts import formatter_prompt, assistant_instructions

# Получение API-ключей
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения OPENAI_API_KEY не найдена!")
if not AIRTABLE_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения AIRTABLE_API_KEY не найдена!")

# Инициализация клиентов
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
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "fields": {
            "Name": name,
            "Phone": phone,
            "Service": service,
            "Amount of money": amount
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
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
            return assistant_data['assistant_id']
    
    knowledge_base_files = ["VmestoSlov_bot_baze.docx"]
    file_ids = []
    for file_path in knowledge_base_files:
        file = client.files.create(file=open(file_path, "rb"), purpose='assistants')
        file_ids.append(file.id)
    
    vector_store = client.beta.vector_stores.create(
        name="Vmesto_slov_Vector_store", file_ids=file_ids
    )
    assistant = client.beta.assistants.create(
        instructions=assistant_instructions,
        model="gpt-4o",
        tools=[{"type": "file_search"}, {"type": "code_interpreter"},
               {"type": "function", "function": {
                   "name": "create_lead",
                   "description": "Захват деталей лида и сохранение в Airtable.",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "name": {"type": "string", "description": "Имя лида."},
                           "phone": {"type": "string", "description": "Телефонный номер лида."},
                           "service": {"type": "string", "description": "Услуга, интересующая лида."},
                           "amount": {"type": "integer", "description": "Сумма сделки."}
                       },
                       "required": ["name", "phone", "service", "amount"]
                   }
               }}
        ],
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
    )
    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
    )
    with open(assistant_file_path, 'w') as file:
        json.dump({'assistant_id': assistant.id}, file)
    return assistant.id
