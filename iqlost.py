import os
import json
import time
import aiohttp
import random
import asyncio
import logging
import threading
import traceback
from html import unescape
from datetime import datetime
from typing import Set, Dict, Any
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import (
    BotCommand,
    Message,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.client.default import DefaultBotProperties

# Load environment variables from file
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 5290407067

# Initialize bot with default properties
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# Global variables for bot state
session: aiohttp.ClientSession = None
semaphore = asyncio.Semaphore(5)
user_ids: Set[int] = set()
group_ids: Set[int] = set()
broadcast_mode: Set[int] = set()
broadcast_target: dict = {}
auto_quiz_active_groups: Set[int] = set()

# Rate limiting and processing variables
user_last_request = {}
user_processing = set()
USER_COOLDOWN = 2
active_polls = {}
help_page_states = {}

# Quiz categories with IDs and emojis
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

# Command descriptions for bot menu
START_COMMAND_DESC = "🚀 Start Bot"
HELP_COMMAND_DESC = "📚 Show Categories"
RANDOM_COMMAND_DESC = "🎲 Random Quiz"

# Image URLs for welcome messages
IMAGE_URLS = [
    "https://ik.imagekit.io/asadofc/Images1.png",
    "https://ik.imagekit.io/asadofc/Images2.png",
    "https://ik.imagekit.io/asadofc/Images3.png",
    "https://ik.imagekit.io/asadofc/Images4.png",
    "https://ik.imagekit.io/asadofc/Images5.png",
    "https://ik.imagekit.io/asadofc/Images6.png",
    "https://ik.imagekit.io/asadofc/Images7.png",
    "https://ik.imagekit.io/asadofc/Images8.png",
    "https://ik.imagekit.io/asadofc/Images9.png",
    "https://ik.imagekit.io/asadofc/Images10.png",
    "https://ik.imagekit.io/asadofc/Images11.png",
    "https://ik.imagekit.io/asadofc/Images12.png",
    "https://ik.imagekit.io/asadofc/Images13.png",
    "https://ik.imagekit.io/asadofc/Images14.png",
    "https://ik.imagekit.io/asadofc/Images15.png",
    "https://ik.imagekit.io/asadofc/Images16.png",
    "https://ik.imagekit.io/asadofc/Images17.png",
    "https://ik.imagekit.io/asadofc/Images18.png",
    "https://ik.imagekit.io/asadofc/Images19.png",
    "https://ik.imagekit.io/asadofc/Images20.png",
    "https://ik.imagekit.io/asadofc/Images21.png",
    "https://ik.imagekit.io/asadofc/Images22.png",
    "https://ik.imagekit.io/asadofc/Images23.png",
    "https://ik.imagekit.io/asadofc/Images24.png",
    "https://ik.imagekit.io/asadofc/Images25.png",
    "https://ik.imagekit.io/asadofc/Images26.png",
    "https://ik.imagekit.io/asadofc/Images27.png",
    "https://ik.imagekit.io/asadofc/Images28.png",
    "https://ik.imagekit.io/asadofc/Images29.png",
    "https://ik.imagekit.io/asadofc/Images30.png",
    "https://ik.imagekit.io/asadofc/Images31.png",
    "https://ik.imagekit.io/asadofc/Images32.png",
    "https://ik.imagekit.io/asadofc/Images33.png",
    "https://ik.imagekit.io/asadofc/Images34.png",
    "https://ik.imagekit.io/asadofc/Images35.png",
    "https://ik.imagekit.io/asadofc/Images36.png",
    "https://ik.imagekit.io/asadofc/Images37.png",
    "https://ik.imagekit.io/asadofc/Images38.png",
    "https://ik.imagekit.io/asadofc/Images39.png",
    "https://ik.imagekit.io/asadofc/Images40.png"
]

# Welcome message template structure
START_MESSAGE = {
    "title": "🎉 Hey there {user_mention}, Welcome!",
    "description": "🧠 iQ Lost brings you fun, fast, and smart quizzes across 24+ categories!",
    "features": """🎯 Key Features
├─ Lightning-fast quiz delivery
├─ 24+ rich categories to explore
├─ Global leaderboard system
└─ Track progress and compete""",
    "action": "🚀 Let's begin your quiz journey now!"
}

# Help messages for user guidance
HELP_MESSAGES = {
    "basic": """🎯 iQ Lost Quiz Bot

Hello {user_mention}! 👋

I'm your intelligent quiz companion with 24+ categories to challenge your knowledge!

🎮 Quick Start:
• /general - General Knowledge 🧠
• /music - Music Trivia 🎵
• /sports - Sports Quiz 🏅
• /random - Surprise me! 🎲

📋 More Commands:
• /start - Welcome message
• /help - This help menu

Ready to test your knowledge? 🚀""",
    "pages": {
        1: """🎯 iQ Lost Guide (1/10)

Hey {user_mention}, welcome to your quiz journey! 🌟  
I'm iQ Lost! Your fun quiz buddy with 24+ categories from science to sports!

🎮 How to Play:  
1. Pick a category  
2. Answer polls & get instant facts  
3. Learn, explore & have fun!

🏆 Features:  
• 24+ topics  
• Interactive polls  
• Instant explanations  
• Fair play system

Let's make learning fun! 🚀""",
        
        2: """📚 Knowledge Categories (2/10)

Hey {user_mention}, explore these brain-boosting categories:

🧠 General Knowledge:
/general - Test your overall knowledge

📚 Literature & History:
/books - Book trivia and literature
/history - Historical events and figures
/mythology - Gods, legends, and myths

🌍 Geography & Politics:
/geography - World geography
/politics - Political knowledge""",
        
        3: """🎬 Entertainment & Media (3/10)

Ready for some fun, {user_mention}? 🎭

🎬 Movies & TV:
/film - Movie trivia and cinema
/tv - Television shows and series
/musicals - Musical theater knowledge

🎵 Music & Performance:
/music - Music trivia across genres

⭐ Celebrity Culture:
/celebs - Celebrity knowledge
/anime - Anime and manga
/cartoons - Animated series""",
        
        4: """🎮 Gaming & Comics (4/10)

Level up your knowledge, {user_mention}! 🕹️

🎮 Video Games:
/games - Video game trivia
/board - Board game knowledge

💥 Comics & Graphics:
/comics - Comic book universe

🎨 Creative Arts:
/art - Art, design, and creativity""",
        
        5: """🔬 Science & Technology (5/10)

Discover the world of science, {user_mention}! 🧪

🌿 Natural Sciences:
/nature - Science and nature facts
/animals - Animal kingdom knowledge

💻 Technology:
/computers - Tech and computer science
/gadgets - Science gadgets and inventions

➗ Mathematics:
/math - Mathematical concepts""",
        
        6: """🏃‍♂️ Sports & Lifestyle (6/10)

Stay active with these topics, {user_mention}! 🏆

🏅 Sports:
/sports - Sports trivia and facts

🚗 Transportation:
/vehicles - Cars, planes, and transport

🎯 Special Commands:
/random - Get a surprise quiz from any category!""",
        
        7: """💡 Pro Tips & Strategies (7/10)

Master the quiz game, {user_mention}! 🎯

🧠 Quiz Strategies:
• Read questions carefully
• Think before answering
• Learn from explanations
• Try different categories

⚡ Rate Limiting:
• 2-second cooldown between requests
• Prevents spam and ensures fair play
• Quality over quantity!""",
        
        8: """🎮 Bot Features & Commands (8/10)

Unlock all features, {user_mention}! 🔓

🤖 Smart Features:
• Interactive poll questions
• Instant explanations
• Group and private chat support
• Auto-quiz in active groups

📋 Main Commands:
/start - Welcome and introduction
/help - This comprehensive guide
/random - Random category quiz

🚀 Auto-Quiz:
Groups get automatic quizzes every 2 hours once activated!""",
        
        9: """🏆 Challenge Yourself (9/10)

Push your limits, {user_mention}! 💪

🎯 Challenge Ideas:
• Try all 24 categories
• Focus on your weak areas
• Challenge friends in groups
• Set daily quiz goals

🌟 Did You Know?
iQ Lost has carefully curated high-quality, verified questions across all categories to give you the best quiz experience!""",
        
        10: """🚀 Ready to Begin? (10/10)

You're all set, {user_mention}! 🎓

🎯 Quick Start Commands:
/general 🧠 | /music 🎵 | /sports 🏅
/history 📜 | /games 🎮 | /nature 🌿

🎲 Feeling Lucky?
Use /random for a surprise quiz!

🏆 Remember:
Every expert was once a beginner. Start your iQ Lost journey today and watch your knowledge grow!

Good luck, quiz master! 🌟"""
    }
}

# Broadcast system message templates
BROADCAST_MESSAGES = {
    "choose_target": "📣 Choose broadcast target:",
    "target_info": "👥 Users: {user_count} individual users\n📢 Groups: {group_count} groups\n\nSelect where you want to send your broadcast message:",
    "mode_enabled": "📣 Broadcast mode enabled!\n\n🎯 Target: {target_name} ({target_count})\n\nSend me any message and I will forward it to all selected targets.",
    "complete": "📊 Broadcast complete!\n\n🎯 Target: {target_name}\n✅ Sent: {success_count}\n❌ Failed: {fail_count}\n\n🔒 Broadcast mode disabled.",
    "restricted": "⛔ This command is restricted."
}

# Ping command response messages
PING_MESSAGES = {
    "pinging": "🛰️ Pinging...",
    "pong": "🏓 <a href='https://t.me/SoulMeetsHQ'>Pong!</a> {response_time}ms"
}

# Error messages for various scenarios
ERROR_MESSAGES = {
    "unknown_command": "🤔 I don't understand that command. Type /help to see available commands.",
    "token_required": "BOT_TOKEN is required",
    "alive": "iQ Lost Quiz Bot is alive!"
}

# Color codes for console logging
class Colors:
    BLUE = '\033[94m'      # INFO/WARNING
    GREEN = '\033[92m'     # DEBUG
    YELLOW = '\033[93m'    # INFO
    RED = '\033[91m'       # ERROR
    RESET = '\033[0m'      # Reset color
    BOLD = '\033[1m'       # Bold text

# Custom formatter for colored logs
class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to entire log messages"""

    COLORS = {
        'DEBUG': Colors.GREEN,
        'INFO': Colors.YELLOW,
        'WARNING': Colors.BLUE,
        'ERROR': Colors.RED,
    }

    def format(self, record):
        # Get the original formatted message
        original_format = super().format(record)

        # Get color based on log level
        color = self.COLORS.get(record.levelname, Colors.RESET)

        # Apply color to the entire message
        colored_format = f"{color}{original_format}{Colors.RESET}"

        return colored_format

# Configure logging with colors system
def setup_colored_logging():
    """Setup colored logging configuration"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Remove existing handlers from logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler for output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create colored formatter with format
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger instance
    logger.addHandler(console_handler)

    return logger

# Initialize colored logger first thing
logger = setup_colored_logging()

# Extract user information from message
def extract_user_info(msg: Message) -> Dict[str, any]:
    """Extract user and chat information from message"""
    try:
        # Log the information extraction process
        logger.debug("🔍 Extracting user information from message")
        u = msg.from_user
        c = msg.chat
        # Build information dictionary for user
        info = {
            "user_id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "chat_id": c.id,
            "chat_type": c.type,
            "chat_title": c.title or c.first_name or "",
            "chat_username": f"@{c.username}" if c.username else "No Username",
            "chat_link": f"https://t.me/{c.username}" if c.username else "No Link",
        }
        # Log successful user info extraction
        logger.info(
            f"📑 User info extracted: {info['full_name']} (@{info['username']}) "
            f"[ID: {info['user_id']}] in {info['chat_title']} [{info['chat_id']}] {info['chat_link']}"
        )
        return info
    except Exception as e:
        # Log error if extraction fails
        logger.error(f"❌ Error extracting user info: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        # Return default info on failure
        return {
            "user_id": msg.from_user.id if msg.from_user else 0,
            "username": "Unknown",
            "full_name": "Unknown User",
            "first_name": "Unknown",
            "last_name": "",
            "chat_id": msg.chat.id if msg.chat else 0,
            "chat_type": "unknown",
            "chat_title": "Unknown Chat",
            "chat_username": "No Username",
            "chat_link": "No Link",
        }

# Log message with user details
def log_with_user_info(level: str, message: str, user_info: Dict[str, any]) -> None:
    """Log message with user information"""
    try:
        # Build detailed user information string
        user_detail = (
            f"👤 {user_info['full_name']} (@{user_info['username']}) "
            f"[ID: {user_info['user_id']}] | "
            f"💬 {user_info['chat_title']} [{user_info['chat_id']}] "
            f"({user_info['chat_type']}) {user_info['chat_link']}"
        )
        full_message = f"{message} | {user_detail}"

        # Log based on specified level
        if level.upper() == "INFO":
            logger.info(full_message)
        elif level.upper() == "DEBUG":
            logger.debug(full_message)
        elif level.upper() == "WARNING":
            logger.warning(full_message)
        elif level.upper() == "ERROR":
            logger.error(full_message)
        else:
            logger.info(full_message)
    except Exception as e:
        # Log error in logging function
        logger.error(f"❌ Error in log_with_user_info: {str(e)}")

# Fetch quiz from trivia API
async def fetch_quiz(category_id: int):
    """Fetch quiz data from OpenTDB API with robust error handling"""
    retries = 2
    
    # Log starting quiz fetch process
    logger.debug(f"🌐 Fetching quiz for category ID: {category_id}")
    
    for attempt in range(retries):
        try:
            # Log current attempt number
            logger.debug(f"🔄 Attempt {attempt + 1}/{retries} for category {category_id}")
            
            async with semaphore:
                # Build API URL for request
                url = f"https://opentdb.com/api.php?amount=1&type=multiple&category={category_id}"
                logger.debug(f"🔗 API URL: {url}")
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    # Log HTTP response status code
                    logger.debug(f"📡 HTTP response status: {resp.status}")
                    
                    # Handle rate limit response
                    if resp.status == 429:
                        logger.warning(f"⚠️ Rate limited (429) on attempt {attempt + 1}")
                        if attempt < retries - 1:
                            await asyncio.sleep(3)
                            continue
                        raise Exception("429 Rate Limited")
                    elif resp.status != 200:
                        logger.error(f"❌ HTTP error {resp.status} for category {category_id}")
                        raise Exception(f"HTTP {resp.status}")
                    
                    # Parse JSON response from API
                    data = await resp.json()
                    logger.debug(f"📊 API response received: {len(str(data))} characters")
                    
                    # Check if results exist
                    if not data.get("results"):
                        logger.error(f"❌ No results in API response for category {category_id}")
                        raise Exception("No quiz results returned")
                    
                    # Extract quiz question and answers
                    result = data["results"][0]
                    logger.debug(f"📝 Quiz question retrieved: {result.get('question', '')[:50]}...")
                    
                    # Clean HTML entities from text
                    q = unescape(result["question"])
                    correct = unescape(result["correct_answer"])
                    opts = [unescape(x) for x in result["incorrect_answers"]] + [correct]
                    
                    # Randomize option order for fairness
                    random.shuffle(opts)
                    correct_index = opts.index(correct)
                    
                    # Log successful quiz data fetch
                    logger.info(f"✅ Quiz fetched successfully for category {category_id}: {len(q)} chars question, {len(opts)} options")
                    
                    return q, opts, correct_index, correct
                    
        except Exception as e:
            # Log failed attempt with error
            logger.error(f"❌ Fetch attempt {attempt + 1} failed for category {category_id}: {str(e)}")
            logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
            if attempt == retries - 1:
                logger.error(f"💥 All attempts failed for category {category_id}")
                raise e

# Send quiz to user or group
async def send_quiz(msg: Message, cat_id: int, emoji: str, category_name: str = None):
    """Send quiz with comprehensive error handling and logging"""
    user_info = extract_user_info(msg)
    user_id = msg.from_user.id
    current_time = time.time()
    
    # Log quiz request with details
    log_with_user_info("INFO", f"🎯 Quiz request for category {category_name or cat_id} ({emoji})", user_info)
    
    # Check if user processing already
    if user_id in user_processing:
        log_with_user_info("WARNING", "⚠️ User already processing request, ignoring", user_info)
        return
    
    # Check cooldown period for rate limiting
    if user_id in user_last_request:
        time_since_last = current_time - user_last_request[user_id]
        if time_since_last < USER_COOLDOWN:
            log_with_user_info("WARNING", f"⚠️ User in cooldown ({USER_COOLDOWN - time_since_last:.1f}s remaining)", user_info)
            return
    
    # Mark user as processing request
    user_processing.add(user_id)
    user_last_request[user_id] = current_time
    
    # Handle group chat auto quiz
    group_id = None
    if msg.chat.type in ['group', 'supergroup']:
        group_id = msg.chat.id
        group_ids.add(group_id)
        auto_quiz_active_groups.add(group_id)
        log_with_user_info("DEBUG", f"📢 Group quiz request, added to active groups", user_info)
    
    try:
        # Send typing indicator to chat
        logger.debug(f"💬 Sending typing action to chat {msg.chat.id}")
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        
        # Fetch quiz data from API
        logger.info(f"🔄 Fetching quiz data for category {cat_id}")
        q, opts, correct_id, correct = await fetch_quiz(cat_id)
        
        # Log quiz data preparation success
        log_with_user_info("INFO", f"📋 Quiz data ready: {len(q)} chars question, {len(opts)} options", user_info)
        
        # Send quiz based on chat type
        if msg.chat.type in ['group', 'supergroup']:
            # Send group poll with reply
            logger.debug(f"📢 Sending group poll to {msg.chat.id}")
            poll_msg = await msg.reply_poll(
                question=f"{q} {emoji}",
                options=opts,
                type="quiz",
                correct_option_id=correct_id,
                is_anonymous=False,
                explanation=f"💡 Correct Answer: {correct}",
            )
        else:
            # Send private poll as answer
            logger.debug(f"👤 Sending private poll to {msg.chat.id}")
            poll_msg = await msg.answer_poll(
                question=f"{q} {emoji}",
                options=opts,
                type="quiz",
                correct_option_id=correct_id,
                is_anonymous=False,
                explanation=f"💡 Correct Answer: {correct}",
            )
        
        # Store poll data for tracking
        poll_data = {
            'question': q,
            'correct_answer': correct,
            'options': opts,
            'category': category_name or 'Unknown',
            'group_id': group_id,
            'message_id': poll_msg.message_id,
            'chat_id': msg.chat.id,
            'timestamp': time.time(),
            'user_id': user_id
        }
        
        # Store poll data with message ID
        active_polls[f"msg_{poll_msg.message_id}"] = poll_data
        logger.debug(f"💾 Stored poll data with key: msg_{poll_msg.message_id}")
        
        # Store poll data with poll ID
        if hasattr(poll_msg, 'poll') and poll_msg.poll and poll_msg.poll.id:
            active_polls[poll_msg.poll.id] = poll_data
            logger.debug(f"💾 Stored poll data with poll ID: {poll_msg.poll.id}")
        
        # Log successful quiz send completion
        log_with_user_info("INFO", f"✅ Quiz sent successfully: {category_name or 'Unknown'} category", user_info)
        
    except Exception as e:
        # Log error during quiz send
        logger.error(f"❌ Error sending quiz for category {cat_id}: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Failed to send quiz: {str(e)}", user_info)
        
    finally:
        # Always remove user from processing
        user_processing.discard(user_id)
        logger.debug(f"🔄 Removed user {user_id} from processing set")

# Auto quiz loop for groups
async def auto_quiz_loop():
    """Auto quiz loop with comprehensive error handling"""
    # Log auto quiz loop startup
    logger.info("🤖 Starting auto-quiz loop")
    
    try:
        # Wait for bot to be ready
        await bot.wait_until_ready() if hasattr(bot, "wait_until_ready") else asyncio.sleep(2)
        logger.info("✅ Bot ready for auto-quiz loop")
    except Exception as e:
        # Log error waiting for bot
        logger.error(f"❌ Error waiting for bot ready: {str(e)}")
        await asyncio.sleep(2)
    
    loop_count = 0
    
    while True:
        try:
            loop_count += 1
            # Log current loop iteration number
            logger.info(f"🔄 Auto-quiz loop iteration #{loop_count}")
            
            # Check if groups available
            if auto_quiz_active_groups:
                logger.info(f"📢 {len(auto_quiz_active_groups)} active groups for auto-quiz")

                # Select random quiz category
                cmd, (cat_id, emoji, desc) = random.choice(list(CATEGORIES.items()))
                logger.info(f"🎲 Selected category: {desc} ({emoji}) [ID: {cat_id}]")

                success_count = 0
                error_count = 0

                # Send quiz to all groups
                for group_id in auto_quiz_active_groups.copy():
                    try:
                        # Log quiz send to group
                        logger.debug(f"📤 Sending auto-quiz to group {group_id}")
                        await asyncio.sleep(1.5)
                        
                        # Send typing action to group
                        await bot.send_chat_action(group_id, ChatAction.TYPING)
                        logger.debug(f"💬 Sent typing action to group {group_id}")

                        # Fetch quiz data for group
                        q, opts, correct_id, correct = await fetch_quiz(cat_id)
                        logger.debug(f"✅ Fetched quiz data for group {group_id}")
                        
                        # Send poll to group directly
                        poll_msg = await bot.send_poll(
                            chat_id=group_id,
                            question=f"{q} {emoji}",
                            options=opts,
                            type="quiz",
                            correct_option_id=correct_id,
                            is_anonymous=False,
                            explanation=f"💡 Correct Answer: {correct}",
                        )
                        
                        # Store poll data for tracking
                        poll_data = {
                            'question': q,
                            'correct_answer': correct,
                            'options': opts,
                            'category': desc,
                            'group_id': group_id,
                            'message_id': poll_msg.message_id,
                            'chat_id': group_id,
                            'timestamp': time.time(),
                            'user_id': None
                        }
                        
                        # Store poll with message key
                        active_polls[f"msg_{poll_msg.message_id}"] = poll_data
                        
                        # Store poll with poll ID
                        if hasattr(poll_msg, 'poll') and poll_msg.poll and poll_msg.poll.id:
                            active_polls[poll_msg.poll.id] = poll_data
                        
                        success_count += 1
                        # Log successful auto quiz send
                        logger.info(f"✅ Auto-quiz sent to group {group_id}: {desc}")
                        
                    except Exception as e:
                        error_count += 1
                        # Log failed auto quiz send
                        logger.error(f"❌ Failed to send auto-quiz to group {group_id}: {str(e)}")
                        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
                        auto_quiz_active_groups.discard(group_id)
                        logger.warning(f"🗑️ Removed inactive group {group_id} from auto-quiz")

                # Log auto quiz round statistics
                logger.info(f"📊 Auto-quiz round complete: {success_count} sent, {error_count} failed")
            else:
                # Log no active groups found
                logger.debug("📭 No active groups for auto-quiz")

        except Exception as err:
            # Log critical error in loop
            logger.error(f"💥 Critical error in auto-quiz loop: {str(err)}")
            logger.debug(f"📊 Error traceback: {traceback.format_exc()}")

        # Sleep for two hours interval
        logger.info("⏰ Auto-quiz loop sleeping for 2 hours")
        await asyncio.sleep(7200)

# Show basic help message display
async def show_basic_help(callback_or_msg, edit=False):
    """Show basic help with error handling"""
    try:
        user_info = extract_user_info(callback_or_msg)
        # Log basic help request received
        log_with_user_info("INFO", "📚 Showing basic help", user_info)
        
        user_id = callback_or_msg.from_user.id
        full_name = callback_or_msg.from_user.full_name
        user_mention = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
        
        # Format help text with mention
        text = HELP_MESSAGES["basic"].format(user_mention=user_mention)

        # Create expand guide keyboard button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Expand Guide", callback_data="help_expand")]
        ])
        
        # Send help based on context
        if edit and hasattr(callback_or_msg, 'message'):
            await callback_or_msg.message.edit_text(text, reply_markup=keyboard)
            logger.debug("✏️ Edited help message")
        elif hasattr(callback_or_msg, 'reply'):
            await callback_or_msg.reply(text, reply_markup=keyboard)
            logger.debug("📤 Sent help message as reply")
        else:
            await callback_or_msg.answer(text, reply_markup=keyboard)
            logger.debug("📤 Sent help message as answer")
            
        # Log successful help display completion
        log_with_user_info("INFO", "✅ Basic help displayed successfully", user_info)
        
    except Exception as e:
        # Log error showing basic help
        logger.error(f"❌ Error showing basic help: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        try:
            # Fallback simple message on error
            await callback_or_msg.reply("❌ Error loading help. Use /start to see available commands.")
        except:
            pass

# Show specific help page number
async def show_help_page(callback_or_msg, user_id, page, edit=False):
    """Show help page with error handling"""
    try:
        user_info = extract_user_info(callback_or_msg)
        # Log help page request details
        log_with_user_info("INFO", f"📖 Showing help page {page}", user_info)
        
        full_name = callback_or_msg.from_user.full_name
        user_mention = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
        
        # Get page text with formatting
        text = HELP_MESSAGES["pages"].get(page, HELP_MESSAGES["pages"][1]).format(user_mention=user_mention)
        logger.debug(f"📄 Help page {page} text prepared: {len(text)} characters")
        
        # Create navigation buttons for pages
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Previous", callback_data="help_prev"))
        if page < 10:
            nav_buttons.append(InlineKeyboardButton(text="Next ▶️", callback_data="help_next"))
        
        keyboard_rows = []
        
        # Special handling for last page
        if page == 10:
            first_row = [InlineKeyboardButton(text="◀️ Previous", callback_data="help_prev")]
            first_row.append(InlineKeyboardButton(text="🏠 Home", callback_data="help_page_1"))
            keyboard_rows.append(first_row)
            keyboard_rows.append([InlineKeyboardButton(text="📖 Minimize", callback_data="help_minimize")])
        else:
            # Regular page navigation buttons
            if nav_buttons:
                keyboard_rows.append(nav_buttons)
            keyboard_rows.append([InlineKeyboardButton(text="📖 Minimize", callback_data="help_minimize")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        # Log keyboard preparation for page
        logger.debug(f"⌨️ Help keyboard prepared with {len(keyboard_rows)} rows")
        
        # Send help page based on context
        if edit and hasattr(callback_or_msg, 'message'):
            await callback_or_msg.message.edit_text(text, reply_markup=keyboard)
            logger.debug(f"✏️ Edited help page {page}")
        elif hasattr(callback_or_msg, 'reply'):
            await callback_or_msg.reply(text, reply_markup=keyboard)
            logger.debug(f"📤 Sent help page {page} as reply")
        else:
            await callback_or_msg.answer(text, reply_markup=keyboard)
            logger.debug(f"📤 Sent help page {page} as answer")
            
        # Log successful help page display
        log_with_user_info("INFO", f"✅ Help page {page} displayed successfully", user_info)
        
    except Exception as e:
        # Log error showing help page
        logger.error(f"❌ Error showing help page {page}: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        try:
            # Fallback to basic help view
            await show_basic_help(callback_or_msg, edit)
        except:
            pass

# Setup bot command menu list
async def setup_bot_commands():
    """Setup bot commands with error handling"""
    try:
        # Log bot command setup process
        logger.info("⚙️ Setting up bot commands...")
        
        # Build command list with descriptions
        cmds = [
            BotCommand(command="start", description=START_COMMAND_DESC),
            BotCommand(command="help", description=HELP_COMMAND_DESC),
            BotCommand(command="random", description=RANDOM_COMMAND_DESC),
        ] + [
            BotCommand(command=cmd, description=f"{emoji} {' '.join(desc.split()[:2])}")
            for cmd, (_, emoji, desc) in CATEGORIES.items()
        ]
        
        # Log number of commands prepared
        logger.debug(f"📋 Prepared {len(cmds)} bot commands")
        
        # Set commands in telegram API
        await bot.set_my_commands(cmds)
        logger.info(f"✅ Bot commands set successfully: {len(cmds)} commands")
        
    except Exception as e:
        # Log error during command setup
        logger.error(f"❌ Error setting up bot commands: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")

# Bot startup initialization and setup
async def on_startup():
    """Bot startup with comprehensive error handling"""
    global session
    
    try:
        # Log bot startup initiation process
        logger.info("🚀 Bot startup initiated...")
        
        # Initialize HTTP session for requests
        try:
            session = aiohttp.ClientSession()
            logger.info("✅ HTTP session initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize HTTP session: {str(e)}")
            raise
        
        # Setup bot commands in menu
        try:
            await setup_bot_commands()
            logger.info("✅ Bot commands setup completed")
        except Exception as e:
            logger.error(f"❌ Bot commands setup failed: {str(e)}")
        
        # Get bot information from API
        try:
            me = await bot.get_me()
            logger.info(f"🤖 Bot info: @{me.username} ({me.first_name}) [ID: {me.id}]")
        except Exception as e:
            logger.error(f"❌ Failed to get bot info: {str(e)}")
            
        # Log successful startup completion
        logger.info("🎉 Bot startup completed successfully!")
        
    except Exception as e:
        # Log critical error during startup
        logger.error(f"💥 Critical error during bot startup: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        raise

# Bot shutdown cleanup and closing
async def on_shutdown():
    """Bot shutdown with error handling"""
    global session
    
    try:
        # Log bot shutdown initiation process
        logger.info("🛑 Bot shutdown initiated...")
        
        # Close HTTP session if exists
        if session:
            try:
                await session.close()
                logger.info("✅ HTTP session closed")
            except Exception as e:
                logger.error(f"❌ Error closing HTTP session: {str(e)}")
        
        # Log shutdown completion message
        logger.info("👋 Bot shutdown completed")
        
    except Exception as e:
        # Log error during shutdown process
        logger.error(f"❌ Error during bot shutdown: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")

# Global error handler for exceptions
async def global_error_handler(update: Update, exception):
    """Global error handler for all bot errors"""
    try:
        error_id = f"ERR_{int(time.time())}"
        # Log global error with ID
        logger.error(f"💥 Global error [{error_id}]: {str(exception)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        
        # Log with user info if available
        if update and update.message:
            user_info = extract_user_info(update.message)
            log_with_user_info("ERROR", f"💥 Global error [{error_id}]: {str(exception)}", user_info)
        elif update and update.callback_query:
            user_info = extract_user_info(update.callback_query)
            log_with_user_info("ERROR", f"💥 Global callback error [{error_id}]: {str(exception)}", user_info)
        
        # Log continuing operation after error
        logger.info(f"🔄 Continuing bot operation after error [{error_id}]")
        
    except Exception as e:
        # Log error in error handler
        logger.error(f"💥 Error in error handler: {str(e)}")
    
    return True

# Dummy HTTP server for deployment
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Log HTTP GET request received
            logger.debug("🌐 HTTP GET request received")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(ERROR_MESSAGES["alive"].encode())
            logger.debug("✅ HTTP GET response sent")
        except Exception as e:
            logger.error(f"❌ Error handling HTTP GET: {str(e)}")

    def do_HEAD(self):
        try:
            # Log HTTP HEAD request received
            logger.debug("🌐 HTTP HEAD request received")
            self.send_response(200)
            self.end_headers()
            logger.debug("✅ HTTP HEAD response sent")
        except Exception as e:
            logger.error(f"❌ Error handling HTTP HEAD: {str(e)}")
        
    def log_message(self, format, *args):
        # Suppress default HTTP server logs
        pass

# Start dummy HTTP server thread
def start_dummy_server():
    """Start dummy HTTP server with error handling"""
    try:
        port = int(os.environ.get("PORT", 10000))
        # Log HTTP server startup process
        logger.info(f"🌐 Starting HTTP server on port {port}")
        
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        logger.info(f"✅ HTTP server started successfully on port {port}")
        server.serve_forever()
        
    except Exception as e:
        # Log error starting HTTP server
        logger.error(f"❌ Error starting HTTP server: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")

# Handle poll updates from telegram
@dp.poll()
async def handle_poll_update(poll: types.Poll):
    """Handle poll updates with error handling"""
    try:
        # Log poll update received ID
        logger.debug(f"📊 Poll update received: {poll.id}")
        
        # Check if poll already tracked
        if poll.id in active_polls:
            logger.debug(f"📊 Poll {poll.id} already in active polls")
            return
        
        poll_data = None
        found_key = None
        
        # Try to match poll data
        for key, data in list(active_polls.items()):
            try:
                # Match message based poll data
                if key.startswith("msg_"):
                    stored_question = data['question']
                    poll_question = poll.question
                    
                    # Clean emoji characters from question
                    emoji_chars = "🧠🎵🏅📜🎮🌿💻➗⚡🌍🏛️🎨⭐🐾🚗💥📱🀄🎪🎬📺🎭🎲📚"
                    clean_poll_q = poll_question.rstrip(' ' + emoji_chars).strip()
                    
                    # Check if questions match exactly
                    if stored_question == clean_poll_q:
                        poll_data = data.copy()
                        found_key = key
                        logger.debug(f"📊 Poll matched with key: {key}")
                        break
                        
            except Exception as e:
                # Log error matching poll data
                logger.error(f"❌ Error matching poll with key {key}: {str(e)}")
                continue
        
        # Store poll data if found
        if poll_data:
            active_polls[poll.id] = poll_data
            logger.info(f"📊 Poll {poll.id} data stored successfully")
        else:
            logger.warning(f"⚠️ No matching data found for poll {poll.id}")
        
    except Exception as e:
        # Log error handling poll update
        logger.error(f"❌ Error handling poll update: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")

# Handle poll answers from users
@dp.poll_answer()
async def handle_poll_answer(poll_answer):
    """Handle poll answers with error handling"""
    try:
        # Log poll answer received ID
        logger.debug(f"✅ Poll answer received for poll {poll_answer.poll_id}")
        
        poll_data = None
        
        # Try to find poll data
        if poll_answer.poll_id in active_polls:
            poll_data = active_polls[poll_answer.poll_id]
            logger.debug(f"📊 Found poll data by poll ID")
        else:
            # Fallback find most recent poll
            current_time = time.time()
            for key, data in list(active_polls.items()):
                try:
                    # Check poll age within limits
                    if current_time - data.get('timestamp', 0) < 600:  # 10 minutes
                        if not poll_data or data.get('timestamp', 0) > poll_data.get('timestamp', 0):
                            poll_data = data
                    else:
                        # Clean up old poll data
                        del active_polls[key]
                        logger.debug(f"🗑️ Cleaned up old poll data: {key}")
                except Exception as e:
                    # Log error processing poll data
                    logger.error(f"❌ Error processing poll data {key}: {str(e)}")
                    continue
        
        # Check if poll data found
        if not poll_data:
            logger.warning(f"⚠️ No poll data found for answer to poll {poll_answer.poll_id}")
            return
            
        # Extract user answer information
        user_id = poll_answer.user.id
        user_answer_index = poll_answer.option_ids[0] if poll_answer.option_ids else -1
        
        # Validate answer index is valid
        if user_answer_index == -1:
            logger.warning(f"⚠️ Invalid answer index for user {user_id}")
            return
            
        # Check if answer is correct
        user_answer = poll_data['options'][user_answer_index]
        correct_answer = poll_data['correct_answer']
        is_correct = user_answer == correct_answer
        
        # Log successful poll answer processing
        logger.info(f"✅ Poll answer processed: User {user_id}, Answer: {user_answer}, Correct: {is_correct}")
        
    except Exception as e:
        # Log error handling poll answer
        logger.error(f"❌ Error handling poll answer: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")

# Category command handlers with logging
@dp.message(Command("general"))
async def cmd_general(msg: Message):
    user_info = extract_user_info(msg)
    # Log general knowledge quiz request
    log_with_user_info("INFO", "🧠 General Knowledge quiz requested", user_info)
    await send_quiz(msg, 9, "🧠", "General Knowledge")

@dp.message(Command("books"))
async def cmd_books(msg: Message):
    user_info = extract_user_info(msg)
    # Log books quiz request received
    log_with_user_info("INFO", "📚 Books quiz requested", user_info)
    await send_quiz(msg, 10, "📚", "Books")

@dp.message(Command("film"))
async def cmd_film(msg: Message):
    user_info = extract_user_info(msg)
    # Log film quiz request received
    log_with_user_info("INFO", "🎬 Film quiz requested", user_info)
    await send_quiz(msg, 11, "🎬", "Film")

@dp.message(Command("music"))
async def cmd_music(msg: Message):
    user_info = extract_user_info(msg)
    # Log music quiz request received
    log_with_user_info("INFO", "🎵 Music quiz requested", user_info)
    await send_quiz(msg, 12, "🎵", "Music")

@dp.message(Command("musicals"))
async def cmd_musicals(msg: Message):
    user_info = extract_user_info(msg)
    # Log musicals quiz request received
    log_with_user_info("INFO", "🎭 Musicals quiz requested", user_info)
    await send_quiz(msg, 13, "🎭", "Musicals")

@dp.message(Command("tv"))
async def cmd_tv(msg: Message):
    user_info = extract_user_info(msg)
    # Log TV shows quiz requested
    log_with_user_info("INFO", "📺 TV Shows quiz requested", user_info)
    await send_quiz(msg, 14, "📺", "TV Shows")

@dp.message(Command("games"))
async def cmd_games(msg: Message):
    user_info = extract_user_info(msg)
    # Log video games quiz requested
    log_with_user_info("INFO", "🎮 Video Games quiz requested", user_info)
    await send_quiz(msg, 15, "🎮", "Video Games")

@dp.message(Command("board"))
async def cmd_board(msg: Message):
    user_info = extract_user_info(msg)
    # Log board games quiz requested
    log_with_user_info("INFO", "🎲 Board Games quiz requested", user_info)
    await send_quiz(msg, 16, "🎲", "Board Games")

@dp.message(Command("nature"))
async def cmd_nature(msg: Message):
    user_info = extract_user_info(msg)
    # Log nature quiz request received
    log_with_user_info("INFO", "🌿 Nature quiz requested", user_info)
    await send_quiz(msg, 17, "🌿", "Nature")

@dp.message(Command("computers"))
async def cmd_computers(msg: Message):
    user_info = extract_user_info(msg)
    # Log computers quiz request received
    log_with_user_info("INFO", "💻 Computers quiz requested", user_info)
    await send_quiz(msg, 18, "💻", "Computers")

@dp.message(Command("math"))
async def cmd_math(msg: Message):
    user_info = extract_user_info(msg)
    # Log mathematics quiz request received
    log_with_user_info("INFO", "➗ Mathematics quiz requested", user_info)
    await send_quiz(msg, 19, "➗", "Mathematics")

@dp.message(Command("mythology"))
async def cmd_mythology(msg: Message):
    user_info = extract_user_info(msg)
    # Log mythology quiz request received
    log_with_user_info("INFO", "⚡ Mythology quiz requested", user_info)
    await send_quiz(msg, 20, "⚡", "Mythology")

@dp.message(Command("sports"))
async def cmd_sports(msg: Message):
    user_info = extract_user_info(msg)
    # Log sports quiz request received
    log_with_user_info("INFO", "🏅 Sports quiz requested", user_info)
    await send_quiz(msg, 21, "🏅", "Sports")

@dp.message(Command("geography"))
async def cmd_geography(msg: Message):
    user_info = extract_user_info(msg)
    # Log geography quiz request received
    log_with_user_info("INFO", "🌍 Geography quiz requested", user_info)
    await send_quiz(msg, 22, "🌍", "Geography")

@dp.message(Command("history"))
async def cmd_history(msg: Message):
    user_info = extract_user_info(msg)
    # Log history quiz request received
    log_with_user_info("INFO", "📜 History quiz requested", user_info)
    await send_quiz(msg, 23, "📜", "History")

@dp.message(Command("politics"))
async def cmd_politics(msg: Message):
    user_info = extract_user_info(msg)
    # Log politics quiz request received
    log_with_user_info("INFO", "🏛️ Politics quiz requested", user_info)
    await send_quiz(msg, 24, "🏛️", "Politics")

@dp.message(Command("art"))
async def cmd_art(msg: Message):
    user_info = extract_user_info(msg)
    # Log art quiz request received
    log_with_user_info("INFO", "🎨 Art quiz requested", user_info)
    await send_quiz(msg, 25, "🎨", "Art")

@dp.message(Command("celebs"))
async def cmd_celebs(msg: Message):
    user_info = extract_user_info(msg)
    # Log celebrities quiz request received
    log_with_user_info("INFO", "⭐ Celebrities quiz requested", user_info)
    await send_quiz(msg, 26, "⭐", "Celebrities")

@dp.message(Command("animals"))
async def cmd_animals(msg: Message):
    user_info = extract_user_info(msg)
    # Log animals quiz request received
    log_with_user_info("INFO", "🐾 Animals quiz requested", user_info)
    await send_quiz(msg, 27, "🐾", "Animals")

@dp.message(Command("vehicles"))
async def cmd_vehicles(msg: Message):
    user_info = extract_user_info(msg)
    # Log vehicles quiz request received
    log_with_user_info("INFO", "🚗 Vehicles quiz requested", user_info)
    await send_quiz(msg, 28, "🚗", "Vehicles")

@dp.message(Command("comics"))
async def cmd_comics(msg: Message):
    user_info = extract_user_info(msg)
    # Log comics quiz request received
    log_with_user_info("INFO", "💥 Comics quiz requested", user_info)
    await send_quiz(msg, 29, "💥", "Comics")

@dp.message(Command("gadgets"))
async def cmd_gadgets(msg: Message):
    user_info = extract_user_info(msg)
    # Log gadgets quiz request received
    log_with_user_info("INFO", "📱 Gadgets quiz requested", user_info)
    await send_quiz(msg, 30, "📱", "Gadgets")

@dp.message(Command("anime"))
async def cmd_anime(msg: Message):
    user_info = extract_user_info(msg)
    # Log anime quiz request received
    log_with_user_info("INFO", "🀄 Anime quiz requested", user_info)
    await send_quiz(msg, 31, "🀄", "Anime")

@dp.message(Command("cartoons"))
async def cmd_cartoons(msg: Message):
    user_info = extract_user_info(msg)
    # Log cartoons quiz request received
    log_with_user_info("INFO", "🎪 Cartoons quiz requested", user_info)
    await send_quiz(msg, 32, "🎪", "Cartoons")

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    user_info = extract_user_info(msg)
    # Log start command received event
    log_with_user_info("INFO", "🚀 Start command received", user_info)
    
    try:
        # Add user to tracking set
        user_ids.add(msg.from_user.id)
        logger.debug(f"👤 Added user {msg.from_user.id} to user_ids set")

        # Handle group chat registration
        if msg.chat.type in ['group', 'supergroup']:
            group_ids.add(msg.chat.id)
            auto_quiz_active_groups.add(msg.chat.id)
            log_with_user_info("DEBUG", "📢 Added group to auto-quiz groups", user_info)

        # Send typing indicator to chat
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        logger.debug(f"💬 Sent typing action to {msg.chat.id}")

        # Create keyboard with useful links
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Updates", url="https://t.me/WorkGlows"),
                InlineKeyboardButton(text="Support", url="https://t.me/SoulMeetsHQ")
            ],
            [
                InlineKeyboardButton(
                    text="Add Me To Your Group",
                    url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"
                )
            ]
        ])

        # Create user mention for message
        user_mention = f"<a href='tg://user?id={msg.from_user.id}'>{msg.from_user.full_name}</a>"

        # Build complete start message text
        text = f"""{START_MESSAGE["title"].format(user_mention=user_mention)}

{START_MESSAGE["description"]}

<blockquote>{START_MESSAGE["features"]}</blockquote>

{START_MESSAGE["action"]}"""

        # Select random welcome image
        selected_image = random.choice(IMAGE_URLS)
        logger.debug(f"🖼️ Selected image: {selected_image}")

        # Send message based on chat type
        if msg.chat.type in ['group', 'supergroup']:
            response = await msg.reply_photo(
                photo=selected_image,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            logger.debug("📤 Sent start message as group reply")
        else:
            response = await msg.answer_photo(
                photo=selected_image,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            logger.debug("📤 Sent start message as private answer")
            
        # Log successful start message send
        log_with_user_info("INFO", "✅ Start message sent successfully", user_info)
        
    except Exception as e:
        # Log error in start command
        logger.error(f"❌ Error in start command: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Start command failed: {str(e)}", user_info)

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    user_info = extract_user_info(msg)
    # Log help command received event
    log_with_user_info("INFO", "📚 Help command received", user_info)
    
    try:
        # Add user to tracking system
        user_ids.add(msg.from_user.id)
        
        # Handle group chat registration
        if msg.chat.type in ['group', 'supergroup']:
            group_ids.add(msg.chat.id)
            auto_quiz_active_groups.add(msg.chat.id)
            log_with_user_info("DEBUG", "📢 Added group to auto-quiz groups", user_info)

        # Send typing indicator to chat
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        logger.debug(f"💬 Sent typing action to {msg.chat.id}")

        # Show basic help to user
        await show_basic_help(msg)
        log_with_user_info("INFO", "✅ Help message sent successfully", user_info)
        
    except Exception as e:
        # Log error in help command
        logger.error(f"❌ Error in help command: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Help command failed: {str(e)}", user_info)
    
@dp.message(Command("random"))
async def cmd_random(msg: Message):
    user_info = extract_user_info(msg)
    # Log random quiz command received
    log_with_user_info("INFO", "🎲 Random quiz command received", user_info)
    
    try:
        # Add user to tracking system
        user_ids.add(msg.from_user.id)
        
        # Handle group chat registration
        if msg.chat.type in ['group', 'supergroup']:
            group_ids.add(msg.chat.id)
            auto_quiz_active_groups.add(msg.chat.id)
            log_with_user_info("DEBUG", "📢 Added group to auto-quiz groups", user_info)
        
        # Send typing indicator to chat
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        logger.debug(f"💬 Sent typing action to {msg.chat.id}")
        
        # Select random category from available
        cmd, (cat_id, emoji, desc) = random.choice(list(CATEGORIES.items()))
        logger.debug(f"🎲 Selected random category: {desc} ({emoji})")
        log_with_user_info("INFO", f"🎲 Selected random category: {desc}", user_info)
        
        # Send quiz with selected category
        await send_quiz(msg, cat_id, emoji, desc)
        
    except Exception as e:
        # Log error in random command
        logger.error(f"❌ Error in random command: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Random command failed: {str(e)}", user_info)

@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    user_info = extract_user_info(msg)
    
    # Check if user is owner
    if msg.from_user.id != OWNER_ID:
        log_with_user_info("WARNING", "⛔ Unauthorized broadcast attempt", user_info)
        return
    
    # Log broadcast command from owner
    log_with_user_info("INFO", "📣 Broadcast command received from owner", user_info)
    
    try:
        # Send typing indicator to chat
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        
        # Create keyboard for broadcast targets
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"👥 Users ({len(user_ids)})", callback_data="broadcast_users"),
                InlineKeyboardButton(text=f"📢 Groups ({len(group_ids)})", callback_data="broadcast_groups")
            ]
        ])
        
        # Send broadcast options to owner
        response = await msg.answer(
            f"{BROADCAST_MESSAGES['choose_target']}\n\n"
            f"{BROADCAST_MESSAGES['target_info'].format(user_count=len(user_ids), group_count=len(group_ids))}",
            reply_markup=keyboard
        )
        
        # Log broadcast options presented successfully
        logger.info(f"📣 Broadcast options presented: {len(user_ids)} users, {len(group_ids)} groups")
        log_with_user_info("INFO", "✅ Broadcast menu sent successfully", user_info)
        
    except Exception as e:
        # Log error in broadcast command
        logger.error(f"❌ Error in broadcast command: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Broadcast command failed: {str(e)}", user_info)

@dp.message(F.text == "/ping")
async def ping_command(msg: Message):
    user_info = extract_user_info(msg)
    # Log ping command received event
    log_with_user_info("INFO", "🏓 Ping command received", user_info)
    
    try:
        # Record start time for measurement
        start = time.perf_counter()

        # Send typing indicator to chat
        await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
        logger.debug(f"💬 Sent typing action to {msg.chat.id}")

        # Send initial ping message response
        if msg.chat.type in ['group', 'supergroup']:
            response = await msg.reply(PING_MESSAGES["pinging"])
            logger.debug("📤 Sent ping message as group reply")
        else:
            response = await msg.answer(PING_MESSAGES["pinging"])
            logger.debug("📤 Sent ping message as private answer")

        # Calculate response time in milliseconds
        end = time.perf_counter()
        response_time = round((end - start) * 1000, 2)
        logger.debug(f"⏱️ Response time calculated: {response_time}ms")

        # Edit message with pong response
        await response.edit_text(
            PING_MESSAGES["pong"].format(response_time=response_time),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
        # Log successful pong response sent
        log_with_user_info("INFO", f"🏓 Pong sent successfully: {response_time}ms", user_info)

    except Exception as e:
        # Log error in ping command
        logger.error(f"❌ Error in ping command: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Ping command failed: {str(e)}", user_info)

@dp.callback_query()
async def handle_help_pagination(callback: types.CallbackQuery):
    user_info = extract_user_info(callback)
    # Log callback query received with data
    log_with_user_info("INFO", f"⚡ Callback query received: {callback.data}", user_info)
    
    try:
        # Handle broadcast callback queries first
        if callback.data.startswith('broadcast_'):
            # Check if user is owner
            if callback.from_user.id != OWNER_ID:
                await callback.answer(BROADCAST_MESSAGES["restricted"], show_alert=True)
                log_with_user_info("WARNING", "⛔ Unauthorized broadcast callback attempt", user_info)
                return
            
            # Get target from callback data
            target = callback.data.split('_')[1]
            broadcast_target[callback.from_user.id] = target
            broadcast_mode.add(callback.from_user.id)
            
            # Set target list based on selection
            if target == "users":
                current_targets = user_ids
            else:
                current_targets = group_ids
            
            # Prepare target information for display
            target_text = "individual users" if target == "users" else "groups"
            target_count = len(current_targets)
            
            # Edit message with broadcast mode
            await callback.message.edit_text(
                BROADCAST_MESSAGES["mode_enabled"].format(
                    target_name=target_text,
                    target_count=target_count
                )
            )
            
            # Log broadcast mode enabled successfully
            logger.info(f"📣 Broadcast mode enabled for {target_text}: {target_count} targets")
            log_with_user_info("INFO", f"✅ Broadcast mode enabled: {target_text}", user_info)
            
            await callback.answer()
            return
        
        # Skip non help callback queries
        if not callback.data.startswith('help_'):
            await callback.answer()
            return
        
        user_id = callback.from_user.id
        action = callback.data.split('_')[1]
        
        # Log help action being processed
        logger.debug(f"📖 Help action: {action} for user {user_id}")
        
        # Handle expand help to full guide
        if action == 'expand':
            help_page_states[user_id] = {'expanded': True, 'page': 1}
            await show_help_page(callback, user_id, 1, edit=True)
            log_with_user_info("DEBUG", "📖 Help expanded to page 1", user_info)
        # Handle minimize help to basic view
        elif action == 'minimize':
            help_page_states.pop(user_id, None)
            await show_basic_help(callback, edit=True)
            log_with_user_info("DEBUG", "📖 Help minimized to basic view", user_info)
        # Handle previous page navigation
        elif action == 'prev':
            current_page = help_page_states.get(user_id, {}).get('page', 1)
            new_page = max(1, current_page - 1)
            help_page_states[user_id] = help_page_states.get(user_id, {})
            help_page_states[user_id]['page'] = new_page
            await show_help_page(callback, user_id, new_page, edit=True)
            log_with_user_info("DEBUG", f"📖 Help previous page: {new_page}", user_info)
        # Handle next page navigation
        elif action == 'next':
            current_page = help_page_states.get(user_id, {}).get('page', 1)
            new_page = min(10, current_page + 1)
            help_page_states[user_id] = help_page_states.get(user_id, {})
            help_page_states[user_id]['page'] = new_page
            await show_help_page(callback, user_id, new_page, edit=True)
            log_with_user_info("DEBUG", f"📖 Help next page: {new_page}", user_info)
        # Handle home page button click
        elif action == 'page' and len(callback.data.split('_')) > 2 and callback.data.split('_')[2] == '1':
            help_page_states[user_id] = help_page_states.get(user_id, {})
            help_page_states[user_id]['page'] = 1
            await show_help_page(callback, user_id, 1, edit=True)
            log_with_user_info("DEBUG", "📖 Help home page (1) requested", user_info)
        
        # Answer callback query to telegram
        await callback.answer()
        log_with_user_info("INFO", f"✅ Callback query handled successfully: {action}", user_info)
        
    except Exception as e:
        # Log error handling callback query
        logger.error(f"❌ Error handling callback query: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Callback query failed: {str(e)}", user_info)
        
        try:
            # Answer with error message
            await callback.answer("❌ Something went wrong. Please try again.")
        except:
            pass

@dp.message()
async def catch_all(msg: Message):
    user_info = extract_user_info(msg)
    
    try:
        # Handle broadcast mode message forwarding
        if msg.from_user.id in broadcast_mode:
            log_with_user_info("INFO", "📣 Processing broadcast message", user_info)
            
            # Send typing indicator to user
            await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

            success_count = 0
            fail_count = 0

            # Get target from broadcast settings
            target = broadcast_target.get(msg.from_user.id, "users")
            
            # Set target list based on type
            if target == "users":
                target_ids = user_ids
            else:
                target_ids = group_ids
            
            target_name = "users" if target == "users" else "groups"
            
            # Log starting broadcast to targets
            logger.info(f"📣 Broadcasting to {len(target_ids)} {target_name}")

            # Send message to all targets
            for target_id in list(target_ids):
                try:
                    # Handle forwarded messages differently
                    if msg.forward_from or msg.forward_from_chat:
                        await bot.forward_message(
                            chat_id=target_id,
                            from_chat_id=msg.chat.id,
                            message_id=msg.message_id
                        )
                        logger.debug(f"📤 Forwarded message to {target_id}")
                    else:
                        # Copy regular messages to targets
                        await bot.copy_message(
                            chat_id=target_id,
                            from_chat_id=msg.chat.id,
                            message_id=msg.message_id
                        )
                        logger.debug(f"📤 Copied message to {target_id}")

                    success_count += 1
                    
                except Exception as e:
                    # Log failed message send
                    logger.error(f"❌ Failed to send to {target_id}: {str(e)}")
                    fail_count += 1

            # Disable broadcast mode after completion
            broadcast_mode.remove(msg.from_user.id)
            broadcast_target.pop(msg.from_user.id, None)

            # Send completion report to user
            response = await msg.answer(
                BROADCAST_MESSAGES["complete"].format(
                    target_name=target_name.capitalize(),
                    success_count=success_count,
                    fail_count=fail_count
                )
            )
            
            # Log broadcast completion statistics
            logger.info(f"📊 Broadcast complete: {success_count} sent, {fail_count} failed")
            log_with_user_info("INFO", f"✅ Broadcast completed: {success_count}/{success_count + fail_count} sent", user_info)
            
        # Handle group chat activity tracking
        elif msg.chat.type in ['group', 'supergroup']:
            group_ids.add(msg.chat.id)
            auto_quiz_active_groups.add(msg.chat.id)
            user_ids.add(msg.from_user.id)
            
            # Log group message activity recorded
            logger.debug(f"📢 Group message processed: {msg.chat.id}")
            log_with_user_info("DEBUG", "📢 Group activity recorded", user_info)
            
        else:
            # Handle unknown commands in private
            if msg.chat.type not in ['group', 'supergroup']:
                await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)
                response = await msg.answer(ERROR_MESSAGES["unknown_command"])
                
                # Log unknown command response sent
                log_with_user_info("INFO", "❓ Unknown command response sent", user_info)
                
    except Exception as e:
        # Log error in catch all handler
        logger.error(f"❌ Error in catch_all handler: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        log_with_user_info("ERROR", f"💥 Catch-all handler failed: {str(e)}", user_info)

# Main execution block for bot
if __name__ == "__main__":
    try:
        # Log bot startup initialization process
        logger.info("🚀 Starting iQ Lost Quiz Bot...")
        
        # Check if bot token exists
        if not TOKEN:
            logger.error("❌ BOT_TOKEN is required but not found")
            raise ValueError(ERROR_MESSAGES["token_required"])
        
        # Log token loaded with partial display
        logger.info(f"✅ Bot token loaded: {TOKEN[:10]}...{TOKEN[-10:]}")
        
        # Start dummy HTTP server thread
        try:
            threading.Thread(target=start_dummy_server, daemon=True).start()
            logger.info("🌐 HTTP server thread started")
        except Exception as e:
            logger.error(f"❌ Failed to start HTTP server: {str(e)}")

        # Register event handlers with dispatcher
        try:
            dp.startup.register(on_startup)
            dp.shutdown.register(on_shutdown)
            dp.errors.register(global_error_handler)
            logger.info("📋 Event handlers registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register event handlers: {str(e)}")

        # Main async function for bot
        async def main():
            try:
                # Start auto quiz loop task
                logger.info("🤖 Starting auto-quiz loop task...")
                asyncio.create_task(auto_quiz_loop())
                
                # Start bot polling for updates
                logger.info("🔄 Starting bot polling...")
                await dp.start_polling(bot)
                
            except Exception as e:
                # Log critical error in main loop
                logger.error(f"💥 Critical error in main loop: {str(e)}")
                logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
                raise

        # Launch bot main function with asyncio
        logger.info("🎯 Launching bot main function...")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        # Log manual bot stop event
        logger.info("⏹️ Bot stopped by user (Ctrl+C)")
    except Exception as e:
        # Log fatal error starting bot
        logger.error(f"💥 Fatal error starting bot: {str(e)}")
        logger.debug(f"📊 Error traceback: {traceback.format_exc()}")
        raise
    finally:
        # Log bot shutdown completion message
        logger.info("👋 Bot shutdown complete")