import re
import asyncio
from pyrogram import Client, filters
from info import CHANNELS

# 👇 INGA UNGA PUTHU CHANNEL ID PODUNGA (Ex: -100xxxxxx)
LOG_CHANNEL_ID = -1003602676231 

def get_simple_name(name):
    if not name: return "Unknown File"
    clean = name.lower()
    
    # 1. Extension Remove panrom
    clean = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', clean)
    
    # 2. Junk words remove panrom (Quality tags)
    junk_words = [
        "1080p", "720p", "480p", "hdrip", "web-dl", "bluray", 
        "x264", "x265", "hevc", "aac", "esub", "hindi", "tamil", "telugu", "dual"
    ]
    for word in junk_words:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean)
        
    # 3. Dots and underscores to space
    clean = re.sub(r'[._-]', ' ', clean)
    
    # 4. Brackets remove panrom (Optional - Year irukkanum na ithai adjust pannalam)
    # Ithu (2022) nu iruntha brackets eduthuttu 2022 nu vakkum
    clean = re.sub(r'[\[\(\)\}]', '', clean)
    
    return clean.strip().title()

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def alert_handler(client, message):
    try:
        # File details edukkurom
        media = getattr(message, message.media.value)
        filename = message.caption if message.caption else media.file_name
        
        # Name-a clean panrom
        clean_name = get_simple_name(filename)
        
        # Message Ready panrom: "Leo 2022 Added ✅"
        text = f"<b>{clean_name} Added ✅</b>"
        
        # Puthu channel-ku send panrom
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text
        )
        
    except Exception as e:
        print(f"Alert Error: {e}")
