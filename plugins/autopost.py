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
    # Order matters: check distinct languages
    if "tamil" in filename: audio.append("Tamil")
    if "telugu" in filename: audio.append("Telugu")
    if "hindi" in filename: audio.append("Hindi")
    if "malayalam" in filename: audio.append("Malayalam")
    if "kan" in filename: audio.append("Kannada")
    if "eng" in filename: audio.append("English")
    if "multi" in filename or "dual" in filename: audio.append("Multi Audio")
    
    return " - ".join(audio) if audio else "Original Audio"

def get_clean_name(name):
    # 1. Lowercase conversion
    clean = name.lower()
    
    # 2. Remove Year (e.g., 2024)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    
    # 3. Remove content inside brackets like [Tamil] or (2024) to group correctly
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\(.*?\)', '', clean)
    
    # 4. Remove Common Keywords (Languages, Quality, etc.) to get RAW Name
    keywords = [
        "tamil", "telugu", "hindi", "malayalam", "kannada", "english", "eng", "tam", "tel", "hin",
        "hq", "hdrip", "bluray", "web-dl", "web", "hd", "cam", "predvd", "dvdscr", "rip",
        "1080p", "720p", "480p", "2160p", "4k", "5.1", "aac", "x264", "x265", "hevc", "esub", "sub"
    ]
    for word in keywords:
        clean = clean.replace(word, "")
    
    # 5. Remove Special Characters (- _ . @)
    clean = re.sub(r'[-_./@]', ' ', clean)
    
    # 6. Remove Extra Spaces
    clean = re.sub(r"\s+", " ", clean).strip()
    
    # 7. Title Case for looks (e.g., "leo movie" -> "Leo Movie")
    return clean.title()

# --- Sender Function ---

async def send_batched_post(client, clean_name):
    # Wait for 10 Seconds (Group all files)
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

    # --- STYLE SECTION (Red 1, 2, 3) ---
    
    first_file = files_list[0]
    # Use the clean name for the title
    movie_name = clean_name 
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
        # Display: 📂 720p HD - 1.4GB (Clickable)
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

        # VERY IMPORTANT: Get the "Grouping Name"
        clean_name = get_clean_name(file_name)
        
        file_data = {
            'name': clean_name,
            'year': get_year(file_name),
            'quality': get_quality(file_name),
            'audio': get_audio(file_name),
            'size': get_size(media.file_size),
            'link': f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"
        }

        # Batch Logic (Smart Timer)
        if clean_name not in BATCH_DATA:
            BATCH_DATA[clean_name] = []
        BATCH_DATA[clean_name].append(file_data)

        # Cancel Old Timer (Reset Clock)
        if clean_name in BATCH_TASKS:
            BATCH_TASKS[clean_name].cancel()

        # Start New Timer
        task = asyncio.create_task(send_batched_post(client, clean_name))
        BATCH_TASKS[clean_name] = task
        
        logger.info(f"⏳ Grouping file under: {clean_name}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
