import os
import time
import libtorrent as lt
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from io import BytesIO

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "torrent_downloads")
STATUS_INTERVAL = 5  # Seconds

# Initialize session
ses = lt.session()
ses.listen_on(6881, 6891)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "📤 Send me a .torrent file to start downloading!"
    )

def handle_torrent(update: Update, context: CallbackContext) -> None:
    try:
        # Get torrent file
        file = update.message.document.get_file()
        file_stream = BytesIO()
        file.download(out=file_stream)
        file_stream.seek(0)
        
        # Save torrent file
        torrent_path = os.path.join(DOWNLOAD_DIR, "temp.torrent")
        with open(torrent_path, 'wb') as f:
            f.write(file_stream.read())
        
        # Add torrent
        params = {
            'ti': lt.torrent_info(torrent_path),
            'save_path': DOWNLOAD_DIR,
            'storage_mode': lt.storage_mode_t(2)
        }
        handle = ses.add_torrent(params)
        
        # Start status updates
        context.job_queue.run_repeating(
            status_update, 
            STATUS_INTERVAL,
            context=(update.message.chat_id, handle),
            name=str(update.message.chat_id)
        )
        
        update.message.reply_text("🚀 Download started!")
        
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

def status_update(context: CallbackContext) -> None:
    job = context.job
    chat_id, handle = job.context
    s = handle.status()
    
    status_msg = f"""
📁 {handle.name()}
⏳ Progress: {s.progress * 100:.2f}%
🔽 DL: {s.download_rate / 1e6:.2f} MB/s
🔼 UL: {s.upload_rate / 1e6:.2f} MB/s
👥 Peers: {s.num_peers}
    """
    
    try:
        context.bot.send_message(chat_id, status_msg)
    except:
        pass

    if s.is_seeding:
        send_files(context.bot, chat_id)
        context.job.schedule_removal()

def send_files(bot: Bot, chat_id: int) -> None:
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.endswith(".torrent"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, 'rb') as f:
                    bot.send_document(chat_id, f)
                os.remove(path)
            except Exception as e:
                bot.send_message(chat_id, f"⚠️ Failed to send {file}: {str(e)}")

def main() -> None:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document.mime_type("application/x-bittorrent"), handle_torrent))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
