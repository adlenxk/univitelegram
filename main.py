import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
import google.generativeai as genai
from dotenv import load_dotenv
import hashlib
import json
import asyncio
from io import BytesIO
import base64
from PIL import Image
import re
import aiohttp

load_dotenv()


genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')
vision_model = genai.GenerativeModel('gemini-pro-vision')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CUSTOM_SEARCH_ENGINE_ID = os.getenv('CUSTOM_SEARCH_ENGINE_ID')

(GPA, COUNTRY, SAT, IELTS, ADDITIONAL_INFO, SHOWING_UNIVERSITIES, 
 UNIVERSITY_INFO, UNIVERSITY_QUESTIONS) = range(8)

async def get_university_image(uni_name: str) -> BytesIO:
    """Получает изображение университета через Google Custom Search API"""
    try:
        search_query = f"{uni_name} university campus main building"
        
        params = {
            'key': GOOGLE_API_KEY,
            'cx': CUSTOM_SEARCH_ENGINE_ID,
            'q': search_query,
            'searchType': 'image',
            'imgSize': 'large',
            'imgType': 'photo',
            'num': 1 
        }
        

        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.googleapis.com/customsearch/v1', params=params) as response:
                data = await response.json()
                
                if 'items' in data and len(data['items']) > 0:
                    image_url = data['items'][0]['link']
                    

                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            img_data = await img_response.read()
                            return BytesIO(img_data)
                

        return get_placeholder_image()
        
    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return get_placeholder_image()

def get_placeholder_image() -> BytesIO:
    """Создает изображение-заглушку"""
    img = Image.new('RGB', (800, 400), color='white')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr



