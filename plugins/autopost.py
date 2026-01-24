import logging
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, UPDATES_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp, get_size

logger = logging.getLogger(__name__)

# --- Details Extract Panra Logic ---

def get_year(filename):
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    return match.group(0) if match else ""

def get_quality(filename):
    filename = filename.lower()
    if "2160p" in filename or "4k" in filename: return "2160p 4K"
    if "1080p" in filename: return "1080p FHD"
    if "720p" in filename: return "720p HD"
    if "480p" in filename: return "480p SD"
    if "360p" in filename: return "360p"
    return "HD" 

def get_print_type(filename):
    filename = filename.lower()
    if "predvd" in filename or "cam" in filename or "scr" in filename: return "PreDVD / CAM"
    if "bluray" in filename: return "BluRay"
    if "web" in filename or "web-dl" in filename: return "WEB-DL"
    if "hdtv" in filename: return "HDTV"
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

def get_clean_name(name):
    # Remove junk tags inside [], (), and specific technical words
    clean = re.sub(r"(\[.*?\]|\{.*?\}|\(.*?\)|720p|1080p|2160p|4k|HEVC|x264|x265|mkv|mp4|avi|www\.|@\w+)", "", name, flags=re.IGNORECASE)
    # Remove Year if sticking to name
    clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

# --- Main Auto Post Logic ---

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def force_auto_post(client, message):
    try:
        # 1. Get Media Details
        media = getattr(message, message.media.value)
        file_id, file_ref = unpack_new_file_id(media.file_id)
        file_name = media.file_name
        
        # 2. Save to DB (Ignore if exists)
        try:
            media.file_type = message.media.value
            media.caption = message.caption
            await save_file(media)
        except:
            pass 

        # 3. Check Channel ID
        if not UPDATES_CHANNEL:
            return

        # 4. Extract All Details
        clean_name = get_clean_name(file_name)
        file_size = get_size(media.file_size)
        year = get_year(file_name)
        audio = get_audio(file_name)
        print_type = get_print_type(file_name)
        quality = get_quality(file_name)
        
        # Format Year (add brackets if exists)
        year_str = f"({year})" if year else ""

        # 5. Generate Direct Bot Link
        # Ithu thaan magic! Text-a Link-a maathum.
        file_link = f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"

        # 6. Stylish Caption Construction
        caption = (
            f"🎬 <b>{clean_name} {year_str}</b>\n"
            f"🔊 <b>Audio:</b> {audio}\n"
            f"💿 <b>Print:</b> {print_type}\n\n"
            f"📥 <b>File:</b> <a href='{file_link}'><b>{quality} - {file_size}</b></a>\n"
            f"<i>(Click the file size to download)</i>"
        )

        # 7. Only One Button (Channel Link)
        # Unga Channel Link inga correct-a irukkanum
        channel_btn = [[InlineKeyboardButton("✨ ᴊᴏɪɴ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇs ✨", url="https://t.me/tamiltechgkofficial")]]

        # 8. Send Message
        await client.send_message(
            chat_id=UPDATES_CHANNEL,
            text=caption,
            reply_markup=InlineKeyboardMarkup(channel_btn)
        )
        logger.info(f"✅ Stylish Post Sent: {clean_name}")

    except Exception as e:
        logger.error(f"❌ Post Error: {e}")
