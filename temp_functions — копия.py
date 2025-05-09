import os
import io
import tempfile
from PIL import Image, ImageDraw, ImageFont
import qrcode  # Добавлен импорт для создания QR-кодов

# Функция для добавления желтой полоски с текстом к изображению для Ban MM
def add_ban_yellow_strip(image, ban_time):
    # Создаем копию изображения
    img_with_strip = image.copy()
    
    # Определяем текст в зависимости от времени бана
    ban_texts = {
        'ban_30min': 'Competitive Cooldown 30 Minutes',
        'ban_1hour': 'Competitive Cooldown 1 Hour',
        'ban_2hours': 'Competitive Cooldown 2 Hours',
        'ban_24hours': 'Competitive Cooldown 24 Hours',
        'ban_7days': 'Competitive Cooldown 7 Days'
    }
    
    ban_text = ban_texts.get(ban_time, 'Competitive Cooldown')
    
    # Создаем желтую полоску
    strip_height = 30  # Высота полоски
    strip = Image.new('RGBA', (img_with_strip.width, strip_height), (255, 215, 0, 255))  # Желтый цвет
    
    # Добавляем текст на полоску
    draw = ImageDraw.Draw(strip)
    
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
                font = ImageFont.truetype(path, 16)  # Размер шрифта для текста
                break
        
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # Вычисляем ширину текста для центрирования
    try:
        if hasattr(font, 'getbbox'):
            text_width = font.getbbox(ban_text)[2]  # Современный метод
        elif hasattr(font, 'getsize'):
            text_width = font.getsize(ban_text)[0]  # Устаревший метод
        else:
            text_width = len(ban_text) * 8  # Примерная оценка
        
        # Центрируем текст на полоске
        text_position = ((strip.width - text_width) // 2, (strip_height - 16) // 2)
    except Exception:
        text_position = (10, 5)  # Запасная позиция
    
    # Рисуем текст черным цветом
    draw.text(text_position, ban_text, fill="black", font=font)
    
    # Накладываем полоску на изображение (в верхней части)
    img_with_strip.paste(strip, (0, 0), strip)
    
    return img_with_strip

# Функция для создания скриншота FP Region Error
async def create_region_error_screenshot(profile_url):
    # Импортируем необходимые модули внутри функции, чтобы избежать циклических импортов
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    import requests
    import random
    import logging
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("region_error")
    
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
            logger.error(f"Ошибка при извлечении аватара: {e}")
            avatar_url = None
        
        # Извлекаем имя пользователя
        try:
            name_element = driver.find_element("css selector", ".actual_persona_name")
            username = name_element.text
        except Exception as e:
            logger.error(f"Ошибка при извлечении имени: {e}")
            username = "Unknown User"
        
        # Генерируем случайный 10-значный код друга
        friend_code = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        
        # Загружаем шаблон Friend Page Region Error
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friendreg.png")
        template_img = Image.open(template_path)
        
        # Если удалось получить аватар, загружаем его и вставляем в шаблон как две квадратные аватарки
        if avatar_url:
            try:
                # Загружаем аватар
                avatar_response = requests.get(avatar_url, stream=True)
                avatar_response.raise_for_status()
                avatar_img = Image.open(io.BytesIO(avatar_response.content))
                
                # Изменяем размер аватара до 37x37 для маленькой аватарки
                avatar_img_small = avatar_img.resize((37, 37), Image.LANCZOS)
                
                # Изменяем размер аватара до 70x70 для большой аватарки
                avatar_img_large = avatar_img.resize((70, 70), Image.LANCZOS)
                
                # Позиции для аватарок согласно уточненным координатам
                # Используем те же координаты, что и в FP Classic
                avatar_position_large = (376, 135)  # Большая аватарка (координаты верхнего левого угла)
                avatar_position_small = (1386, 5)  # Маленькая аватарка (координаты верхнего левого угла)
                
                # Вставляем аватары в шаблон без маски (квадратные)
                template_img.paste(avatar_img_large, avatar_position_large)
                template_img.paste(avatar_img_small, avatar_position_small)
            except Exception as e:
                logger.error(f"Ошибка при обработке аватара: {e}")
        
        # Добавляем имя пользователя и код друга на изображение
        logger.info("Добавление текста на изображение")
        draw = ImageDraw.Draw(template_img)  # Определяем draw здесь
        
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
                    font = ImageFont.truetype(path, 20)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифта: {e}")
            font = ImageFont.load_default()
        
        # Добавляем имя пользователя только в основной позиции
        # Используем Inter SemiBold размера 67 для имени пользователя
        try:
            # Пробуем использовать Inter SemiBold
            inter_semibold_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Inter-Medium.otf")
            if os.path.exists(inter_semibold_path):
                name_font = ImageFont.truetype(inter_semibold_path, 67)
                logger.info(f"Используется шрифт для имени: Inter SemiBold")
            else:
                # Если Inter SemiBold не найден, пробуем Arial SemiBold
                logger.warning(f"Шрифт Inter SemiBold не найден, пробуем Arial SemiBold")
                arial_semibold_path = "C:\\Windows\\Fonts\\arialsb.ttf"  # Путь к Arial SemiBold
                if os.path.exists(arial_semibold_path):
                    name_font = ImageFont.truetype(arial_semibold_path, 67)
                else:
                    # Если Arial SemiBold не найден, используем обычный Arial с большим размером
                    logger.warning(f"Шрифт Arial SemiBold не найден, используем стандартный Arial")
                    for path in font_paths:
                        if os.path.exists(path):
                            name_font = ImageFont.truetype(path, 67)
                            break
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифта для имени: {e}")
            name_font = font  # Используем стандартный шрифт, если произошла ошибка
        
        # Добавляем имя пользователя только на указанные координаты (319, 391)
        name_position = (319, 391)
        draw.text(name_position, username, fill="white", font=name_font)
        
        # Удаляем код для отображения имени рядом с маленькой аватаркой
        
        # Добавляем только одну ссылку на профиль (убираем дублирование)
        link_font = font
        try:
            for path in font_paths:
                if os.path.exists(path):
                    link_font = ImageFont.truetype(path, 18)
                    break
        except Exception:
            pass
        
        # Проверяем, не слишком ли длинная ссылка для поля 610x100
        max_field_link_length = 60
        field_display_url = profile_url if len(profile_url) <= max_field_link_length else profile_url[:max_field_link_length] + '...'
        
        
        # Добавляем ссылку профиля с использованием шрифта Inter Regular размером 41
        try:
            # Пробуем использовать шрифт Inter Regular
            inter_regular_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Inter-Regular.otf")
            if os.path.exists(inter_regular_path):
                profile_link_font = ImageFont.truetype(inter_regular_path, 41)
                logger.info(f"Используется шрифт для ссылки профиля: Inter Regular")
            else:
                # Если Inter Regular не найден, используем обычный Arial
                logger.warning(f"Шрифт Inter Regular не найден, используем стандартный Arial")
                for path in font_paths:
                    if os.path.exists(path):
                        profile_link_font = ImageFont.truetype(path, 41)
                        break
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифта для ссылки профиля: {e}")
            profile_link_font = font  # Используем стандартный шрифт, если произошла ошибка
        
        # Позиция для ссылки профиля (слева-135, сверху-1890)
        link_position_x = 135
        link_position_y = 1890
        
        # Проверяем, не слишком ли длинная ссылка для поля шириной 610
        max_width = 610
        
        # Разбиваем ссылку на строки, если она слишком длинная
        if hasattr(profile_link_font, 'getbbox'):
            text_width = profile_link_font.getbbox(profile_url)[2]
        elif hasattr(profile_link_font, 'getsize'):
            text_width = profile_link_font.getsize(profile_url)[0]
        else:
            text_width = len(profile_url) * 20  # Примерная оценка
        
        if text_width > max_width:
            # Разбиваем ссылку на части
            words = profile_url.split('/')
            lines = []
            current_line = ""
            
            for word in words:
                # Добавляем слеш обратно, кроме первого слова
                if current_line:
                    test_line = current_line + "/" + word
                else:
                    test_line = word
                
                # Проверяем ширину текущей строки с добавленным словом
                if hasattr(profile_link_font, 'getbbox'):
                    test_width = profile_link_font.getbbox(test_line)[2]
                elif hasattr(profile_link_font, 'getsize'):
                    test_width = profile_link_font.getsize(test_line)[0]
                else:
                    test_width = len(test_line) * 20
                
                # Если строка слишком длинная, начинаем новую
                if test_width > max_width:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = test_line
            
            # Добавляем последнюю строку
            if current_line:
                lines.append(current_line)
            
            # Рисуем каждую строку
            line_height = 50  # Высота строки с отступом
            for i, line in enumerate(lines):
                draw.text((link_position_x, link_position_y + i * line_height), line, fill="white", font=profile_link_font)
        else:
            # Если ссылка помещается в одну строку, просто рисуем ее
            draw.text((link_position_x, link_position_y), profile_url, fill="white", font=profile_link_font)
        
        # Убираем код друга и текст "Enter your friend's code"
        # Убираем дублирование ссылки в поле Quick Invite
        
        # Добавляем время, если оно указано
        if timestamp:
            logger.info(f"Добавление времени: {timestamp}")
            time_font = font
            try:
                # Пробуем использовать Inter Bold
                inter_bold_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Inter-Bold.otf")
                if os.path.exists(inter_bold_path):
                    time_font = ImageFont.truetype(inter_bold_path, 50)
                    logger.info(f"Используется шрифт для времени: Inter Bold")
                else:
                    logger.warning(f"Шрифт Inter Bold не найден, используем стандартный Arial")
                    # Если Inter Bold не найден, используем обычный Arial
                    arial_path = "C:\\Windows\\Fonts\\arial.ttf"
                    if os.path.exists(arial_path):
                        time_font = ImageFont.truetype(arial_path, 50)
            except Exception as e:
                logger.error(f"Ошибка при загрузке шрифта для времени: {e}")
                # Если не удалось загрузить шрифт, используем обычный с увеличенным размером
                try:
                    for path in font_paths:
                        if os.path.exists(path):
                            time_font = ImageFont.truetype(path, 50)
                            break
                except Exception:
                    pass
            
            # Позиция для времени на указанных координатах (слева-160, сверху-60)
            time_position = (160, 60)
            draw.text(time_position, timestamp, fill="white", font=time_font)
        
        # Сохраняем результат во временный файл
        logger.info("Сохранение результата во временный файл")
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            logger.info(f"Файл сохранен: {temp_file.name}")
            return temp_file.name
    
    except Exception as e:
        logger.error(f"Ошибка при создании Friend Page Region Error: {e}")
        return None
    
    finally:
        # Закрываем драйвер
        driver.quit()

# Функция для создания QR Friend Page
async def create_qr_friend_page(profile_url, timestamp=None):
    # Импортируем необходимые модули внутри функции
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    import requests
    import random
    import logging
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("qr_friend_page")
    
    # Настройка Chrome в headless режиме
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Инициализация драйвера
    driver = None
    try:
        logger.info(f"Инициализация драйвера Chrome для URL: {profile_url}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Переход на страницу профиля
        logger.info("Переход на страницу профиля")
        driver.get(profile_url)
        
        # Даем странице время загрузиться
        time.sleep(5)  # Увеличиваем время ожидания
        
        # Извлекаем аватар пользователя с использованием нескольких селекторов
        avatar_url = None
        try:
            logger.info("Извлечение аватара пользователя")
            # Пробуем разные селекторы для аватара
            selectors = [
                ".playerAvatarAutoSizeInner img",
                ".profile_avatar_frame img",
                ".playerAvatar img",
                ".avatar_medium_border img",
                ".user_avatar img"
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements("css selector", selector)
                    if elements:
                        if len(elements) >= 2 and selector == ".playerAvatarAutoSizeInner img":
                            avatar_url = elements[1].get_attribute("src")
                        else:
                            avatar_url = elements[0].get_attribute("src")
                        logger.info(f"Найден аватар с селектором {selector}: {avatar_url}")
                        break
                except Exception as e:
                    logger.warning(f"Селектор {selector} не сработал: {e}")
            
            # Если аватар не найден, пробуем найти любое изображение на странице
            if not avatar_url:
                all_images = driver.find_elements("tag name", "img")
                for img in all_images:
                    src = img.get_attribute("src")
                    if src and ("avatars" in src or "avatar" in src):
                        avatar_url = src
                        logger.info(f"Найден аватар через поиск по всем изображениям: {avatar_url}")
                        break
        except Exception as e:
            logger.error(f"Ошибка при извлечении аватара: {e}")
            avatar_url = None
        
        # Извлекаем имя пользователя с использованием нескольких селекторов
        username = None
        try:
            logger.info("Извлечение имени пользователя")
            # Пробуем разные селекторы для имени
            name_selectors = [
                ".actual_persona_name",
                ".persona_name",
                ".profile_header_centered_persona .persona_name",
                ".playerNameContainer",
                ".profile_header_title"
            ]
            
            for selector in name_selectors:
                try:
                    elements = driver.find_elements("css selector", selector)
                    if elements:
                        username = elements[0].text
                        logger.info(f"Найдено имя пользователя с селектором {selector}: {username}")
                        break
                except Exception as e:
                    logger.warning(f"Селектор {selector} для имени не сработал: {e}")
            
            # Если имя не найдено, используем значение по умолчанию
            if not username:
                username = "Unknown User"
                logger.warning("Имя пользователя не найдено, используем значение по умолчанию")
        except Exception as e:
            logger.error(f"Ошибка при извлечении имени: {e}")
            username = "Unknown User"
        
        # Остальной код функции остается без изменений
        # Генерируем случайный 10-значный код друга
        friend_code = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        logger.info(f"Сгенерирован код друга: {friend_code}")
        
        # Загружаем шаблон QR Friend Page
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_friend.png")
        logger.info(f"Загрузка шаблона из: {template_path}")
        
        if not os.path.exists(template_path):
            logger.error(f"Шаблон не найден по пути: {template_path}")
            return None
            
        template_img = Image.open(template_path)
        
        # Создаем QR-код для ссылки на профиль
        logger.info("Создание QR-кода")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(profile_url)
        qr.make(fit=True)
        
        # Создаем QR-код и изменяем его размер до 429x429
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((429, 429), Image.LANCZOS)
        
        # Создаем маску для скругление углов QR-кода
        mask = Image.new('L', (429, 429), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([(0, 0), (429, 429)], radius=25, fill=255)
        
        # Создаем новое изображение с прозрачным фоном для QR-кода со скругленными углами
        qr_rounded = Image.new('RGBA', (429, 429), (255, 255, 255, 0))
        qr_rounded.paste(qr_img, (0, 0), mask)
        
        # Позиция для QR-кода на шаблоне (слева-374, сверху-918)
        qr_position = (374, 918)
        template_img.paste(qr_rounded, qr_position, qr_rounded)
        
        # Если удалось получить аватар, загружаем его и вставляем в шаблон
        if avatar_url:
            try:
                # Загружаем аватар
                logger.info("Загрузка аватара")
                avatar_response = requests.get(avatar_url, stream=True)
                avatar_response.raise_for_status()
                avatar_img = Image.open(io.BytesIO(avatar_response.content))
                
                # Изменяем размер аватара для маленькой и большой аватарки
                avatar_img_small = avatar_img.resize((111, 111), Image.LANCZOS)  # Изменен размер на 111x111
                avatar_img_large = avatar_img.resize((70, 70), Image.LANCZOS)
                
                # Позиции для аватарок
                avatar_position_large = (376, 135)  # Большая аватарка
                avatar_position_small = (1015, 183)  # Маленькая аватарка (справа-55, сверху-183)
                
                # Вставляем аватары в шаблон
                template_img.paste(avatar_img_small, avatar_position_small)
                
                # Добавляем большую аватарку на указанные координаты (86, 352) с размером 195x195
                avatar_img_extra_large = avatar_img.resize((195, 195), Image.LANCZOS)
                avatar_position_extra_large = (86, 352)  # Указанные координаты
                template_img.paste(avatar_img_extra_large, avatar_position_extra_large)
                logger.info("Аватары успешно добавлены")
            except Exception as e:
                logger.error(f"Ошибка при обработке аватара: {e}")
        
        # Добавляем имя пользователя и код друга на изображение
        logger.info("Добавление текста на изображение")
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
                    font = ImageFont.truetype(path, 20)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Добавляем имя пользователя только в основной позиции
        # Используем Inter SemiBold размера 67 для имени пользователя
        try:
            # Пробуем использовать Inter SemiBold
            inter_semibold_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Inter-Medium.otf")
            if os.path.exists(inter_semibold_path):
                name_font = ImageFont.truetype(inter_semibold_path, 67)
                logger.info(f"Используется шрифт для имени: Inter SemiBold")
            else:
                # Если Inter SemiBold не найден, пробуем Arial SemiBold
                logger.warning(f"Шрифт Inter SemiBold не найден, пробуем Arial SemiBold")
                arial_semibold_path = "C:\\Windows\\Fonts\\arialsb.ttf"  # Путь к Arial SemiBold
                if os.path.exists(arial_semibold_path):
                    name_font = ImageFont.truetype(arial_semibold_path, 67)
                else:
                    # Если Arial SemiBold не найден, используем обычный Arial с большим размером
                    logger.warning(f"Шрифт Arial SemiBold не найден, используем стандартный Arial")
                    for path in font_paths:
                        if os.path.exists(path):
                            name_font = ImageFont.truetype(path, 67)
                            break
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифта для имени: {e}")
            name_font = font  # Используем стандартный шрифт, если произошла ошибка
        
        # Добавляем имя пользователя только на указанные координаты (319, 391)
        name_position = (319, 391)
        draw.text(name_position, username, fill="white", font=name_font)
        
        # Удаляем код для отображения имени рядом с маленькой аватаркой
        
        # Добавляем только одну ссылку на профиль (убираем дублирование)
        link_font = font
        try:
            for path in font_paths:
                if os.path.exists(path):
                    link_font = ImageFont.truetype(path, 18)
                    break
        except Exception:
            pass
        
        # Проверяем, не слишком ли длинная ссылка для поля 610x100
        max_field_link_length = 60
        field_display_url = profile_url if len(profile_url) <= max_field_link_length else profile_url[:max_field_link_length] + '...'
        
        
        # Добавляем ссылку профиля с использованием шрифта Inter Regular размером 41
        try:
            # Пробуем использовать шрифт Inter Regular
            inter_regular_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Inter-Regular.otf")
            if os.path.exists(inter_regular_path):
                profile_link_font = ImageFont.truetype(inter_regular_path, 41)
                logger.info(f"Используется шрифт для ссылки профиля: Inter Regular")
            else:
                # Если Inter Regular не найден, используем обычный Arial
                logger.warning(f"Шрифт Inter Regular не найден, используем стандартный Arial")
                for path in font_paths:
                    if os.path.exists(path):
                        profile_link_font = ImageFont.truetype(path, 41)
                        break
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифта для ссылки профиля: {e}")
            profile_link_font = font  # Используем стандартный шрифт, если произошла ошибка
        
        # Позиция для ссылки профиля (слева-135, сверху-1890)
        link_position_x = 135
        link_position_y = 1890
        
        # Проверяем, не слишком ли длинная ссылка для поля шириной 610
        max_width = 610
        
        # Разбиваем ссылку на строки, если она слишком длинная
        if hasattr(profile_link_font, 'getbbox'):
            text_width = profile_link_font.getbbox(profile_url)[2]
        elif hasattr(profile_link_font, 'getsize'):
            text_width = profile_link_font.getsize(profile_url)[0]
        else:
            text_width = len(profile_url) * 20  # Примерная оценка
        
        if text_width > max_width:
            # Разбиваем ссылку на части
            words = profile_url.split('/')
            lines = []
            current_line = ""
            
            for word in words:
                # Добавляем слеш обратно, кроме первого слова
                if current_line:
                    test_line = current_line + "/" + word
                else:
                    test_line = word
                
                # Проверяем ширину текущей строки с добавленным словом
                if hasattr(profile_link_font, 'getbbox'):
                    test_width = profile_link_font.getbbox(test_line)[2]
                elif hasattr(profile_link_font, 'getsize'):
                    test_width = profile_link_font.getsize(test_line)[0]
                else:
                    test_width = len(test_line) * 20
                
                # Если строка слишком длинная, начинаем новую
                if test_width > max_width:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = test_line
            
            # Добавляем последнюю строку
            if current_line:
                lines.append(current_line)
            
            # Рисуем каждую строку
            line_height = 50  # Высота строки с отступом
            for i, line in enumerate(lines):
                draw.text((link_position_x, link_position_y + i * line_height), line, fill="white", font=profile_link_font)
        else:
            # Если ссылка помещается в одну строку, просто рисуем ее
            draw.text((link_position_x, link_position_y), profile_url, fill="white", font=profile_link_font)
        
        # Убираем код друга и текст "Enter your friend's code"
        # Убираем дублирование ссылки в поле Quick Invite
        
        # Добавляем время, если оно указано
        if timestamp:
            logger.info(f"Добавление времени: {timestamp}")
            time_font = font
            try:
                # Используем стандартный Arial Black из Windows
                arial_black_path = "C:\\Windows\\Fonts\\ariblk.ttf"
                if os.path.exists(arial_black_path):
                    time_font = ImageFont.truetype(arial_black_path, 50)
                    logger.info(f"Используется шрифт для времени: Arial Black")
                else:
                    logger.warning(f"Шрифт Arial Black не найден, используем стандартный Arial")
                    # Если Arial Black не найден, используем обычный Arial
                    arial_path = "C:\\Windows\\Fonts\\arial.ttf"
                    if os.path.exists(arial_path):
                        time_font = ImageFont.truetype(arial_path, 50)
            except Exception as e:
                logger.error(f"Ошибка при загрузке шрифта для времени: {e}")
                # Если не удалось загрузить шрифт, используем обычный с увеличенным размером
                try:
                    for path in font_paths:
                        if os.path.exists(path):
                            time_font = ImageFont.truetype(path, 50)
                            break
                except Exception:
                    pass
            
            # Позиция для времени на указанных координатах (слева-160, сверху-60)
            time_position = (160, 60)
            draw.text(time_position, timestamp, fill="white", font=time_font)
        
        # Сохраняем результат во временный файл
        logger.info("Сохранение результата во временный файл")
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            logger.info(f"Файл сохранен: {temp_file.name}")
            return temp_file.name
    
    except Exception as e:
        logger.error(f"Ошибка при создании QR Friend Page: {e}")
        return None
    
    finally:
        # Закрываем драйвер
        if driver:
            logger.info("Закрытие драйвера Chrome")
            driver.quit()



# Функция для создания CS2 Code скриншота
async def create_cs2_code_screenshot(profile_url, username=None, cs2_code=None):
    # Импортируем необходимые модули внутри функции
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    import requests
    import random
    
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
        # Если имя пользователя не предоставлено, получаем его из профиля
        if not username:
            # Переход на страницу профиля
            driver.get(profile_url)
            
            # Даем странице время загрузиться
            time.sleep(3)
            
            # Извлекаем аватар пользователя
            try:
                avatar_elements = driver.find_elements("css selector", ".playerAvatarAutoSizeInner img")
                if len(avatar_elements) >= 2:
                    avatar_url = avatar_elements[1].get_attribute("src")
                else:
                    avatar_element = driver.find_element("css selector", ".profile_avatar_frame img")
                    avatar_url = avatar_element.get_attribute("src")
            except Exception as e:
                print(f"Ошибка при извлечении аватара: {e}")
                avatar_url = None
            
            # Извлекаем имя пользователя
            try:
                name_element = driver.find_element("css selector", ".actual_persona_name")
                username = name_element.text
            except Exception as e:
                print(f"Ошибка при извлечении имени: {e}")
                username = "Unknown User"
        else:
            # Если имя предоставлено, но нужно получить аватар
            driver.get(profile_url)
            time.sleep(3)
            
            try:
                avatar_elements = driver.find_elements("css selector", ".playerAvatarAutoSizeInner img")
                if len(avatar_elements) >= 2:
                    avatar_url = avatar_elements[1].get_attribute("src")
                else:
                    avatar_element = driver.find_element("css selector", ".profile_avatar_frame img")
                    avatar_url = avatar_element.get_attribute("src")
            except Exception as e:
                print(f"Ошибка при извлечении аватара: {e}")
                avatar_url = None
        
        # Генерируем случайный CS2 код, если не предоставлен
        if not cs2_code:
            # Формат CS2 кода: XXXX-XXXX-XXXX
            cs2_code = '-'.join([''.join([random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(4)]) for _ in range(3)])
        
        # Загружаем шаблон CS2 Code
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cs2code.png")
        template_img = Image.open(template_path)
        
        # Если удалось получить аватар, загружаем его и вставляем в шаблон
        if avatar_url:
            try:
                # Загружаем аватар
                avatar_response = requests.get(avatar_url, stream=True)
                avatar_response.raise_for_status()
                avatar_img = Image.open(io.BytesIO(avatar_response.content))
                
                # Изменяем размер аватара для маленькой и большой аватарки
                avatar_img_small = avatar_img.resize((37, 37), Image.LANCZOS)
                avatar_img_large = avatar_img.resize((70, 70), Image.LANCZOS)
                
                # Позиции для аватарок
                avatar_position_large = (376, 135)  # Большая аватарка
                avatar_position_small = (1386, 5)   # Маленькая аватарка
                
                # Вставляем аватары в шаблон
                template_img.paste(avatar_img_large, avatar_position_large)
                template_img.paste(avatar_img_small, avatar_position_small)
            except Exception as e:
                print(f"Ошибка при обработке аватара: {e}")
        
        # Добавляем имя пользователя и CS2 код на изображение
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
                    font = ImageFont.truetype(path, 20)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Позиция для имени пользователя
        name_position = (462, 146)
        draw.text(name_position, username, fill="white", font=font)
        
        # Добавляем дублирование имени мелким шрифтом рядом с маленькой аватаркой
        small_font = font
        try:
            for path in font_paths:
                if os.path.exists(path):
                    small_font = ImageFont.truetype(path, 12)
                    break
        except Exception:
            pass
        
        # Вычисляем ширину текста для правильного размещения
        try:
            if hasattr(small_font, 'getbbox'):
                text_width = small_font.getbbox(username)[2]
            elif hasattr(small_font, 'getsize'):
                text_width = small_font.getsize(username)[0]
            else:
                text_width = len(username) * 6
            small_name_position = (1353 - text_width, 16)
        except Exception:
            small_name_position = (1320, 5)
        draw.text(small_name_position, username, fill="white", font=small_font)
        
        # Добавляем CS2 код
        code_font = font
        try:
            for path in font_paths:
                if os.path.exists(path):
                    code_font = ImageFont.truetype(path, 36)
                    break
        except Exception:
            pass
        
        # Позиция для CS2 кода
        code_position = (660, 347)
        draw.text(code_position, cs2_code, fill="white", font=code_font)
        
        # Добавляем текст "Your CS2 Code"
        cs2_text_position = (660, 300)
        draw.text(cs2_text_position, "Your CS2 Code", fill="white", font=font)
        
        # Сохраняем результат во временный файл
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            return temp_file.name
    
    except Exception as e:
        print(f"Ошибка при создании CS2 Code скриншота: {e}")
        return None
    
    finally:
        # Закрываем драйвер
        driver.quit()



# Функция для создания скриншота ошибки Wanmei с ID мамонта
async def create_wanmei_error_screenshot(mammoth_id):
    import os
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    import logging
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("wanmei_error")
    
    try:
        logger.info(f"Создание скриншота ошибки Wanmei с ID: {mammoth_id}")
        
        # Загружаем шаблон ошибки Wanmei
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wanmei.png")
        if not os.path.exists(template_path):
            logger.error(f"Шаблон не найден по пути: {template_path}")
            return None
            
        template_img = Image.open(template_path)
        
        # Создаем объект для рисования на изображении
        draw = ImageDraw.Draw(template_img)
        
        # Пытаемся использовать шрифт для ID мамонта
        try:
            # Пробуем использовать шрифт Inter Regular
            inter_regular_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Inter-Regular.otf")
            if os.path.exists(inter_regular_path):
                id_font = ImageFont.truetype(inter_regular_path, 16)
                logger.info(f"Используется шрифт для ID мамонта: Inter Regular")
            else:
                # Если Inter Regular не найден, используем обычный Arial
                logger.warning(f"Шрифт Inter Regular не найден, используем стандартный Arial")
                font_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "arial.ttf"),
                    "C:\\Windows\\Fonts\\arial.ttf",
                    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
                ]
                
                id_font = None
                for path in font_paths:
                    if os.path.exists(path):
                        id_font = ImageFont.truetype(path, 16)
                        break
                
                if id_font is None:
                    id_font = ImageFont.load_default()
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифта для ID мамонта: {e}")
            id_font = ImageFont.load_default()
        
        # Добавляем ID мамонта на изображение по указанным координатам
        id_position = (401, 176)
        draw.text(id_position, mammoth_id, fill="white", font=id_font)
        
        # Сохраняем результат во временный файл
        logger.info("Сохранение результата во временный файл")
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            logger.info(f"Файл сохранен: {temp_file.name}")
            return temp_file.name
    
    except Exception as e:
        logger.error(f"Ошибка при создании скриншота ошибки Wanmei: {e}")
        return None


# Функция для создания CS2 Code Fake с использованием готового изображения и аватарки
async def create_cs2_code_fake(profile_url):
    import os
    import tempfile
    import requests
    from PIL import Image, ImageDraw, ImageFont
    import logging
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    import io
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("cs2_code_fake")
    
    try:
        logger.info(f"Создание CS2 Code Fake для профиля: {profile_url}")
        
        # Загружаем шаблон CS2 Code Fake
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codefake.png")
        if not os.path.exists(template_path):
            logger.error(f"Шаблон не найден по пути: {template_path}")
            return None
            
        template_img = Image.open(template_path)
        
        # Настройка Chrome в headless режиме для получения аватарки
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Инициализация драйвера
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        avatar_url = None
        
        try:
            # Переход на страницу профиля
            driver.get(profile_url)
            
            # Даем странице время загрузиться
            time.sleep(3)
            
            # Извлекаем аватар пользователя
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
                logger.error(f"Ошибка при извлечении аватара: {e}")
        
        finally:
            # Закрываем драйвер
            driver.quit()
        
        # Если удалось получить аватар, загружаем его и вставляем в шаблон
        if avatar_url:
            try:
                # Загружаем аватар
                response = requests.get(avatar_url)
                avatar_img = Image.open(io.BytesIO(response.content))
                
                # Изменяем размер аватара (например, до 64x64 пикселей)
                avatar_size = (64, 64)
                avatar_img = avatar_img.resize(avatar_size)
                
                # Вставляем аватар в шаблон на указанные координаты (925, 731)
                template_img.paste(avatar_img, (925, 731))
                logger.info(f"Аватар успешно вставлен на координаты (925, 731)")
            except Exception as e:
                logger.error(f"Ошибка при вставке аватара: {e}")
        
        # Сохраняем результат во временный файл
        logger.info("Сохранение результата во временный файл")
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            template_img.save(temp_file, format='PNG')
            logger.info(f"Файл сохранен: {temp_file.name}")
            return temp_file.name
    
    except Exception as e:
        logger.error(f"Ошибка при создании CS2 Code Fake: {e}")
        return None