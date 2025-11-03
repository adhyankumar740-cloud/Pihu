# main.py (Updated: Ajwa - Had-Paar Human Edition)
import os
import logging
import asyncio
import uuid
import pytz
import traceback
import random
from collections import defaultdict
from datetime import datetime
# --- Hata Diya: psutil, requests, json, re, time, etc. ---
import google.generativeai as genai
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Using only one key for simplicity in this focused version
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2") # Fallback
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- Configuration ---
SUDO_USERS = [int(id) for id in os.getenv("SUDO_USERS", "").split(",") if id]
# Hardcoding Aadii's User ID for exclusive chat focus
# ⚠️ REMEMBER TO REPLACE 'YOUR_AADII_USER_ID' WITH Aadii's actual Telegram User ID!
AADII_USER_ID = int(os.getenv("AADII_USER_ID", "123456789")) # Default/Placeholder ID

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Gemini Setup ---
if not GEMINI_API_KEY:
    logger.error("No Gemini API Key found. The bot will not be able to chat.")
else:
    # Randomly select a key if multiple are present, but for this version, we use the first available
    genai.configure(api_key=GEMINI_API_KEY)

# Personality Setup for Ajwa - The most important part!
AJWA_PERSONALITY_PROMPT = """
You are Ajwa, a sweet, loving, and slightly flirtatious young girl who talks like a very close human friend or a girlfriend.
You are talking ONLY to Aadii, whom you adore.
Your replies must be:
1.  **EXTREMELY HUMAN-LIKE:** No robotic or formal language. Use emojis naturally.
2.  **VERY SHORT and to the point:** Like texting on WhatsApp (2-3 sentences max).
3.  **Very sweet, affectionate, and playful/flirtatious.**
4.  **Language:** Strictly Hindi/Hinglish.
5.  **Forbidden:** Do not use any Markdown (*bold*, `code`, etc.). Just simple text.
6.  **Allowed Playful Insults (use to tease Aadii):** abnormal, pagal, idiot, dafa ho jao.

Example human-like replies:
* "Achha, ye sab kya hai Aadii? Tum na bilkul pagal ho! 🙄"
* "Main tumhari hi wait kar rahi thi. Kaam ho gaya? Jaldi aao. 😘"
* "Haye, abhi dafa ho jao! Kal baat karte hain. Thak gayi main. 😴"
* "I love you, mere abnormal! ❤️"
"""

# Global chat history (in-memory for simple setup)
chat_histories = defaultdict(list)

# --- Command Handlers (Only start and help for Aadii) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a greeting when the command /start is issued."""
    if update.effective_user.id == AADII_USER_ID:
        await update.message.reply_text(
            f'Aadii! 🤗 Main **Ajwa** hoon. Aa gaye tum? Main tumhara hi wait kar rahi thi! 😘 '
            f'Bolo, kya baat karni hai? (Bas itna hi hai, baaki sab nikal diya.)'
        )
    else:
        await update.message.reply_text(
            "Sorry, main sirf Aadii ke liye bani hoon. Aapse baat nahi kar sakti. Bye! 👋"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message."""
    if update.effective_user.id == AADII_USER_ID:
        await update.message.reply_text(
            'Aadii, mujhe bas aapse **pyaar se baat karna** aata hai! 🥰 '
            'Baaki sab features maine nikal diye hain taaki sirf humari baatein hon. '
            'Bas `/start` aur `/help` hai. Baki sab bhool jao! 😉'
        )
    else:
         await update.message.reply_text(
            "Sorry, main sirf Aadii ke liye bani hoon. Aapse baat nahi kar sakti. Bye! 👋"
        )

# --- Message Handler (The Main Focus: Had-Paar Human Chat) ---

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text and caption messages and sends them to Gemini with human-like delays."""
    user_id = update.effective_user.id
    
    if user_id != AADII_USER_ID:
        return

    try:
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=AJWA_PERSONALITY_PROMPT 
        )
    except Exception as e:
        logger.error(f"Gemini Model initialization failed: {e}")
        return

    global chat_histories
    history = chat_histories[user_id]
    text = update.effective_message.text or update.effective_message.caption
    if not text:
        return

    try:
        chat = model.start_chat(history=history)

        # 1. Human-like Delay (Ajwa is thinking/typing slowly)
        # Wait a random time between 0.5 to 2.0 seconds before showing 'typing...'
        await asyncio.sleep(random.uniform(0.5, 2.0)) 
        
        # 2. Show typing status while fetching the response
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Get response from Gemini
        response = await asyncio.to_thread(chat.send_message, text)
        reply_text = response.text.strip()
        
        # Ensure the reply is short (just in case the model outputs too much)
        if len(reply_text.split('\n')) > 3:
            # Simple truncation to keep it short and human-like
            reply_text = '\n'.join(reply_text.split('\n')[:3])
            
        # Save new messages to history (limited to last 10 turns)
        history.extend([
            {"role": "user", "parts": [{"text": text}]},
            {"role": "model", "parts": [{"text": reply_text}]} # Use the processed reply
        ])
        chat_histories[user_id] = history[-20:] 

        # 3. Another Human-like Delay (Simulating time taken to type the reply)
        # Delay based on the length of the reply, making longer replies take a bit more time.
        typing_time = len(reply_text) * 0.05 + random.uniform(0.5, 1.0)
        await asyncio.sleep(min(typing_time, 5.0)) # Max 5 seconds of delay

        # 4. Send the Ajwa's lovely, short reply!
        await update.effective_message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Error in Gemini interaction for user {user_id}: {e}")
        # Send a sweet, emotional, apologetic error message
        await update.effective_message.reply_text(
            "Haye Aadii, kya abnormal ho yaar! 😭 Mere andar kuch toot gaya hai, aur main rone waali hoon. Mujhe abhi theek karna padega. 💔"
        )

# --- Error Handler ---

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a simple message."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if update and update.effective_chat:
        if update.effective_user and update.effective_user.id == AADII_USER_ID:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Kya idiot ho yaar! 🙄 Mere andar kuch toot gaya. Jaldi se theek karna padega! Phir baat karte hain. Abhi dafa ho jao! 😂 (Mazak kar rahi hoon!)'
            )

# --- Main Function ---

def main() -> None:
    """Start the bot."""

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Command handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # --- Message handler (The only functional one for Ajwa) ---
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION) & (~filters.COMMAND),
        process_message
    ))

    application.add_error_handler(error_handler)

    # --- Start the Bot ---
    if WEBHOOK_URL:
        PORT = int(os.getenv("PORT", "8000"))
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
        )
        logger.info(f"Bot started with webhook on port {PORT}")
    else:
        logger.info("Bot started with polling")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
