import re
import logging
from pyrogram import Client, filters
from info import CHANNELS

# 👇 LOGS SETUP
logger = logging.getLogger(__name__)

# 👇 INGA UNGA PUTHU CHANNEL ID PODUNGA (Ex: -100xxxxxx)
LOG_CHANNEL_ID = -1003602676231 

def get_simple_name(name):
    if not name: return "Unknown File"
    clean = name.lower()
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
    junk_words = [
        "1080p", "720p", "480p", "hdrip", "web-dl", "bluray", 
        "x264", "x265", "hevc", "aac", "esub", "hindi", "tamil", "telugu", "dual"
    ]
    for word in junk_words:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)
    clean = re.sub(r'[._-]', ' ', clean)
    clean = re.sub(r'[\[\(\)\}]', '', clean)
    return clean.strip().title()

# 👇 'group=10' ADD PANNIRUKKEN (Mukkiyam!)
@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio), group=10)
async def alert_handler(client, message):
    try:
        # Logs-la check panna
        logger.info(f"🔔 New Alert Handler Triggered for: {message.chat.title}")

        media = getattr(message, message.media.value)
        filename = message.caption if message.caption else media.file_name
        
        clean_name = get_simple_name(filename)
        text = f"<b>{clean_name} Added ✅</b>"
        
        # Message Send Panrom
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text
        )
        logger.info(f"✅ Alert Sent to Channel: {clean_name}")
        
    except Exception as e:
        logger.error(f"❌ Alert Error: {e}")
