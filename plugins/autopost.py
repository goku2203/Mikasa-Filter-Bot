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

# --- 1. AGGRESSIVE CLEANER (Fixes Split Posts) ---

def get_clean_name(name):
    clean = name.lower()
    
    # 1. Remove Specific Channel Tags (First Priority)
    clean = clean.replace("@goku_stark", "").replace("goku stark", "").replace("trollmaa", "")
    
    # 2. Remove Extensions
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
    
    # 3. Remove Brackets/Parentheses content
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\(.*?\)', '', clean)
    
    # 4. Remove Year (e.g., 1999, 2024)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    
    # 5. Remove Sizes (Fixes "400mb" vs "700mb" split issue)
    clean = re.sub(r'\b\d{3,4}mb\b', '', clean)
    clean = re.sub(r'\b\d(\.\d+)?gb\b', '', clean)
    
    # 6. Remove Quality Indicators
    clean = re.sub(r'\b(1080p|720p|480p|360p|2160p|4k)\b', '', clean)
    
    # 7. Remove ALL Junk Words (Aggressive List)
    junk_words = [
        "proper", "true", "avc", "remastered", "hq", "hdrip", "bluray", "web-dl", 
        "web", "hd", "cam", "predvd", "dvdscr", "rip", "dd5.1", "aac", "x264", 
        "x265", "hevc", "esub", "sub", "audio", "dual", "multi", "tamil", 
        "telugu", "hindi", "malayalam", "kannada", "english", "eng", "tam", "tel"
    ]
    for word in junk_words:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)
    
    # 8. Final Cleanup (Remove - . _ and extra spaces)
    clean = re.sub(r'[-_./@|]', ' ', clean)
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
        # Wait 20 seconds for all parts (400mb, 700mb etc) to arrive
        await asyncio.sleep(20)
    except asyncio.CancelledError:
        return 

    if clean_name not in BATCH_DATA:
        return

    # Pop Data
    raw_files_list = BATCH_DATA.pop(clean_name)
    if clean_name in BATCH_TASKS:
        del BATCH_TASKS[clean_name]

    # --- DUPLICATE CHECKER ---
    unique_files = []
    seen_sizes = set()
    
    for f in raw_files_list:
        # Filter duplicates based on File Size
        if f['size'] not in seen_sizes:
            unique_files.append(f)
            seen_sizes.add(f['size'])
            
    if not unique_files:
        return

    # Sort High Quality First
    unique_files.sort(key=lambda x: x['quality_rank'], reverse=True)

    # --- CATEGORIZE ---
    categorized = { "4K": [], "FULL HD": [], "Only HD": [], "HD-Rip": [] }
    first_file = unique_files[0]
    
    for file in unique_files:
        cat = file['category']
        if cat in categorized:
            categorized[cat].append(file)
        else:
            categorized["HD-Rip"].append(file)

    # --- FINAL CAPTION FORMAT ---
    movie_name = clean_name
    year = first_file['year']
    audio = first_file['audio']

    caption = (
        f"🎬 <b>{movie_name}</b>\n"
        f"🗓️ <b>Year:</b> {year}\n"
        f"🔊 <b>Audio:</b> {audio}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )

    # Order: HD-Rip -> Only HD -> FULL HD -> 4K
    order = ["HD-Rip", "Only HD", "FULL HD", "4K"]
    
    for category in order:
        files = categorized[category]
        if files:
            caption += f"<b>{category}</b>\n"
            for f in files:
                # Format: 📂 HD - 1.4GB
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
        logger.info(f"✅ Post Sent for: {movie_name}")
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

        # Clean Name logic applied here
        clean_name = get_clean_name(file_name)
        
        # Determine Quality Rank for Sorting
        q_rank = 0
        fname_lower = file_name.lower()
        if "2160p" in fname_lower or "4k" in fname_lower: q_rank = 4
        elif "1080p" in fname_lower: q_rank = 3
        elif "720p" in fname_lower: q_rank = 2
        else: q_rank = 1

        file_data = {
            'name': clean_name,
            'year': get_year(file_name),
            'category': get_quality_category(file_name),
            'short_q': get_quality_short(file_name),
            'audio': get_audio(file_name),
            'size': get_size(media.file_size),
            'link': f"https://t.me/{temp.U_NAME}?start=filep_{file_id}",
            'quality_rank': q_rank
        }

        # Add to Batch
        if clean_name not in BATCH_DATA:
            BATCH_DATA[clean_name] = []
        BATCH_DATA[clean_name].append(file_data)

        # Timer Logic (Wait for more files of same movie)
        if clean_name in BATCH_TASKS:
            BATCH_TASKS[clean_name].cancel()

        task = asyncio.create_task(send_batched_post(client, clean_name))
        BATCH_TASKS[clean_name] = task
        
        logger.info(f"⏳ Processing: {clean_name} (Waiting for more versions...)")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