def clean_json_string(s: str) -> str:
    """Clean and format the string to be valid JSON"""

    match = re.search(r'\{[\s\S]*\}', s)
    if not match:
        return '{}'
    
    json_str = match.group(0)

    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```', '', json_str)
    return json_str
async def handle_university_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка вопросов о университете"""

    loading_message = await update.message.reply_text(
        "🤔 *Анализирую ваш вопрос...*",
        parse_mode='Markdown'
    )
    

    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action="typing"
    )

    question = update.message.text
    selected_uni = context.user_data.get('selected_uni')
    

    await loading_message.edit_text(
        "🔄 *Генерирую подробный ответ...*",
        parse_mode='Markdown'
    )
    
    prompt = f"""
    Вопрос про университет {selected_uni['name']}:
    {question}

    Контекст об университете:
    {json.dumps(selected_uni, ensure_ascii=False)}

    Дай максимально подробный и полезный ответ на вопрос студента, 
    включая конкретные факты, цифры и рекомендации где это уместно.
    """
    
    try:
        response = model.generate_content(prompt)
        

        await loading_message.delete()
        

        response_text = (
            f"*Ответ на ваш вопрос про {selected_uni['name']}:*\n\n"
            f"{response.text}\n\n"
            f"_Задайте ещё вопрос или вернитесь к информации об университете_"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("↩️ Вернуться к информации", callback_data="back"),
                InlineKeyboardButton("❓ Задать ещё вопрос", callback_data=f"q_{selected_uni['name']}")
            ]
        ]
        
        await update.message.reply_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return SHOWING_UNIVERSITIES
        
    except Exception as e:

        await loading_message.delete()
        print(f"Error: {str(e)}")
        
        error_keyboard = [
            [
                InlineKeyboardButton("🔄 Попробовать снова", callback_data=f"q_{selected_uni['name']}"),
                InlineKeyboardButton("↩️ Вернуться назад", callback_data="back")
            ]
        ]
        
        await update.message.reply_text(
            "❌ *Произошла ошибка при обработке вопроса*\n"
            "Попробуйте сформулировать вопрос иначе или вернитесь к информации об университете",
            reply_markup=InlineKeyboardMarkup(error_keyboard),
            parse_mode='Markdown'
        )
        return SHOWING_UNIVERSITIES
async def process_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка информации о студенте и подбор университетов"""
    
    loading_message = await update.message.reply_text(
        "*🔄 Анализируем ваши данные и подбираем университеты...*",
        parse_mode='Markdown'
    )
    
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action="typing"
    )
    
    user_info = context.user_data
    location_prompt = f"в городе {user_info.get('country', 'Не указано')}" if user_info.get('country') else ""
    
    prompt = f"""
    На основе данных студента создай JSON строго в следующем формате с информацией о трех подходящих университетах {location_prompt}.
    Важно: выбирай только реально существующие университеты в указанном городе/стране.

    {{
        "universities": [
            {{
                "name": "Название университета",
                "description": "Описание университета",
                "requirements": {{
                    "gpa": "3.0",
                    "sat": "1200",
                    "ielts": "6.5",
                    "documents": "Список документов",
                    "additional": "Доп требования"
                }},
                "deadlines": {{
                    "early": "Дата",
                    "regular": "Дата",
                    "rolling": "Да/Нет"
                }},
                "tuition": {{
                    "amount": "10000",
                    "currency": "USD"
                }},
                "programs": [
                    "Программа 1",
                    "Программа 2",
                    "Программа 3"
                ],
                "scholarships": {{
                    "types": [
                        "Стипендия 1",
                        "Стипендия 2"
                    ],
                    "amounts": [
                        "Сумма 1",
                        "Сумма 2"
                    ],
                    "requirements": "Требования для стипендий"
                }}
            }}
        ]
    }}

    Данные студента:
    GPA: {user_info.get('gpa', 'Не указано')}
    Страна/Город: {user_info.get('country', 'Не указано')}
    SAT: {user_info.get('sat', 'Не указано')}
    IELTS: {user_info.get('ielts', 'Не указано')}
    Дополнительная информация: {user_info.get('additional_info', 'Не указано')}

    Верни только JSON без дополнительного текста.
    """
    
    try:

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        

        json_str = clean_json_string(response_text)
        data = json.loads(json_str)
        universities = data.get('universities', [])
        
        if not universities:
            raise ValueError("No universities found in response")
        
        await loading_message.delete()
        

        await update.message.reply_text(
            "🎯 *Найдены подходящие университеты!*\n"
            "_Нажмите на кнопки под каждым университетом для подробной информации_",
            parse_mode='Markdown'
        )
        
        user_universities = {}
        
        for uni in universities:
            try:
                uni_id = generate_uni_id(uni['name'])
                user_universities[uni_id] = uni
                
                programs_text = "\n".join([f"• {prog}" for prog in uni.get('programs', [])])
                

                main_info = (
                    f"🏛 *{uni['name']}*\n\n"
                    f"📝 *Описание:*\n{uni['description']}\n\n"
                    f"🎓 *Доступные программы:*\n{programs_text}\n\n"
                    f"💰 *Стоимость обучения:*\n"
                    f"{uni['tuition']['amount']} {uni['tuition']['currency']}/год"
                )
                

                keyboard = [
                    [
                        InlineKeyboardButton("📋 Требования", callback_data=f"r_{uni_id}"),
                        InlineKeyboardButton("💰 Стипендии", callback_data=f"s_{uni_id}")
                    ],
                    [
                        InlineKeyboardButton("❓ Задать вопрос", callback_data=f"q_{uni_id}"),
                        InlineKeyboardButton("📚 Подробнее", callback_data=f"u_{uni_id}")
                    ]
                ]
                
                img_data = await get_university_image(uni['name'])
                await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=img_data,
                    caption=main_info,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error processing university {uni['name']}: {str(e)}")
                continue
        
        context.user_data['universities'] = user_universities
        
        final_keyboard = [
            [InlineKeyboardButton("🔄 Начать поиск заново", callback_data="restart")]
        ]
        
        await update.message.reply_text(
            "💡 *Выберите университет выше для получения подробной информации*",
            reply_markup=InlineKeyboardMarkup(final_keyboard),
            parse_mode='Markdown'
        )
        
        return SHOWING_UNIVERSITIES
        
    except Exception as e:
        print(f"Error in process_info: {str(e)}")
        await loading_message.delete()
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте еще раз с командой /start",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def handle_scholarship_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        uni_id = query.data.split('_')[1]
        universities = context.user_data.get('universities', {})
        selected_uni = universities.get(uni_id)
        
        if selected_uni:
            scholarships_text = (
                f"💰 *Стипендии в {selected_uni['name']}*\n\n"
                f"{selected_uni.get('scholarships', 'Информация о стипендиях не указана')}\n\n"
                f"💡 *Как получить стипендию:*\n"
                f"• Подайте заявку заранее\n"
                f"• Подготовьте все необходимые документы\n"
                f"• Следите за дедлайнами\n"
                f"• Свяжитесь с финансовым отделом университета"
            )
            
            keyboard = [
                [InlineKeyboardButton("↩️ Назад", callback_data=f"u_{uni_id}")],
                [InlineKeyboardButton("❓ Задать вопрос о стипендиях", callback_data=f"q_{uni_id}")]
            ]
            
            await query.message.edit_text(
                scholarships_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        return SHOWING_UNIVERSITIES
        
    except Exception as e:
        print(f"Error in handle_scholarship_info: {str(e)}")
        await query.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")
        return SHOWING_UNIVERSITIES



async def handle_university_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "restart":
        await query.message.reply_text("🔄 Начнем сначала! Введите ваш GPA:")
        return GPA
    
    try:
        if '_' not in query.data:
            return SHOWING_UNIVERSITIES
            
        action, uni_id = query.data.split('_')
        universities = context.user_data.get('universities', {})
        selected_uni = universities.get(uni_id)
        
        if not selected_uni:
            await query.message.reply_text("❌ Информация не найдена")
            return SHOWING_UNIVERSITIES

        if action == 'q': 
            context.user_data['selected_uni'] = selected_uni
            await query.message.reply_text(
                f"❓ *Задайте ваш вопрос про {selected_uni['name']}*\n\n"
                "Я постараюсь предоставить подробную информацию по интересующей вас теме.",
                parse_mode='Markdown'
            )
            return UNIVERSITY_QUESTIONS
        
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data="back")]]
        
        if action == 'r':  
            requirements = selected_uni['requirements']
            deadlines = selected_uni['deadlines']
            info_text = (
                f"📋 *Требования для поступления в {selected_uni['name']}*\n\n"
                f"📊 *GPA:* {requirements['gpa']}\n"
                f"📝 *SAT:* {requirements['sat']}\n"
                f"🌐 *IELTS:* {requirements['ielts']}\n\n"
                f"📎 *Необходимые документы:*\n{requirements['documents']}\n\n"
                f"ℹ️ *Дополнительно:*\n{requirements['additional']}\n\n"
                f"📅 *Сроки подачи:*\n"
                f"• Ранняя подача: {deadlines['early']}\n"
                f"• Обычная подача: {deadlines['regular']}\n"
                f"• Rolling admission: {deadlines['rolling']}"
            )
            
            await query.message.reply_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif action == 's':  
            scholarships = selected_uni['scholarships']
            info_text = (
                f"💰 *Стипендии в {selected_uni['name']}*\n\n"
                f"📋 *Доступные виды стипендий:*\n"
                + "\n".join([f"• {s}" for s in scholarships['types']]) + "\n\n"
                f"💵 *Размеры стипендий:*\n"
                + "\n".join([f"• {a}" for a in scholarships['amounts']]) + "\n\n"
                f"✅ *Требования для получения:*\n{scholarships['requirements']}"
            )
            
            await query.message.reply_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif action == 'u':  
            programs_text = "\n".join([f"• {prog}" for prog in selected_uni['programs']])
            info_text = (
                f"🏛 *{selected_uni['name']}*\n\n"
                f"📝 *Описание:*\n{selected_uni['description']}\n\n"
                f"🎓 *Программы обучения:*\n{programs_text}\n\n"
                f"💰 *Стоимость обучения:*\n"
                f"{selected_uni['tuition']['amount']} {selected_uni['tuition']['currency']}/год"
            )
            
            await query.message.reply_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return UNIVERSITY_INFO
        
    except Exception as e:
        print(f"Error in handle_university_selection: {str(e)}")
        await query.message.reply_text(
            "❌ Произошла ошибка. Попробуйте еще раз с командой /start",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Начать сначала", callback_data="restart")
            ]])
        )
        return ConversationHandler.END


async def handle_question_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_uni = context.user_data.get('selected_uni')
    if not selected_uni:
        await query.message.reply_text("❌ Информация не найдена")
        return SHOWING_UNIVERSITIES
        
    history = context.user_data.get('question_history', {}).get(selected_uni['name'], [])
    
    if not history:
        await query.message.reply_text(
            "📝 История вопросов пуста",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="back")
            ]])
        )
        return SHOWING_UNIVERSITIES
    

    history_text = f"📝 *История вопросов про {selected_uni['name']}:*\n\n"
    for i, question in enumerate(history, 1):
        history_text += f"{i}. {question}\n"
    
    keyboard = [
        [InlineKeyboardButton("❓ Задать новый вопрос", callback_data=f"q_{selected_uni['name']}")],
        [InlineKeyboardButton("🗑️ Очистить историю", callback_data="clear_history")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back")]
    ]
    
    await query.message.reply_text(
        history_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return SHOWING_UNIVERSITIES


async def clear_question_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_uni = context.user_data.get('selected_uni')
    if selected_uni and selected_uni['name'] in context.user_data.get('question_history', {}):
        context.user_data['question_history'][selected_uni['name']] = []
    
    await query.message.reply_text(
        "🗑️ История вопросов очищена",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Назад", callback_data="back")
        ]])
    )
    return SHOWING_UNIVERSITIES
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало разговора и запрос GPA"""
    context.user_data.clear()  
    context.user_data['state'] = GPA  
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе подобрать подходящие университеты!\n\n"
        "Пожалуйста, введи свой GPA (например, 3.5)\n"
        "Если хочешь пропустить этот шаг, используй команду /skip"
    )
    return GPA

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск текущего шага"""
    current_state = context.user_data.get('state', GPA)
    
    next_states = {
        GPA: (COUNTRY, "Введи страну, где хочешь учиться (или /skip):"),
        COUNTRY: (SAT, "Введи свой балл SAT (или /skip):"),
        SAT: (IELTS, "Введи свой балл IELTS (или /skip):"),
        IELTS: (ADDITIONAL_INFO, "Добавь дополнительную информацию о себе (или /skip):")
    }
    
    if current_state in next_states:
        next_state, message = next_states[current_state]
        context.user_data['state'] = next_state
        await update.message.reply_text(message)
        return next_state
    
    return await process_info(update, context)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка пользовательского ввода"""
    user_input = update.message.text
    current_state = context.user_data.get('state', GPA)
    

    state_keys = {
        GPA: 'gpa',
        COUNTRY: 'country',
        SAT: 'sat',
        IELTS: 'ielts',
        ADDITIONAL_INFO: 'additional_info'
    }
    

    if current_state in state_keys:
        context.user_data[state_keys[current_state]] = user_input
    
 
    next_states = {
        GPA: (COUNTRY, "Отлично! Теперь введи страну, где хочешь учиться:"),
        COUNTRY: (SAT, "Хорошо! Теперь введи свой балл SAT (или /skip):"),
        SAT: (IELTS, "Отлично! Теперь введи свой балл IELTS (или /skip):"),
        IELTS: (ADDITIONAL_INFO, "Хорошо! Добавь любую дополнительную информацию о себе (или /skip):")
    }
    
    if current_state in next_states:
        next_state, message = next_states[current_state]
        context.user_data['state'] = next_state
        await update.message.reply_text(message)
        return next_state
    
    return await process_info(update, context)

def generate_uni_id(uni_name: str) -> str:
    """Генерирует короткий идентификатор для университета"""
    return hashlib.md5(uni_name.encode()).hexdigest()[:8]


async def handle_back_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки Назад"""
    query = update.callback_query
    await query.answer()

    universities = context.user_data.get('universities', {})
    if not universities:
        await query.message.reply_text(
            "❌ Информация о университетах не найдена. Начните поиск заново: /start"
        )
        return ConversationHandler.END

    message_text = "🎯 *Выберите университет для получения информации:*\n\n"

    for uni_id, uni in universities.items():
        programs_text = "\n".join([f"• {prog}" for prog in uni.get('programs', [])])
        
        uni_info = (
            f"🏛 *{uni['name']}*\n\n"
            f"📝 *Описание:*\n{uni['description']}\n\n"
            f"🎓 *Доступные программы:*\n{programs_text}\n\n"
            f"💰 *Стоимость обучения:*\n"
            f"{uni['tuition']['amount']} {uni['tuition']['currency']}/год"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📋 Требования", callback_data=f"r_{uni_id}"),
                InlineKeyboardButton("💰 Стипендии", callback_data=f"s_{uni_id}")
            ],
            [
                InlineKeyboardButton("❓ Задать вопрос", callback_data=f"q_{uni_id}"),
                InlineKeyboardButton("📚 Подробнее", callback_data=f"u_{uni_id}")
            ]
        ]
        
        try:
            img_data = await get_university_image(uni['name'])
            await context.bot.send_photo(
                chat_id=update.callback_query.message.chat_id,
                photo=img_data,
                caption=uni_info,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error sending photo for {uni['name']}: {str(e)}")
            await query.message.reply_text(
                uni_info,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    final_keyboard = [[InlineKeyboardButton("🔄 Начать поиск заново", callback_data="restart")]]
    await query.message.reply_text(
        "💡 *Выберите действие для интересующего вас университета*",
        reply_markup=InlineKeyboardMarkup(final_keyboard),
        parse_mode='Markdown'
    )
    
    return SHOWING_UNIVERSITIES
async def handle_university_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    selected_uni = context.user_data.get('selected_uni')
    
    prompt = f"""
    Вопрос про университет {selected_uni['name']}:
    {question}

    Контекст об университете:
    {json.dumps(selected_uni, ensure_ascii=False)}

    Дай максимально подробный и полезный ответ на вопрос студента.
    """
    
    try:
        response = model.generate_content(prompt)
        
        keyboard = [[InlineKeyboardButton("↩️ Вернуться к информации", callback_data="back")]]
        
        await update.message.reply_text(
            f"*Ответ на ваш вопрос про {selected_uni['name']}:*\n\n"
            f"{response.text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return SHOWING_UNIVERSITIES
        
    except Exception as e:
        print(f"Error: {str(e)}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке вопроса. Попробуйте спросить иначе."
        )
        return SHOWING_UNIVERSITIES
async def update_loading_message(message, initial_text="🔄 Загрузка"):
    loading_states = [
        f"{initial_text}",
        f"{initial_text}.",
        f"{initial_text}..",
        f"{initial_text}..."
    ]
    
    for state in loading_states:
        try:
            await message.edit_text(state)
            await asyncio.sleep(0.5)
        except Exception:
            break


def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GPA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input),
                CommandHandler('skip', skip)
            ],
            COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input),
                CommandHandler('skip', skip)
            ],
            SAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input),
                CommandHandler('skip', skip)
            ],
            IELTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input),
                CommandHandler('skip', skip)
            ],
            ADDITIONAL_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input),
                CommandHandler('skip', skip)
            ],
            SHOWING_UNIVERSITIES: [
                CallbackQueryHandler(handle_back_action, pattern="^back$"),
                CallbackQueryHandler(handle_university_selection)
            ],
            UNIVERSITY_INFO: [
                CallbackQueryHandler(handle_back_action, pattern="^back$"),
                CallbackQueryHandler(handle_university_selection)
            ],
            UNIVERSITY_QUESTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_university_question),
                CallbackQueryHandler(handle_back_action, pattern="^back$")
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    application.run_polling()
if __name__ == '__main__':
    main()