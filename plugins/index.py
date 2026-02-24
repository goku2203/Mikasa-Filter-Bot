import logging
import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, LOG_CHANNEL, CHANNELS, UPDATES_CHANNEL, PICS
from database.ia_filterdb import save_file, Media, unpack_new_file_id, get_search_results
from utils import temp, get_size
from database.users_chats_db import db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

# Helper Function for Clean Name
def get_clean_name(name):
    clean = re.sub(r"(\[.*?\]|\{.*?\}|\(.*?\)|720p|1080p|480p|HEVC|x264|x265|mkv|mp4|avi|www\.|@\w+)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.lower()

# ====================================================
# 👇👇 THIS IS THE MAIN AUTO INDEX & POST FUNCTION 👇👇
# ====================================================

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media(client, message):
    """
    Automatic-a File-a Save pannum & Updates Channel-la Post podum.
    """
    try:
        # 1. Save to Database
        # -------------------
        for file_type in ("document", "video", "audio"):
            media = getattr(message, file_type, None)
            if media is not None:
                break
        else:
            return

        media.file_type = file_type
        media.caption = message.caption

        # Save File
        await save_file(media)
        logger.info(f"✅ Auto Index: File Saved -> {media.file_name}")

        # 2. Post to Updates Channel
        # --------------------------
        if not UPDATES_CHANNEL:
            return

        file_name = media.file_name
        clean_name = get_clean_name(file_name)
        file_size = get_size(media.file_size)
        file_id = media.file_id

        # Simple Caption
        caption = (
            f"<b>📂 New File Uploaded!</b>\n\n"
            f"<b>🎬 Name:</b> {clean_name.upper()}\n"
            f"<b>💾 Size:</b> {file_size}\n"
            f"<b>📁 Original Name:</b> <code>{file_name}</code>\n\n"
            f"<i>Get this file from the bot! 👇</i>"
        )

        # Button
        btn = [[InlineKeyboardButton("📥 Get File", url=f"https://t.me/{temp.U_NAME}?start=filep_{file_id}")]]

        # Send Message
        try:
            await client.send_message(
                chat_id=UPDATES_CHANNEL,
                text=caption,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            logger.info(f"✅ Auto Post Sent: {clean_name}")
        except Exception as e:
            logger.error(f"❌ Auto Post Failed: {e}")

    except Exception as e:
        logger.error(f"❌ Auto Index Error: {e}")

# ====================================================
# 👇👇 MANUAL INDEXING CODE (Optimized for No Lag) 👇👇
# ====================================================

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(int(from_user),
                               f'Your Submission for indexing {chat} has been decliened by our moderators.',
                               reply_to_message_id=int(lst_msg_id))
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    # 🟢 FIX 1: Answer Query Immediately to Stop Loading Animation
    await query.answer('Processing...⏳', show_alert=True)
    
    if int(from_user) not in ADMINS:
        await bot.send_message(int(from_user),
                               f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',
                               reply_to_message_id=int(lst_msg_id))
    await msg.edit(
        "Starting Indexing... Please Wait.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
        
    # 🟢 FIX 2: Background Task - Ithu bot-a block pannama background la run aaga vekkum
    asyncio.create_task(index_files_to_db(int(lst_msg_id), chat, msg, bot))


@Client.on_message((filters.forwarded | (filters.regex("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text ) & filters.private & filters.incoming)
async def send_for_index(bot, message):
    if message.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(message.text)
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await message.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    if k.empty:
        return await message.reply('This may be group and iam not a admin of the group.')

    if message.from_user.id in ADMINS:
        buttons = [
            [
                InlineKeyboardButton('Yes',
                                     callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
            ],
            [
                InlineKeyboardButton('close', callback_data='close_data'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup)

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [
        [
            InlineKeyboardButton('Accept Index',
                                 callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],
        [
            InlineKeyboardButton('Reject Index',
                                 callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(LOG_CHANNEL,
                           f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',
                           reply_markup=reply_markup)
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("Skip number should be an integer.")
        await message.reply(f"Successfully set SKIP number as {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply("Give me a skip number")

async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0

    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            
            # 🟢 FIX 3: Reduced chunk size to prevent Memory Crashes (RAM problems)
            CHUNK_SIZE = 100 
            
            while current <= lst_msg_id:
                if temp.CANCEL:
                    await msg.edit(f"Successfully Cancelled!!\n\nSaved <code>{total_files}</code> files to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>")
                    break
                
                end_msg_id = min(current + CHUNK_SIZE - 1, lst_msg_id)
                msg_ids_to_fetch = list(range(current, end_msg_id + 1))
                
                try:
                    messages = await bot.get_messages(chat, msg_ids_to_fetch)
                except FloodWait as e:
                    logger.warning(f"FloodWait encountered: sleeping for {e.value} seconds.")
                    await asyncio.sleep(e.value)
                    continue 
                except Exception as fetch_error:
                    logger.error(f"Error fetching chunk: {fetch_error}")
                    errors += len(msg_ids_to_fetch)
                    current = end_msg_id + 1
                    # Breathing space for the bot
                    await asyncio.sleep(0.5) 
                    continue
                
                for message in messages:
                    if temp.CANCEL:
                        break 
                        
                    # 🟢 FIX 4: YIELD - Ithu bot freeze aagura prechanaiya 100% thadukkum!
                    await asyncio.sleep(0.01)
                    
                    current_msg_id = message.id if message and not message.empty else 0
                    
                    if current % 100 == 0: 
                        can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                        reply = InlineKeyboardMarkup(can)
                        try:
                             await msg.edit_text(
                                 text=f"Total messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nErrors Occurred: <code>{errors}</code>",
                                 reply_markup=reply)
                        except MessageNotModified:
                            pass 
                        except FloodWait as fw:
                             await asyncio.sleep(fw.value)
                    
                    if message is None or message.empty:
                        deleted += 1
                        continue
                    elif not message.media:
                        no_media += 1
                        continue
                    elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                        unsupported += 1
                        continue
                    
                    media = getattr(message, message.media.value, None)
                    if not media:
                        unsupported += 1
                        continue
                        
                    media.file_type = message.media.value
                    media.caption = message.caption
                    
                    aynav, vnay = await save_file(media)
                    if aynav:
                        total_files += 1
                    elif vnay == 0:
                        duplicate += 1
                    elif vnay == 2:
                        errors += 1
                
                current = end_msg_id + 1
                
                # 🟢 FIX 5: Extra Breathing space - Start command lag varama irukka
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')
        else:
            if not temp.CANCEL:
                 await msg.edit(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nErrors Occurred: <code>{errors}</code>')
