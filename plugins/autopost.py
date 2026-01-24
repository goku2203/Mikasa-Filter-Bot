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

# --- 1. SMART NAME CLEANER (Google Style) ---
def get_clean_name(name):
    # 1. Lowercase
    clean = name.lower()
    
    # 2. Remove Specific Junk (Unga Channel Name & Ext)
    clean = clean.replace("goku stark", "")
    clean = clean.replace("@goku_stark", "")
    clean = clean.replace("trollmaa", "")
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean) # Remove .mkv
    
    # 3. Remove Year (to group same movies)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    
    # 4. Remove Tags inside [], ()
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\(.*?\)', '', clean)
    
    # 5. Remove Common Quality/Lang Tags (Aggressive Cleaning)
    keywords = [
        "tamil", "telugu", "hindi", "malayalam", "kannada", "english", "eng", "tam", "tel", "hin",
        "hq", "hdrip", "bluray", "web-dl", "web", "hd", "cam", "predvd", "dvdscr", "rip",
        "1080p", "720p", "480p", "2160p", "4k", "5.1", "aac", "x264", "x265", "hevc", "esub", "sub",
        "remastered", "bd", "dual", "multi", "audio"
    ]
    for word in keywords:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)
    
    # 6. Remove Special Characters & Extra Spaces
    clean = re.sub(r'[-_./@|]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # 7. Title Case (First Letter Capital)
    return clean.title()

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

# --- 2. BATCH SENDER (Duplicate Remover) ---

async def send_batched_post(client, clean_name):
    # Wait 10s for all files to arrive
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        return 

    if clean_name not in BATCH_DATA:
        return

    # Pop Data
    raw_files_list = BATCH_DATA.pop(clean_name)
    if clean_name in BATCH_TASKS:
        del BATCH_TASKS[clean_name]

    # --- DUPLICATE REMOVAL LOGIC ---
    # Ore size iruntha delete pannidum
    unique_files = []
    seen_sizes = set()
    
    for f in raw_files_list:
        if f['size'] not in seen_sizes:
            unique_files.append(f)
            seen_sizes.add(f['size'])
            
    if not unique_files:
        return

    # Sort: Highest Quality First
    unique_files.sort(key=lambda x: x['quality'], reverse=True)

    # Extract Details
    first_file = unique_files[0]
    movie_name = clean_name  # Use Clean Name (No junk)
    year = first_file['year']
    audio = first_file['audio']

    # --- FINAL STYLE ---
    caption = (
        f"🎥 <b>{movie_name}</b>\n"
        f"📅 <b>Year:</b> {year}\n"
        f"🎧 <b>Audio:</b> {audio}\n"
        f"──────────────────\n"
    )

    for file in unique_files:
        # Link Format: 📂 720p HD [1.4GB]
        caption += f"📂 <a href='{file['link']}'><b>{file['quality']} [{file['size']}]</b></a>\n"

    caption += "──────────────────\n"
    caption += "<i>(Click the file size to download)</i>"

    channel_btn = [[InlineKeyboardButton("✨ ᴊᴏɪɴ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇs ✨", url="https://t.me/tamiltechgkofficial")]]

    try:
        await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption,
            reply_markup=InlineKeyboardMarkup(channel_btn)
        )
        logger.info(f"✅ Group Post Sent: {movie_name} ({len(unique_files)} Files)")
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

        # Clean Name for Grouping
        clean_name = get_clean_name(file_name)
        
        file_data = {
            'name': clean_name,
            'year': get_year(file_name),
            'quality': get_quality(file_name),
            'audio': get_audio(file_name),
            'size': get_size(media.file_size),
            'link': f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"
        }

        # Add to Batch
        if clean_name not in BATCH_DATA:
            BATCH_DATA[clean_name] = []
        BATCH_DATA[clean_name].append(file_data)

        # Reset Timer
        if clean_name in BATCH_TASKS:
            BATCH_TASKS[clean_name].cancel()

        task = asyncio.create_task(send_batched_post(client, clean_name))
        BATCH_TASKS[clean_name] = task
        
        logger.info(f"⏳ Grouping file: {clean_name}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
