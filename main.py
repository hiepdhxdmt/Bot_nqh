import sqlite3
import json
from telegram.ext import Updater, CommandHandler
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

def start(update, context):
    update.message.reply_text("Welcome! Use /signup to register and start earning points.")

def help_command(update, context):
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
    update.message.reply_text(help_text)

def signup(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username
    try:
        cursor.execute("INSERT INTO users (telegram_id, username, points) VALUES (?, ?, 0)", (user_id, username))
        conn.commit()
        update.message.reply_text("Signup successful! Use /post to submit your link.")
    except sqlite3.IntegrityError:
        update.message.reply_text("You're already signed up.")

def info(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT points, vip FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        points, vip = user
        vip_status = "✅ VIP" if vip else "❌ Regular"
        update.message.reply_text(f"Your points: {points}\nStatus: {vip_status}")
    else:
        update.message.reply_text("Please /signup first.")

def post(update, context):
    user_id = update.effective_user.id
    if len(context.args) == 0:
        update.message.reply_text("Please include your post link after /post")
        return
    link = context.args[0]
    cursor.execute("SELECT id, points FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        update.message.reply_text("You must /signup before posting.")
        return
    uid, points = user
    if points < 20:
        update.message.reply_text("Not enough points (need 20).")
        return
    cursor.execute("INSERT INTO posts (user_id, link) VALUES (?, ?)", (uid, link))
    cursor.execute("UPDATE users SET points = points - 20 WHERE id=?", (uid,))
    conn.commit()
    update.message.reply_text("Post submitted successfully. You lost 20 points.")

def my_posts(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT id FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        update.message.reply_text("Please /signup first.")
        return
    uid = user[0]
    cursor.execute("SELECT link, created_at FROM posts WHERE user_id=? ORDER BY created_at DESC", (uid,))
    posts = cursor.fetchall()
    if not posts:
        update.message.reply_text("You have no posts.")
        return
    now = datetime.now()
    response = "📝 Your Posts:\n"
    for link, created in posts:
        created_time = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        age = now - created_time
        status = "🟢" if age < timedelta(hours=12) else "🔴"
        response += f"{status} {link} ({created})\n"
    update.message.reply_text(response)

def all_posts(update, context):
    cursor.execute("SELECT link, created_at FROM posts ORDER BY created_at DESC LIMIT 20")
    posts = cursor.fetchall()
    if not posts:
        update.message.reply_text("No posts found.")
        return
    now = datetime.now()
    response = "📢 All Posts:\n"
    for link, created in posts:
        created_time = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        age = now - created_time
        status = "🟢" if age < timedelta(hours=12) else "🔴"
        response += f"{status} {link} ({created})\n"
    update.message.reply_text(response)

def my_user(update, context):
    username = update.effective_user.username or "No username"
    update.message.reply_text(f"Your username: @{username}")

def vip(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT points, vip FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        update.message.reply_text("Please /signup first.")
        return
    points, vip = user
    if vip:
        update.message.reply_text("You're already a VIP!")
        return
    if points < 10:
        update.message.reply_text("Not enough points to upgrade (need 10).")
        return
    cursor.execute("UPDATE users SET vip = 1, points = points - 10 WHERE telegram_id=?", (user_id,))
    conn.commit()
    update.message.reply_text("You are now a VIP! 🎉")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("signup", signup))
    dp.add_handler(CommandHandler("info", info))
    dp.add_handler(CommandHandler("post", post))
    dp.add_handler(CommandHandler("my_posts", my_posts))
    dp.add_handler(CommandHandler("all_posts", all_posts))
    dp.add_handler(CommandHandler("my_user", my_user))
    dp.add_handler(CommandHandler("vip", vip))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
