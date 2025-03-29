import os
import time
import libtorrent as lt
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from io import BytesIO

# Configuration
TOKEN = "7260376583:AAHrxxeuV76xQk-Wubivwhoa2OHbJuPtE5o"
DOWNLOAD_DIR = "torrent_downloads"
STATUS_INTERVAL = 5  # Update interval in seconds

# Initialize libtorrent session
ses = lt.session()
ses.listen_on([6881, 6891])  # Updated listen method

# Start command handler
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "📤 Send me a torrent file to start downloading!\n"
        "I'll send you the files once completed and clean up automatically!"
    )

# Handle received torrent file
async def handle_torrent(update: Update, context: CallbackContext) -> None:
    try:
        # Get torrent file from user
        torrent_file = update.message.document.get_file()
        file_stream = BytesIO()
        await torrent_file.download(out=file_stream)
        file_stream.seek(0)
        
        # Save torrent file temporarily
        torrent_path = os.path.join(DOWNLOAD_DIR, "temp.torrent")
        with open(torrent_path, 'wb') as f:
            f.write(file_stream.read())
        
        # Add torrent to session
        params = {
            'ti': lt.torrent_info(torrent_path),
            'save_path': DOWNLOAD_DIR,
            'storage_mode': lt.storage_mode_t(2)
        }
        handle = ses.add_torrent(params)
        
        # Start status updates
        context.job_queue.run_repeating(
            update_status,
            STATUS_INTERVAL,
            context=(update.message.chat_id, handle),
            name=str(update.message.chat_id)
        )
        
        await update.message.reply_text("🚀 Download started! I'll keep you updated...")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        cleanup()

# Update download status periodically
async def update_status(context: CallbackContext) -> None:
    job = context.job
    chat_id, handle = job.context
    s = handle.status()
    
    # Format status message
    status_msg = (
        f"📁 **{handle.name()}**\n"
        f"⏳ **Progress:** {s.progress * 100:.2f}%\n"
        f"🔽 **Download:** {s.download_rate / 1e6:.2f} MB/s\n"
        f"🔼 **Upload:** {s.upload_rate / 1e6:.2f} MB/s\n"
        f"📦 **Size:** {s.total_wanted / 1e9:.2f} GB\n"
        f"👥 **Peers:** {s.num_peers}"
    )
    
    try:
        await context.bot.send_message(chat_id, status_msg, parse_mode='Markdown')
    except:
        pass

    if s.is_seeding:
        await send_files(context.bot, chat_id)
        cleanup()
        job.schedule_removal()

# Send completed files to user
async def send_files(bot: Bot, chat_id: int) -> None:
    try:
        for root, _, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                if file.endswith(".torrent"):
                    continue
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    await bot.send_document(chat_id, f)
                os.remove(file_path)
        await bot.send_message(chat_id, "✅ All files sent and cleaned up!")
    except Exception as e:
        await bot.send_message(chat_id, f"⚠️ Error sending files: {str(e)}")

# Clean up residual files
def cleanup():
    """Clean up residual files"""
    for f in os.listdir(DOWNLOAD_DIR):
        if f.endswith(".torrent") or os.path.isfile(os.path.join(DOWNLOAD_DIR, f)):
            os.remove(os.path.join(DOWNLOAD_DIR, f))

# Main function to initialize the bot
def main() -> None:
    # Create download directory
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/x-bittorrent"), handle_torrent))
    
    app.run_polling()

if __name__ == '__main__':
    main()
