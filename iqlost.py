import asyncio
import logging
import os
import random
import time
from html import unescape
from typing import Set

import aiohttp
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types

# ─── Imports for Dummy HTTP Server ──────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
from aiogram.types import BotCommand, Message, Update, InlineKeyboardMarkup, InlineKeyboardButton

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if we should use colors
        import os
        import sys
        self.use_colors = (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty() or
            os.environ.get('FORCE_COLOR') == '1' or
            os.environ.get('TERM', '').lower() in ('xterm', 'xterm-color', 'xterm-256color', 'screen', 'screen-256color')
        )
    
    COLORS = {
        'DEBUG': '\x1b[36m',    # Cyan
        'INFO': '\x1b[32m',     # Green  
        'WARNING': '\x1b[33m',  # Yellow
        'ERROR': '\x1b[31m',    # Red
        'CRITICAL': '\x1b[35m', # Magenta
        'RESET': '\x1b[0m',     # Reset
        'BLUE': '\x1b[34m',     # Blue
        'PURPLE': '\x1b[35m',   # Purple
        'CYAN': '\x1b[36m',     # Cyan
        'YELLOW': '\x1b[33m',   # Yellow
        'GREEN': '\x1b[32m',    # Green
        'RED': '\x1b[31m',      # Red (alias for ERROR)
        'BOLD': '\x1b[1m',      # Bold
        'DIM': '\x1b[2m'        # Dim
    }
    
    def format(self, record):
        if not self.use_colors:
            return super().format(record)
            
        # Create a copy to avoid modifying the original
        formatted_record = logging.makeLogRecord(record.__dict__)
        
        # Get the basic formatted message
        message = super().format(formatted_record)
        
        # Apply colors to the entire message
        return self.colorize_full_message(message, record.levelname)
    
    def colorize_full_message(self, message, level):
        """Apply colors to the entire formatted message"""
        if not self.use_colors:
            return message
            
        # Color based on log level
        level_color = self.COLORS.get(level, self.COLORS['RESET'])
        
        # Apply level-based coloring to the entire message
        if level == 'ERROR' or level == 'CRITICAL':
            return f"{self.COLORS['ERROR']}{self.COLORS['BOLD']}{message}{self.COLORS['RESET']}"
        elif level == 'WARNING':
            return f"{self.COLORS['YELLOW']}{message}{self.COLORS['RESET']}"
        elif level == 'INFO':
            # For INFO messages, use subtle coloring
            if any(word in message for word in ['Bot', 'Quiz', 'startup', 'connected', 'Success']):
                return f"{self.COLORS['GREEN']}{message}{self.COLORS['RESET']}"
            elif any(word in message for word in ['API', 'HTTP', 'Fetching']):
                return f"{self.COLORS['BLUE']}{message}{self.COLORS['RESET']}"
            elif any(word in message for word in ['User', 'extracted']):
                return f"{self.COLORS['CYAN']}{message}{self.COLORS['RESET']}"
            else:
                return f"{self.COLORS['GREEN']}{message}{self.COLORS['RESET']}"
        else:
            return f"{level_color}{message}{self.COLORS['RESET']}"

# Force color support in terminal
os.environ['FORCE_COLOR'] = '1'
os.environ['TERM'] = 'xterm-256color'

# Setup colored logging
logger = logging.getLogger("quizbot")
logger.setLevel(logging.INFO)

# Remove any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create and configure console handler with colors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter("%(asctime)s | %(levelname)s | %(message)s"))

# Add handler to logger
logger.addHandler(console_handler)

# Prevent propagation to root logger to avoid duplicate messages
logger.propagate = False

def extract_user_info(msg: Message):
    """Extract user and chat information from message"""
    logger.debug("🔍 Extracting user information from message")
    u = msg.from_user
    c = msg.chat
    info = {
        "user_id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "chat_id": c.id,
        "chat_type": c.type,
        "chat_title": c.title or c.first_name or "",
        "chat_username": f"@{c.username}" if c.username else "No Username",
        "chat_link": f"https://t.me/{c.username}" if c.username else "No Link",
    }
    logger.info(
        f"📑 User info extracted: {info['full_name']} (@{info['username']}) "
        f"[ID: {info['user_id']}] in {info['chat_title']} [{info['chat_id']}] {info['chat_link']}"
    )
    return info

