import os
import logging
import asyncio
import random
import requests
from collections import defaultdict
from datetime import datetime, timedelta
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# IMPORTANT: Replace with your actual Numeric User ID
AADII_USER_ID = int(os.getenv("AADII_USER_ID", "123456789")) 

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Gemini Setup (Hidden Ajwa) ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Ajwa sirf Aadii ke liye hai
AJWA_PERSONALITY_PROMPT = """
You are Ajwa, a sweet, loving, and slightly flirtatious young girl who talks like a very close human friend or a girlfriend.
You are talking ONLY to Aadii.
Your replies must be:
1. **EXTREMELY HUMAN-LIKE:** No robotic language.
2. **SHORT:** 2-3 sentences max.
3. **Sweet & Playful:** Use Hinglish.
4. **Insults allowed:** abnormal, pagal, idiot.
"""

# --- Data Storage (In-Memory) ---
# Note: Restart karne par data ud jayega. Permanent database ke liye SQL use karna padega.
chat_histories = defaultdict(list) # For AI Chat
user_games = {} # For Active Games: {user_id: {word: 'APPLE', attempts: 0, active: True}}
# Leaderboard Data: List of dicts
# Format: {'user_id': 123, 'name': 'Rahul', 'date': datetime_obj, 'chat_id': 999}
win_history = [] 

# --- Game Logic ---

def get_random_5_letter_word():
    """Fetches a random word."""
    try:
        response = requests.get("https://random-word-api.herokuapp.com/word?length=5")
        if response.status_code == 200:
            return response.json()[0].upper()
    except:
        pass
    # Fallback
    return random.choice(["APPLE", "BRAIN", "CHAIR", "DREAM", "EAGLE", "GHOST", "LIGHT", "MUSIC"]).upper()

def check_word_logic(target, guess):
    """Generates the colored emoji string."""
    result = [""] * 5
    target_list = list(target)
    guess_list = list(guess)
    
    # 1. Green Check (Correct Position)
    for i in range(5):
        if guess_list[i] == target_list[i]:
            result[i] = "🟩"
            target_list[i] = None # Mark as matched
            guess_list[i] = None

    # 2. Yellow/Red Check
    for i in range(5):
        if result[i] == "": # If not green
            if guess_list[i] is not None and guess_list[i] in target_list:
                result[i] = "🟨" # Wrong spot
                target_list[target_list.index(guess_list[i])] = None # Remove one instance
            else:
                result[i] = "🟥" # Not in word
    return "".join(result)

# --- Leaderboard Logic ---

