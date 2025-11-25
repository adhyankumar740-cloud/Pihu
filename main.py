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
chat_histories = defaultdict(list) 
user_games = {} 

# Score History Format: {'user_id': 123, 'name': 'Rahul', 'points': 5, 'date': datetime, 'chat_id': 999}
# Note: This stores every score event (+5 or -1). Leaderboard sums them up.
score_history = [] 

# --- Game Logic ---

def get_random_5_letter_word():
    try:
        response = requests.get("https://random-word-api.herokuapp.com/word?length=5")
        if response.status_code == 200:
            return response.json()[0].upper()
    except:
        pass
    return random.choice(["APPLE", "BRAIN", "CHAIR", "DREAM", "EAGLE", "GHOST", "LIGHT", "MUSIC"]).upper()

def format_guess_result(target, guess):
    """Creates a beautiful grid interface."""
    target_list = list(target)
    guess_list = list(guess)
    result_emoji = [""] * 5
    
    # Logic for Colors
    # 1. Green
    for i in range(5):
        if guess_list[i] == target_list[i]:
            result_emoji[i] = "🟩"
            target_list[i] = None
            guess_list[i] = None
            
    # 2. Yellow/Red
    for i in range(5):
        if result_emoji[i] == "":
            if guess_list[i] is not None and guess_list[i] in target_list:
                result_emoji[i] = "🟨"
                target_list[target_list.index(guess_list[i])] = None
            else:
                result_emoji[i] = "⬛" # Using Black for incorrect instead of Red for cleaner look
    
    # Formatting into a nice grid
    # e.g.  A  P  P  L  E
    #       🟩 ⬛ 🟨 ⬛ 🟥
    
    letter_row = "  ".join([f"` {l} `" for l in guess])
    emoji_row = " ".join(result_emoji)
    
    return f"{letter_row}\n{emoji_row}"

# --- Leaderboard Logic (English) ---