logger.info("🚀 Quiz bot starting up - loading configuration")

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "5290407067"))

logger.info(f"🔑 Bot token loaded: {'✅ Success' if TOKEN else '❌ Missing'}")
logger.info(f"👑 Owner ID configured: {OWNER_ID}")

if not TOKEN:
    logger.error("❌ BOT_TOKEN environment variable missing - cannot start bot")
    raise ValueError("BOT_TOKEN is required")

logger.info("🤖 Initializing bot and dispatcher with HTML parse mode")
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
logger.info("✅ Bot and dispatcher initialized successfully")

CATEGORIES = {
    "general":   (9,  "🧠", "General Knowledge"),
    "books":     (10, "📚", "Book Trivia"),
    "film":      (11, "🎬", "Movie Quiz"),
    "music":     (12, "🎵", "Music Trivia"),
    "musicals":  (13, "🎭", "Musical Theater"),
    "tv":        (14, "📺", "TV Shows"),
    "games":     (15, "🎮", "Video Games"),
    "board":     (16, "🎲", "Board Games"),
    "nature":    (17, "🌿", "Nature Science"),
    "computers": (18, "💻", "Tech & Science"),
    "math":      (19, "➗", "Math Quiz"),
    "mythology": (20, "⚡", "Mythology Quiz"),
    "sports":    (21, "🏅", "Sports Trivia"),
    "geography": (22, "🌍", "Geography Quiz"),
    "history":   (23, "📜", "History Quiz"),
    "politics":  (24, "🏛️", "Politics Quiz"),
    "art":       (25, "🎨", "Art Design"),
    "celebs":    (26, "⭐", "Celebrity Quiz"),
    "animals":   (27, "🐾", "Animal Quiz"),
    "vehicles":  (28, "🚗", "Vehicle Quiz"),
    "comics":    (29, "💥", "Comic Books"),
    "gadgets":   (30, "📱", "Science Gadgets"),
    "anime":     (31, "🀄", "Anime Quiz"),
    "cartoons":  (32, "🎪", "Cartoon Quiz"),
}

logger.info(f"📋 Loaded {len(CATEGORIES)} quiz categories successfully")

session: aiohttp.ClientSession = None
semaphore = asyncio.Semaphore(5)
user_ids: Set[int] = set()
broadcast_mode: Set[int] = set()

# User throttling to prevent spam and rate limit issues
user_last_request = {}
user_processing = set()  # Track users currently processing requests
USER_COOLDOWN = 2  # seconds between requests per user

logger.info("🔧 Global variables initialized - ready for operations")

async def fetch_quiz(category_id: int):
    """Fetch quiz question from OpenTDB API with retry logic"""
    logger.info(f"🎯 Starting quiz fetch for category ID: {category_id}")
    retries = 2
    
    for attempt in range(retries):
        logger.info(f"🔄 Attempt {attempt + 1}/{retries} for category {category_id}")
        try:
            async with semaphore:
                url = f"https://opentdb.com/api.php?amount=1&type=multiple&category={category_id}"
                logger.debug(f"🌐 Making HTTP request to: {url}")
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    logger.info(f"📡 API response received: HTTP {resp.status}")
                    
                    if resp.status == 429:
                        logger.warning(f"⏳ Rate limit hit for category {category_id}")
                        if attempt < retries - 1:
                            logger.info(f"😴 Waiting 3 seconds before retry (attempt {attempt + 1})")
                            await asyncio.sleep(3)
                            continue
                        logger.error("❌ Rate limit exceeded after all retries")
                        raise Exception("429 Rate Limited")
                    elif resp.status != 200:
                        logger.error(f"❌ HTTP error {resp.status} for category {category_id}")
                        raise Exception(f"HTTP {resp.status}")
                    
                    data = await resp.json()
                    logger.debug(f"📦 Raw API data received: {data}")
                    
                    if not data.get("results"):
                        logger.error("❌ No quiz results found in API response")
                        raise Exception("No quiz results returned")
                    
                    result = data["results"][0]
                    logger.info(f"📝 Processing quiz question: {result.get('question', 'Unknown')[:50]}...")
                    
                    q = unescape(result["question"])
                    correct = unescape(result["correct_answer"])
                    opts = [unescape(x) for x in result["incorrect_answers"]] + [correct]
                    
                    logger.info(f"❓ Question: {q}")
                    logger.info(f"✅ Correct answer: {correct}")
                    logger.debug(f"🎲 Options before shuffle: {opts}")
                    
                    random.shuffle(opts)
                    correct_index = opts.index(correct)
                    
                    logger.info(f"🔀 Options shuffled, correct answer at index: {correct_index}")
                    logger.info(f"📋 Final options: {opts}")
                    
                    return q, opts, correct_index, correct
                    
        except Exception as e:
            logger.error(f"💥 Error on attempt {attempt + 1}: {str(e)}")
            if attempt == retries - 1:
                logger.error(f"❌ All retries exhausted for category {category_id}")
                raise e

