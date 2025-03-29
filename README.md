# Telegram Torrent Bot 🤖

A bot that downloads torrent files and sends back the content with real-time stats.

## Features
- Real-time download/upload speed
- Progress tracking
- Automatic file cleanup
- Multi-file support

## Setup
1. Clone repo
2. Install requirements: `pip install -r requirements.txt`
3. Set `TELEGRAM_TOKEN` in .env
4. Run: `python bot.py`

## Deployment
```bash
sudo cp torrent-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start torrent-bot
