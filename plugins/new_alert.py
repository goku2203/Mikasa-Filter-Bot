import re
import time
import logging
from pyrogram import Client, filters
from info import CHANNELS

# 👇 LOGS SETUP
logger = logging.getLogger(__name__)

# 👇 INGA UNGA PUTHU CHANNEL ID PODUNGA
LOG_CHANNEL_ID = -1003602676231 

# 👇 DUPLICATE CHECK MEMORY
# Ithu oru chinna memory mathiri, anupuna padatha nyabagam vachikkum
LAST_SENT = {} 

def get_name_with_year(name):
    if not name: return "Unknown File"
    clean = name.lower()
    
    # 1. Goku Stark Removal (More Powerful)
    # Case insensitive-a start-la irukka 'goku stark' remove pannum
    clean = re.sub(r'(?i)^\s*@?goku\s*stark\s*', '', clean)
    clean = clean.replace("goku stark", "") 
    
    # 2. YEAR LOGIC (1950 - 2030)
    match = re.search(r'\b(19[5-9][0-9]|20[0-3][0-9])\b', clean)
    
    if match:
        end_index = match.end()
        clean = clean[:end_index]
    else:
        # Year illana extension & junk remove pannuvom
        clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
        junk_words = ["hq", "predvd", "clean", "proper", "1080p", "720p", "480p", "hdrip"]
        for word in junk_words:
            clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)

    # 3. Final Polish
    clean = re.sub(r'[\[\(\)\}\]]', '', clean)
    clean = re.sub(r'[-_./@|:+]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return clean.title()

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio), group=10)
async def alert_handler(client, message):
    try:
        # --- CHANGE START ---
        ANIME_CHANNEL_ID = -1002591922002 # Replace with UR Anime Channel ID

        if message.chat.id == ANIME_CHANNEL_ID:
            return # Anime channel na Alert anupa vendam, Bye!
        # --- CHANGE END ---

        media = getattr(message, message.media.value)
        filename = message.caption if message.caption else media.file_name
        
        # ... (Meethi code apdiye irukattum) ...
        
        # Clean Name Edukkurom
        clean_name = get_name_with_year(filename)
        
        # --- DUPLICATE FILTER LOGIC START ---
        current_time = time.time()
        
        # Already intha padam 5 mins (300 seconds) ulla anupiruntha, SKIP pannidum
        if clean_name in LAST_SENT:
            last_time = LAST_SENT[clean_name]
            if current_time - last_time < 300:  # 300 Seconds = 5 Minutes
                logger.info(f"🚫 Duplicate Skipped: {clean_name}")
                return

        # Puthu padam na, time-a note pannikkum
        LAST_SENT[clean_name] = current_time
        # --- DUPLICATE FILTER LOGIC END ---

        # Output Text
        text = f"<b>{clean_name} Added ✅</b>"
        
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text
        )
        logger.info(f"✅ Alert Sent: {clean_name}")
        
    except Exception as e:
        logger.error(f"❌ Alert Error: {e}")