async def send_quiz(msg: Message, cat_id: int, emoji: str):
    """Send quiz poll to user with typing indicator and throttling"""
    info = extract_user_info(msg)
    user_id = info['user_id']
    current_time = time.time()
    
    # Check if user is already processing a request
    if user_id in user_processing:
        logger.info(f"🚫 User {info['full_name']} already has a request in progress, ignoring")
        return
    
    # Check user cooldown
    if user_id in user_last_request:
        time_since_last = current_time - user_last_request[user_id]
        if time_since_last < USER_COOLDOWN:
            remaining = USER_COOLDOWN - time_since_last
            logger.info(f"⏱️ User {info['full_name']} on cooldown, {remaining:.1f}s remaining")
            return
    
    # Mark user as processing and update last request time
    user_processing.add(user_id)
    user_last_request[user_id] = current_time
    
    logger.info(f"🎯 Sending quiz to user {info['full_name']} for category {cat_id}")
    
    try:
        logger.debug("⌨️ Showing typing indicator to user")
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        
        logger.info("📥 Fetching quiz question from API")
        q, opts, correct_id, correct = await fetch_quiz(cat_id)
        
        logger.info(f"📊 Creating poll with question: {q[:50]}...")
        
        # Reply to user message in groups, send normally in private chats
        if info['chat_type'] in ['group', 'supergroup']:
            logger.info(f"📢 Sending quiz as reply in group {info['chat_title']}")
            poll_msg = await msg.reply_poll(
                question=f"{q} {emoji}",
                options=opts,
                type="quiz",
                correct_option_id=correct_id,
                is_anonymous=False,
                explanation=f"💡 Correct Answer: {correct}",
            )
        else:
            logger.info(f"💬 Sending quiz in private chat with {info['full_name']}")
            poll_msg = await msg.answer_poll(
                question=f"{q} {emoji}",
                options=opts,
                type="quiz",
                correct_option_id=correct_id,
                is_anonymous=False,
                explanation=f"💡 Correct Answer: {correct}",
            )
        logger.info(f"✅ Quiz poll sent successfully, message ID: {poll_msg.message_id}")
        
    except Exception as e:
        logger.error(f"💥 Error sending quiz: {str(e)}")
        # Silently handle errors - no "busy" message to user
        logger.info(f"🔇 Silently handled error for user {info['full_name']}")
        
    finally:
        # Always remove user from processing set
        user_processing.discard(user_id)

# Category command handlers
@dp.message(Command("general"))
async def cmd_general(msg: Message):
    """Handle general knowledge quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🧠 General quiz requested by {info['full_name']}")
    await send_quiz(msg, 9, "🧠")

@dp.message(Command("books"))
async def cmd_books(msg: Message):
    """Handle books quiz command"""
    info = extract_user_info(msg)
    logger.info(f"📚 Books quiz requested by {info['full_name']}")
    await send_quiz(msg, 10, "📚")

@dp.message(Command("film"))
async def cmd_film(msg: Message):
    """Handle film quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎬 Film quiz requested by {info['full_name']}")
    await send_quiz(msg, 11, "🎬")

