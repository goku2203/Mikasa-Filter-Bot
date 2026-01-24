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
BATCH_DATA = {}
BATCH_TASKS = {} 

# --- 1. SMART INFO EXTRACTORS ---

def get_year(filename):
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    return match.group(0) if match else "N/A"

def get_quality_category(filename):
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "4K"
    if "1080p" in filename: return "FULL HD"
    if "720p" in filename: return "Only HD"
    return "HD-Rip" 

def get_quality_short(filename):
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "4K"
    if "1080p" in filename: return "FHD"
    if "720p" in filename: return "HD"
    return "HD-Rip"

def get_audio(filename):
    filename = filename.lower()
    audio = []
    if "tamil" in filename: audio.append("Tamil")
    if "telugu" in filename: audio.append("Telugu")
    if "hindi" in filename: audio.append("Hindi")
    if "malayalam" in filename: audio.append("Malayalam")
    if "kan" in filename: audio.append("Kannada")
    if "eng" in filename: audio.append("English")
    if "multi" in filename or "dual" in filename: audio.append("Multi Audio")
    
    return " - ".join(audio) if audio else "Original Audio"

def get_clean_name(name):
    clean = name.lower()
    # Remove Extension
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
    # Remove Year
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    # Remove Brackets
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\(.*?\)', '', clean)
    # Remove Keywords
    keywords = [
        "tamil", "telugu", "hindi", "malayalam", "kannada", "english", "eng", "tam", "tel", "hin",
        "hq", "hdrip", "bluray", "web-dl", "web", "hd", "cam", "predvd", "dvdscr", "rip",
        "1080p", "720p", "480p", "2160p", "4k", "5.1", "aac", "x264", "x265", "hevc", "esub", "sub",
        "remastered", "bd", "dual", "multi", "audio", "trollmaa", "goku stark", "@goku_stark"
    ]
    for word in keywords:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)
    
    clean = re.sub(r'[-_./@|]', ' ', clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.title()

# --- 2. BATCH SENDER ---

async def send_batched_post(client, clean_name):
    try:
        # INCREASED WAIT TIME TO 20 SECONDS (To fix grouping issue)
        await asyncio.sleep(20) 
    except asyncio.CancelledError:
        return 

    if clean_name not in BATCH_DATA:
        return

    # Pop Data
    raw_files_list = BATCH_DATA.pop(clean_name)
    if clean_name in BATCH_TASKS:
        del BATCH_TASKS[clean_name]

    # Remove Duplicates
    unique_files = []
    seen_sizes = set()
    for f in raw_files_list:
        if f['size'] not in seen_sizes:
            unique_files.append(f)
            seen_sizes.add(f['size'])
            
    if not unique_files:
        return

    # Categorize
    categorized = { "4K": [], "FULL HD": [], "Only HD": [], "HD-Rip": [] }
    first_file = unique_files[0]
    
    for file in unique_files:
        cat = file['category']
        if cat in categorized:
            categorized[cat].append(file)
        else:
            categorized["HD-Rip"].append(file)

    # --- BUILD CAPTION (Removed Original Name) ---
    movie_name = clean_name
    year = first_file['year']
    audio = first_file['audio']

    caption = (
        f"🎬 <b>{movie_name}</b>\n"
        f"🗓️ <b>Year:</b> {year}\n"
        f"🔊 <b>Audio:</b> {audio}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )

    order = ["HD-Rip", "Only HD", "FULL HD", "4K"]
    
    for category in order:
        files = categorized[category]
        if files:
            caption += f"<b>{category}</b>\n"
            for f in files:
                caption += f"📂 <a href='{f['link']}'><b>{f['short_q']} - {f['size']}</b></a>\n"
            caption += "\n"

    caption += "━━━━━━━━━━━━━━━━━━━\n"
    caption += "<i>(Click the file size to download)</i>"

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

# --- 3. MAIN LISTENER ---

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
            'category': get_quality_category(file_name),
            'short_q': get_quality_short(file_name),
            'audio': get_audio(file_name),
            'size': get_size(media.file_size),
            'link': f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"
        }

        if clean_name not in BATCH_DATA:
            BATCH_DATA[clean_name] = []
        BATCH_DATA[clean_name].append(file_data)

        if clean_name in BATCH_TASKS:
            BATCH_TASKS[clean_name].cancel()

        task = asyncio.create_task(send_batched_post(client, clean_name))
        BATCH_TASKS[clean_name] = task
        
        logger.info(f"⏳ Processing: {clean_name} (Waiting 20s)")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
