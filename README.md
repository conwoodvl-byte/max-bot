# AutoProfi Asia MAX Bot

Бот для MAX мессенджера с интеграцией DeepSeek AI. Помогает клиентам с подбором автомобилей из Кореи, Японии и Китая.

## Возможности

- ✅ Подбор автомобилей
- ✅ Информация о ценах и доставке
- ✅ Консультации по запчастям и сервису
- ✅ История диалогов
- ✅ Работает 24/7

## Развёртывание на Render

1. Нажми кнопку "Deploy" ниже
2. Выбери GitHub репозиторий
3. Добавь переменные окружения:
   - `MAX_BOT_TOKEN` - токен бота MAX
   - `DEEPSEEK_API_KEY` - API ключ DeepSeek

4. Нажми "Deploy"

## Переменные окружения

```
MAX_BOT_TOKEN=f9LHodD0cOJu6fhHJWrlK12JgPI--lwLp9a3BCjv15QOjun6WOmrntPxqbyZHn6iDNybJePw90nJRxwEU2Y3
DEEPSEEK_API_KEY=sk-e2ada56f857e435196a2c126a21d5271
```

## Endpoints

- `GET /` - Информация о сервисе
- `GET /health` - Проверка здоровья
- `POST /webhook` - Получение сообщений от MAX

## Локальный запуск

```bash
pip install -r requirements.txt
python main.py
```

Сервер запустится на `http://localhost:5000`

## Тестирование

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "text": "Привет!"}'
```

## Контакты

- Email: info@autoprofasia.ru
- Telegram: @autoprofasia
