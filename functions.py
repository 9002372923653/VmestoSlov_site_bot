import json
import requests
import re
import os
from openai import OpenAI
from prompts import formatter_prompt, assistant_instructions

import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения OPENAI_API_KEY не найдена!")

if not AIRTABLE_API_KEY:
    raise ValueError("❌ Ошибка: переменная окружения AIRTABLE_API_KEY не найдена!")

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
# Инициализация API Airtable
AIRTABLE_BASE_ID = "Untitled Base"  # Используй свой Base ID из Airtable
AIRTABLE_TABLE_NAME = "Table 1"  # Используй точное название таблицы

# Регулярные выражения для извлечения информации
def process_contact_data(data):
    name_pattern = r"[А-Яа-яA-Za-z]+(?:\s[А-Яа-яA-Za-z]+)?"
    phone_pattern = r"\+?\d{10,15}"
    service_pattern = r"(?:букет|цветы|композиция|повод|свадьба|юбилей).*?"
    amount_pattern = r"\b\d{3,6}\b"  # Бюджет (число от 3 до 6 цифр)

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

# Добавление лида в Airtable
def create_lead(name, phone, email):
    url = "https://api.airtable.com/v0/appVoeCexAh2D0WmI/Table%201"  # Измените это на ваш URL API Airtable
    headers = {
        "Authorization": "Bearer " + AIRTABLE_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "records": [{
            "fields": {
                "Name": name,
            "Phone": phone,
            "Service": service,
            "Amount of money": amount
            }
        }]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Лид успешно создан.")
        return response.json()
    else:
        print(f"Не удалось создать лида: {response.text}")

# Создание или загрузка ассистента
def create_assistant(client):
    assistant_file_path = 'assistant.json'

    # Если файл assistant.json уже существует, то загружаем этого ассистента: Сюда подставить название документов с вашей базой знаний! ЭТИ ДОКУМЕНТЫ ДОЛЖНЫ БЫТЬ ДОБАВЛЕНЫ В Replit
    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            print("Загружен существующий ID ассистента.")
            return assistant_id
    
    else:
        knowledge_base_files = ["VmestoSlov_bot_baze.docx"]
        file_ids = []

        for file_path in knowledge_base_files:
            
            file = client.files.create(file=open("VmestoSlov_bot_baze.docx", "rb"),
                purpose='assistants')
            file_ids.append(file.id)
            
        # Создаем Vector Store для базы знаний : Называние в кавычках измените на любое свое.
        vector_store = client.beta.vector_stores.create(
            name="Vmesto_slov_Vector_store",
            file_ids=file_ids
        )

        # Загружаем файл базы знаний через Files API: Сюда подставить название документов с вашей базой знаний!
        knowledge_base_file = client.files.create(
            file=open("VmestoSlov_bot_baze.docx", "rb"),
            purpose='assistants'
        )
       

        # Получаем file_id загруженного файла
        knowledge_base_file_id = knowledge_base_file.id

        # Заливаем файл с базой знаний в Vector Store
        file_batch = client.beta.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store.id,
            file_ids=[knowledge_base_file_id]  # Используем полученный file_id
        )

        # Создаем Assistant с настроенным Vector Store
        assistant = client.beta.assistants.create(
            instructions=assistant_instructions,
            model="gpt-4o",
            tools=[
                {
                    "type": "file_search"  # file_search вместо retrieval
                },
                {
                    "type": "code_interpreter"
                },
                {
                    "type": "function",
                    "function": {
                        "name": "create_lead",
                        "description":
                        "Захват деталей лида и сохранение в Airtable.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Имя лида."
                                },
                                "phone": {
                                    "type": "string",
                                    "description": "Телефонный номер лида."
                                },
                                "email": {
                                    "type": "string",
                                    "description": "email лида."
                                }
                            },
                            "required": ["name", "phone", "email"]
                        }
                    }
                }
            ],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )

        assistant = client.beta.assistants.update(
          assistant_id=assistant.id,
          tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )
        # Создание нового файла assistant.json для загрузки при будущих запусках
        with open(assistant_file_path, 'w') as file:
            json.dump({'assistant_id': assistant.id}, file)
            print("Создан новый ассистент и сохранен ID.")


    assistant_id = assistant.id

    return assistant_id
