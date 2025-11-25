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
score_history = [] 

# --- Game Logic ---

def get_random_5_letter_word():
    """Fetches a random word."""
    try:
        response = requests.get("https://random-word-api.herokuapp.com/word?length=5")
        if response.status_code == 200:
            return response.json()[0].upper()
    except:
        pass
    return random.choice(["APPLE", "BRAIN", "CHAIR", "DREAM", "EAGLE", "GHOST", "LIGHT", "MUSIC"]).upper()

def format_guess_result(target, guess):
    """
    Generates the premium colored emoji string (🟩, 🟨, 🟥).
    """
    target_list = list(target)
    guess_list = list(guess)
    result_emoji = [""] * 5
    
    # 1. Green Check (Correct Position)
    for i in range(5):
        if guess_list[i] == target_list[i]:
            result_emoji[i] = "🟩"
            target_list[i] = None 
            guess_list[i] = None
            
    # 2. Yellow/Red Check
    for i in range(5):
        if result_emoji[i] == "":
            if guess_list[i] is not None and guess_list[i] in target_list:
                result_emoji[i] = "🟨"
                target_list[target_list.index(guess_list[i])] = None
            else:
                result_emoji[i] = "🟥" # Red Square for incorrect letter (Premium Look)
    
    return "".join(result_emoji)

# --- Leaderboard Logic (English) ---
def get_leaderboard_text(time_frame, scope, chat_id):
    now = datetime.now()
    user_totals = defaultdict(int)
    user_names = {}

    # Aggregate Scores
    for entry in score_history:
        if scope == 'local' and entry['chat_id'] != chat_id:
            continue
        
        include = False
        if time_frame == 'today':
            include = entry['date'].date() == now.date()
        elif time_frame == 'week':
            include = entry['date'] >= now - timedelta(days=7)
        else:
            include = True
            
        if include:
            user_totals[entry['user_id']] += entry['points']
            user_names[entry['user_id']] = entry['name']

    # Sort Top 10
    sorted_scores = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    # Header Text
    scope_txt = "🌍 Global" if scope == 'global' else "🏠 This Chat"
    time_labels = {'today': "📅 Today", 'week': "📆 This Week", 'all': "⏳ All Time"}
    time_txt = time_labels.get(time_frame, "")

    text = (
        "🏆 **WORD SEEK — LEADERBOARD** 🏆\n"
        f"{scope_txt} • {time_txt}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Empty State
    if not sorted_scores:
        text += "No players yet.\nStart playing with **/game**! 🎮"
        return text
    
    # Ranks
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for idx, (uid, score) in enumerate(sorted_scores, 1):
        icon = medals.get(idx, f"{idx}.")
        name = user_names.get(uid, "Player")
        text += f"{icon} **{name}** — {score} pts\n"

    return text
def get_leaderboard_markup(current_time, current_scope):
    new_scope = 'local' if current_scope == 'global' else 'global'
    scope_switch_txt = "🏠 Local" if current_scope == 'global' else "🌍 Global"

    keyboard = [
        [
            InlineKeyboardButton("📅 Today", callback_data=f"lb_today_{current_scope}"),
            InlineKeyboardButton("📆 Week", callback_data=f"lb_week_{current_scope}"),
            InlineKeyboardButton("⏳ All Time", callback_data=f"lb_all_{current_scope}"),
        ],
        [
            InlineKeyboardButton(f"Switch to {scope_switch_txt}", callback_data=f"lb_{current_time}_{new_scope}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


    
# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Replace PHOTO_ID_HERE with your Telegram file_id
    await update.message.reply_photo(
        photo="AgACAgUAAxkBAAI-RGkllZajU0MtaSv1NVp84YhJl8JuAAIGDWsbLhEoVfXhwnFaElgWAQADAgADeAADNgQ",
        caption=(
            "✨ **Welcome to Word Seek!** ✨\n\n"
            "🧩 **Guess the Secret 5-Letter Word** and climb the leaderboard!\n\n"
            "🎮 **How to Play**\n"
            "• Type `/game` to begin your challenge.\n"
            "• Send ANY **5-letter word** as your guess — no command needed.\n\n"
            "📊 **Scoring System**\n"
            "• 🟢 Correct Word: **+5 Points**\n"
            "• 🔴 Wrong Guess: **−1 Point**\n\n"
            "🏆 **See your ranking:** `/leaderboard`\n\n"
            "Ready to test your vocabulary? Let’s go! 🚀"
        )
    )


async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id in user_games and user_games[user_id]["active"]:
        await update.message.reply_text("⚠️ You already have an active game! Just type a 5-letter word.")
        return

    word = get_random_5_letter_word()
    user_games[user_id] = {
        "word": word,
        "attempts": 0,
        "active": True,
        "history": [] # Stores previous (guess_word, emoji_result) for premium display
    }
    
    await update.message.reply_text(
        f"🎮 **Game Started!**\n"
        f"I have picked a secret 5-letter word.\n\n"
        f"👉 **Just type your 5-letter guess here.**\n"
        f"(Unlimited attempts. +5 for win, -1 for fail)"
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    # --- 1. GAME LOGIC ---
    is_game_active = user_id in user_games and user_games[user_id]["active"]
    
    if is_game_active and len(text) == 5 and text.isalpha():
        game = user_games[user_id]
        game["attempts"] += 1
        
        # Get Premium Emoji String
        result_emoji = format_guess_result(game["word"], text)
        
        # Store for display history
        game["history"].append((text, result_emoji)) 
        
        # --- Generate PREMIUM Display ---
        current_score = sum(e['points'] for e in score_history if e['user_id'] == user_id)
        
        display_message = "🧩 **WORD SEEK GAME**\n\n"
        
        # Stacked Guess History
        for guessed_word, emoji_res in game["history"]:
            # Use fixed width for neat letter display
            letter_display = " ".join(list(guessed_word))
            
            # Premium format: Emoji blocks first, then the word in fixed-width font
            display_message += f"{emoji_res}  `{letter_display}`\n"
        
        display_message += "\n"
        display_message += f"Attempts: **{game['attempts']}** | Score: **{current_score} pts**\n"
        
        # WIN
        if text == game["word"]:
            del user_games[user_id]
            
            # Add +5 Points
            score_history.append({
                'user_id': user_id, 'name': update.effective_user.first_name, 
                'points': 5, 'date': datetime.now(), 'chat_id': chat_id
            })
            
            await update.message.reply_text(
                f"🎉 **VICTORY!**\n\n"
                f"{display_message}\n"
                f"✅ **Solved in {game['attempts']} attempts.**\n"
                f"🏆 **Points:** +5 added! Check `/leaderboard`"
            )
            
            # Ajwa Secret Celebration
            if user_id == AADII_USER_ID and chat_type == Chat.PRIVATE:
                await asyncio.sleep(1)
                await update.message.reply_text("Waah mere genius Aadii! Tum toh sabse best ho! 😘")
                
        # INCORRECT
        else:
            # Deduct -1 Point
            score_history.append({
                'user_id': user_id, 'name': update.effective_user.first_name, 
                'points': -1, 'date': datetime.now(), 'chat_id': chat_id
            })
            
            await update.message.reply_text(display_message, parse_mode='Markdown')
        return 

    # --- 2. AJWA LOGIC (Secret) ---
    if user_id == AADII_USER_ID and chat_type == Chat.PRIVATE:
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
            await update.message.reply_text("Abnormal, mera net slow hai shayad. Wapas bolo? 🥺")

# --- Main ---

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command)) 

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
