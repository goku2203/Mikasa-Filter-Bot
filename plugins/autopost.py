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

# --- 1. SUPER CLEANER (THE FIX) ---

def get_clean_name(name):
    # 1. Lowercase & Basic Clean
    clean = name.lower()
    
    # 2. Remove File Extension (.mkv, .mp4)
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
    
    # 3. Remove Year (1990-2029)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    
    # 4. Remove Channel Names (Add your channel names here)
    junk_channels = ["@goku_stark", "goku stark", "trollmaa", "backup - tamil movies"]
    for junk in junk_channels:
        clean = clean.replace(junk, "")

    # 5. Remove Sizes (400mb, 1.4gb)
    clean = re.sub(r'\b\d{3,4}mb\b', '', clean)
    clean = re.sub(r'\b\d+(\.\d+)?gb\b', '', clean)

    # 6. Remove Quality (1080p, 720p...)
    clean = re.sub(r'\b(2160p|4k|1080p|720p|480p|360p|hdrip|hq|hd|bd|bluray|web-dl|web)\b', '', clean)

    # 7. Remove Audio/Codec Junk (Dd+5, Dd5.1, AAC, etc.)
    # This specifically fixes "Dd+5", "Dd5 1" issues
    clean = re.sub(r'\b(dd\+?5\.?1?|dd\+?|aac|ac3|eac3|dts|esub|sub)\b', '', clean)

    # 8. Remove "Proper", "True", "AVC", "Remastered"
    junk_words = ["proper", "true", "avc", "remastered", "uncut", "extended", "dual", "multi", "audio", "tamil", "telugu", "hindi", "eng", "english"]
    for word in junk_words:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)

    # 9. Remove ALL Special Characters (Brackets, Dashes, etc.)
    # This fixes the "Manam [" issue
    clean = re.sub(r'[\[\]\(\)\{\}\-_./@|:+]', ' ', clean)

    # 10. Remove Single Letters at End (Fixes "Leo E")
    clean = re.sub(r'\s+[a-z]$', '', clean)

    # Final Strip
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.title()

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
    if "eng" in filename: audio.append("English")
    if "multi" in filename or "dual" in filename: audio.append("Multi Audio")
    return " - ".join(audio) if audio else "Original Audio"

# --- 2. BATCH SENDER ---

async def send_batched_post(client, clean_name):
    try:
        # 30 Seconds Wait (Safe Time)
        await asyncio.sleep(30)
    except asyncio.CancelledError:
        return 

    if clean_name not in BATCH_DATA:
        return

    # Pop Data
    raw_files_list = BATCH_DATA.pop(clean_name)
    if clean_name in BATCH_TASKS:
        del BATCH_TASKS[clean_name]

    # Check for Duplicates (Based on Size)
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

    # --- BUILD CAPTION ---
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
    
    has_files = False
    for category in order:
        files = categorized[category]
        if files:
            has_files = True
            caption += f"<b>{category}</b>\n"
            for f in files:
                caption += f"📂 <a href='{f['link']}'><b>{f['short_q']} - {f['size']}</b></a>\n"
            caption += "\n"

    if not has_files:
        return

    caption += "━━━━━━━━━━━━━━━━━━━\n"
    caption += "<i>(Click the file size to download)</i>"

    channel_btn = [[InlineKeyboardButton("✨ ᴊᴏɪɴ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇs ✨", url="https://t.me/tamiltechgkofficial")]]

    try:
        await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption,
            reply_markup=InlineKeyboardMarkup(channel_btn)
        )
        logger.info(f"✅ Post Sent: {movie_name}")
    except Exception as e:
        logger.error(f"❌ Post Failed: {e}")

# --- 3. MAIN LISTENER ---

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_handler(client, message):
    try:
        media = getattr(message, message.media.value)
        file_id, file_ref = unpack_new_file_id(media.file_id)
        file_name = media.file_name
        
        try:
            media.file_type = message.media.value
            media.caption = message.caption
            await save_file(media)
        except:
            pass 

        if not UPDATES_CHANNEL:
            return

        # THIS IS THE KEY: CLEAN NAME
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

        # Reset Timer on new file
        if clean_name in BATCH_TASKS:
            BATCH_TASKS[clean_name].cancel()

        task = asyncio.create_task(send_batched_post(client, clean_name))
        BATCH_TASKS[clean_name] = task
        
        logger.info(f"⏳ Grouping: {clean_name} (30s Wait)")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
