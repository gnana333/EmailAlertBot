from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import sqlite3

TOKEN = "8104815167:AAE5mXfgJzeNIsx0wVRO9RqMlWKnajk8wRQ"  # Use your valid Telegram bot token

# Initialize SQLite database
conn = sqlite3.connect('user_preferences.db', check_same_thread=False)
c = conn.cursor()

# Ensure the keywords column exists in the user_credentials table
c.execute("PRAGMA table_info(user_credentials)")
columns = c.fetchall()
if 'keywords' not in [column[1] for column in columns]:
    c.execute("ALTER TABLE user_credentials ADD COLUMN keywords TEXT")
    conn.commit()

# Create the table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS user_credentials
             (user_id INTEGER PRIMARY KEY, email TEXT, app_password TEXT, keywords TEXT)''')
conn.commit()

# Dictionary to store user states (email, app password, or keyword input)
user_states = {}

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = "awaiting_email"  # Set state to awaiting email
    await update.message.reply_text(
        "I am an Email Alert Bot. I will forward your emails to you here.\n\n"
        "If you want to get the emails, please provide me with your email first."
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text

    if user_id not in user_states:
        await update.message.reply_text("Please start the bot using the /start command.")
        return

    if user_states[user_id] == "awaiting_email":
        # Validate email format (basic check)
        if "@" in user_input and "." in user_input:
            # Store the email in the database
            c.execute("INSERT OR REPLACE INTO user_credentials (user_id, email) VALUES (?, ?)", (user_id, user_input))
            conn.commit()

            # Update state to awaiting app password
            user_states[user_id] = "awaiting_app_password"
            await update.message.reply_text("Thank you! Now, please provide your app password.")
        else:
            await update.message.reply_text("Please provide a valid email address.")

    elif user_states[user_id] == "awaiting_app_password":
        # Store the app password in the database
        c.execute("UPDATE user_credentials SET app_password = ? WHERE user_id = ?", (user_input, user_id))
        conn.commit()

        # Ask if the user wants to set keywords
        user_states[user_id] = "awaiting_keyword_choice"
        reply_keyboard = [["Yes Set keywords", "No, Forward all emails"]]
        await update.message.reply_text(
            "Do you want to set keywords?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )

    elif user_states[user_id] == "awaiting_keyword_choice":
        if user_input == "Yes Set keywords":
            user_states[user_id] = "awaiting_keywords"
            await update.message.reply_text("Please provide the keywords separated by commas.")
        elif user_input == "No, Forward all emails":
            c.execute("UPDATE user_credentials SET keywords = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            del user_states[user_id]
            await update.message.reply_text("Thank you! I will forward all emails to you.")
        else:
            await update.message.reply_text("Please choose one of the options.")

    elif user_states[user_id] == "awaiting_keywords":
        # Store the keywords in the database
        c.execute("UPDATE user_credentials SET keywords = ? WHERE user_id = ?", (user_input, user_id))
        conn.commit()

        # Clear the user state
        del user_states[user_id]

        await update.message.reply_text("Thank you! Your keywords have been saved. I will now forward emails matching these keywords.")

def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()