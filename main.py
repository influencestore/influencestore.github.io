import logging
import os
import io
import time
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TimedOut, NetworkError, TelegramError
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Функция для повторных попыток при ошибках сети
async def retry_telegram_request(func, *args, max_retries=3, initial_delay=1, **kwargs):
    """Выполняет функцию с повторными попытками при ошибках сети.
    
    Args:
        func: Асинхронная функция для выполнения
        *args: Аргументы для функции
        max_retries: Максимальное количество повторных попыток
        initial_delay: Начальная задержка перед повторной попыткой (в секундах)
        **kwargs: Именованные аргументы для функции
        
    Returns:
        Результат выполнения функции или None в случае неудачи
    """
    retries = 0
    delay = initial_delay
    
    while retries <= max_retries:
        try:
            return await func(*args, **kwargs)
        except (TimedOut, NetworkError) as e:
            retries += 1
            if retries > max_retries:
                logging.error(f"Превышено максимальное количество попыток. Последняя ошибка: {e}")
                raise
            
            logging.warning(f"Ошибка сети при выполнении запроса (попытка {retries}/{max_retries}): {e}")
            logging.info(f"Повторная попытка через {delay} сек...")
            
            await asyncio.sleep(delay)
            # Экспоненциальная задержка с небольшим случайным компонентом
            delay = delay * 2

# Токен вашего бота (замените на свой)
TOKEN = '8131594462:AAEoRFyev7tBQ4PM8zvXmN0sLILRyg2WRNM'

# Словарь для хранения состояний пользователей
user_states = {}

# Константы для состояний
STATE_WAITING_FOR_AF_CLASSIC_LINK = 'waiting_for_af_classic_link'
STATE_WAITING_FOR_AF_QUICK_LINK = 'waiting_for_af_quick_link'
STATE_WAITING_FOR_FP_CLASSIC_LINK = 'waiting_for_fp_classic_link'
STATE_WAITING_FOR_FP_REGION_ERROR_LINK = 'waiting_for_fp_region_error_link'
STATE_WAITING_FOR_WANMEI_ID = 'waiting_for_wanmei_id'
STATE_WAITING_FOR_QR_FRIEND_LINK = 'waiting_for_qr_friend_link'
STATE_WAITING_FOR_QR_FRIEND_TIMESTAMP = 'waiting_for_qr_friend_timestamp'
STATE_WAITING_FOR_CS2_CODE_FAKE_LINK = 'waiting_for_cs2_code_fake_link'  # Новое состояние

# Константы для состояний Ban MM
STATE_WAITING_FOR_BAN_30MIN_PHOTO = 'waiting_for_ban_30min_photo'
STATE_WAITING_FOR_BAN_1HOUR_PHOTO = 'waiting_for_ban_1hour_photo'
STATE_WAITING_FOR_BAN_2HOURS_PHOTO = 'waiting_for_ban_2hours_photo'
STATE_WAITING_FOR_BAN_24HOURS_PHOTO = 'waiting_for_ban_24hours_photo'
STATE_WAITING_FOR_BAN_7DAYS_PHOTO = 'waiting_for_ban_7days_photo'