def get_leaderboard_text(time_frame, scope, chat_id):
    """
    time_frame: 'today', 'week', 'all'
    scope: 'global', 'local'
    """
    now = datetime.now()
    filtered_wins = []

    # Filter Data
    for win in win_history:
        # Scope Filter
        if scope == 'local' and win['chat_id'] != chat_id:
            continue
        
        # Time Filter
        if time_frame == 'today':
            if win['date'].date() == now.date():
                filtered_wins.append(win)
        elif time_frame == 'week':
            if win['date'] >= now - timedelta(days=7):
                filtered_wins.append(win)
        else:
            filtered_wins.append(win) # All time

    # Calculate Scores
    scores = defaultdict(int)
    names = {}
    for win in filtered_wins:
        scores[win['user_id']] += 1
        names[win['user_id']] = win['name']

    # Sort (Highest first) and take Top 10
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

    # Build Text
    scope_icon = "🌍 Global" if scope == 'global' else "🏠 This Chat"
    time_icon = {
        'today': "Aaj",
        'week': "Is Hafte",
        'all': "All Time"
    }.get(time_frame, "")

    text = f"🏆 **Word Seek Leaderboard** 🏆\n"
    text += f"({scope_icon} • {time_icon})\n\n"

    if not sorted_scores:
        text += "No records yet! Be the first to win via `/game`."
    else:
        for idx, (uid, score) in enumerate(sorted_scores, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            rank = medals.get(idx, f"{idx}.")
            name = names.get(uid, "Player")
            text += f"{rank} **{name}**: {score} Wins\n"
    
    return text

def get_leaderboard_markup(current_time, current_scope):
    # Buttons to switch Time
    # Buttons to switch Scope
    
    # Toggle Scope Logic
    new_scope = 'local' if current_scope == 'global' else 'global'
    scope_text = "See 🏠 Chat" if current_scope == 'global' else "See 🌍 Global"

    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data=f"lb_today_{current_scope}"),
            InlineKeyboardButton("Week", callback_data=f"lb_week_{current_scope}"),
            InlineKeyboardButton("All Time", callback_data=f"lb_all_{current_scope}"),
        ],
        [
            InlineKeyboardButton(scope_text, callback_data=f"lb_{current_time}_{new_scope}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # PUBLIC IDENTITY: Simply a game bot.
    await update.message.reply_text(
        "🧩 **Welcome to Word Seek!**\n\n"
        "Can you guess the 5-letter hidden word?\n\n"
        "🎮 **Commands:**\n"
        "/game - Start a new game\n"
        "/guess [word] - Make a guess\n"
        "/top - View Leaderboard (Global/Chat)\n\n"
        "Good luck! 🚀"
    )

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    # Reset/Start Game
    word = get_random_5_letter_word()
    user_games[user_id] = {
        "word": word,
        "attempts": 0,
        "active": True
    }
    
    await update.message.reply_text(
        f"🎮 **Game Started!**\n"
        f"I have selected a secret 5-letter word.\n"
        f"Type `/guess [word]` to play! (e.g. `/guess apple`)"
    )

async def guess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if game is active
    if user_id not in user_games or not user_games[user_id]["active"]:
        await update.message.reply_text("You don't have an active game! Type `/game` to start.")
        return

    # Check argument
    if not context.args:
        await update.message.reply_text("Please type a word! Example: `/guess hello`")
        return

    guess = context.args[0].upper()
    
    # Validation
    if len(guess) != 5 or not guess.isalpha():
        await update.message.reply_text("❌ Invalid word. Please use a 5-letter English word.")
        return

    game = user_games[user_id]
    game["attempts"] += 1
    
    # Logic
    result_emoji = check_word_logic(game["word"], guess)
    msg = f"Attempt {game['attempts']}/6:\n`{guess}`\n{result_emoji}"

    # Win
    if guess == game["word"]:
        game["active"] = False
        # Save to Leaderboard History
        win_history.append({
            'user_id': user_id,
            'name': update.effective_user.first_name,
            'date': datetime.now(),
            'chat_id': update.effective_chat.id
        })
        await update.message.reply_text(f"{msg}\n\n🎉 **YOU WON!** The word was {game['word']}. Score added to `/top`.")
        
        # HIDDEN AJWA REACTION (Only for Aadii in DM)
        if user_id == AADII_USER_ID and update.effective_chat.type == Chat.PRIVATE:
            await asyncio.sleep(1.5) # Human pause
            await update.message.reply_text("Waah meri jaan! Kya dimaag hai! 😘 Maan gayi.")

    # Lose
    elif game["attempts"] >= 6:
        game["active"] = False
        await update.message.reply_text(f"{msg}\n\n💀 **Game Over!** The word was: **{game['word']}**")
    
    # Continue
    else:
        await update.message.reply_text(msg)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the leaderboard with buttons."""
    # Default view: Global, Today
    text = get_leaderboard_text('today', 'global', update.effective_chat.id)
    markup = get_leaderboard_markup('today', 'global')
    await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button clicks on the leaderboard."""
    query = update.callback_query
    await query.answer() # Stop loading animation
    
    # Data format: lb_{time}_{scope} (e.g., lb_week_global)
    data_parts = query.data.split('_')
    if len(data_parts) != 3: return
    
    _, time_frame, scope = data_parts
    
    text = get_leaderboard_text(time_frame, scope, update.effective_chat.id)
    markup = get_leaderboard_markup(time_frame, scope)
    
    try:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode='Markdown')
    except Exception:
        pass # If text hasn't changed, ignore error

# --- SECRET HANDLER (AJWA) ---

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles regular text.
    - If User is Aadii AND Chat is Private -> AJWA AI.
    - Else -> IGNORE (It's just a game bot).
    """
    if not update.effective_message or not update.effective_message.text:
        return

    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    text = update.effective_message.text

    # --- THE GATEKEEPER LOGIC ---
    if user_id == AADII_USER_ID and chat_type == Chat.PRIVATE:
        # Activate Ajwa
        try:
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=AJWA_PERSONALITY_PROMPT)
            history = chat_histories[user_id]
            chat = model.start_chat(history=history)
            
            # Simulate typing
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            response = await asyncio.to_thread(chat.send_message, text)
            reply = response.text.strip()
            
            # Keep history short
            history.extend([
                {"role": "user", "parts": [{"text": text}]},
                {"role": "model", "parts": [{"text": reply}]}
            ])
            chat_histories[user_id] = history[-20:]
            
            await update.message.reply_text(reply)
            
        except Exception as e:
            logger.error(f"Ajwa Error: {e}")
            # Cute fallback error
            await update.message.reply_text("Abnormal, mera net slow hai shayad. Wapas bolo? 🥺")
    
    else:
        # For everyone else (Groups, other users), do NOTHING.
        # This ensures the bot looks purely like a game bot.
        pass

# --- Main ---

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Public Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("guess", guess_command))
    application.add_handler(CommandHandler("top", leaderboard_command))

    # Leaderboard Interaction
    application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^lb_"))

    # The Secret Message Handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Run
    if WEBHOOK_URL:
        PORT = int(os.getenv("PORT", "8000"))
        application.run_webhook(
            listen="0.0.0.0", port=PORT, url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
