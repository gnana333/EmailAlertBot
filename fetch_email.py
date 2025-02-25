import imaplib
import email
import requests
import re
import sqlite3
from email.header import decode_header
from bs4 import BeautifulSoup  # Convert HTML emails to plain text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Telegram Bot credentials
TELEGRAM_BOT_TOKEN = "8104815167:AAE5mXfgJzeNIsx0wVRO9RqMlWKnajk8wRQ"

# Function to escape special characters for Telegram MarkdownV2
def escape_markdown_v2(text):
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

# Function to extract plain text from HTML emails
def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n").strip()

# Function to clean and preprocess text
def clean_text(text):
    # Remove special characters and extra spaces
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove special characters
    return text.lower().strip()  # Convert to lowercase and strip leading/trailing spaces

# Function to check if email matches keywords using TF-IDF and cosine similarity
def matches_keywords(email_text, keywords):
    if not keywords:
        return True  # No keywords set, forward all emails

    # Clean the email text and keywords
    email_text = clean_text(email_text)
    keyword_list = [clean_text(keyword) for keyword in keywords.split(',')]

    # Debugging: Print email text and keywords
    print(f"📧 Email Text: {email_text}")
    print(f"🔑 Keywords: {keyword_list}")

    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([email_text] + keyword_list)
    
    # Calculate cosine similarity between the email and each keyword
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    
    # Debugging: Print cosine similarity scores
    print(f"🔍 Cosine Similarities: {cosine_similarities[0]}")

    # Check if any similarity score is above a threshold (e.g., 0.1)
    return any(score > 0.05 for score in cosine_similarities[0])


# Connect to SQLite database
conn = sqlite3.connect('user_preferences.db', check_same_thread=False)
c = conn.cursor()

# Ensure the keywords column exists in the user_credentials table
c.execute("PRAGMA table_info(user_credentials)")
columns = c.fetchall()
if 'keywords' not in [column[1] for column in columns]:
    c.execute("ALTER TABLE user_credentials ADD COLUMN keywords TEXT")
    conn.commit()

# Fetch user credentials from the database
c.execute("SELECT user_id, email, app_password, keywords FROM user_credentials")
user_credentials = c.fetchall()

for user_id, email_addr, app_password, keywords in user_credentials:
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_addr, app_password)
        mail.select("inbox")
        print(f"✅ Connected to email server for {email_addr}.")

        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print(f"📭 No new unread emails for {email_addr}.")
            mail.logout()
            continue

        for email_id in email_ids:
            try:
                # Fetch the email
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        email_content = response_part[1]

                        # Ensure the email data is treated correctly
                        if isinstance(email_content, bytes):
                            msg = email.message_from_bytes(email_content)
                        elif isinstance(email_content, str):
                            msg = email.message_from_string(email_content)
                        else:
                            print(f"⚠️ Unexpected email content type: {type(email_content)}")
                            continue  # Skip this email

                        # Parse the email
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        sender = msg.get("From")

                        # Extract email body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))

                                # Get the email content (skip attachments)
                                if "attachment" not in content_disposition:
                                    try:
                                        body_bytes = part.get_payload(decode=True)
                                        if body_bytes:
                                            body = body_bytes.decode(part.get_content_charset() or "utf-8")
                                            
                                            # Convert HTML emails to plain text
                                            if content_type == "text/html":
                                                body = extract_text_from_html(body)
                                    except Exception as e:
                                        print(f"⚠️ Error decoding email part: {e}")
                                        body = "(Error reading email content)"
                        else:
                            try:
                                body_bytes = msg.get_payload(decode=True)
                                if body_bytes:
                                    body = body_bytes.decode(msg.get_content_charset() or "utf-8")
                                    
                                    # Convert HTML emails to plain text
                                    if msg.get_content_type() == "text/html":
                                        body = extract_text_from_html(body)
                            except Exception as e:
                                print(f"⚠️ Error decoding email body: {e}")
                                body = "(Error reading email content)"

                        # Check if the email matches the keywords
                        email_text = f"{subject} {body}"
                        if not matches_keywords(email_text, keywords):
                            print(f"📨 Email does not match keywords for {email_addr}.")
                            continue

                        # Escape MarkdownV2 characters for Telegram
                        safe_subject = escape_markdown_v2(subject)
                        safe_sender = escape_markdown_v2(sender)
                        safe_body = escape_markdown_v2(body)

                        # Format the message for Telegram
                        telegram_message = f"📩 *New Email Received\!*\n\n" \
                                           f"📧 *From:* {safe_sender}\n" \
                                           f"📌 *Subject:* {safe_subject}\n\n"

                        # Send the email details first
                        print("🚀 Sending email details to Telegram...")
                        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        payload = {
                            "chat_id": user_id,
                            "text": telegram_message,
                            "parse_mode": "MarkdownV2"
                        }
                        response = requests.post(telegram_api_url, json=payload)

                        if response.status_code == 200:
                            print("✅ Email details sent!")
                        else:
                            print(f"❌ Failed to send email details. Response: {response.status_code}, {response.text}")

                        # Split the email body into 4000-character chunks
                        max_length = 4000
                        body_chunks = [safe_body[i:i + max_length] for i in range(0, len(safe_body), max_length)]

                        for chunk in body_chunks:
                            payload = {
                                "chat_id": user_id,
                                "text": chunk,
                                "parse_mode": "MarkdownV2"
                            }
                            response = requests.post(telegram_api_url, json=payload)

                            if response.status_code == 200:
                                print("✅ Email body chunk sent!")
                            else:
                                print(f"❌ Failed to send email body. Response: {response.status_code}, {response.text}")

            except Exception as e:
                print(f"❌ Error processing email ID {email_id}: {e}")

        # Logout from the email server
        mail.logout()
        print(f"📤 Logged out from email server for {email_addr}.")

    except Exception as e:
        print(f"❌ Failed to connect to the mail server or login for {email_addr}: {e}")