# Add this constant with other states
STATE_WAITING_FOR_CS2_CODE_NOT_FOUND_LINK = 'waiting_for_cs2_code_not_found_link'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👥 Add Friend", callback_data='add_friend'),
         InlineKeyboardButton("⚠️ Ban MM", callback_data='ban_mm')],
        [InlineKeyboardButton("🔎 Friend Page", callback_data='friend_page'),
         InlineKeyboardButton("🔑 CS2 Code", callback_data='cs2_code')],
        [InlineKeyboardButton("🎫 QR Friend Page", callback_data='qr_friend'),
         InlineKeyboardButton("🚫 Ошибка Wanmei", callback_data='wanmei_error')],
        [InlineKeyboardButton("⚪️ DOBIV BY A777MP", callback_data='dobiv_by_a777mp'),
         InlineKeyboardButton("💬 Купить WECHAT/QQ", callback_data='buy_wechat_qq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = "👋 Привет, воркер! Это твой мульти-инструмент для ворка!\n\n" \
               "📍 Спасибо, что доверяете нам!\n" \
               "❤️ [Поддержать бота](https://t.me/send?start=IVufKXTbCfU1)"
                   
    
    await retry_telegram_request(
        update.message.reply_text,
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Проверяем, есть ли текст в сообщении для редактирования
    has_text = hasattr(query.message, 'text') and query.message.text
    
    # Функция для отправки нового сообщения вместо редактирования, если нет текста
    async def safe_edit_message(message_text, reply_markup, parse_mode=None, disable_web_page_preview=None):
        if has_text:
            try:
                await retry_telegram_request(
                    query.message.edit_text,
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview
                )
            except Exception as e:
                logging.error(f"Ошибка при редактировании сообщения: {e}")
                # Если не удалось отредактировать, пробуем отправить новое сообщение
                await retry_telegram_request(
                    query.message.reply_text,
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview
                )
        else:
            # Если нет текста (например, в сообщении с фото), отправляем новое сообщение
            await retry_telegram_request(
                query.message.reply_text,
                message_text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
    
    if query.data == 'add_friend':
        keyboard = [
            [InlineKeyboardButton("📝 AF Classic", callback_data='af_classic'),
             InlineKeyboardButton("⚡️ AF Quick Link", callback_data='af_quick_link')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message("💫 Выбери, что тебе нужно!", reply_markup)
    elif query.data == 'af_classic':
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_add_friend')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message("🔗 Отправь ссылку на профиль мамонта:", reply_markup)
        
        # Устанавливаем состояние пользователя для ожидания ссылки
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_AF_CLASSIC_LINK
    elif query.data == 'af_quick_link':
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_add_friend')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message("🔗 Отправь ссылку на профиль мамонта:", reply_markup)
        
        # Устанавливаем состояние пользователя для ожидания ссылки
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_AF_QUICK_LINK
    elif query.data == 'back_to_add_friend':
        keyboard = [
            [InlineKeyboardButton("📝 AF Classic", callback_data='af_classic'),
             InlineKeyboardButton("⚡️ AF Quick Link", callback_data='af_quick_link')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message("💫 Выбери, что тебе нужно!", reply_markup)
    elif query.data == 'back_to_main':
        # Используем edit_message_text вместо вызова start, так как мы работаем с callback_query
        keyboard = [
            [InlineKeyboardButton("👥 Add Friend", callback_data='add_friend'),
             InlineKeyboardButton("⚠️ Ban MM", callback_data='ban_mm')],
            [InlineKeyboardButton("🔎 Friend Page", callback_data='friend_page'),
             InlineKeyboardButton("🔑 CS2 Code", callback_data='cs2_code')],
            [InlineKeyboardButton("🎫 QR Friend Page", callback_data='qr_friend'),
             InlineKeyboardButton("🚫 Ошибка Wanmei", callback_data='wanmei_error')],
            [InlineKeyboardButton("⚪️ DOBIV BY A777MP", callback_data='dobiv_by_a777mp'),
             InlineKeyboardButton("💬 Купить WECHAT/QQ", callback_data='buy_wechat_qq')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = "👋 Привет, воркер! Это твой мульти-инструмент для ворка!\n\n" \
                       "📍 Спасибо, что доверяете нам!\n" \
                       "❤️ [Поддержать бота](https://t.me/send?start=IVufKXTbCfU1)\n" 
       
        
        await safe_edit_message(welcome_text, reply_markup, parse_mode='Markdown', disable_web_page_preview=True)
    elif query.data == 'ban_mm':
        keyboard = [
            [InlineKeyboardButton("⏱ 30 минут", callback_data='ban_30min'),
             InlineKeyboardButton("⏱ 1 час", callback_data='ban_1hour')],
            [InlineKeyboardButton("⏱ 2 часа", callback_data='ban_2hours'),
             InlineKeyboardButton("⏱ 24 часа", callback_data='ban_24hours')],
            [InlineKeyboardButton("⏱ 7 дней", callback_data='ban_7days')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        warning_text = "⚠️ Ban MM\n🔒 Отрисовка бана в MM\n\n❗️ CS2 должна быть на английском и в формате 16:9\n\n📌 Выбери длительность твоего фейкового бана!"
        await safe_edit_message(warning_text, reply_markup)
    elif query.data == 'friend_page':
        keyboard = [
            [InlineKeyboardButton("📝 FP Classic", callback_data='fp_classic')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message("💫 Выбери, что тебе нужно!", reply_markup)
    elif query.data == 'fp_classic':
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "💫 Отправь fake-invite ссылку:\n\n❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки"
        await safe_edit_message(message_text, reply_markup)
    
        # Устанавливаем состояние пользователя для ожидания ссылки
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_FP_CLASSIC_LINK
    elif query.data == 'fp_region_error':
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "💫 Отправь fake-invite ссылку:\n\n❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки"
        await safe_edit_message(message_text, reply_markup)
        
        # Устанавливаем состояние пользователя для ожидания ссылки
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_FP_REGION_ERROR_LINK
    elif query.data == 'back_to_friend_page':
        keyboard = [
            [InlineKeyboardButton("📝 FP Classic", callback_data='fp_classic'),
             InlineKeyboardButton("🌐 FP Region Error", callback_data='fp_region_error')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message("💫 Выбери, что тебе нужно!", reply_markup)
    elif query.data == 'cs2_code':
        keyboard = [
            [InlineKeyboardButton("🔐 CS2 Code Fake", callback_data='cs2_code_fake'),
             InlineKeyboardButton("⛳️ CS2 Code Not Found", callback_data='cs2_code_not_found')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message(
            "🔐 CS2 Code Fake\n"
            "          ╰ отрисовка невалидного кода CS2\n"
            "⛳️ CS2 Code Not Found\n"
            "           ╰ отрисовка ненайденного кода мамонта\n\n"
            "🎯 Выбери, что тебе нужно!", 
            reply_markup
        )
    
    elif query.data == 'cs2_code_fake':
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "👀 Отправь fake-invite ссылку:\n\n❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n❗️ Проверяйте так всегда, ибо клоака — вещь неудобная"
        await safe_edit_message(message_text, reply_markup)
        
        # Устанавливаем состояние пользователя для ожидания ссылки
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_CS2_CODE_FAKE_LINK
    
    elif query.data == 'back_to_cs2_code':
        keyboard = [
            [InlineKeyboardButton("🔐 CS2 Code Fake", callback_data='cs2_code_fake'),
             InlineKeyboardButton("⛳️ CS2 Code Not Found", callback_data='cs2_code_not_found')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message(
            "🔐 CS2 Code Fake\n"
            "          ╰ отрисовка невалидного кода CS2\n"
            "⛳️ CS2 Code Not Found\n"
            "           ╰ отрисовка ненайденного кода мамонта\n\n"
            "🎯 Выбери, что тебе нужно!", 
            reply_markup
        )
    
    # Modify the cs2_code_not_found handler in button_callback function
    elif query.data == 'cs2_code_not_found':
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "👀 Отправь fake-invite ссылку:\n\n❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n❗️ Проверяйте так всегда, ибо клоака — вещь неудобная"
        await safe_edit_message(message_text, reply_markup)
        
        # Set user state
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_CS2_CODE_NOT_FOUND_LINK
    elif query.data == 'qr_friend':
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "🎫 QR Friend Page\n📝 отрисовка QR-кода на странице друзей с твоим фейком\n\n💫 Отправь fake-invite ссылку:\n\n❗️ Для корректной работы отрисовщика, сначала зайдите сами на ссылку и следом скопируйте адрес из адресной строки\n\n❗️ Проверяйте так всегда, ибо клоака — вещь неудобная"
        await safe_edit_message(message_text, reply_markup)
        
        # Устанавливаем состояние пользователя для ожидания ссылки
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_QR_FRIEND_LINK
        print(f"Установлено состояние {STATE_WAITING_FOR_QR_FRIEND_LINK} для пользователя {user_id}")
    elif query.data == 'wanmei_error':
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "⚠️ Ошибка Wanmei\n🔒 отрисовка ненайденного ID мамонта в меню\n\n📱 Отправьте ID мамонта для генерации скриншота:"
        await safe_edit_message(message_text, reply_markup)
        
        # Устанавливаем состояние пользователя для ожидания ID мамонта
        user_id = query.from_user.id
        user_states[user_id] = STATE_WAITING_FOR_WANMEI_ID
    elif query.data == 'dobiv_by_a777mp':
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        dobiv_text = "*Статичный процент на любую сумму - 10%*\n\n" \
                   "*Добив через Wechat/Telegram - 15%*\n\n" \
                   "*Работаем по любому ГЕО*\n\n" \
                   "*Уникальный способ добива*\n\n" \
                   "*Чистим карты/кошельки(70/30% ваши)*\n\n" \
                   "*ВСЕ ДОБИТЫЕ СЕССИИ ВЫ МОЖЕТЕ ПОСМОТРЕТЬ* [ТУТ](https://t.me/a777mpdobiv) \n\n" \
                   "*ТЕМА* [ZELENKA](https://lolz.live/threads/8355679)\n\n" \
                   "*ТЕМА* [YOUHACK](https://youhack.top/threads/940448)\n\n" \
                   "*Контакт : @dobiv178*"
        await safe_edit_message(dobiv_text, reply_markup, parse_mode='Markdown', disable_web_page_preview=True)
    elif query.data == 'buy_wechat_qq':
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("💬 Для покупки WECHAT/QQ аккаунтов обратитесь к администратору: @mynameisblood", reply_markup=reply_markup)
    # Удалены обработчики для магазина аккаунтов
    elif query.data in ['ban_30min', 'ban_1hour', 'ban_2hours', 'ban_24hours', 'ban_7days']:
        ban_times = {
            'ban_30min': '30 минут',
            'ban_1hour': '1 час',
            'ban_2hours': '2 часа',
            'ban_24hours': '24 часа',
            'ban_7days': '7 дней'
        }
        # Сохраняем выбранное время бана в состоянии пользователя
        user_id = query.from_user.id
        ban_states = {
            'ban_30min': STATE_WAITING_FOR_BAN_30MIN_PHOTO,
            'ban_1hour': STATE_WAITING_FOR_BAN_1HOUR_PHOTO,
            'ban_2hours': STATE_WAITING_FOR_BAN_2HOURS_PHOTO,
            'ban_24hours': STATE_WAITING_FOR_BAN_24HOURS_PHOTO,
            'ban_7days': STATE_WAITING_FOR_BAN_7DAYS_PHOTO
        }
        user_states[user_id] = ban_states[query.data]
        
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = f"📱 Отправь ФАЙЛОМ полный скриншот из меню CS2 для бана на {ban_times[query.data]}\n\n❗️ Убери галку в пункте \"Сжать изображение\" при отправке скриншота"
        await query.message.edit_text(message_text, reply_markup=reply_markup)

# Обработчик текстовых сообщений и фотографий
# В функции handle_message добавьте следующий блок кода для обработки QR Friend Page ссылок
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Проверяем, есть ли фотография в сообщении
    if update.message.photo and user_id in user_states:
        # Проверяем, ожидаем ли мы фотографию для Ban MM
        ban_states = [
            STATE_WAITING_FOR_BAN_30MIN_PHOTO,
            STATE_WAITING_FOR_BAN_1HOUR_PHOTO,
            STATE_WAITING_FOR_BAN_2HOURS_PHOTO,
            STATE_WAITING_FOR_BAN_24HOURS_PHOTO,
            STATE_WAITING_FOR_BAN_7DAYS_PHOTO
        ]
        
        if user_states[user_id] in ban_states:
            # Получаем состояние пользователя
            current_state = user_states[user_id]
            
            # Определяем тип бана по состоянию
            ban_type_map = {
                STATE_WAITING_FOR_BAN_30MIN_PHOTO: 'ban_30min',
                STATE_WAITING_FOR_BAN_1HOUR_PHOTO: 'ban_1hour',
                STATE_WAITING_FOR_BAN_2HOURS_PHOTO: 'ban_2hours',
                STATE_WAITING_FOR_BAN_24HOURS_PHOTO: 'ban_24hours',
                STATE_WAITING_FOR_BAN_7DAYS_PHOTO: 'ban_7days'
            }
            ban_type = ban_type_map[current_state]
            
            # Отправляем сообщение о начале обработки
            processing_message = await retry_telegram_request(
                update.message.reply_text,
                "⏳ Обрабатываю скриншот, пожалуйста, подождите..."
            )
            
            try:
                # Получаем фотографию наибольшего размера
                photo_file = await retry_telegram_request(
                    update.message.photo[-1].get_file
                )
                photo_bytes = await retry_telegram_request(
                    photo_file.download_as_bytearray
                )
                
                # Открываем изображение
                img = Image.open(io.BytesIO(photo_bytes))
                
                # Добавляем желтую полоску с текстом
                img_with_strip = add_ban_yellow_strip(img, ban_type)
                
                # Сохраняем результат во временный файл
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    img_with_strip.save(temp_file, format='PNG')
                    screenshot_path = temp_file.name
                
                # Отправляем изображение с кнопками
                with open(screenshot_path, 'rb') as photo:
                    await retry_telegram_request(
                        update.message.reply_photo,
                        photo=photo,
                        caption="✅ Бан сгенерирован!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                        ])
                    )
                
                # Удаляем временный файл
                os.unlink(screenshot_path)
                
            except Exception as e:
                logging.error(f"Ошибка при обработке скриншота: {e}")
                await retry_telegram_request(
                    update.message.reply_text,
                    f"❌ Произошла ошибка при обработке скриншота. Пожалуйста, попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                    ])
                )
            
            finally:
                # Удаляем сообщение о обработке
                try:
                    await retry_telegram_request(processing_message.delete)
                except Exception as e:
                    logging.warning(f"Не удалось удалить сообщение о обработке: {e}")
                
                # Сбрасываем состояние пользователя
                del user_states[user_id]
            
            return
    
    # Если нет фотографии, обрабываем текстовые сообщения
    if not hasattr(update.message, 'text'):
        return
    
    message_text = update.message.text
    
    # Проверяем, ожидаем ли мы ID мамонта для ошибки Wanmei
    if user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_WANMEI_ID:
        # Отправляем сообщение о начале обработки
        processing_message = await update.message.reply_text("⏳ Генерирую скриншот ошибки Wanmei...")
        
        try:
            # Получаем ID мамонта из сообщения
            mammoth_id = message_text.strip()
            
            # Импортируем функцию для создания скриншота
            from temp_functions import create_wanmei_error_screenshot
            
            # Создаем скриншот с ошибкой Wanmei и ID мамонта
            screenshot_path = await create_wanmei_error_screenshot(mammoth_id)
            
            # Отправляем изображение с кнопками
            if screenshot_path:
                with open(screenshot_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption="✅ Ошибка Wanmei сгенерирована!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                        ])
                    )
                
                # Удаляем временный файл
                os.unlink(screenshot_path)
            else:
                await update.message.reply_text(
                    "❌ Не удалось создать скриншот ошибки Wanmei. Пожалуйста, попробуйте снова.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                    ])
                )
        
        except Exception as e:
            logging.error(f"Ошибка при создании скриншота ошибки Wanmei: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка при обработке ID мамонта. Пожалуйста, попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                ])
            )
        
        finally:
            # Удаляем сообщение о обработке
            await processing_message.delete()
            
            # Сбрасываем состояние пользователя
            del user_states[user_id]
    
    # Проверяем, ожидаем ли мы ссылку для CS2 Code Fake
    elif user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_CS2_CODE_FAKE_LINK:
        # Проверяем, что сообщение похоже на ссылку
        if message_text.startswith('http'):
            # Отправляем сообщение о начале обработки
            processing_message = await update.message.reply_text("⏳ Генерирую CS2 Code Fake...")
            
            try:
                # Импортируем функцию для создания CS2 Code Fake
                from temp_functions import create_cs2_code_fake
                
                # Создаем изображение CS2 Code Fake с аватаркой
                screenshot_path = await create_cs2_code_fake(message_text)
                
                # Отправляем изображение с кнопками
                if screenshot_path:
                    with open(screenshot_path, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption="✅ CS2 Code Fake сгенерирован!",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                                [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                            ])
                        )
                    
                    # Удаляем временный файл
                    os.unlink(screenshot_path)
                else:
                    await update.message.reply_text(
                        "❌ Не удалось создать CS2 Code Fake. Пожалуйста, попробуйте снова.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                        ])
                    )
            
            except Exception as e:
                logging.error(f"Ошибка при создании CS2 Code Fake: {e}")
                await update.message.reply_text(
                    f"❌ Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                    ])
                )
            
            finally:
                # Удаляем сообщение о обработке
                try:
                    await retry_telegram_request(processing_message.delete)
                except Exception as e:
                    logging.warning(f"Не удалось удалить сообщение о обработке: {e}")
                
                # Сбрасываем состояние пользователя
                del user_states[user_id]
        else:
            # Если сообщение не похоже на ссылку
            await update.message.reply_text(
                "❌ Это не похоже на ссылку. Пожалуйста, отправьте корректную ссылку на профиль Steam.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                ])
            )
    
    # Проверяем, ожидаем ли мы ссылку для QR Friend Page
    elif user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_QR_FRIEND_LINK:
        # Проверяем, что сообщение похоже на ссылку
        if message_text.startswith('http'):
            # Сохраняем ссылку в контексте пользователя
            if not hasattr(context, 'user_data'):
                context.user_data = {}
            context.user_data[user_id] = {'qr_friend_link': message_text}
            
            # Запрашиваем время для скриншота
            await update.message.reply_text(
                "⌚️ Отправь время у скриншота:\n\n❗️ Пример: 4:20",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                ])
            )
            
            # Меняем состояние пользователя на ожидание времени
            user_states[user_id] = STATE_WAITING_FOR_QR_FRIEND_TIMESTAMP
        else:
            # Если сообщение не похоже на ссылку
            await update.message.reply_text(
                "❌ Это не похоже на ссылку. Пожалуйста, отправьте корректную ссылку на профиль Steam.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                ])
            )
    
    # Проверяем, ожидаем ли мы время для QR Friend Page
    elif user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_QR_FRIEND_TIMESTAMP:
        # Отправляем сообщение о начале обработки
        processing_message = await update.message.reply_text("⏳ Обрабатываю ссылку, пожалуйста, подождите...")
        
        try:
            # Получаем сохраненную ссылку
            profile_url = context.user_data[user_id]['qr_friend_link']
            timestamp = message_text  # Время, введенное пользователем
            
            # Импортируем вспомогательные функции
            from temp_functions import add_ban_yellow_strip, create_region_error_screenshot, create_qr_friend_page
            
            # Создаем изображение QR Friend Page с указанным временем
            screenshot_path = await create_qr_friend_page(profile_url, timestamp)
            
            # Отправляем изображение с кнопками
            if screenshot_path:
                with open(screenshot_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption="✅ QR Friend Page сгенерирована!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                        ])
                    )
                
                # Удаляем временный файл
                os.unlink(screenshot_path)
            else:
                await update.message.reply_text(
                    "❌ Не удалось создать QR Friend Page. Пожалуйста, проверьте ссылку и попробуйте снова.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                    ])
                )
        
        except Exception as e:
            logging.error(f"Ошибка при создании QR Friend Page: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
                ])
            )
        
        finally:
            # Удаляем сообщение о обработке
            await processing_message.delete()
            
            # Сбрасываем состояние пользователя
            if user_id in user_states:
                del user_states[user_id]
            
            # Очищаем данные пользователя
            if hasattr(context, 'user_data') and user_id in context.user_data:
                del context.user_data[user_id]
    
    # Проверяем, ожидаем ли мы ссылку для AF Classic или AF Quick Link
    if user_id in user_states and user_states[user_id] in [STATE_WAITING_FOR_AF_CLASSIC_LINK, STATE_WAITING_FOR_AF_QUICK_LINK]:
        # Проверяем, что сообщение похоже на ссылку
        if message_text.startswith('http'):
            # Отправляем сообщение о начале обработки
            processing_message = await update.message.reply_text("⏳ Обрабатываю ссылку, пожалуйста, подождите...")
            
            try:
                # Создаем скриншоты с ошибками
                # Вместо модификации URL, передаем тип обработки как отдельный параметр
                is_quick_link = user_states[user_id] == STATE_WAITING_FOR_AF_QUICK_LINK
                screenshot_paths = await create_steam_screenshot(message_text, is_quick_link)
                
                # Отправляем первое изображение с кнопками
                if screenshot_paths and len(screenshot_paths) > 0:
                    with open(screenshot_paths[0], 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption="✅ Ошибка 1 сгенерирована!",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                                [InlineKeyboardButton("↩️ Назад", callback_data='back_to_add_friend')]
                            ])
                        )
                
                # Отправляем остальные изображения без кнопок
                # Для AF Quick Link отправляем только первые 3 изображения
                max_images_to_send = min(3, len(screenshot_paths))
                for i, path in enumerate(screenshot_paths[1:max_images_to_send], 2):
                    with open(path, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=f"✅ Ошибка {i} сгенерирована!"
                        )
                
                # Удаляем временные файлы
                for path in screenshot_paths:
                    os.unlink(path)
                
            except Exception as e:
                logging.error(f"Ошибка при создании скриншота: {e}")
                await update.message.reply_text(
                    f"❌ Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_add_friend')]
                    ])
                )
            
            finally:
                # Удаляем сообщение о обработке
                try:
                    await retry_telegram_request(processing_message.delete)
                except Exception as e:
                    logging.warning(f"Не удалось удалить сообщение о обработке: {e}")
                
                # Сбрасываем состояние пользователя
                del user_states[user_id]
        else:
            # Если сообщение не похоже на ссылку
            await update.message.reply_text(
                "❌ Это не похоже на ссылку. Пожалуйста, отправьте корректную ссылку на профиль Steam.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_add_friend')]
                ])
            )
    
    # Проверяем, ожидаем ли мы ссылку для FP Classic
    elif user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_FP_CLASSIC_LINK:
        # Проверяем, что сообщение похоже на ссылку
        if message_text.startswith('http'):
            # Отправляем сообщение о начале обработки
            processing_message = await update.message.reply_text("⏳ Обрабатываю ссылку, пожалуйста, подождите...")
            
            try:
                # Создаем изображение Friend Page
                screenshot_path = await create_friend_page_screenshot(message_text)
                
                # Отправляем изображение с кнопками
                if screenshot_path:
                    with open(screenshot_path, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption="✅ Friend Page сгенерирована!",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                                [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
                            ])
                        )
                
                # Удаляем временный файл
                if screenshot_path:
                    os.unlink(screenshot_path)
                
            except Exception as e:
                logging.error(f"Ошибка при создании Friend Page: {e}")
                await update.message.reply_text(
                    f"❌ Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
                    ])
                )
            
            finally:
                # Удаляем сообщение о обработке
                try:
                    await retry_telegram_request(processing_message.delete)
                except Exception as e:
                    logging.warning(f"Не удалось удалить сообщение о обработке: {e}")
                
                # Сбрасываем состояние пользователя
                del user_states[user_id]
        else:
            # Если сообщение не похоже на ссылку
            await update.message.reply_text(
                "❌ Это не похоже на ссылку. Пожалуйста, отправьте корректную ссылку.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
                ])
            )
    # Add this condition in the handle_message function where other state checks are
    elif user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_CS2_CODE_NOT_FOUND_LINK:
        # Check if the message is a valid URL
        if not message_text.startswith('http'):
            await update.message.reply_text(
                "❌ Это не похоже на ссылку. Пожалуйста, отправьте корректную ссылку на профиль Steam.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                ])
            )
            return
    
        processing_message = await update.message.reply_text("⏳ Генерирую CS2 Code Not Found...")
        
        try:
            from temp_functions import create_cs2_code_not_found
    
            # Pass the actual message text (URL) instead of the state
            result_path = await create_cs2_code_not_found(message_text)
    
            if result_path and os.path.exists(result_path):
                with open(result_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption="✅ CS2 Code Not Found сгенерирован!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                            [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                        ])
                    )
                # Удаляем временный файл
                os.remove(result_path)
            else:
                await update.message.reply_text(
                    "❌ Не удалось создать CS2 Code Not Found. Пожалуйста, попробуйте снова.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                    ])
                )
    
        except Exception as e:
            logging.error(f"Ошибка при создании CS2 Code Not Found: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_cs2_code')]
                ])
            )
    
        finally:
            await processing_message.delete()
            user_states.pop(user_id, None)
    
    
    # Проверяем, ожидаем ли мы ссылку для FP Region Error
    elif user_id in user_states and user_states[user_id] == STATE_WAITING_FOR_FP_REGION_ERROR_LINK:
        # Проверяем, что сообщение похоже на ссылку
        if message_text.startswith('http'):
            processing_message = await update.message.reply_text("⏳ Обрабатываю ссылку, пожалуйста, подождите...")
            
            try:
                screenshot_path = await create_fp_region_error(message_text)
                
                if screenshot_path and os.path.exists(screenshot_path):
                    with open(screenshot_path, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption="✅ Friend Page Region Error сгенерирована!",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("❤️ Поддержать бота", url='https://t.me/send?start=IVufKXTbCfU1')],
                                [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
                            ])
                        )
                    os.unlink(screenshot_path)
                else:
                    raise Exception("Failed to generate screenshot")
                    
            except Exception as e:
                logging.error(f"Error creating Region Error screenshot: {str(e)}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
                    ])
                )
            
            finally:
                await processing_message.delete()
                del user_states[user_id]
        else:
            # Если сообщение не похоже на ссылку
            await update.message.reply_text(
                "❌ Это не похоже на ссылку. Пожалуйста, отправьте корректную ссылку.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data='back_to_friend_page')]
                ])
            )

