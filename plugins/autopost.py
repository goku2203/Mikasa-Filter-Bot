import logging
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, UPDATES_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp, get_size

logger = logging.getLogger(__name__)

# --- BATCH STORAGE ---
# Ingatha files wait pannum
BATCH_DATA = {}
BATCH_LOCK = asyncio.Lock()

# --- Helper Functions ---

def get_year(filename):
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    return match.group(0) if match else ""

def get_quality(filename):
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "2160p 4K"
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
    if "multi" in filename or "dual" in filename: audio.append("Multi Audio")
    return " - ".join(audio) if audio else "Original Audio"

def get_clean_name(name):
    # Remove junk tags
    clean = re.sub(r"(\[.*?\]|\{.*?\}|\(.*?\)|720p|1080p|480p|2160p|4k|HEVC|x264|x265|mkv|mp4|avi|www\.|@\w+)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean) # Remove year from name
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

# --- Batch Sender (After 5 Seconds) ---

async def send_batched_post(client, clean_name):
    # Wait for 5 Seconds (Tag Remover & Grouping)
    await asyncio.sleep(5)
    
    async with BATCH_LOCK:
        if clean_name not in BATCH_DATA:
            return
        files_list = BATCH_DATA.pop(clean_name)

    # Sort files by name or quality (Optional)
    files_list.sort(key=lambda x: x['quality'], reverse=True)

    if not files_list:
        return

    # Extract Common Details from first file
    first_file = files_list[0]
    movie_name = first_file['name']
    year = first_file['year']
    audio = first_file['audio']
    year_str = f"({year})" if year else ""

    # Construct Header
    caption = (
        f"🎬 <b>{movie_name} {year_str}</b>\n"
        f"🔊 <b>Audio:</b> {audio}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )

    # Add File Links (Loop through grouped files)
    for file in files_list:
        caption += f"📂 <a href='{file['link']}'><b>{file['quality']} - {file['size']}</b></a>\n"

    caption += "━━━━━━━━━━━━━━━━━━━\n"
    caption += "<i>(Click the file size to download)</i>"

    # Channel Button
    channel_btn = [[InlineKeyboardButton("✨ ᴊᴏɪɴ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇs ✨", url="https://t.me/tamiltechgkofficial")]]

    try:
        await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption,
            reply_markup=InlineKeyboardMarkup(channel_btn)
        )
        logger.info(f"✅ Group Post Sent: {movie_name} ({len(files_list)} Files)")
    except Exception as e:
        logger.error(f"❌ Post Failed: {e}")

# --- Main Listener ---

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_handler(client, message):
    try:
        # 1. Get Media
        media = getattr(message, message.media.value)
        file_id, file_ref = unpack_new_file_id(media.file_id)
        file_name = media.file_name
        
        # 2. Save to DB (Always)
        try:
            media.file_type = message.media.value
            media.caption = message.caption
            await save_file(media)
        except:
            pass 

        if not UPDATES_CHANNEL:
            return

        # 3. Prepare Data for Grouping
        clean_name = get_clean_name(file_name)
        file_data = {
            'name': clean_name,
            'year': get_year(file_name),
            'quality': get_quality(file_name),
            'audio': get_audio(file_name),
            'size': get_size(media.file_size),
            'link': f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"
        }

        # 4. Add to Batch & Start Timer
        async with BATCH_LOCK:
            if clean_name not in BATCH_DATA:
                BATCH_DATA[clean_name] = []
                # First file for this movie? Start the 5-sec timer
                asyncio.create_task(send_batched_post(client, clean_name))
            
            BATCH_DATA[clean_name].append(file_data)
            logger.info(f"➕ Added to Batch: {file_name}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
