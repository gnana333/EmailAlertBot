from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import sqlite3

TOKEN = "8104815167:AAE5mXfgJzeNIsx0wVRO9RqMlWKnajk8wRQ"  # Use your valid Telegram bot token

# Initialize SQLite database
conn = sqlite3.connect('user_preferences.db', check_same_thread=False)
c = conn.cursor()

# Drop the existing table if it exists
c.execute("DROP TABLE IF EXISTS user_credentials")
conn.commit()

# Recreate the table with the updated schema
c.execute('''CREATE TABLE IF NOT EXISTS user_credentials
             (user_id INTEGER PRIMARY KEY, email1 TEXT, app_password1 TEXT, email2 TEXT, app_password2 TEXT, keywords TEXT)''')
conn.commit()

# Dictionary to store user states (email, app password, or keyword input)
user_states = {}

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = {"state": "awaiting_email_count"}  # Set state to awaiting email count
    await update.message.reply_text(
        "I am an Email Alert Bot. I will forward your emails to you here.\n\n"
        "How many emails do you want to add? (1 or 2)"
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text

    if user_id not in user_states:
        await update.message.reply_text("Please start the bot using the /start command.")
        return

    state = user_states[user_id].get("state")

    if state == "awaiting_email_count":
        if user_input in ["1", "2"]:
            user_states[user_id]["email_count"] = int(user_input)
            user_states[user_id]["current_email"] = 1
            user_states[user_id]["state"] = "awaiting_email"
            await update.message.reply_text(f"Please provide your email {user_states[user_id]['current_email']}.")
        else:
            await update.message.reply_text("Please enter either 1 or 2.")

    elif state == "awaiting_email":
        if "@" in user_input and "." in user_input:
            current_email = user_states[user_id]["current_email"]
            if current_email == 1:
                c.execute("INSERT OR REPLACE INTO user_credentials (user_id, email1) VALUES (?, ?)", (user_id, user_input))
            else:
                c.execute("UPDATE user_credentials SET email2 = ? WHERE user_id = ?", (user_input, user_id))
            conn.commit()

            user_states[user_id]["state"] = "awaiting_app_password"
            await update.message.reply_text(f"Thank you! Now, please provide the app password for email {current_email}.")
        else:
            await update.message.reply_text("Please provide a valid email address.")

    elif state == "awaiting_app_password":
        current_email = user_states[user_id]["current_email"]
        if current_email == 1:
            c.execute("UPDATE user_credentials SET app_password1 = ? WHERE user_id = ?", (user_input, user_id))
        else:
            c.execute("UPDATE user_credentials SET app_password2 = ? WHERE user_id = ?", (user_input, user_id))
        conn.commit()

        if user_states[user_id]["email_count"] == 2 and current_email == 1:
            user_states[user_id]["current_email"] = 2
            user_states[user_id]["state"] = "awaiting_email"
            await update.message.reply_text("Please provide your email 2.")
        else:
            user_states[user_id]["state"] = "awaiting_keyword_choice"
            reply_keyboard = [["Yes Set keywords", "No, Forward all emails"]]
            await update.message.reply_text(
                "Do you want to set keywords?",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            )

    elif state == "awaiting_keyword_choice":
        if user_input == "Yes Set keywords":
            user_states[user_id]["state"] = "awaiting_keywords"
            await update.message.reply_text("Please provide the keywords separated by commas.")
        elif user_input == "No, Forward all emails":
            c.execute("UPDATE user_credentials SET keywords = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            del user_states[user_id]
            await update.message.reply_text("Thank you! I will forward all emails to you.")
        else:
            await update.message.reply_text("Please choose one of the options.")

    elif state == "awaiting_keywords":
        c.execute("UPDATE user_credentials SET keywords = ? WHERE user_id = ?", (user_input, user_id))
        conn.commit()
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