@dp.message(Command("music"))
async def cmd_music(msg: Message):
    """Handle music quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎵 Music quiz requested by {info['full_name']}")
    await send_quiz(msg, 12, "🎵")

@dp.message(Command("musicals"))
async def cmd_musicals(msg: Message):
    """Handle musicals quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎭 Musicals quiz requested by {info['full_name']}")
    await send_quiz(msg, 13, "🎭")

@dp.message(Command("tv"))
async def cmd_tv(msg: Message):
    """Handle TV shows quiz command"""
    info = extract_user_info(msg)
    logger.info(f"📺 TV quiz requested by {info['full_name']}")
    await send_quiz(msg, 14, "📺")

@dp.message(Command("games"))
async def cmd_games(msg: Message):
    """Handle video games quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎮 Games quiz requested by {info['full_name']}")
    await send_quiz(msg, 15, "🎮")

@dp.message(Command("board"))
async def cmd_board(msg: Message):
    """Handle board games quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎲 Board games quiz requested by {info['full_name']}")
    await send_quiz(msg, 16, "🎲")

@dp.message(Command("nature"))
async def cmd_nature(msg: Message):
    """Handle nature quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🌿 Nature quiz requested by {info['full_name']}")
    await send_quiz(msg, 17, "🌿")

@dp.message(Command("computers"))
async def cmd_computers(msg: Message):
    """Handle computers quiz command"""
    info = extract_user_info(msg)
    logger.info(f"💻 Computers quiz requested by {info['full_name']}")
    await send_quiz(msg, 18, "💻")

@dp.message(Command("math"))
async def cmd_math(msg: Message):
    """Handle mathematics quiz command"""
    info = extract_user_info(msg)
    logger.info(f"➗ Math quiz requested by {info['full_name']}")
    await send_quiz(msg, 19, "➗")

@dp.message(Command("mythology"))
async def cmd_mythology(msg: Message):
    """Handle mythology quiz command"""
    info = extract_user_info(msg)
    logger.info(f"⚡ Mythology quiz requested by {info['full_name']}")
    await send_quiz(msg, 20, "⚡")

@dp.message(Command("sports"))
async def cmd_sports(msg: Message):
    """Handle sports quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🏅 Sports quiz requested by {info['full_name']}")
    await send_quiz(msg, 21, "🏅")

@dp.message(Command("geography"))
async def cmd_geography(msg: Message):
    """Handle geography quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🌍 Geography quiz requested by {info['full_name']}")
    await send_quiz(msg, 22, "🌍")

@dp.message(Command("history"))
async def cmd_history(msg: Message):
    """Handle history quiz command"""
    info = extract_user_info(msg)
    logger.info(f"📜 History quiz requested by {info['full_name']}")
    await send_quiz(msg, 23, "📜")

@dp.message(Command("politics"))
async def cmd_politics(msg: Message):
    """Handle politics quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🏛️ Politics quiz requested by {info['full_name']}")
    await send_quiz(msg, 24, "🏛️")

@dp.message(Command("art"))
async def cmd_art(msg: Message):
    """Handle art quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎨 Art quiz requested by {info['full_name']}")
    await send_quiz(msg, 25, "🎨")

@dp.message(Command("celebs"))
async def cmd_celebs(msg: Message):
    """Handle celebrities quiz command"""
    info = extract_user_info(msg)
    logger.info(f"⭐ Celebrities quiz requested by {info['full_name']}")
    await send_quiz(msg, 26, "⭐")

@dp.message(Command("animals"))
async def cmd_animals(msg: Message):
    """Handle animals quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🐾 Animals quiz requested by {info['full_name']}")
    await send_quiz(msg, 27, "🐾")