# Функция для создания Friend Page с данными из профиля Steam
async def create_friend_page_screenshot(profile_url):
    # Настройка Chrome в headless режиме
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Инициализация драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Переход на страницу профиля
        driver.get(profile_url)
        
        # Даем странице время загрузиться
        time.sleep(3)
        
        # Извлекаем аватар пользователя (берем второе изображение из div playerAvatarAutoSizeInner)
        try:
            # Сначала пробуем найти второе изображение в div playerAvatarAutoSizeInner
            avatar_elements = driver.find_elements("css selector", ".playerAvatarAutoSizeInner img")
            if len(avatar_elements) >= 2:
                # Берем второе изображение (аватар пользователя)
                avatar_url = avatar_elements[1].get_attribute("src")
            else:
                # Если не нашли, пробуем старый метод
                avatar_element = driver.find_element("css selector", ".profile_avatar_frame img")
                avatar_url = avatar_element.get_attribute("src")
        except Exception as e:
            logging.error(f"Ошибка при извлечении аватара: {e}")
            avatar_url = None
        
        # Извлекаем имя пользователя
        try:
            name_element = driver.find_element("css selector", ".actual_persona_name")
            username = name_element.text
        except Exception as e:
            logging.error(f"Ошибка при извлечении имени: {e}")
            username = "Unknown User"
        
        # Генерируем случайный 10-значный код друга (как на втором скриншоте)
        import random
        friend_code = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        
        # Загружаем шаблон Friend Page
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friend.png")
        template_img = Image.open(template_path)
        
        # Если удалось получить аватар, загружаем его и вставляем в шаблон как две квадратные аватарки
        if avatar_url:
            try:
                # Загружаем аватар
                import requests
                avatar_response = requests.get(avatar_url, stream=True)
                avatar_response.raise_for_status()
                avatar_img = Image.open(io.BytesIO(avatar_response.content))
                
                # Изменяем размер аватара до 37x37 для маленькой аватарки
                avatar_img_small = avatar_img.resize((37, 37), Image.LANCZOS)
                
                # Изменяем размер аватара до 70x70 для большой аватарки
                avatar_img_large = avatar_img.resize((70, 70), Image.LANCZOS)
                
                # Позиции для аватарок согласно уточненным координатам
                # Координаты центра большой аватарки (402, 64), размер 70x70
                # Координаты центра маленькой аватарки (1386, 5), размер 37x37
                avatar_position_large = (376, 135)  # Большая аватарка (координаты верхнего левого угла)
                avatar_position_small = (1386, 5)  # Маленькая аватарка (координаты верхнего левого угла)
                
                # Вставляем аватары в шаблон без маски (квадратные)
                template_img.paste(avatar_img_large, avatar_position_large)
                template_img.paste(avatar_img_small, avatar_position_small)
            except Exception as e:
                logging.error(f"Ошибка при обработке аватара: {e}")
        
        # Добавляем имя пользователя и код друга на изображение
        draw = ImageDraw.Draw(template_img)
        
        # Используем встроенный шрифт по умолчанию
        try:
            from PIL import ImageFont
            # Пытаемся использовать шрифт Arial, если он доступен
            try:
                # Пути к шрифтам в разных ОС
                font_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "arial.ttf"),
                    "C:\\Windows\\Fonts\\arial.ttf",
                    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
                ]
                
                font = None
                for path in font_paths:
                    if os.path.exists(path):
                        font = ImageFont.truetype(path, 20)
                        break
                
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # Позиция для имени пользователя (начало имени)
            name_position = (462, 146)  # Координаты из старого скриншота
            draw.text(name_position, username, fill="white", font=font)
            
            # Добавляем дублирование имени мелким шрифтом рядом с маленькой аватаркой
            # Конец имени должен быть на координатах (1353, 18)
            small_font = font
            try:
                for path in font_paths:
                    if os.path.exists(path):
                        small_font = ImageFont.truetype(path, 12)  # Мелкий шрифт
                        break
            except Exception:
                pass
            
            # Вычисляем ширину текста, чтобы разместить конец имени на нужных координатах
            try:
                if hasattr(small_font, 'getbbox'):
                    text_width = small_font.getbbox(username)[2]  # Современный метод
                elif hasattr(small_font, 'getsize'):
                    text_width = small_font.getsize(username)[0]  # Устаревший метод
                else:
                    text_width = len(username) * 6  # Примерная оценка
                # Корректируем позицию имени рядом с маленькой аватаркой в соответствии с новыми координатами
                small_name_position = (1353 - text_width, 16)  # Позиция рядом с маленькой аватаркой
            except Exception:
                small_name_position = (1320, 5)  # Запасная позиция
            draw.text(small_name_position, username, fill="white", font=small_font)
            
            # Добавляем код друга в поле Your Friend Code
            # Используем более крупный шрифт для кода друга
            code_font = font
            try:
                for path in font_paths:
                    if os.path.exists(path):
                        code_font = ImageFont.truetype(path, 36)  # Увеличиваем размер шрифта для кода друга
                        break
            except Exception:
                pass
            
            # Позиция для кода друга (центр поля Your Friend Code на координатах 913, 362)
            # Вычисляем ширину текста, чтобы центрировать его
            try:
                if hasattr(code_font, 'getbbox'):
                    code_width = code_font.getbbox(friend_code)[2]  # Современный метод
                elif hasattr(code_font, 'getsize'):
                    code_width = code_font.getsize(friend_code)[0]  # Устаревший метод
                else:
                    code_width = len(friend_code) * 12  # Примерная оценка для крупного шрифта
                    #913
                code_position = (660, 362 - 15)  # Центрируем код, немного выше для лучшего выравнивания
            except Exception:
                code_position = (863, 362 - 15)  # Запасная позиция
            draw.text(code_position, friend_code, fill="white", font=code_font)
            
            # Добавляем ссылку в поле Quick Invite
            # Обрезаем ссылку, если она слишком длинная
            max_link_length = 40
            display_url = profile_url if len(profile_url) <= max_link_length else profile_url[:max_link_length] + '...'
            # Располагаем ссылку в блоке Quick Invite (центр на координатах 913, 650)
            # Вычисляем ширину текста, чтобы центрировать его
            try:
                if hasattr(font, 'getbbox'):
                    url_width = font.getbbox(display_url)[2]  # Современный метод
                elif hasattr(font, 'getsize'):
                    url_width = font.getsize(display_url)[0]  # Устаревший метод
                else:
                    url_width = len(display_url) * 8  # Примерная оценка
                invite_position = (660, 650 - 5)  # Центрируем ссылку по координатам из старого скриншота
            except Exception:
                invite_position = (660, 650 - 10)  # Запасная позиция
            draw.text(invite_position, display_url, fill="white", font=font)
        except Exception as e:
            logging.error(f"Ошибка при добавлении текста: {e}")
        
        # Сохраняем результат во временный файл
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            return temp_file.name
    
    except Exception as e:
        logging.error(f"Ошибка при создании Friend Page: {e}")
        return None
    
    finally:
        # Закрываем драйвер
        driver.quit()

