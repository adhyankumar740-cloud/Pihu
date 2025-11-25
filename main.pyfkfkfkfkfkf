import os
import logging
import asyncio
import random
import requests
from collections import defaultdict
from datetime import datetime, timedelta
# import psycopg2 # <-- Uncomment this after installation: pip install psycopg2-binary
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
DATABASE_URL = os.getenv("DATABASE_URL")

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

# --- Data Storage ---
chat_histories = defaultdict(list) 
user_games = {} 

# --- TEMPORARY IN-MEMORY FALLBACK for Leaderboard/Broadcast until SQL is implemented ---
if 'score_history_for_db_fallback' not in user_games:
    user_games['score_history_for_db_fallback'] = []
# --------------------------------------------------------------------------------------


# --- DATABASE INTERFACE (POSTGRESQL - NEON TECH) ---

def db_init():
    """Initializes DB connection and ensures necessary tables exist."""
    logger.info("Database initialization structure called. Connect to DB here.")
    # Implement actual DB connection and table creation here.
    pass

def db_add_score(user_id, name, points, chat_id):
    """Adds a score entry to the database."""
    # Implement actual SQL INSERT here.
    # TEMPORARY FALLBACK:
    pass

def db_get_leaderboard(time_filter, scope, chat_id):
    """Fetches and aggregates leaderboard data from the database."""
    # TEMPORARY IN-MEMORY FALLBACK 
    now = datetime.now()
    score_history_temp = user_games['score_history_for_db_fallback'] 
    user_totals = defaultdict(int)
    user_names = {}
    
    for entry in score_history_temp:
        if scope == 'local' and entry['chat_id'] != chat_id: continue
        include = False
        if time_filter == 'today': include = entry['date'].date() == now.date()
        elif time_filter == 'week': include = entry['date'] >= now - timedelta(days=7)
        else: include = True
        
        if include:
            user_totals[entry['user_id']] += entry['points']
            user_names[entry['user_id']] = entry['name']
            
    sorted_scores = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    return sorted_scores, user_names
    
def db_add_chat_id(chat_id, chat_title):
    """Adds or updates chat ID for broadcasting."""
    # Implement actual SQL INSERT/UPDATE here.
    pass

def db_get_all_chat_ids():
    """Returns a list of all chat IDs for broadcasting."""
    # TEMPORARY FALLBACK
    return list(set(e.get('chat_id') for e in user_games['score_history_for_db_fallback']))

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
    Generates the colored emoji string (🟩, 🟨, 🟥).
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
                result_emoji[i] = "🟥" 
    
    return "".join(result_emoji)

# --- Leaderboard Logic (English) ---

