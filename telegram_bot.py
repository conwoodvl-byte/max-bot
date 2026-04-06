#!/usr/bin/env python3
"""
AutoProfi Asia Telegram Bot v2.0
- Диалог с DeepSeek AI (Дмитрий)
- Сбор заявок (10 параметров + телефон)
- Уведомления Павлу при новых заявках
- Продолжение диалога после заявки
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

from openai import AsyncOpenAI

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Конфигурация ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = "8552742401:AAFLR2KvB7q2QPJ2Hw165BiCEqdg_rS7hys"
DEEPSEEK_KEY = "sk-6790bd7c97f84e6f816899e78c911c9f"
PAVEL_CHAT_ID = 532718681

# ─── Инициализация ──────────────────────────────────────────────────────────
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
deepseek = AsyncOpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

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

# ─── FSM (Finite State Machine) ─────────────────────────────────────────────
class ChatState(StatesGroup):
    chatting = State()

# ─── Клавиатуры ────────────────────────────────────────────────────────────
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Подобрать автомобиль", callback_data="start_chat")],
        [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/pavel_autoprofiasia")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="go_home")],
    ])

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

async def send_lead_to_pavel(lead: Dict[str, Any], user: types.User):
    """Отправить заявку Павлу"""
    username_display = f"@{user.username}" if user.username else f"ID {user.id}"
    text = (
        f"<b>🔔 НОВАЯ ЗАЯВКА!</b>\n\n"
        f"<b>Клиент:</b> {username_display} ({user.full_name})\n"
        f"<b>Страна:</b> {lead.get('country', '—').upper()}\n"
        f"<b>Марка:</b> {lead.get('make', '—')}\n"
        f"<b>Модель:</b> {lead.get('model', '—')}\n"
        f"<b>Год:</b> {lead.get('year', '—')}\n"
        f"<b>Объём:</b> {lead.get('engine_volume', '—')} куб.см\n"
        f"<b>Мощность:</b> {lead.get('engine_power', '—')} л.с.\n"
        f"<b>Цвет:</b> {lead.get('color', '—')}\n"
        f"<b>Пробег до:</b> {lead.get('mileage', '—')} км\n"
        f"<b>Привод:</b> {lead.get('drive_type', '—')}\n"
        f"<b>📞 Телефон:</b> {lead.get('phone', 'не указан')}"
    )
    try:
        await bot.send_message(PAVEL_CHAT_ID, text)
        logger.info(f"Lead sent to Pavel: {lead}")
    except Exception as e:
        logger.error(f"Error sending lead to Pavel: {e}")

# ─── Обработчики команд ────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Команда /start"""
    await message.answer(
        f"Привет! 👋 Я Дмитрий, менеджер компании AutoProfi Asia.\n\n"
        f"Помогу вам подобрать идеальный автомобиль из Японии, Кореи или Китая! 🚗",
        reply_markup=main_keyboard()
    )
    logger.info(f"User {message.from_user.id} started bot")

@dp.callback_query(F.data == "start_chat")
async def start_chat(query: types.CallbackQuery, state: FSMContext):
    """Начать диалог"""
    await query.answer()
    await query.message.edit_text(
        "Отлично! Давайте начнём. Какую страну вы предпочитаете?\n\n"
        "Япония 🇯🇵 | Корея 🇰🇷 | Китай 🇨🇳",
        reply_markup=None
    )
    await state.set_state(ChatState.chatting)
    # Инициализируем историю
    await state.update_data(history=[])
    logger.info(f"User {query.from_user.id} started chat")

@dp.message(ChatState.chatting)
async def chat_handler(message: types.Message, state: FSMContext):
    """Обработчик сообщений в режиме чата"""
    user_text = message.text
    data = await state.get_data()
    history = data.get('history', [])
    
    # Добавляем сообщение в историю
    history.append({"role": "user", "content": user_text})
    
    # Показываем "печатает..."
    async with message.bot.session.get_session() as session:
        await message.bot.send_chat_action(message.chat.id, "typing")
    
    # Получаем ответ от DeepSeek
    response_text = await ask_deepseek(history)
    
    # Добавляем ответ в историю
    history.append({"role": "assistant", "content": response_text})
    
    # Сохраняем историю
    await state.update_data(history=history[-20:])  # Храним последние 20 сообщений
    
    # Проверяем есть ли заявка в ответе
    lead = extract_lead(response_text)
    if lead:
        # Отправляем заявку Павлу
        await send_lead_to_pavel(lead, message.from_user)
        # Убираем JSON из ответа клиенту
        response_text = re.sub(r'LEAD_JSON:.*?\}', '', response_text).strip()
    
    # Отправляем ответ
    await message.answer(response_text, reply_markup=back_keyboard())
    logger.info(f"User {message.from_user.id}: {user_text[:50]}")

@dp.callback_query(F.data == "go_home")
async def go_home(query: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await query.answer()
    await state.clear()
    await query.message.edit_text(
        "Вы вернулись в главное меню 🏠",
        reply_markup=main_keyboard()
    )

# ─── Запуск бота ───────────────────────────────────────────────────────────
async def main():
    """Запуск бота"""
    logger.info("🤖 Telegram Bot v2.0 запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
