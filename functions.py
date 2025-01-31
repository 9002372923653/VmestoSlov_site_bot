import json
import requests
import re
import os
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
AIRTABLE_BASE_ID = "appVoeCexAh2D0WmI"  # Убедись, что это правильный Base ID
AIRTABLE_TABLE_NAME = "Table 1"  # Убедись, что это правильное название таблицы

# 🆕 Улучшенная обработка данных пользователя
def process_contact_data(data):
    """Извлекает имя, телефон, тип услуги и сумму из текста"""
    
    name_pattern = r"[А-Яа-яA-Za-z]+(?:\s[А-Яа-яA-Za-z]+)?"  # Улучшено: теперь может захватить 2 слова (Имя + Фамилия)
    phone_pattern = r"\+?\d{10,15}"
    service_pattern = r"(?:букет|цветы|композиция|повод|свадьба|юбилей|день рождения|праздник|годовщина).*?"
    amount_pattern = r"(\d{3,8})\s?(?:рублей|р|₽)?"  # Теперь корректно понимает число + "рублей"

    name = re.search(name_pattern, data)
    phone = re.search(phone_pattern, data)
    service = re.search(service_pattern, data, re.IGNORECASE)
    amount = re.search(amount_pattern, data)

    # Логируем найденные данные
    print(f"🔍 Найдено: Name: {name.group(0) if name else '❌'}, "
          f"Phone: {phone.group(0) if phone else '❌'}, "
          f"Service: {service.group(0) if service else '❌'}, "
          f"Amount: {amount.group(1) if amount else '❌'}")

    return (
        name.group(0) if name else "Неизвестно",
        phone.group(0) if phone else "Не указан",
        service.group(0) if service else "Не указано",
        int(amount.group(1)) if amount else 0
    )

# 🆕 Исправленная функция записи в Airtable
def create_lead(name, phone, service, amount):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    # ✅ Проверяем и конвертируем amount в число, если это возможно
    try:
        amount = int(amount)
    except (ValueError, TypeError):
        amount = 0  # Если ошибка — записываем 0

    data = {
        "fields": {
            "Name": name,
            "Phone": phone,
            "Service": service,
            "Amount of money": amount
        }
    }

    # 🔍 Логируем перед отправкой
    print("📤 Отправляем данные в Airtable:")
    print(json.dumps(data, indent=4, ensure_ascii=False))

    response = requests.post(url, json=data, headers=headers)

    # 🔍 Логируем ответ от Airtable
    print("🛑 Ответ от Airtable:", response.status_code, response.text)

    if response.status_code in [200, 201]:  
        print("✅ Лид успешно добавлен в Airtable!")
    else:
        print(f"❌ Ошибка при добавлении: {response.text}")

# 🆕 Исправленная функция создания ассистента
def create_assistant(client):
    assistant_file_path = 'assistant.json'

    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            print("Загружен существующий ID ассистента.")
            return assistant_id

    # 🆕 Создаём ассистента с правильными параметрами
    assistant = client.beta.assistants.create(
        instructions=assistant_instructions,
        model="gpt-4o",
        tools=[
            {"type": "file_search"},
            {"type": "code_interpreter"},
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Захват деталей лида и сохранение в Airtable.",
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
                            "service": {   # 🆕 Исправлено: Теперь передаём service
                                "type": "string",
                                "description": "Тип услуги или повод."
                            },
                            "amount": {   # 🆕 Исправлено: Теперь передаём budget
                                "type": "integer",
                                "description": "Бюджет заказа в рублях."
                            }
                        },
                        "required": ["name", "phone", "service", "amount"]
                    }
                }
            }
        ]
    )

    # 🆕 Сохраняем ID ассистента
    with open(assistant_file_path, 'w') as file:
        json.dump({'assistant_id': assistant.id}, file)
        print("Создан новый ассистент и сохранен ID.")

    return assistant.id
