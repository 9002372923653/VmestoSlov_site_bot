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
AIRTABLE_BASE_ID = "Untitled Base"  # ✅ Взято из твоего кода
AIRTABLE_TABLE_NAME = "Table 1"  # ✅ Взято из твоего кода

# 🔍 **Функция поиска существующего лида**
def find_existing_lead(client_id, phone=None):
    """Ищет лид в Airtable по client_id или номеру телефона"""
    url = f"https://api.airtable.com/v0/appVoeCexAh2D0WmI/Table%201"
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
    url = f"https://api.airtable.com/v0/appVoeCexAh2D0WmI/Table%201/{record_id}"
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
        url = f"https://api.airtable.com/v0/appVoeCexAh2D0WmI/Table%201"
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
