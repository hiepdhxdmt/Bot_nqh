import sqlite3
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  # Import đúng từ telegram
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta

# Load config
with open("config.json", "r") as f:
    config = json.load(f)
TOKEN = config["bot_token"]

# Connect to database
conn = sqlite3.connect("database.sqlite", check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    points INTEGER DEFAULT 0,
    vip INTEGER DEFAULT 0
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    link TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

# Create a menu with commands for the user
def get_commands_keyboard():
    keyboard = [
        [InlineKeyboardButton("/start", callback_data="start")],
        [InlineKeyboardButton("/help", callback_data="help")],
        [InlineKeyboardButton("/signup", callback_data="signup")],
        [InlineKeyboardButton("/info", callback_data="info")],
        [InlineKeyboardButton("/my_posts", callback_data="my_posts")],
        [InlineKeyboardButton("/all_posts", callback_data="all_posts")],
        [InlineKeyboardButton("/post", callback_data="post")],
        [InlineKeyboardButton("/vip", callback_data="vip")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Choose an action:", reply_markup=get_commands_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Bot Commands:\n\n"
        "Basic:\n"
        "/start - Begin using the bot\n"
        "/help - Show this guide\n"
        "/my_user - View your Telegram username\n"
        "/signup - Register a new account\n"
        "/logout - (Coming soon)\n\n"
        "Member:\n"
        "/info - View your account info\n"
        "/my_posts - View your posts (🟢 <12h, 🔴 >12h)\n"
        "/all_posts - View all submitted posts\n"
        "/post <link> - Submit a new post (-20 points)\n"
        "/vip - Upgrade to VIP (-10 points)\n\n"
        "Point System:\n"
        "Add post = -20 pts\nReply = +5 pts\nVIP upgrade = -10 pts"
    )
    await update.message.reply_text(help_text)

# Callback for handling the selection of commands via keyboard
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'start':
        await query.edit_message_text("Starting the bot...")
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'signup':
        await query.edit_message_text("Please use /signup to register.")
    elif query.data == 'info':
        await query.edit_message_text("Your account info is...")
    elif query.data == 'my_posts':
        await query.edit_message_text("Your posts...")
    elif query.data == 'all_posts':
        await query.edit_message_text("All posts...")
    elif query.data == 'post':
        await query.edit_message_text("Use /post to submit a link.")
    elif query.data == 'vip':
        await query.edit_message_text("Use /vip to upgrade to VIP.")

# Main function to start bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))  # Handle button presses

    application.run_polling()
    application.idle()

if __name__ == '__main__':
    main()