@dp.message(Command("vehicles"))
async def cmd_vehicles(msg: Message):
    """Handle vehicles quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🚗 Vehicles quiz requested by {info['full_name']}")
    await send_quiz(msg, 28, "🚗")

@dp.message(Command("comics"))
async def cmd_comics(msg: Message):
    """Handle comics quiz command"""
    info = extract_user_info(msg)
    logger.info(f"💥 Comics quiz requested by {info['full_name']}")
    await send_quiz(msg, 29, "💥")

@dp.message(Command("gadgets"))
async def cmd_gadgets(msg: Message):
    """Handle gadgets quiz command"""
    info = extract_user_info(msg)
    logger.info(f"📱 Gadgets quiz requested by {info['full_name']}")
    await send_quiz(msg, 30, "📱")

@dp.message(Command("anime"))
async def cmd_anime(msg: Message):
    """Handle anime quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🀄 Anime quiz requested by {info['full_name']}")
    await send_quiz(msg, 31, "🀄")

@dp.message(Command("cartoons"))
async def cmd_cartoons(msg: Message):
    """Handle cartoons quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎪 Cartoons quiz requested by {info['full_name']}")
    await send_quiz(msg, 32, "🎪")

def register_category_handlers():
    """All category handlers registered using decorators"""
    logger.info("✅ All 24 category command handlers registered successfully")

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    """Handle start command with welcome message and inline buttons"""
    info = extract_user_info(msg)
    logger.info(f"🚀 Start command received from {info['full_name']}")

    user_ids.add(msg.from_user.id)
    logger.info(f"👥 User added to database. Total users: {len(user_ids)}")

    logger.debug("⌨️ Showing typing indicator")
    await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

    logger.info("🔗 Creating inline keyboard with channel and group links")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Updates", url="https://t.me/WorkGlows"),
            InlineKeyboardButton(text="Support", url="https://t.me/TheCryptoElders")
        ],
        [
            InlineKeyboardButton(
                text="Add Me To Your Group",
                url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"
            )
        ]
    ])

    # Create user mention with href
    user_mention = f"<a href='tg://user?id={msg.from_user.id}'>{info['full_name']}</a>"

    text = (
        f"🎉 <b>Welcome, {user_mention}!</b>\n\n"
        "🧠 <b>iQ Lost</b> brings you fun, fast, and smart quizzes across 24+ categories!\n\n"
        "🎯 <b>Key Features</b>\n"
        "├─ Lightning-fast quiz delivery\n"
        "├─ 24+ rich categories to explore\n"
        "└─ Track your progress and compete\n\n"
        "📋 <b>Quick Commands</b>\n"
        "├─ /random ─ Surprise quiz 🎲\n"
        "├─ /help ─ View all categories 📚\n"
        "├─ /music ─ Music trivia 🎵\n"
        "├─ /sports ─ Sports knowledge 🏅\n"
        "└─ /general ─ General knowledge 🧠\n\n"
        "🚀 <b>Let’s begin your quiz journey now!</b>"
    )

    logger.info("📤 Sending welcome message with inline buttons")
    if info['chat_type'] in ['group', 'supergroup']:
        logger.info(f"📢 Sending start message as reply in group {info['chat_title']}")
        response = await msg.reply(text, reply_markup=keyboard)
    else:
        logger.info(f"💬 Sending start message in private chat with {info['full_name']}")
        response = await msg.answer(text, reply_markup=keyboard)

    logger.info(f"✅ Welcome message sent successfully, ID: {response.message_id}")

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    """Handle help command showing all categories"""
    info = extract_user_info(msg)
    logger.info(f"❓ Help command requested by {info['full_name']}")

    user_ids.add(msg.from_user.id)
    logger.info(f"👥 User added to database. Total users: {len(user_ids)}")

    await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

    logger.info("📋 Building help message with all available categories")

    # Group categories
    knowledge_cats = [(cmd, emoji, desc) for cmd, (_, emoji, desc) in CATEGORIES.items() if cmd in ['general', 'books', 'history', 'geography', 'politics', 'mythology']]
    entertainment_cats = [(cmd, emoji, desc) for cmd, (_, emoji, desc) in CATEGORIES.items() if cmd in ['film', 'music', 'tv', 'musicals', 'celebs', 'anime', 'cartoons', 'comics']]
    games_cats = [(cmd, emoji, desc) for cmd, (_, emoji, desc) in CATEGORIES.items() if cmd in ['games', 'board']]
    science_cats = [(cmd, emoji, desc) for cmd, (_, emoji, desc) in CATEGORIES.items() if cmd in ['nature', 'computers', 'math', 'gadgets']]
    lifestyle_cats = [(cmd, emoji, desc) for cmd, (_, emoji, desc) in CATEGORIES.items() if cmd in ['sports', 'art', 'animals', 'vehicles']]

    user_mention = f"<a href='tg://user?id={msg.from_user.id}'>{info['full_name']}</a>"

    def format_section(title: str, cats: list) -> str:
        lines = [f"├─ /{cmd} ─ {emoji} {desc}" for cmd, emoji, desc in cats[:-1]]
        if cats:
            lines.append(f"└─ /{cats[-1][0]} ─ {cats[-1][1]} {cats[-1][2]}")
        return f"📂 <b>{title}</b>\n" + "\n".join(lines)

    text = (
        f"📚 <b>Quiz Categories for {user_mention}</b>\n\n"
        + format_section("Knowledge & Education", knowledge_cats) + "\n\n"
        + format_section("Entertainment & Media", entertainment_cats) + "\n\n"
        + format_section("Games & Gaming", games_cats) + "\n\n"
        + format_section("Science & Technology", science_cats) + "\n\n"
        + format_section("Lifestyle & Hobbies", lifestyle_cats) + "\n\n"
        "🎲 <b>Special Commands</b>\n"
        "├─ /random ─ 🎯 Random quiz\n"
        "├─ /start ─ 🚀 Welcome message\n"
        "└─ /help ─ 📋 This help menu\n\n"
        f"💡 <b>Pro Tip:</b> Use any command to begin your quiz adventure!\n"
        "🏆 Challenge yourself and rise to the top!"
    )

    logger.info("📤 Sending help message to user")
    if info['chat_type'] in ['group', 'supergroup']:
        logger.info(f"📢 Sending help message as reply in group {info['chat_title']}")
        response = await msg.reply(text)
    else:
        logger.info(f"💬 Sending help message in private chat with {info['full_name']}")
        response = await msg.answer(text)

    logger.info(f"✅ Help message sent successfully, ID: {response.message_id}")
    
@dp.message(Command("random"))
async def cmd_random(msg: Message):
    """Handle random quiz command"""
    info = extract_user_info(msg)
    logger.info(f"🎲 Random quiz requested by {info['full_name']}")
    
    user_ids.add(msg.from_user.id)
    logger.info(f"👥 User added to database. Total users: {len(user_ids)}")
    
    await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
    
    logger.info("🎯 Selecting random category from available options")
    cmd, (cat_id, emoji, desc) = random.choice(list(CATEGORIES.items()))
    logger.info(f"✨ Random category selected: {cmd} (ID: {cat_id}, {emoji} {desc})")
    
    await send_quiz(msg, cat_id, emoji)

@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    """Handle broadcast command (owner only)"""
    info = extract_user_info(msg)
    logger.info(f"📢 Broadcast command attempted by {info['full_name']}")
    
    if msg.from_user.id != OWNER_ID:
        logger.warning(f"🚫 Unauthorized broadcast attempt by user {msg.from_user.id}")
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        response = await msg.answer("⛔ This command is restricted.")
        logger.info(f"⚠️ Unauthorized access message sent, ID: {response.message_id}")
        return
    
    await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
    logger.info(f"👑 Enabling broadcast mode for owner {msg.from_user.id}")
    broadcast_mode.add(msg.from_user.id)
    
    response = await msg.answer("📣 <b>Broadcast mode enabled.</b> Send me any message and I will forward it to all users.")
    logger.info(f"✅ Broadcast mode enabled, message ID: {response.message_id}")

@dp.message()
async def catch_all(msg: Message):
    """Handle all other messages and broadcast functionality"""
    info = extract_user_info(msg)
    logger.debug(f"💬 Message received from {info['full_name']}")
    
    if msg.from_user.id in broadcast_mode:
        logger.info(f"📡 Broadcasting message from owner {info['full_name']}")
        
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        
        success_count = 0
        fail_count = 0
        
        logger.info(f"📊 Starting broadcast to {len(user_ids)} users")
        
        for user_id in user_ids.copy():
            try:
                await bot.send_message(user_id, msg.text or msg.caption or "📢 Broadcast message")
                success_count += 1
                logger.debug(f"✅ Broadcast sent successfully to user {user_id}")
            except Exception as e:
                fail_count += 1
                logger.warning(f"❌ Failed to send broadcast to user {user_id}: {str(e)}")
                user_ids.discard(user_id)
        
        logger.info(f"📈 Broadcast complete. Success: {success_count}, Failed: {fail_count}")
        
        response = await msg.answer(f"📊 Broadcast complete!\n✅ Sent: {success_count}\n❌ Failed: {fail_count}")
        logger.info(f"📋 Broadcast summary sent, ID: {response.message_id}")
    else:
        logger.debug(f"❓ Unknown command from user {info['full_name']}")
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        
        if info['chat_type'] in ['group', 'supergroup']:
            logger.info(f"📢 Sending unknown command response as reply in group {info['chat_title']}")
            response = await msg.reply("🤔 I don't understand that command. Type /help to see available commands.")
        else:
            logger.info(f"💬 Sending unknown command response in private chat with {info['full_name']}")
            response = await msg.answer("🤔 I don't understand that command. Type /help to see available commands.")
        logger.info(f"💭 Unknown command response sent, ID: {response.message_id}")

async def global_error_handler(update: Update, exception):
    """Handle global errors gracefully"""
    logger.error(f"💥 Global error occurred: {str(exception)}")
    logger.debug(f"🔍 Update that caused error: {update}")
    return True

async def setup_bot_commands():
    """Set up bot command menu"""
    logger.info("⚙️ Setting up bot command menu")
    
    cmds = [
        BotCommand(command="start", description="🚀 Start Bot"),
        BotCommand(command="help", description="📚 Show Categories"),
        BotCommand(command="random", description="🎲 Random Quiz"),
    ] + [
        BotCommand(command=cmd, description=f"{emoji} {' '.join(desc.split()[:2])}")
        for cmd, (_, emoji, desc) in CATEGORIES.items()
    ]
    
    logger.info(f"📋 Setting {len(cmds)} bot commands in menu")
    await bot.set_my_commands(cmds)
    logger.info("✅ Bot command menu configured successfully")

async def on_startup():
    """Initialize bot resources on startup"""
    logger.info("🌟 Bot startup sequence initiated")
    
    global session
    logger.info("🌐 Creating HTTP session for API requests")
    session = aiohttp.ClientSession()
    logger.info("✅ HTTP session created successfully")
    
    logger.info("⚙️ Setting up bot commands menu")
    await setup_bot_commands()
    
    logger.info("🔗 Testing bot connection to Telegram")
    me = await bot.get_me()
    logger.info(f"🤖 Bot connected successfully: @{me.username} (ID: {me.id})")
    
    logger.info("🎉 Startup sequence completed - bot is ready!")

async def on_shutdown():
    """Clean up resources on shutdown"""
    logger.info("🛑 Bot shutdown sequence initiated")
    
    global session
    if session:
        logger.info("🌐 Closing HTTP session")
        await session.close()
        logger.info("✅ HTTP session closed successfully")
    
    logger.info("👋 Bot shutdown completed")

 # ─── Dummy HTTP Server to Keep Render Happy ─────────────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))  # Render injects this
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    logger.info(f"🌐 Dummy server listening on port {port}")
    server.serve_forever()

if __name__ == "__main__":

# Start dummy HTTP server (needed for Render health check)
    threading.Thread(target=start_dummy_server, daemon=True).start()

    logger.info("🎯 Quiz Bot main execution started")
    try:
        loop = asyncio.get_running_loop()
        logger.info(f"🐍 Python event loop: {loop}")
    except RuntimeError:
        logger.info("🐍 Python event loop: No running loop (will be created)")
    logger.info(f"📊 Total categories available: {len(CATEGORIES)}")
    
    logger.info("📝 Registering command handlers")
    register_category_handlers()
    
    logger.info("🔧 Registering startup and shutdown handlers")
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.errors.register(global_error_handler)
    
    logger.info("🚀 Starting bot polling - quiz bot is now live!")
    asyncio.run(dp.start_polling(bot))
