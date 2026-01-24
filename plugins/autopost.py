import logging
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, UPDATES_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp, get_size

logger = logging.getLogger(__name__)

# --- BATCH STORAGE & TASKS ---
BATCH_DATA = {}
BATCH_TASKS = {} 

# --- Helper Functions ---

def get_year(filename):
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    return match.group(0) if match else "N/A"

def get_quality(filename):
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "4K 2160p"
    if "1080p" in filename: return "1080p FHD"
    if "720p" in filename: return "720p HD"
    if "480p" in filename: return "480p SD"
    if "360p" in filename: return "360p"
    return "HD-Rip" 

def get_audio(filename):
    filename = filename.lower()
    audio = []
    if "tamil" in filename: audio.append("Tamil")
    if "telugu" in filename: audio.append("Telugu")
    if "hindi" in filename: audio.append("Hindi")
    if "malayalam" in filename: audio.append("Malayalam")
    if "eng" in filename: audio.append("English")
    if "kan" in filename: audio.append("Kannada")
    if "multi" in filename or "dual" in filename: audio.append("Multi Audio")
    return " - ".join(audio) if audio else "Original Audio"

def get_clean_name(name):
    # Remove junk tags
    clean = re.sub(r"(\[.*?\]|\{.*?\}|\(.*?\)|720p|1080p|480p|2160p|4k|HEVC|x264|x265|mkv|mp4|avi|www\.|@\w+)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean) # Remove year
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

# --- Sender Function ---

async def send_batched_post(client, clean_name):
    # Wait for 10 Seconds
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        return 

    if clean_name not in BATCH_DATA:
        return

    # Pop Data
    files_list = BATCH_DATA.pop(clean_name)
    if clean_name in BATCH_TASKS:
        del BATCH_TASKS[clean_name]

    # Sort files (High Quality first)
    files_list.sort(key=lambda x: x['quality'], reverse=True)

    if not files_list:
        return

    # --- STYLE SECTION ---
    # Inga thaan neenga ketta 1, 2, 3 order irukku
    
    first_file = files_list[0]
    movie_name = first_file['name']
    year = first_file['year']
    audio = first_file['audio']

    # 1. Movie Name | 2. Year | 3. Audio
    caption = (
        f"🎥 <b>{movie_name}</b>\n"
        f"📅 <b>Year:</b> {year}\n"
        f"🎧 <b>Audio:</b> {audio}\n"
        f"──────────────────\n"
    )

    # Files List (Clean Look)
    for file in files_list:
        # Display: 📂 720p HD - 1.4GB
        caption += f"📂 <a href='{file['link']}'><b>{file['quality']} - {file['size']}</b></a>\n"

    caption += "──────────────────\n"
    caption += "<i>(Click the file size to download)</i>"

    # Channel Button
    channel_btn = [[InlineKeyboardButton("✨ ᴊᴏɪɴ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇs ✨", url="https://t.me/tamiltechgkofficial")]]

    try:
        await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption,
            reply_markup=InlineKeyboardMarkup(channel_btn)
        )
        logger.info(f"✅ Group Post Sent: {movie_name}")
    except Exception as e:
        logger.error(f"❌ Post Failed: {e}")

# --- Main Listener ---

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_handler(client, message):
    try:
        media = getattr(message, message.media.value)
        file_id, file_ref = unpack_new_file_id(media.file_id)
        file_name = media.file_name
        
        # Save to DB
        try:
            media.file_type = message.media.value
            media.caption = message.caption
            await save_file(media)
        except:
            pass 

        if not UPDATES_CHANNEL:
            return

        clean_name = get_clean_name(file_name)
        file_data = {
            'name': clean_name,
            'year': get_year(file_name),
            'quality': get_quality(file_name),
            'audio': get_audio(file_name),
            'size': get_size(media.file_size),
            'link': f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"
        }

        # Batch Logic
        if clean_name not in BATCH_DATA:
            BATCH_DATA[clean_name] = []
        BATCH_DATA[clean_name].append(file_data)

        if clean_name in BATCH_TASKS:
            BATCH_TASKS[clean_name].cancel()

        task = asyncio.create_task(send_batched_post(client, clean_name))
        BATCH_TASKS[clean_name] = task
        
        logger.info(f"⏳ Waiting for files: {clean_name}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
