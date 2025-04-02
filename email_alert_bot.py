import imaplib
import email
import requests
import re
import sqlite3
from email.header import decode_header
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import threading
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Configuration
TELEGRAM_BOT_TOKEN = "8104815167:AAE5mXfgJzeNIsx0wVRO9RqMlWKnajk8wRQ"
MONGO_URI = "mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/"

# MongoDB setup
cluster = MongoClient(MONGO_URI)
db = cluster["email_alert_bot"]
collection = db["emails"]

# Initialize SQLite database
conn = sqlite3.connect('user_preferences.db', check_same_thread=False)
c = conn.cursor()

# Create table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS user_credentials
             (user_id INTEGER PRIMARY KEY, email1 TEXT, app_password1 TEXT, 
              email2 TEXT, app_password2 TEXT, keywords TEXT)''')
conn.commit()

# Dictionary to store user states
user_states = {}
fetch_email_running = False

# Function to escape special characters for Telegram MarkdownV2
def escape_markdown_v2(text):
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

# Function to extract plain text from HTML emails
def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.replace_with(p.get_text() + "\n\n")
    text = soup.get_text(separator="\n").strip()
    return text

# Function to clean and preprocess text
def clean_text(text):
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# Function to check if email matches keywords using Cosine TF-IDF
def matches_keywords(email_text, keywords, user_email):
    if not keywords or not keywords.strip():
        return True  # Forward all emails if no keywords are set

    keyword_list = [keyword.strip().lower() for keyword in keywords.split(',') if keyword.strip()]
    if not keyword_list:
        return True

    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words='english')
    
    # Combine email text and keywords into documents
    documents = [email_text.lower()] + keyword_list
    
    try:
        # Calculate TF-IDF matrix
        tfidf_matrix = vectorizer.fit_transform(documents)
        
        # Calculate cosine similarity between email and each keyword
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
        
        # Check if any similarity exceeds threshold
        max_similarity = np.max(similarities)
        if max_similarity >= 0.05:  # Threshold set to 0.05
            # Get the matched keyword
            matched_keyword_idx = np.argmax(similarities)
            matched_keyword = keyword_list[matched_keyword_idx]
            
            # Store the match in MongoDB for analytics
            collection.insert_one({
                "email_text": email_text,
                "keywords": keyword_list,
                "user_email": user_email,
                "matched_keyword": matched_keyword,
                "similarity_score": float(max_similarity),
                "timestamp": datetime.datetime.now()
            })
            return True
    except Exception as e:
        print(f"Error in TF-IDF matching: {e}")
        # Fallback to simple keyword matching in case of error
        email_text_lower = clean_text(email_text).lower()
        for keyword in keyword_list:
            if keyword in email_text_lower:
                collection.insert_one({
                    "email_text": email_text,
                    "keywords": keyword_list,
                    "user_email": user_email,
                    "matched_keyword": keyword,
                    "similarity_score": 1.0,
                    "timestamp": datetime.datetime.now()
                })
                return True
    
    return False

# Function to fetch and process emails
def fetch_emails():
    global fetch_email_running
    fetch_email_running = True
    
    while fetch_email_running:
        try:
            c.execute("SELECT user_id, email1, app_password1, email2, app_password2, keywords FROM user_credentials")
            user_credentials = c.fetchall()

            for user_id, email1, app_password1, email2, app_password2, keywords in user_credentials:
                emails = [(email1, app_password1)]
                if email2 and app_password2:
                    emails.append((email2, app_password2))

                for email_addr, app_password in emails:
                    try:
                        mail = imaplib.IMAP4_SSL("imap.gmail.com")
                        mail.login(email_addr, app_password)
                        mail.select("inbox")

                        status, messages = mail.search(None, 'UNSEEN')
                        email_ids = messages[0].split()

                        for email_id in email_ids:
                            try:
                                status, msg_data = mail.fetch(email_id, "(RFC822)")
                                for response_part in msg_data:
                                    if isinstance(response_part, tuple):
                                        email_content = response_part[1]
                                        msg = email.message_from_bytes(email_content) if isinstance(email_content, bytes) else email.message_from_string(email_content)

                                        subject, encoding = decode_header(msg["Subject"])[0]
                                        if isinstance(subject, bytes):
                                            subject = subject.decode(encoding if encoding else "utf-8")
                                        sender = msg.get("From")

                                        body = ""
                                        if msg.is_multipart():
                                            for part in msg.walk():
                                                content_type = part.get_content_type()
                                                content_disposition = str(part.get("Content-Disposition"))
                                                if "attachment" not in content_disposition:
                                                    try:
                                                        body_bytes = part.get_payload(decode=True)
                                                        if body_bytes:
                                                            body = body_bytes.decode(part.get_content_charset() or "utf-8")
                                                            if content_type == "text/html":
                                                                body = extract_text_from_html(body)
                                                    except Exception as e:
                                                        body = "(Error reading email content)"
                                        else:
                                            try:
                                                body_bytes = msg.get_payload(decode=True)
                                                if body_bytes:
                                                    body = body_bytes.decode(msg.get_content_charset() or "utf-8")
                                                    if msg.get_content_type() == "text/html":
                                                        body = extract_text_from_html(body)
                                            except Exception as e:
                                                body = "(Error reading email content)"

                                        body = clean_text(body)
                                        email_text = f"{subject} {body}"
                                        
                                        # Only check keywords if they exist
                                        if keywords and not matches_keywords(email_text, keywords, email_addr):
                                            continue

                                        safe_subject = escape_markdown_v2(subject)
                                        safe_sender = escape_markdown_v2(sender)
                                        safe_body = escape_markdown_v2(body)

                                        telegram_message = f"📩 *New Email Received\!*\n\n" \
                                                           f"📧 *From:* {safe_sender}\n" \
                                                           f"📌 *Subject:* {safe_subject}\n\n" \
                                                           f"{safe_body}"

                                        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                                        payload = {
                                            "chat_id": user_id,
                                            "text": telegram_message,
                                            "parse_mode": "MarkdownV2"
                                        }
                                        requests.post(telegram_api_url, json=payload)

                            except Exception as e:
                                print(f"Error processing email: {e}")

                        mail.logout()
                    except Exception as e:
                        print(f"Failed to connect to mail server for {email_addr}: {e}")

            # Sleep for 60 seconds before checking again
            time.sleep(60)
        except Exception as e:
            print(f"Error in fetch_emails loop: {e}")
            time.sleep(60)

# Telegram Bot Handlers
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = {"state": "awaiting_email_count"}
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
            start_fetch_email_thread()
        else:
            await update.message.reply_text("Please choose one of the options.")

    elif state == "awaiting_keywords":
        c.execute("UPDATE user_credentials SET keywords = ? WHERE user_id = ?", (user_input, user_id))
        conn.commit()
        del user_states[user_id]
        await update.message.reply_text("Thank you! Your keywords have been saved. I will now forward emails matching these keywords.\nTo continue with analytics visit https://emailalertbot.onrender.com")
        start_fetch_email_thread()

def start_fetch_email_thread():
    global fetch_email_running
    if not fetch_email_running:
        threading.Thread(target=fetch_emails, daemon=True).start()

def main():
    # Start the email fetching thread
    start_fetch_email_thread()

    # Create and run the Telegram bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
