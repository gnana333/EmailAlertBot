# Email Alert Bot 📩🤖

## Overview
**Email Alert Bot** is an AI-powered email notification system that fetches unread emails from a user's inbox, filters them using **TF-IDF and cosine similarity**, and forwards relevant emails to a Telegram bot. 

This bot helps users receive real-time email alerts directly on Telegram while allowing **customized keyword filtering** for efficient email management.

---

## 🚀 Features
- 🔍 **Fetch unread emails** from Gmail using IMAP.
- 🧠 **Keyword-based filtering** with AI (TF-IDF & Cosine Similarity).
- 💬 **Telegram bot integration** for real-time notifications.
- 🔐 **Secure storage** of user credentials in an SQLite database.
- 🎛️ **Customizable keywords** for precise email filtering.
- 🛑 **Handles HTML emails** and converts them to plain text.

---

## 🛠️ Tech Stack
- **Python**
- **IMAPLIB** (For email fetching)
- **SQLite** (For storing user credentials)
- **Telegram Bot API** (For sending notifications)
- **Scikit-learn** (For AI-based email filtering)
- **BeautifulSoup** (For HTML parsing)

---

## 📂 Project Structure
📂 Email-Alert-Bot/ │── 📄 fetch_email.py # Fetches emails, applies filtering, and sends alerts │── 📄 telegram_bot.py # Handles user interactions and configurations via Telegram │── 📄 requirements.txt # List of required dependencies │── 📄 README.md # Project documentation

**🔐 Security Note**
Use an App Password instead of your actual email password.
Never hardcode sensitive credentials in your scripts.
Store API keys securely (e.g., in an environment variable).

**🛠️ Future Enhancements**
✅ Support for multiple email providers (Outlook, Yahoo, etc.).
✅ Add web-based dashboard for email management.
✅ Improve AI filtering with NLP techniques.

**🤝 Contributing**
Pull requests and improvements are welcome! Open an issue if you find any bugs or have feature requests.

**📬 Contac**t
For any queries, feel free to reach out on Telegram or GitHub Issues.

🔥 Enjoy Real-Time Email Alerts with AI-Powered Filtering! 🔥


---

Let me know if you need modifications! 🚀

