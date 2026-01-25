import logging
import asyncio
import re
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, UPDATES_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp, get_size

logger = logging.getLogger(__name__)

# ================= CONFIG =================
OMDB_API_KEY = ""  # optional, empty na Google verify skip
WAIT_TIME = 30

# ================= STORAGE =================
BATCH_DATA = {}
BATCH_TASKS = {}

# ================= CLEANERS =================

def get_year(filename):
    m = re.search(r'\b(19|20)\d{2}\b', filename)
    return m.group(0) if m else "N/A"

def clean_base_name(filename):
    name = filename.lower()

    # 1. remove extension
    name = re.sub(r'\.(mkv|mp4|avi|flv|webm)$', '', name)

    # 2. remove year
    name = re.sub(r'\b(19|20)\d{2}\b', '', name)

    # 3. remove size & bitrate
    name = re.sub(r'\b\d+(\.\d+)?\s?(gb|mb|kb)\b', '', name)

    # 4. remove quality / format / subtitle / audio junk
    junk_patterns = [
        r'\b(2160p|4k|1080p|720p|480p|hdrip|bluray|web[- ]?dl|hq)\b',
        r'\b(esub|sub|subs)\b',
        r'\b(ddp?5\.?1?|aac|ac3|dts|eac3)\b',
        r'\b(x264|x265|hevc|avc)\b',
        r'\b(uncut|extended|proper|remastered)\b',
        r'\b(tamil|telugu|hindi|malayalam|english|multi|dual)\b',
        r'\b(mkv|mp4)\b'
    ]

    for p in junk_patterns:
        name = re.sub(p, '', name)

    # 5. remove channel / uploader junk
    channels = [
        "goku stark", "gokustark", "@gokustark",
        "trollmaa", "backup tamil movies"
    ]
    for ch in channels:
        name = name.replace(ch, '')

    # 6. remove symbols
    name = re.sub(r'[^a-z0-9 ]', ' ', name)

    # 7. normalize spaces
    name = re.sub(r'\s+', ' ', name).strip()

    return name.title()



def get_quality_category(filename):
    f = filename.lower()
    if "2160p" in f or "4k" in f: return "4K"
    if "1080p" in f: return "FULL HD"
    if "720p" in f: return "Only HD"
    return "HD-Rip"


def get_quality_short(filename):
    f = filename.lower()
    if "2160p" in f or "4k" in f: return "4K"
    if "1080p" in f: return "FHD"
    if "720p" in f: return "HD"
    return "HD-Rip"


def get_audio(filename):
    f = filename.lower()
    audio = []
    if "tamil" in f: audio.append("Tamil")
    if "telugu" in f: audio.append("Telugu")
    if "hindi" in f: audio.append("Hindi")
    if "malayalam" in f: audio.append("Malayalam")
    if "eng" in f: audio.append("English")
    if "multi" in f or "dual" in f: audio.append("Multi Audio")
    return " - ".join(audio) if audio else "Original Audio"


# ================= OMDB (OPTIONAL) =================

def fetch_movie_title(title, year):
    if not OMDB_API_KEY:
        return title, year

    try:
        url = f"http://www.omdbapi.com/?t={title}&y={year}&apikey={OMDB_API_KEY}"
        r = requests.get(url, timeout=5).json()
        if r.get("Response") == "True":
            return r["Title"], r["Year"]
    except:
        pass

    return title, year


# ================= BATCH SENDER =================

async def send_batched_post(client, group_key):
    try:
        await asyncio.sleep(WAIT_TIME)
    except asyncio.CancelledError:
        return

    if group_key not in BATCH_DATA:
        return

    files = BATCH_DATA.pop(group_key)
    BATCH_TASKS.pop(group_key, None)

    # true dedupe (link based)
    unique = []
    seen = set()
    for f in files:
        if f['link'] not in seen:
            unique.append(f)
            seen.add(f['link'])

    if not unique:
        return

    categorized = {"HD-Rip": [], "Only HD": [], "FULL HD": [], "4K": []}
    for f in unique:
        categorized[f['category']].append(f)

    first = unique[0]

    caption = (
        f"🎬 <b>{first['title']}</b>\n"
        f"🗓️ <b>Year:</b> {first['year']}\n"
        f"🔊 <b>Audio:</b> {first['audio']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )

    order = ["HD-Rip", "Only HD", "FULL HD", "4K"]
    has_files = False

    for cat in order:
        if categorized[cat]:
            has_files = True
            caption += f"<b>{cat}</b>\n"
            for f in categorized[cat]:
                caption += f"📂 <a href='{f['link']}'><b>{f['short_q']} - {f['size']}</b></a>\n"
            caption += "\n"

    if not has_files:
        return

    caption += "━━━━━━━━━━━━━━━━━━━\n<i>(Click file size to download)</i>"

    btn = [[InlineKeyboardButton("✨ Join Movie Updates ✨", url="https://t.me/tamiltechgkofficial")]]

    await client.send_message(
        chat_id=UPDATES_CHANNEL,
        text=caption,
        reply_markup=InlineKeyboardMarkup(btn)
    )

    logger.info(f"✅ Sent: {group_key}")


# ================= MAIN HANDLER =================

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_handler(client, message):
    media = getattr(message, message.media.value)
    file_id, _ = unpack_new_file_id(media.file_id)
    file_name = media.file_name

    try:
        media.file_type = message.media.value
        media.caption = message.caption
        await save_file(media)
    except:
        pass

    base = clean_base_name(file_name)
    year = get_year(file_name)
    title, year = fetch_movie_title(base, year)

    group_key = f"{title} ({year})"

    file_data = {
        "title": title,
        "year": year,
        "category": get_quality_category(file_name),
        "short_q": get_quality_short(file_name),
        "audio": get_audio(file_name),
        "size": get_size(media.file_size),
        "link": f"https://t.me/{temp.U_NAME}?start=filep_{file_id}"
    }

    BATCH_DATA.setdefault(group_key, []).append(file_data)

    if group_key in BATCH_TASKS:
        BATCH_TASKS[group_key].cancel()

    BATCH_TASKS[group_key] = asyncio.create_task(
        send_batched_post(client, group_key)
    )

    logger.info(f"⏳ Grouping: {group_key}")
