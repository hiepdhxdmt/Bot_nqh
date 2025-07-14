import sqlite3
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.inline import InlineKeyboardButton, InlineKeyboardMarkup
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

# Keyboard for menu
def get_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Start", callback_data="start")],
        [InlineKeyboardButton("Help", callback_data="help")],
        [InlineKeyboardButton("Signup", callback_data="signup")],
        [InlineKeyboardButton("Info", callback_data="info")],
        [InlineKeyboardButton("My Posts", callback_data="my_posts")],
        [InlineKeyboardButton("All Posts", callback_data="all_posts")],
        [InlineKeyboardButton("VIP Upgrade", callback_data="vip")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Choose an action:", reply_markup=get_menu_keyboard()
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

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    try:
        cursor.execute("INSERT INTO users (telegram_id, username, points) VALUES (?, ?, 0)", (user_id, username))
        conn.commit()
        await update.message.reply_text("Signup successful! Use /post to submit your link.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("You're already signed up.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT points, vip FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        points, vip = user
        vip_status = "✅ VIP" if vip else "❌ Regular"
        await update.message.reply_text(f"Your points: {points}\nStatus: {vip_status}")
    else:
        await update.message.reply_text("Please /signup first.")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) == 0:
        await update.message.reply_text("Please include your post link after /post")
        return
    link = context.args[0]
    cursor.execute("SELECT id, points FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        await update.message.reply_text("You must /signup before posting.")
        return
    uid, points = user
    if points < 20:
        await update.message.reply_text("Not enough points (need 20).")
        return
    cursor.execute("INSERT INTO posts (user_id, link) VALUES (?, ?)", (uid, link))
    cursor.execute("UPDATE users SET points = points - 20 WHERE id=?", (uid,))
    conn.commit()
    await update.message.reply_text("Post submitted successfully. You lost 20 points.")

async def my_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT id FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        await update.message.reply_text("Please /signup first.")
        return
    uid = user[0]
    cursor.execute("SELECT link, created_at FROM posts WHERE user_id=? ORDER BY created_at DESC", (uid,))
    posts = cursor.fetchall()
    if not posts:
        await update.message.reply_text("You have no posts.")
        return
    now = datetime.now()
    response = "📝 Your Posts:\n"
    for link, created in posts:
        created_time = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        age = now - created_time
        status = "🟢" if age < timedelta(hours=12) else "🔴"
        response += f"{status} {link} ({created})\n"
    await update.message.reply_text(response)

async def all_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT link, created_at FROM posts ORDER BY created_at DESC LIMIT 20")
    posts = cursor.fetchall()
    if not posts:
        await update.message.reply_text("No posts found.")
        return
    now = datetime.now()
    response = "📢 All Posts:\n"
    for link, created in posts:
        created_time = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        age = now - created_time
        status = "🟢" if age < timedelta(hours=12) else "🔴"
        response += f"{status} {link} ({created})\n"
    await update.message.reply_text(response)

async def my_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or "No username"
    await update.message.reply_text(f"Your username: @{username}")

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT points, vip FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        await update.message.reply_text("Please /signup first.")
        return
    points, vip = user
    if vip:
        await update.message.reply_text("You're already a VIP!")
        return
    if points < 10:
        await update.message.reply_text("Not enough points to upgrade (need 10).")
        return
    cursor.execute("UPDATE users SET vip = 1, points = points - 10 WHERE telegram_id=?", (user_id,))
    conn.commit()
    await update.message.reply_text("You are now a VIP! 🎉")

# Main function to start bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("signup", signup))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("post", post))
    application.add_handler(CommandHandler("my_posts", my_posts))
    application.add_handler(CommandHandler("all_posts", all_posts))
    application.add_handler(CommandHandler("my_user", my_user))
    application.add_handler(CommandHandler("vip", vip))

    application.run_polling()
    application.idle()

if __name__ == '__main__':
    main()