def get_leaderboard_text(time_frame, scope, chat_id):
    now = datetime.now()
    user_totals = defaultdict(int)
    user_names = {}

    # Aggregate Scores
    for entry in score_history:
        # Scope Filter
        if scope == 'local' and entry['chat_id'] != chat_id:
            continue
        
        # Time Filter
        include = False
        if time_frame == 'today':
            if entry['date'].date() == now.date(): include = True
        elif time_frame == 'week':
            if entry['date'] >= now - timedelta(days=7): include = True
        else:
            include = True
            
        if include:
            user_totals[entry['user_id']] += entry['points']
            user_names[entry['user_id']] = entry['name']

    # Sort
    sorted_scores = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    # Build Text (Pure English)
    scope_txt = "🌍 Global" if scope == 'global' else "🏠 This Chat"
    time_txt = {
        'today': "Today",
        'week': "This Week",
        'all': "All Time"
    }.get(time_frame, "")

    text = f"🏆 **WORD SEEK LEADERBOARD** 🏆\n"
    text += f"({scope_txt} • {time_txt})\n\n"

    if not sorted_scores:
        text += "No scores yet. Start playing with `/game`!"
    else:
        for idx, (uid, score) in enumerate(sorted_scores, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            rank = medals.get(idx, f"{idx}.")
            name = user_names.get(uid, "Player")
            text += f"{rank} **{name}**: {score} pts\n"
    
    return text

def get_leaderboard_markup(current_time, current_scope):
    new_scope = 'local' if current_scope == 'global' else 'global'
    scope_text = "View 🏠 Local" if current_scope == 'global' else "View 🌍 Global"

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
    await update.message.reply_text(
        "👋 **Welcome to Word Seek!**\n\n"
        "Can you guess the hidden 5-letter word?\n\n"
        "🎮 **How to Play:**\n"
        "1. Type `/game` to start.\n"
        "2. Just type any **5-letter word** in chat to guess.\n"
        "   (No need for /guess command!)\n\n"
        "📈 **Scoring:**\n"
        "✅ Correct Word: **+5 Points**\n"
        "❌ Wrong Guess: **-1 Point**\n\n"
        "🏆 Check rank: `/leaderboard`"
    )

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if already playing
    if user_id in user_games and user_games[user_id]["active"]:
        await update.message.reply_text("⚠️ You already have an active game! Just type a 5-letter word.")
        return

    word = get_random_5_letter_word()
    user_games[user_id] = {
        "word": word,
        "attempts": 0,
        "active": True
    }
    
    await update.message.reply_text(
        f"🎮 **Game Started!**\n"
        f"I have picked a secret 5-letter word.\n\n"
        f"👉 **Just type your guess here.**\n"
        f"(Unlimited attempts. +5 for win, -1 for fail)"
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the game manually."""
    user_id = update.effective_user.id
    if user_id in user_games and user_games[user_id]["active"]:
        word = user_games[user_id]["word"]
        del user_games[user_id]
        await update.message.reply_text(f"🛑 Game stopped. The word was: **{word}**")
    else:
        await update.message.reply_text("You are not playing any game.")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = get_leaderboard_text('today', 'global', update.effective_chat.id)
    markup = get_leaderboard_markup('today', 'global')
    await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    if len(data_parts) != 3: return
    
    _, time_frame, scope = data_parts
    
    text = get_leaderboard_text(time_frame, scope, update.effective_chat.id)
    markup = get_leaderboard_markup(time_frame, scope)
    
    try:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode='Markdown')
    except:
        pass

# --- MAIN MESSAGE PROCESSOR (The Brain) ---

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.text:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    text = update.effective_message.text.strip().upper()

    # --- 1. GAME LOGIC (Priority) ---
    # If user has an active game AND sends a valid 5-letter word
    is_game_active = user_id in user_games and user_games[user_id]["active"]
    
    if is_game_active and len(text) == 5 and text.isalpha():
        game = user_games[user_id]
        game["attempts"] += 1
        
        # Grid Display
        grid = format_guess_result(game["word"], text)
        
        # WIN
        if text == game["word"]:
            del user_games[user_id] # End game
            
            # Add +5 Points
            score_history.append({
                'user_id': user_id,
                'name': update.effective_user.first_name,
                'points': 5,
                'date': datetime.now(),
                'chat_id': chat_id
            })
            
            await update.message.reply_text(
                f"🎉 **VICTORY!**\n\n"
                f"{grid}\n\n"
                f"✅ **Solved in {game['attempts']} attempts.**\n"
                f"🏆 **Points:** +5 added!"
            )
            
            # Ajwa Secret Celebration
            if user_id == AADII_USER_ID and chat_type == Chat.PRIVATE:
                await asyncio.sleep(1)
                await update.message.reply_text("Wow! You are smart! 😘")
                
        # INCORRECT
        else:
            # Deduct -1 Point
            score_history.append({
                'user_id': user_id,
                'name': update.effective_user.first_name,
                'points': -1,
                'date': datetime.now(),
                'chat_id': chat_id
            })
            
            await update.message.reply_text(
                f"Attempt {game['attempts']}:\n"
                f"{grid}\n"
                f"❌ **Incorrect** (-1 Point). Try again!"
            )
        return # Stop here, don't trigger AI

    # --- 2. AJWA LOGIC (Secret) ---
    # Runs ONLY if: No valid game move was made AND It's Aadii in DM
    if user_id == AADII_USER_ID and chat_type == Chat.PRIVATE:
        # If Aadii is typing non-5-letter words, or just chatting
        try:
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=AJWA_PERSONALITY_PROMPT)
            history = chat_histories[user_id]
            chat = model.start_chat(history=history)
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            response = await asyncio.to_thread(chat.send_message, update.effective_message.text)
            reply = response.text.strip()
            
            history.extend([
                {"role": "user", "parts": [{"text": update.effective_message.text}]},
                {"role": "model", "parts": [{"text": reply}]}
            ])
            chat_histories[user_id] = history[-20:]
            
            await update.message.reply_text(reply)
            
        except Exception as e:
            logger.error(f"Ajwa Error: {e}")
            await update.message.reply_text("Something went wrong with connection.")

# --- Main ---

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command)) # Renamed

    # Buttons
    application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^lb_"))

    # Message Handler (Auto-Guess + Ajwa)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

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
