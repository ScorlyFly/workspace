import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from bs4 import BeautifulSoup
import random
import hashlib
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
import urllib3

# Отключение предупреждений SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Конфигурация
TOKEN = 'token'
MEMIFY_URL = 'https://www.memify.ru/highfive/'

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

sent_memes = set()

async def get_memes_with_selenium():
    """Асинхронно получает мемы с использованием Selenium"""
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        
        driver = webdriver.Chrome(options=options)
        driver.get(MEMIFY_URL)
        await asyncio.sleep(5)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        await asyncio.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        memes = []
        meme_containers = soup.find_all('div', class_='meme-card')
        
        for container in meme_containers:
            img_tag = container.find('img')
            if img_tag and 'src' in img_tag.attrs:
                img_url = urljoin(MEMIFY_URL, img_tag['src'])
                
                if any(x in img_url.lower() for x in ['logo', 'icon', 'avatar']):
                    continue
                
                text_tag = container.find('div', class_='meme-text')
                meme_text = text_tag.get_text(strip=True) if text_tag else "Мем с Memify.ru"
                
                memes.append({
                    'url': img_url,
                    'text': meme_text
                })
        
        return memes
    
    except Exception as e:
        print(f"Ошибка в Selenium: {str(e)}")
        return []

async def get_memes_from_memify():
    """Асинхронный парсинг мемов"""
    try:
        headers = {
            'User-Agent': UserAgent().random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.memify.ru/',
            'DNT': '1'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(MEMIFY_URL, headers=headers, ssl=False) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                memes = []
                selectors = [
                    ('div.meme-card', 'img', 'div.meme-text'),
                    ('div.card', 'img', None),
                    ('div.post', 'img', None),
                    ('article', 'img', None)
                ]
                
                for container_sel, img_sel, text_sel in selectors:
                    containers = soup.select(container_sel)
                    if not containers:
                        continue
                        
                    for container in containers:
                        img = container.select_one(img_sel)
                        if img and img.get('src'):
                            img_url = urljoin(MEMIFY_URL, img['src'])
                            
                            if any(x in img_url.lower() for x in ['logo', 'icon', 'avatar']):
                                continue
                            
                            text = container.select_one(text_sel).get_text(strip=True) if text_sel else "Мем с Memify.ru"
                            memes.append({
                                'url': img_url,
                                'text': text
                            })
                
                if memes:
                    return memes
                    
                return await get_memes_with_selenium()
    
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
        return await get_memes_with_selenium()

async def get_random_meme():
    """Асинхронно получает случайный мем"""
    memes = await get_memes_from_memify()
    if not memes:
        print("Не удалось найти мемы")
        return None
    
    new_memes = [m for m in memes if hashlib.md5(m['url'].encode()).hexdigest() not in sent_memes]
    
    if not new_memes:
        print("Все мемы уже были отправлены")
        sent_memes.clear()
        new_memes = memes
    
    meme = random.choice(new_memes)
    meme['hash'] = hashlib.md5(meme['url'].encode()).hexdigest()
    return meme

# Обработчики команд
@dp.message(Command("start", "help"))
async def send_welcome(message: Message):
    await message.answer(
        "🎭 Memify Bot - присылает свежие мемы с Memify.ru!\n\n"
        "🔹 /meme - Получить случайный мем\n"
        "🔹 /stats - Статистика бота"
    )

@dp.message(Command("meme"))
async def send_instant_meme(message: Message):
    """Асинхронная отправка мема"""
    try:
        meme = await get_random_meme()
        if meme:
            await message.answer_photo(
                photo=meme['url'], 
                caption=meme.get('text', 'Мем с Memify.ru')
            )
            sent_memes.add(meme['hash'])
            print(f"Мем отправлен пользователю {message.from_user.username}")
        else:
            await message.answer("😢 Сейчас не могу найти мем. Попробуйте позже.")
    except Exception as e:
        await message.answer("⚠️ Ошибка при отправке мема. Попробуйте снова.")
        print(f"Ошибка: {str(e)}")

@dp.message(Command("stats"))
async def show_stats(message: Message):
    stats = (
        f"📊 Статистика Memify Bot:\n"
        f"• Отправлено мемов: {len(sent_memes)}\n"
        f"• Источник: {MEMIFY_URL}"
    )
    await message.answer(stats)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("=== Асинхронный Memify Bot запущен ===")

    asyncio.run(main())

