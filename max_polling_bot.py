#!/usr/bin/env python3
"""
MAX Bot с Polling интеграцией
Бот проверяет новые сообщения в MAX каждые 5 секунд и отвечает
"""

import os
import time
import requests
import json
import logging
from datetime import datetime
import threading

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "f9LHodD0cOJu6fhHJWrlK12JgPI--lwLp9a3BCjv15QOjun6WOmrntPxqbyZHn6iDNybJePw90nJRxwEU2Y3")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-e2ada56f857e435196a2c126a21d5271")
MAX_API_URL = "https://api.max.ru/v1"

# Хранилище истории и обработанных сообщений
conversation_history = {}
processed_messages = set()

SYSTEM_PROMPT = """Ты - помощник компании AutoProfi Asia, которая специализируется на импорте автомобилей из Кореи, Японии и Китая.

Твоя задача:
1. Помогать клиентам с подбором автомобилей
2. Отвечать на вопросы о ценах и условиях доставки
3. Консультировать по запчастям и сервису
4. Помогать с оформлением документов
5. Предоставлять контактную информацию

Информация о компании:
- Специализация: импорт авто из Кореи, Японии, Китая под заказ
- Работаем 24/7
- Гарантия на все автомобили
- Быстрая доставка по России
- Телефон: +7 (914) 798-09-99
- Сайт: https://autoprofasia.ru

Будь вежливым, профессиональным и помогающим."""


def get_deepseek_response(user_message, user_id):
    """Получить ответ от DeepSeek AI"""
    try:
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(conversation_history[user_id][-4:])
        messages.append({"role": "user", "content": user_message})
        
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'deepseek-chat',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_message = data['choices'][0]['message']['content']
            
            conversation_history[user_id].append({"role": "user", "content": user_message})
            conversation_history[user_id].append({"role": "assistant", "content": ai_message})
            
            if len(conversation_history[user_id]) > 20:
                conversation_history[user_id] = conversation_history[user_id][-20:]
            
            return ai_message
        else:
            logger.error(f"DeepSeek error: {response.status_code}")
            return "Извините, произошла ошибка. Пожалуйста, попробуйте позже."
    
    except Exception as e:
        logger.error(f"DeepSeek exception: {e}")
        return "Ошибка при обработке запроса. Пожалуйста, попробуйте позже."


def send_message_to_max(user_id, message_text):
    """Отправить сообщение в MAX"""
    try:
        # Попытка отправить через MAX API
        response = requests.post(
            f'{MAX_API_URL}/messages/send',
            headers={
                'Authorization': f'Bearer {MAX_BOT_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'user_id': user_id,
                'text': message_text
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Сообщение отправлено пользователю {user_id}")
            return True
        else:
            logger.warning(f"MAX API error: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        return False


def get_messages_from_max():
    """Получить новые сообщения из MAX"""
    try:
        response = requests.get(
            f'{MAX_API_URL}/messages',
            headers={
                'Authorization': f'Bearer {MAX_BOT_TOKEN}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get('messages', [])
        else:
            logger.warning(f"Ошибка получения сообщений: {response.status_code}")
            return []
    
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        return []


def polling_loop():
    """Основной цикл polling"""
    logger.info("Запущен polling loop")
    
    while True:
        try:
            messages = get_messages_from_max()
            
            for msg in messages:
                msg_id = msg.get('id')
                user_id = msg.get('from_id') or msg.get('user_id')
                text = msg.get('text') or msg.get('message')
                
                if not msg_id or not user_id or not text:
                    continue
                
                # Проверяем не обработано ли уже это сообщение
                if msg_id in processed_messages:
                    continue
                
                logger.info(f"Новое сообщение от {user_id}: {text}")
                processed_messages.add(msg_id)
                
                # Получаем ответ
                response = get_deepseek_response(text, user_id)
                
                # Отправляем ответ
                send_message_to_max(user_id, response)
            
            # Ограничиваем размер processed_messages
            if len(processed_messages) > 1000:
                processed_messages.clear()
            
            time.sleep(5)  # Проверяем каждые 5 секунд
        
        except Exception as e:
            logger.error(f"Ошибка в polling loop: {e}")
            time.sleep(10)


if __name__ == '__main__':
    logger.info("Запуск MAX Bot с polling")
    polling_loop()
