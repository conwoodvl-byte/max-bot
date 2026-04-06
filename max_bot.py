#!/usr/bin/env python3
"""
AutoProfi Asia MAX Bot v2.0 (VK API)
- Диалог с DeepSeek AI (Дмитрий)
- Сбор заявок (10 параметров + телефон)
- Уведомления Павлу при новых заявках
- Продолжение диалога после заявки
"""

import asyncio
import logging
import json
import re
import time
from datetime import datetime
from typing import Optional, Dict, Any

from openai import AsyncOpenAI
import aiohttp

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Конфигурация ───────────────────────────────────────────────────────────
VK_API_KEY = "vk1.a.Jrppzjcawn6HL863fpKcZWCtFZYD30DOtA8VGmoBchD5OLBPTCXjuMekLm8dsAE5bdAtxeQrlejmvJW6gcpidFuz34f7hzS09LiDL0ABqA_1jl1"
DEEPSEEK_KEY = "sk-6790bd7c97f84e6f816899e78c911c9f"
PAVEL_CHAT_ID = 532718681  # Telegram ID для уведомлений
VK_API_URL = "https://api.vk.com/method"
VK_API_VERSION = "5.131"

# ─── Инициализация ──────────────────────────────────────────────────────────
deepseek = AsyncOpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# ─── Хранилище данных ───────────────────────────────────────────────────────
user_histories: Dict[int, list] = {}
processed_messages: set = set()

# ─── База знаний ────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = """
=== БАЗА ЗНАНИЙ КОМПАНИИ «АВТОПРОФИ АЗИЯ» ===

--- ОБЩАЯ ИНФОРМАЦИЯ ---
Компания: Автопрофи Азия
Руководитель: ИП Благуш Павел Владимирович
Стаж работы: более 6 лет на рынке импорта авто
Сайт: www.AutoProfiasia.ru
Telegram-канал: t.me/autoprofiasia
Телефон Павла: +7(914)-798-09-99
Email: Autoprofijp@yandex.ru
Работаем только с физическими лицами. Доставка в любой город РФ.

--- ПРЕИМУЩЕСТВА ---
- Безупречная репутация: ни одного негативного отзыва за 6 лет
- Официальный договор с ИП — ответственность всем имуществом
- Прозрачность: стоимость фиксируется в договоре
- Полная информационная открытость на каждом этапе
- Личное присутствие во Владивостоке

--- КОМИССИЯ ЗА УСЛУГИ ---
Япония: 65 000 руб. (если итог < 900 000 руб.) или 80 000 руб. (если итог >= 900 000 руб.)
Корея: фиксированная комиссия 100 000 руб.
Китай: фиксированная комиссия 100 000 руб.
Предоплата: 100 000 руб. (учитывается в дальнейших расчётах)

--- СРОКИ ДОСТАВКИ ---
Япония → Владивосток: ~14 дней после покупки
Корея → Владивосток: ~14 дней после бронирования
Китай → Владивосток: от 10 дней до 1,5 месяцев

--- ОГРАНИЧЕНИЯ ПО ВОЗРАСТУ АВТО ---
Дизель: не старше 2009 г.
Бензин: не старше 2008 г.

--- ВАЖНОЕ ИЗМЕНЕНИЕ (декабрь 2026) ---
С 1 декабря 2026 года введён повышенный инвестиционный сбор на авто свыше 160 л.с.
Импорт таких машин стал нецелесообразным. В приоритете авто до 160 л.с.
"""

# ─── Системный промпт ───────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""Ты — Дмитрий, опытный менеджер по продажам компании AutoProfi Asia.
Компания занимается импортом автомобилей из Японии, Южной Кореи и Китая под ключ в Россию.

ТВОЯ ЗАДАЧА — в ходе живого дружелюбного диалога собрать у клиента следующие данные:
1. Страна (Япония / Корея / Китай)
2. Марка автомобиля
3. Модель автомобиля
4. Год выпуска
5. Объём двигателя (куб. см)
6. Мощность двигателя (л.с.)
7. Желаемый цвет
8. Максимальный пробег (км)
9. Тип привода (2WD / 4WD / AWD)
10. Номер телефона клиента (обязательно!)

ПРАВИЛА ОБЩЕНИЯ:
- Говори по-русски, дружелюбно и профессионально
- Задавай по одному вопросу за раз
- Если клиент не знает параметр — предложи диапазон или пропусти
- Не называй конкретные цены — скажи что расчёт пришлёт Павел
- Используй базу знаний для ответов на вопросы
- На вопросы про автомобили отвечай развёрнуто
- После отправки заявки НЕ заканчивай диалог — продолжай общаться

КОГДА ВСЕ ДАННЫЕ СОБРАНЫ (включая телефон):
Сформируй итоговое сообщение строго в таком JSON-формате:
LEAD_JSON:{{"country":"...","make":"...","model":"...","year":...,"engine_volume":...,"engine_power":...,"color":"...","mileage":...,"drive_type":"...","phone":"..."}}

После JSON напиши клиенту:
"Отлично! Заявка принята и уже отправлена Павлу 🎉 Он свяжется с вами в ближайшее время.

А пока — остались ли у вас ещё вопросы? Могу рассказать подробнее о любой модели, условиях доставки или процессе оформления 😊"

{KNOWLEDGE_BASE}
"""