def get_leaderboard_text(time_frame, scope, chat_id):
    # Fetch data using DB structure (uses temporary fallback)
    sorted_scores, user_names = db_get_leaderboard(time_frame, scope, chat_id)

    scope_txt = "🌍 Global" if scope == 'global' else "🏠 This Chat"
    time_labels = {'today': "📅 Today", 'week': "📆 This Week", 'all': "⏳ All Time"}
    time_txt = time_labels.get(time_frame, "")

    text = (
        "🏆 **WORD SEEK — LEADERBOARD** 🏆\n"
        f"{scope_txt} • {time_txt}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if not sorted_scores:
        text += "No scores yet. Start playing with **/game**! 🎮"
        return text
    
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
    # Add chat ID to DB for broadcast
    if update.effective_chat.type != Chat.PRIVATE:
        db_add_chat_id(update.effective_chat.id, update.effective_chat.title)
        
    await update.message.reply_text(
        (
            "✨ **Welcome to Word Seek!** ✨\n\n"
            "🧩 **Guess the Secret 5-Letter Word** and climb the leaderboard!\n\n"
            "🎮 **How to Play**\n"
            "• Type `/game` to begin your challenge.\n"
            "• Send ANY **5-letter word** as your guess — no command needed.\n"
            "• To get a file's ID, reply to the media with `/getfileid`.\n\n"
            "📊 **Scoring System**\n"
            "• 🟢 Correct Word: **+5 Points**\n"
            "• 🔴 Wrong Guess: **−1 Point**\n\n"
            "🏆 **See your ranking:** `/leaderboard`\n\n"
            "Ready to test your vocabulary? Let’s go! 🚀"
        ),
        parse_mode='Markdown'
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
        "history": [] 
    }
    
    # Premium /game start interface
    await update.message.reply_text(
        "--- **WORD SEEK CHALLENGE** ---\n"
        "🎯 **Target:** A 5-letter English word.\n"
        "⏱️ **Attempts:** Unlimited.\n\n"
        "**[ G O G O G ]**\n"
        "**[ L U C K ! ]**\n\n"
        "Type your first 5-letter word below to begin the hunt!",
        parse_mode='Markdown'
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

async def get_file_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gets the file_id for a replied-to message containing media."""
    message = update.effective_message
    target_message = message.reply_to_message

    if not target_message:
        await message.reply_text(
            "❌ **Error:** Please reply to the media (Photo, Video, Document, etc.) "
            "you want the File ID for, and then use the `/getfileid` command.",
            parse_mode='Markdown'
        )
        return

    file_id = None
    file_type = "File"

    if target_message.photo:
        file_id = target_message.photo[-1].file_id
        file_type = "Photo"
    elif target_message.document:
        file_id = target_message.document.file_id
        file_type = "Document"
    elif target_message.video:
        file_id = target_message.video.file_id
        file_type = "Video"
    elif target_message.audio:
        file_id = target_message.audio.file_id
        file_type = "Audio"
    elif target_message.sticker:
        file_id = target_message.sticker.file_id
        file_type = "Sticker"
    elif target_message.voice:
        file_id = target_message.voice.file_id
        file_type = "Voice"

    if file_id:
        await message.reply_text(
            f"✅ **{file_type} File ID:**\n\n`{file_id}`\n\n"
            "You can use this ID in your code for sending media.",
            parse_mode='Markdown'
        )
    else:
        await message.reply_text(
            f"❌ **Error:** No recognized media found in the replied message. (Found: {target_message.content_type})",
            parse_mode='Markdown'
        )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message to all recorded chats (Owner only)."""
    if update.effective_user.id != AADII_USER_ID:
        await update.message.reply_text("⛔️ **Access Denied:** Only the bot owner can use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/broadcast Your message text here`")
        return

    message_to_send = " ".join(context.args)
    chat_ids = db_get_all_chat_ids()
    
    success_count = 0
    
    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📣 **BROADCAST:**\n{message_to_send}", parse_mode='Markdown')
            success_count += 1
        except Exception as e:
            logger.error(f"Broadcast failed for chat {chat_id}: {e}")
            
    await update.message.reply_text(f"✅ **Broadcast Complete!** Sent message to {success_count} chats.")


# --- MAIN MESSAGE PROCESSOR (The Brain) ---

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.text:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    text = update.effective_message.text.strip().upper()

    # --- 1. GAME LOGIC (Runs in ALL chats) ---
    is_game_active = user_id in user_games and user_games[user_id]["active"]
    
    if is_game_active and len(text) == 5 and text.isalpha():
        game = user_games[user_id]
        game["attempts"] += 1
        
        result_emoji = format_guess_result(game["word"], text)
        game["history"].append((text, result_emoji)) 
        
        # --- Generate PREMIUM Display ---
        # Fetch current score (using temporary fallback)
        current_total_score = sum(e['points'] for e in user_games['score_history_for_db_fallback'] if e['user_id'] == user_id)
        
        display_message = "🧩 **WORD SEEK CHALLENGE**\n"
        display_message += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Stacked Guess History (NEW SIDE-BY-SIDE FORMAT)
        for guessed_word, emoji_res in game["history"]:
            # Word is bolded. Emojis are separated. Single newline to reduce gap.
            blocks_display = " ".join(list(emoji_res))
            
            # Format: **WORD** 🟩 🟨 🟥 🟩 🟨\n
            display_message += f"**{guessed_word}** {blocks_display}\n"
        
        display_message += "\n" # Add one separator line before the footer
        
        # Calculate new score after this attempt
        score_change = 5 if text == game["word"] else -1
        
        display_message += f"Attempts: **{game['attempts']}** | Score: **{current_total_score + score_change} pts**\n"
        
        # WIN
        if text == game["word"]:
            del user_games[user_id]
            
            # Add score (using temporary fallback and calling DB structure)
            new_score_entry = {
                'user_id': user_id, 'name': update.effective_user.first_name, 
                'points': 5, 'date': datetime.now(), 'chat_id': chat_id
            }
            user_games['score_history_for_db_fallback'].append(new_score_entry)
            db_add_score(new_score_entry['user_id'], new_score_entry['name'], new_score_entry['points'], new_score_entry['chat_id'])
            
            await update.message.reply_text(
                f"🎉 **VICTORY! YOU CRACKED IT!** 🎉\n\n"
                f"{display_message}\n"
                f"✅ **Solved in {game['attempts']} attempts.**\n"
                f"🏆 **Reward:** +5 Points added! Check your rank: `/leaderboard`"
            )
            
            # Ajwa Secret Celebration (DM/Owner only check)
            if user_id == AADII_USER_ID and chat_type == Chat.PRIVATE:
                await asyncio.sleep(1)
                await update.message.reply_text("Waah mere genius Aadii! Tum toh sabse best ho! 😘")
                
        # INCORRECT
        else:
            # Deduct score (using temporary fallback and calling DB structure)
            new_score_entry = {
                'user_id': user_id, 'name': update.effective_user.first_name, 
                'points': -1, 'date': datetime.now(), 'chat_id': chat_id
            }
            user_games['score_history_for_db_fallback'].append(new_score_entry)
            db_add_score(new_score_entry['user_id'], new_score_entry['name'], new_score_entry['points'], new_score_entry['chat_id'])
            
            await update.message.reply_text(display_message, parse_mode='Markdown')
        return 

    # --- 2. AJWA LOGIC (Secret - ONLY Aadii's DM) ---
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
    db_init()
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command)) 
    application.add_handler(CommandHandler("getfileid", get_file_id_command)) 
    application.add_handler(CommandHandler("broadcast", broadcast_command)) 

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
