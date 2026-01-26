import re
import logging
from pyrogram import Client, filters
from info import CHANNELS

# 👇 LOGS SETUP
logger = logging.getLogger(__name__)

# 👇 INGA UNGA PUTHU CHANNEL ID PODUNGA
LOG_CHANNEL_ID = -1003602676231 

def get_name_with_year(name):
    if not name: return "Unknown File"
    clean = name.lower()
    
    # 1. Remove Usernames first (MUKKIYAM)
    clean = clean.replace("@goku stark", "")
    clean = clean.replace("goku stark", "")
    
    # 2. YEAR LOGIC: (1990 - 2029) varaikum Year iruntha kandupudikkum
    # Year kidaichathum, athuku apuram irukka ellathayum cut pannidum.
    match = re.search(r'\b(19|20)\d{2}\b', clean)
    
    if match:
        # Year iruntha: Start muthal Year mudiyum varaikum edukkum
        # Example: "Leo 2023 1080p.mkv" -> "Leo 2023"
        end_index = match.end()
        clean = clean[:end_index]
    else:
        # Year illana mattum: Extension & Junk words remove pannum
        clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
        junk_words = ["hq", "predvd", "clean", "proper", "1080p", "720p", "480p", "hdrip"]
        for word in junk_words:
            clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)

    # 3. Final Polish: Brackets & Symbols removal
    clean = re.sub(r'[\[\(\)\}\]]', '', clean) # Brackets removal
    clean = re.sub(r'[-_./@|:+]', ' ', clean)  # Symbols to space
    clean = re.sub(r'\s+', ' ', clean).strip() # Extra spaces removal
    
    return clean.title()

# 👇 GROUP ID 10
@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio), group=10)
async def alert_handler(client, message):
    try:
        media = getattr(message, message.media.value)
        filename = message.caption if message.caption else media.file_name
        
        # Clean Name with Year
        clean_name = get_name_with_year(filename)
        
        # Output: "Leo 2023 Added ✅"
        text = f"<b>{clean_name} Added ✅</b>"
        
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text
        )
        logger.info(f"✅ Alert Sent: {clean_name}")
        
    except Exception as e:
        logger.error(f"❌ Alert Error: {e}")