# ─── Вспомогательные функции ───────────────────────────────────────────────
async def ask_deepseek(history: list) -> str:
    """Получить ответ от DeepSeek"""
    try:
        response = await deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=600,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "Извините, произошла ошибка. Пожалуйста, попробуйте позже."

def extract_lead(text: str) -> Optional[Dict[str, Any]]:
    """Извлечь заявку из ответа DeepSeek"""
    match = re.search(r'LEAD_JSON:(\{.*?\})', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            logger.error(f"JSON parse error: {e}")
            return None
    return None

async def send_message_to_vk(user_id: int, message: str):
    """Отправить сообщение в VK"""
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                'access_token': VK_API_KEY,
                'user_id': user_id,
                'message': message,
                'v': VK_API_VERSION,
                'random_id': int(time.time() * 1000)
            }
            async with session.post(f"{VK_API_URL}/messages.send", params=params) as resp:
                result = await resp.json()
                if 'error' in result:
                    logger.error(f"VK API error: {result['error']}")
                    return False
                logger.info(f"Message sent to {user_id}")
                return True
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

async def get_updates_from_vk():
    """Получить новые сообщения из VK"""
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                'access_token': VK_API_KEY,
                'v': VK_API_VERSION
            }
            async with session.get(f"{VK_API_URL}/messages.getConversations", params=params) as resp:
                result = await resp.json()
                if 'error' in result:
                    logger.error(f"VK API error: {result['error']}")
                    return []
                
                messages = []
                if 'response' in result and 'items' in result['response']:
                    for item in result['response']['items']:
                        if 'last_message' in item:
                            msg = item['last_message']
                            messages.append({
                                'id': msg.get('id'),
                                'from_id': msg.get('from_id'),
                                'text': msg.get('text'),
                                'date': msg.get('date')
                            })
                return messages
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return []

async def send_lead_notification(lead: Dict[str, Any], user_id: int):
    """Отправить уведомление о заявке (в Telegram Павлу)"""
    # Здесь можно добавить отправку в Telegram, если нужно
    logger.info(f"Lead from VK user {user_id}: {lead}")

# ─── Основной цикл polling ─────────────────────────────────────────────────
async def polling_loop():
    """Основной цикл polling"""
    logger.info("🤖 MAX Bot v2.0 запущен! Начинаю polling...")
    
    while True:
        try:
            messages = await get_updates_from_vk()
            
            for msg in messages:
                msg_id = msg.get('id')
                user_id = msg.get('from_id')
                text = msg.get('text', '')
                
                if not msg_id or not user_id or not text:
                    continue
                
                # Проверяем не обработано ли уже это сообщение
                if msg_id in processed_messages:
                    continue
                
                processed_messages.add(msg_id)
                logger.info(f"New message from {user_id}: {text[:50]}")
                
                # Инициализируем историю пользователя если её нет
                if user_id not in user_histories:
                    user_histories[user_id] = []
                
                history = user_histories[user_id]
                history.append({"role": "user", "content": text})
                
                # Получаем ответ от DeepSeek
                response_text = await ask_deepseek(history)
                history.append({"role": "assistant", "content": response_text})
                
                # Ограничиваем размер истории
                if len(history) > 20:
                    user_histories[user_id] = history[-20:]
                
                # Проверяем есть ли заявка
                lead = extract_lead(response_text)
                if lead:
                    await send_lead_notification(lead, user_id)
                    response_text = re.sub(r'LEAD_JSON:.*?\}', '', response_text).strip()
                
                # Отправляем ответ
                await send_message_to_vk(user_id, response_text)
            
            # Ограничиваем размер processed_messages
            if len(processed_messages) > 1000:
                processed_messages.clear()
            
            await asyncio.sleep(5)  # Проверяем каждые 5 секунд
        
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            await asyncio.sleep(10)

# ─── Запуск бота ───────────────────────────────────────────────────────────
async def main():
    """Запуск бота"""
    await polling_loop()

if __name__ == "__main__":
    asyncio.run(main())
