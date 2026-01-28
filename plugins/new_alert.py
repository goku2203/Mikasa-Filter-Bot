import re
import time
import logging
from pyrogram import Client, filters
from info import CHANNELS

# 👇 LOGS SETUP
logger = logging.getLogger(__name__)

# ⚠️ Unga Channel ID Inga Podunga
LOG_CHANNEL_ID = -1001234567890 

# DUPLICATE CHECK MEMORY
LAST_SENT = {} 

def get_name_with_year(name):
    if not name: return "Unknown File"
    clean = name.lower()
    
    # 1. UNIVERSAL GOKU STARK REMOVER 🛠️
    # Ithu '@Goku Stark', 'Goku_Stark', '[Goku Stark]' ellathayum remove pannum
    clean = re.sub(r'(?i)(?:\[|\(|@)?\s*goku[\s._-]*stark\s*(?:\]|\))?', '', clean)
    
    # 2. Remove Junk Characters at Start (Like - or ] or space)
    # "Goku Stark" remove panna apuram munaadi "- " ninna athayum thookidum
    clean = re.sub(r'^[\s\-_\[\]\(\)\.]+', '', clean)

    # 3. YEAR LOGIC
    match = re.search(r'\b(19[5-9][0-9]|20[0-3][0-9])\b', clean)
    
    if match:
        end_index = match.end()
        clean = clean[:end_index]
    else:
        clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
        junk_words = ["hq", "predvd", "clean", "proper", "1080p", "720p", "480p", "hdrip"]
        for word in junk_words:
            clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)

    # 4. Final Polish
    clean = re.sub(r'[\[\(\)\}\]]', '', clean)
    clean = re.sub(r'[-_./@|:+]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return clean.title()

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio), group=10)
async def alert_handler(client, message):
    try:
        media = getattr(message, message.media.value)
        filename = message.caption if message.caption else media.file_name
        
        # Clean Name Edukkurom
        clean_name = get_name_with_year(filename)
        
        # Check if name became empty after cleaning
        if not clean_name:
            clean_name = "Unknown Movie"

        # --- DUPLICATE FILTER LOGIC ---
        current_time = time.time()
        
        if clean_name in LAST_SENT:
            last_time = LAST_SENT[clean_name]
            # 5 Minutes Time Gap
            if current_time - last_time < 300:
                return

        # Output Text
        text = f"<b>{clean_name} Added ✅</b>"
        
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text
        )
        
        LAST_SENT[clean_name] = current_time
        
    except Exception as e:
        logger.error(f"❌ Alert Error: {e}")
        
