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
