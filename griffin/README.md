# Telegram Bot System with Admin Panel and Referral System

This system consists of two Telegram bots:
1. Main Bot - with admin panel and referral system
2. Info Bot - for receiving and displaying all logs and payment information

## Features

### Main Bot
- Admin Panel with:
  - User management
  - Payment statistics
  - User statistics
  - Referral system tracking
- Support for 2 admins with protection against mutual removal
- Worker panel for users who joined through referral links
- Comprehensive logging system

### Info Bot
- Receives and displays all logs
- Shows payment information
- Tracks user actions

## Setup

1. Create two Telegram bots using [@BotFather](https://t.me/BotFather)
2. Copy `.env.example` to `.env` and fill in the following:
   - `MAIN_BOT_TOKEN` - Token for the main bot
   - `INFO_BOT_TOKEN` - Token for the info bot
   - `ADMIN_IDS` - Comma-separated list of admin Telegram IDs
   - `INFO_BOT_CHAT_ID` - Chat ID where the info bot will send logs

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the bots:
```bash
# Terminal 1
python main_bot.py

# Terminal 2
python info_bot.py
```

## Usage

### Admin Panel
- Access the admin panel by starting the bot as an admin
- View and manage users
- Track payments and statistics
- Get your referral link

### Worker Panel
- Access the worker panel by joining through a referral link
- View your referrals
- Get your referral link

### Info Bot
- All logs and payment information will be automatically sent to the info bot
- Only accessible to the specified chat ID

## Security
- Admins cannot remove each other
- Info bot is restricted to a specific chat
- All sensitive operations are logged 