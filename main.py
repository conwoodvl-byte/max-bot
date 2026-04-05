#!/usr/bin/env python3
"""
MAX Bot с интеграцией DeepSeek AI
Бот AutoProfi Asia для консультаций по импорту автомобилей
"""

from flask import Flask, request, jsonify
import requests
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)

# Конфигурация из переменных окружения
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "f9LHodD0cOJu6fhHJWrlK12JgPI--lwLp9a3BCjv15QOjun6WOmrntPxqbyZHn6iDNybJePw90nJRxwEU2Y3")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-e2ada56f857e435196a2c126a21d5271")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# Системный промпт
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

Будь вежливым, профессиональным и помогающим. Если не знаешь ответ, предложи связаться с менеджером."""

# Хранилище для истории диалогов
conversation_history = {}


class DeepSeekClient:
    """Клиент для работы с DeepSeek API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = DEEPSEEK_API_URL
    
    def generate_response(self, user_message: str, conversation_history: list = None) -> Optional[str]:
        """Генерирует ответ с использованием DeepSeek"""
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
            
            # Добавляем историю диалога если есть
            if conversation_history:
                messages.extend(conversation_history[-4:])
            
            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": user_message})
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Запрос к DeepSeek: {user_message[:100]}")
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data['choices'][0]['message']['content']
                logger.info(f"Ответ от DeepSeek: {bot_response[:100]}")
                return bot_response
            else:
                logger.error(f"Ошибка DeepSeek: {response.status_code} - {response.text}")
                return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
                
        except Exception as e:
            logger.error(f"Исключение при работе с DeepSeek: {e}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."


class MAXBotHandler:
    """Обработчик для MAX Bot"""
    
    def __init__(self):
        self.deepseek = DeepSeekClient(DEEPSEEK_API_KEY)
    
    def process_message(self, user_id: str, message_text: str) -> str:
        """Обрабатывает входящее сообщение"""
        try:
            # Получаем или создаём историю для пользователя
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            history = conversation_history[user_id]
            
            # Генерируем ответ
            response = self.deepseek.generate_response(message_text, history)
            
            if response:
                # Сохраняем в историю
                history.append({"role": "user", "content": message_text})
                history.append({"role": "assistant", "content": response})
                
                # Ограничиваем размер истории
                if len(history) > 10:
                    conversation_history[user_id] = history[-10:]
                
                return response
            else:
                return "Извините, не удалось обработать ваш запрос."
                
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            return "Произошла ошибка. Пожалуйста, попробуйте позже."


# Инициализация обработчика
handler = MAXBotHandler()


@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint для получения сообщений от MAX"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        logger.info(f"Webhook получен: {json.dumps(data)}")
        
        # Парсим данные
        user_id = data.get('from_id') or data.get('user_id') or data.get('sender_id')
        message_text = data.get('text') or data.get('message') or data.get('body')
        
        if not user_id or not message_text:
            logger.warning(f"Неполные данные в webhook: {data}")
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        logger.info(f"Сообщение от {user_id}: {message_text}")
        
        # Обрабатываем сообщение
        response = handler.process_message(str(user_id), message_text)
        
        # Возвращаем ответ
        return jsonify({
            "status": "ok",
            "response": response,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка в webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья приложения"""
    return jsonify({
        "status": "ok",
        "service": "AutoProfi Asia Bot",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Главная страница"""
    return jsonify({
        "service": "AutoProfi Asia Bot",
        "version": "1.0",
        "endpoints": {
            "webhook": "/webhook (POST)",
            "health": "/health (GET)"
        },
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
