import logging
import asyncio
import re
import os
from pyrogram import Client, filters
from info import CHANNELS, UPDATES_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp, get_size

logger = logging.getLogger(__name__)

# --- SETTINGS ---
# 3 Hours = 3 * 60 * 60 = 10800 Seconds
AUTO_DELETE_TIME = 10800 

# --- BATCH STORAGE ---
BATCH_DATA = {}
BATCH_TASKS = {} 

# --- 1. AUTO DELETE FUNCTION ---
async def delete_post_after_delay(client, chat_id, message_id):
    try:
        # Wait for 3 Hours
        await asyncio.sleep(AUTO_DELETE_TIME)
        # Delete Message
        await client.delete_messages(chat_id, message_id)
        logger.info(f"🗑️ Auto Deleted Post: {message_id} in {chat_id}")
    except Exception as e:
        logger.error(f"❌ Failed to Delete Post: {e}")

# --- 2. SMART INFO EXTRACTORS ---

def get_audio(filename):
    if not filename: return "Original Audio"
    filename = filename.lower()
    audio = []
    
    if re.search(r'\b(tam|tamil)\b', filename): audio.append("Tamil")
    if re.search(r'\b(tel|telugu)\b', filename): audio.append("Telugu")
    if re.search(r'\b(hin|hindi)\b', filename): audio.append("Hindi")
    if re.search(r'\b(mal|malayalam)\b', filename): audio.append("Malayalam")
    if re.search(r'\b(kan|kannada)\b', filename): audio.append("Kannada")
    if re.search(r'\b(eng|english)\b', filename): audio.append("English")
    
    if "multi" in filename or "dual" in filename: 
        if not audio: audio.append("Multi Audio")
    
    return " - ".join(audio) if audio else "Original Audio"

def get_clean_name(name):
    if not name: return ""
    clean = name.lower()
    
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    
    junk_list = [
        "@goku_stark", "goku stark", "trollmaa", "@skmain1", "skmain1", 
        "backup - tamil movies", "gokustark", "@gokustark", "www.", ".com"
    ]
    for junk in junk_list:
        clean = clean.replace(junk, "")

    clean = re.sub(r'[\[\(\{].*?[\]\)\}]', '', clean)
    clean = re.sub(r'\b\d{3,4}mb\b', '', clean)
    clean = re.sub(r'\b\d+(\.\d+)?gb\b', '', clean)

    junk_words = [
        "2160p", "4k", "1080p", "720p", "480p", "360p", 
        "hdrip", "hq", "hd", "bd", "bluray", "blu-ray", "br-rip", "brrip", "web-dl", "web",
        "dvdscr", "dvd", "cam", "hdcam", "proper", "true", "avc", "remastered", 
        "uncut", "extended", "dual", "multi", "audio", "esubs", "esub", "x264", "x265", "hevc",
        "dd5.1", "dd+", "aac", "ac3"
    ]
    for word in junk_words:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)

    langs = ["tamil", "telugu", "hindi", "english", "tam", "tel", "hin", "eng", "malayalam", "kannada"]
    for lang in langs:
        clean = re.sub(r'\b' + re.escape(lang) + r'\b', '', clean)

    clean = re.sub(r'[-_./@|:+]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.title()

def get_year(filename):
    if not filename: return "N/A"
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    return match.group(0) if match else "N/A"

def get_quality_category(filename):
    if not filename: return "HD-Rip"
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "4K"
    if "1080p" in filename: return "FULL HD"
    if "720p" in filename: return "Only HD"
    return "HD-Rip" 

def get_quality_short(filename):
    if not filename: return "HD-Rip"
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "4K"
    if "1080p" in filename: return "FHD"
    if "720p" in filename: return "HD"
    return "HD-Rip"

# --- 3. BATCH SENDER ---

async def send_batched_post(client, clean_name):
    try:
        await asyncio.sleep(30)
    except asyncio.CancelledError:
        return 

    if clean_name not in BATCH_DATA:
        return

    raw_files_list = BATCH_DATA.pop(clean_name)
    if clean_name in BATCH_TASKS:
        del BATCH_TASKS[clean_name]

    unique_files = []
    seen_sizes = set()
    for f in raw_files_list:
        if f['size'] not in seen_sizes:
            unique_files.append(f)
            seen_sizes.add(f['size'])
            
    if not unique_files:
        return

    all_audios = set()
    first_file = unique_files[0]
    for f in unique_files:
        langs = f['audio'].split(' - ')
        for l in langs:
            if l != "Original Audio":
                all_audios.add(l)
    
    if all_audios:
        priority = ['Tamil', 'Telugu', 'Hindi', 'Malayalam', 'Kannada', 'English']
        sorted_audios = sorted(all_audios, key=lambda x: priority.index(x) if x in priority else 99)
        final_audio_str = " - ".join(sorted_audios)
    else:
        final_audio_str = first_file['audio']

    categorized = { "4K": [], "FULL HD": [], "Only HD": [], "HD-Rip": [] }
    for file in unique_files:
        cat = file['category']
        if cat in categorized:
            categorized[cat].append(file)
        else:
            categorized["HD-Rip"].append(file)

    caption = (
        f"🎬 <b>{clean_name}</b>\n"
        f"🗓️ <b>Year:</b> {first_file['year']}\n"
        f"🔊 <b>Audio:</b> {final_audio_str}\n"
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
    caption += "<i>(Click the file size to download)</i>\n\n"
    caption += "<b><a href='https://t.me/+buF9u_rT7o5mMmRl'>by Own Channel</a></b>"

    try:
        # Send Message
        sent_msg = await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption
        )
        logger.info(f"✅ Post Sent: {clean_name}")
        
        # --- SCHEDULE AUTO DELETE ---
        asyncio.create_task(delete_post_after_delay(client, UPDATES_CHANNEL, sent_msg.id))
        
    except Exception as e:
        logger.error(f"❌ Post Failed: {e}")

# --- 4. MAIN LISTENER ---

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_handler(client, message):
    try:
        media = getattr(message, message.media.value)
        file_id, file_ref = unpack_new_file_id(media.file_id)
        
        raw_name = message.caption if message.caption else media.file_name
        
        try:
            media.file_type = message.media.value
            media.caption = message.caption
            await save_file(media)
        except:
            pass 

        if not UPDATES_CHANNEL:
            return

        clean_name = get_clean_name(raw_name)
        
        file_data = {
            'name': clean_name,
            'year': get_year(raw_name),
            'category': get_quality_category(raw_name),
            'short_q': get_quality_short(raw_name),
            'audio': get_audio(raw_name),
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
        
        logger.info(f"⏳ Grouping: {clean_name}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
