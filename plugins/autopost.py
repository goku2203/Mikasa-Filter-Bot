import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, UPDATES_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp, get_size
import re

logger = logging.getLogger(__name__)

# Clean Name Helper
def get_clean_name(name):
    clean = re.sub(r"(\[.*?\]|\{.*?\}|\(.*?\)|720p|1080p|480p|HEVC|x264|x265|mkv|mp4|avi|www\.|@\w+)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.lower()

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def force_auto_post(client, message):
    try:
        # 1. Get Media Details
        media = getattr(message, message.media.value)
        file_id, file_ref = unpack_new_file_id(media.file_id)
        file_name = media.file_name
        
        # 2. Try to Save (Ignore if already exists)
        try:
            media.file_type = message.media.value
            media.caption = message.caption
            await save_file(media)
        except:
            pass # Already saved na paravalla, leave it.

        # 3. FORCE POST TO CHANNEL (This will run anyway)
        if not UPDATES_CHANNEL:
            logger.error("❌ UPDATES_CHANNEL ID Missing in Variables!")
            return

        clean_name = get_clean_name(file_name)
        file_size = get_size(media.file_size)

        # Caption
        caption = (
            f"<b>📂 New File Added!</b>\n\n"
            f"<b>🎬 Name:</b> {clean_name}\n"
            f"<b>💾 Size:</b> {file_size}\n"
            f"<b>📁 Original Name:</b> <code>{file_name}</code>\n\n"
            f"<i>Get this file from the bot! 👇</i>"
        )

        # Button
        btn = [[InlineKeyboardButton("📥 Get File", url=f"https://t.me/{temp.U_NAME}?start=filep_{file_id}")]]

        # Send Message
        await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption,
            reply_markup=InlineKeyboardMarkup(btn)
        )
        logger.info(f"✅ FORCE POST SENT: {clean_name}")

    except Exception as e:
        logger.error(f"❌ Force Post Error: {e}")