# Функция для создания скриншота Steam с наложением ошибок
async def create_steam_screenshot(profile_url, is_quick_link=False):
    # Настройка Chrome в headless режиме
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Инициализация драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Переход на страницу профиля - всегда используем исходный URL
        driver.get(profile_url)
        
        # Даем странице время загрузиться
        time.sleep(3)
        
        # Создаем скриншот
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        
        # Затемняем основное изображение
        enhancer = ImageEnhance.Brightness(img)
        darkened_img = enhancer.enhance(0.7)  # Уменьшаем яркость на 30%
        
        # Загружаем изображения ошибок
        error_images = []
        # Определяем количество изображений для загрузки (4 для quick link, 3 для classic)
        max_images = 4 if is_quick_link else 3
        
        for i in range(1, max_images + 1):
            error_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{i}.png")
            if os.path.exists(error_path):
                error_img = Image.open(error_path)
                # Сразу конвертируем все изображения в RGBA для корректного наложения
                if error_img.mode != 'RGBA':
                    error_img = error_img.convert('RGBA')
                error_images.append(error_img)
        
        # Создаем список для хранения путей к созданным изображениям
        screenshot_paths = []
        
        # Создаем отдельное изображение для каждой ошибки
        for i, error_img in enumerate(error_images):
            # Пропускаем последнее изображение для quick link (оно накладывается на остальные)
            if is_quick_link and i == 3:
                continue
                
            # Создаем копию затемненного изображения для каждой ошибки
            img_with_error = darkened_img.copy()
            
            # Определяем позицию для ошибки - все ошибки по центру
            position = ((img_with_error.width - error_img.width) // 2, 
                       (img_with_error.height - error_img.height) // 2)
            
            # Накладыем ошибку на изображение
            img_with_error.paste(error_img, position, error_img)
            
            # Для AF Quick Link добавляем изображение 4.png поверх каждого скриншота с ошибкой
            if is_quick_link and len(error_images) >= 4:
                # Получаем изображение 4.png (последнее в списке)
                top_error_img = error_images[3]
                # Изменяем размер изображения 4.png, чтобы оно растягивалось по всей ширине
                resized_top_img = top_error_img.resize((img_with_error.width, top_error_img.height), Image.LANCZOS)
                # Накладываем его в верхней части скриншота (x=0, y=0)
                img_with_error.paste(resized_top_img, (0, 0), resized_top_img)
            
            # Сохраняем результат во временный файл
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                img_with_error.save(temp_file, format='PNG')
                screenshot_paths.append(temp_file.name)
        
        return screenshot_paths
    
    finally:
        # Закрываем драйвер
        driver.quit()

# Функция для создания скриншота ошибки Wanmei с ID мамонта
async def create_wanmei_error_screenshot(mammont_id):
    try:
        # Загружаем шаблон Wanmei Error
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wanmei.png")
        template_img = Image.open(template_path)
        
        # Добавляем ID мамонта на изображение
        draw = ImageDraw.Draw(template_img)
        
        # Пытаемся использовать шрифт Arial, если он доступен
        try:
            font_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "arial.ttf"),
                "C:\\Windows\\Fonts\\arial.ttf",
                "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
            ]
            
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, 20)  # Размер шрифта для ID
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Позиция для ID мамонта (координаты 401, 176)
        id_position = (401, 176)
        draw.text(id_position, mammont_id, fill="white", font=font)
        
        # Сохраняем результат во временный файл
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            return temp_file.name
    
    except Exception as e:
        logging.error(f"Ошибка при создании Wanmei Error: {e}")
        return None

def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()