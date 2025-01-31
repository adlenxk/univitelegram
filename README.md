
# Skillset AI Chat Bot Development Challenge 2025
# 🤖 UNIVI - Telegram Bot для Подбора Университетов с AI

## 📌 Описание проекта
UNIVI - этот бот для Telegram помогает студентам подобрать подходящие университеты на основе их академических данных и предпочтений. Используя API Google Custom Search и AI-модель Gemini, бот предоставляет подробную информацию об университетах, включая требования к поступлению, стоимость обучения и доступные стипендии.

## 🚀 Функционал
✅ Интерактивный подбор университетов по GPA, SAT, IELTS и другим параметрам  
✅ Запрос изображений кампусов университетов через Google API  
✅ Детальная информация о программах, стоимости обучения и стипендиях  
✅ Возможность задавать вопросы и получать AI-ответы о конкретных университетах  
✅ Интерактивные inline-кнопки для навигации по информации  
✅ Поддержка истории запросов и управления данными пользователя  

## 🛠️ Используемые технологии
- **Python** (основной язык)
- **Telegram Bot API** (бот для Telegram)
- **Google Custom Search API** (поиск изображений)
- **Generative AI (Gemini)** (обработка запросов и генерация ответов)
- **aiohttp** (асинхронные HTTP-запросы)
- **Pillow** (работа с изображениями)

## 🔧 Установка и запуск
### 1️⃣ Установка зависимостей
Убедитесь, что у вас установлен Python 3.8+ и выполните команду:
```bash
pip install -r requirements.txt
```

### 2️⃣ Настройка переменных окружения
Создайте файл `.env` и добавьте ключи API:
```
TELEGRAM_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_API_KEY=your_google_api_key 
CUSTOM_SEARCH_ENGINE_ID=your_search_engine_id (если не можете взять апишник свяжитесь со мной @alqzow)
```

### 3️⃣ Запуск бота
```bash
python main.py
```

## 🏗️ Структура кода
```
📂 project_root
├── 📜 main.py  # Основной код бота
├── 📜 requirements.txt  # Список зависимостей
├── 📜 .env  # Переменные окружения
```

## 🏆 Примеры команд
- `/start` – Начать подбор университетов
- `/skip` – Пропустить текущий шаг
- Ввод GPA, страны, SAT, IELTS – Фильтрация университетов
- Интерактивные кнопки – Запрос требований, стипендий, вопросов и изображений

## 🤝 Контакты и авторы
Автор: Вахит Аль - Азим
Telegram: Alqzow  
