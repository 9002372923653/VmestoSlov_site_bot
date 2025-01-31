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
    # Регулярные выражения для извлечения информации
    name_pattern = r"[А-Яа-яA-Za-z]+(?:\s[А-Яа-яA-Za-z]+)?"  # Имя
    phone_pattern = r"\+?\d{10,15}"  # Телефон
    service_pattern = r"(?:букет|цветы|композиция|повод|свадьба|юбилей|день рождения|праздник|годовщина).*?"  # Тип услуги
    amount_pattern = r"(\d{3,8})\s?(?:рублей|р|₽)?"  # Бюджет (число от 3 до 8 цифр с "рублей")

    # Ищем совпадения в тексте
    name = re.search(name_pattern, data)
    phone = re.search(phone_pattern, data)
    service = re.search(service_pattern, data, re.IGNORECASE)
    amount = re.search(amount_pattern, data)

    # Логируем найденные данные
    print(f"🔍 Найдено: Name: {name.group(0) if name else '❌'}, Phone: {phone.group(0) if phone else '❌'}, Service: {service.group(0) if service else '❌'}, Amount: {amount.group(1) if amount else '❌'}")

    return (
        name.group(0) if name else "Неизвестно",
        phone.group(0) if phone else "Не указан",
        service.group(0) if service else "Не указано",
        int(amount.group(1)) if amount else 0
    )

# Добавление лида в Airtable
import requests
import json

def create_lead(name, phone, service, amount):
    url = "https://api.airtable.com/v0/appVoeCexAh2D0WmI/Table%201"  # Твой URL API Airtable

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
# ✅ Проверяем и конвертируем amount в число, если это возможно
    try:
        amount = int(amount)  # Принудительно переводим в число
    except (ValueError, TypeError):
        amount = 0  # Если ошибка — записываем 0

    data = {
        "fields": {  # 🔴 Убрал "records", теперь данные отправляются корректно!
            "Name": name,
            "Phone": phone,
            "Service": service,
            "Amount of money": amount
        }
    }

    # Отладка: Вывод перед отправкой
    print("📤 Отправляем данные в Airtable:")
    print(json.dumps(data, indent=4, ensure_ascii=False))

    response = requests.post(url, json=data, headers=headers)

# 🔍 Логируем ответ от Airtable
    print("🛑 Ответ от Airtable:", response.status_code, response.text)

    if response.status_code in [200, 201]:  # ✅ Airtable возвращает 201 при успешном добавлении
        print("✅ Лид успешно добавлен в Airtable!")
    else:
        print(f"❌ Ошибка при добавлении: {response.text}")


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
