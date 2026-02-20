import logging
import re
import os
import aiohttp
import time
from datetime import datetime, timedelta
from typing import List, Union
from pyrogram import enums
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from imdb import IMDb
from bs4 import BeautifulSoup
import requests

# Database & Info Imports
from database.users_chats_db import db
from info import (
    LONG_IMDB_DESCRIPTION, MAX_LIST_ELM, VERIFY_EXPIRE, 
    SHORTLINK_URL, SHORTLINK_API, AUTH_USERS, 
    REQUEST_FSUB_MODE, IS_VERIFY
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- GLOBAL VARIABLES ---
imdb = IMDb() 
BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))")
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)
JOIN_REQUEST_USERS = {}

# --- TEMP CLASS ---
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CURRENT = int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    SETTINGS = {}

# --- HELPER FUNCTIONS ---

def get_size(size):
    """Get size in readable format"""
    if not size: return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    size = float(size)
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def humanbytes(size):
    return get_size(size)

def get_file_id(msg: Message):
    if msg.media:
        for message_type in ("photo", "animation", "audio", "document", "video", "video_note", "voice", "sticker"):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name
    elif len(message.command) > 1:
        if len(message.entities) > 1 and message.entities[1].type == enums.MessageEntityType.TEXT_MENTION:
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

def list_to_str(k):
    if not k: return "N/A"
    elif len(k) == 1: return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

# --- PARSER FUNCTIONS ---

def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res

def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)
    key = remove_escapes(text[1:counter].strip())
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])
        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]
    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

# --- VERIFICATION & SHORTLINK LOGIC ---

async def get_shortlink(link):
    if not SHORTLINK_URL or not SHORTLINK_API: return link
    shortener_url = f"https://{SHORTLINK_URL}/api"
    params = {'api': SHORTLINK_API, 'url': link}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(shortener_url, params=params, raise_for_status=True) as response:
                data = await response.json()
                return data["shortenedUrl"]
    except Exception as e:
        logger.error(f"Shortener Error: {e}")
        return link

async def get_short(link):
    return await get_shortlink(link)

# 👇 FIX: Changed argument to match commands.py exactly
async def get_verify_link(user_id, file_id=None):
    if file_id:
        link = f"https://t.me/{temp.U_NAME}?start=verify_{user_id}_{file_id}"
    else:
        link = f"https://t.me/{temp.U_NAME}?start=verify_{user_id}"
    return await get_shortlink(link)

async def verify_user(user_id):
    expiry = datetime.now() + timedelta(seconds=86400) 
    await db.col.update_one(
        {'id': user_id}, 
        {'$set': {'verify_status': {'is_verified': True, 'verify_until': expiry}}}, 
        upsert=True
    )

async def check_verification(client, user_id):
    if not IS_VERIFY: return True
    user = await db.col.find_one({'id': user_id})
    if not user: return False
    verify_status = user.get('verify_status', {})
    expiry = verify_status.get('verify_until')
    if expiry and datetime.now() < expiry: return True 
    return False 

async def get_verify_status(user_id):
    if user_id in AUTH_USERS: return True
    return await check_verification(None, user_id)

# --- SUBSCRIPTION CHECKS ---

async def is_subscribed(user_id: int, client) -> bool:
    auth_channels = await db.get_auth_channels()
    if not auth_channels: return True
    joined_all = True
    for channel in auth_channels:
        try:
            member = await client.get_chat_member(channel, user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                joined_all = False
                break
        except Exception:
            joined_all = False
            break
    if joined_all: return True
    if REQUEST_FSUB_MODE:
        requested_channels = JOIN_REQUEST_USERS.get(user_id, set())
        if set(auth_channels).issubset(requested_channels): return True
    return False

async def create_invite_links(client) -> dict:
    links = {}
    auth_channels = await db.get_auth_channels()
    for channel in auth_channels:
        try:
            invite = await client.create_chat_invite_link(
                channel,
                creates_join_request=REQUEST_FSUB_MODE,
                name="BotAuthAccess"
            )
            links[channel] = invite.invite_link
        except Exception:
            continue
    return links

# --- IMDB & SEARCH ---

async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        title = query
        year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1]) 
        else:
            year = None
        movieid = imdb.search_movie(title.lower(), results=10)
        if not movieid: return None
        if year:
            filtered=list(filter(lambda k: str(k.get('year')) == str(year), movieid))
            if not filtered: filtered = movieid
        else: filtered = movieid
        movieid=list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
        if not movieid: movieid = filtered
        if bulk: return movieid
        movieid = movieid[0].movieID
    else: movieid = query
    movie = imdb.get_movie(movieid)
    if movie.get("original air date"): date = movie["original air date"]
    elif movie.get("year"): date = movie.get("year")
    else: date = "N/A"
    plot = ""
    if not LONG_IMDB_DESCRIPTION:
        plot = movie.get('plot')
        if plot and len(plot) > 0: plot = plot[0]
    else: plot = movie.get('plot outline')
    if plot and len(plot) > 800: plot = plot[0:800] + "..."
    return {
        'title': movie.get('title'),
        'votes': movie.get('votes'),
        "aka": list_to_str(movie.get("akas")),
        "seasons": movie.get("number of seasons"),
        "box_office": movie.get('box office'),
        'localized_title': movie.get('localized title'),
        'kind': movie.get("kind"),
        "imdb_id": f"tt{movie.get('imdbID')}",
        "cast": list_to_str(movie.get("cast")),
        "runtime": list_to_str(movie.get("runtimes")),
        "countries": list_to_str(movie.get("countries")),
        "certificates": list_to_str(movie.get("certificates")),
        "languages": list_to_str(movie.get("languages")),
        "director": list_to_str(movie.get("director")),
        "writer":list_to_str(movie.get("writer")),
        "producer":list_to_str(movie.get("producer")),
        "composer":list_to_str(movie.get("composer")) ,
        "cinematographer":list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_str(movie.get("genres")),
        'poster': movie.get('full-size cover url'),
        'plot': plot,
        'rating': str(movie.get("rating")),
        'url':f'https://www.imdb.com/title/tt{movieid}'
    }

async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
        }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all( 'h3' )
    return [title.getText() for title in titles]

async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"
