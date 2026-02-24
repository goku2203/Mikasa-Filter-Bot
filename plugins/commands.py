# Force Update v2.0 - Confirm New Code
import os
import logging
import random
import asyncio
import re
import json
import base64
from datetime import datetime, timedelta
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id, get_search_results
from database.users_chats_db import db
from info import CHANNELS, ADMINS, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, FILE_CHANNELS, FILE_CHANNEL_SENDING_MODE, FILE_AUTO_DELETE_SECONDS, IS_VERIFY, UPDATES_CHANNEL, BOT_USERNAME
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp, create_invite_links, get_verify_link, check_verification, verify_user
from database.connections_mdb import active_connection

logger = logging.getLogger(__name__)

BATCH_FILES = {}
AUTO_DELETE_SECONDS = 15

# 🟢 CACHE FIX: Bot lag aagama irukka link ah save panni vechukkum
INVITE_LINK_CACHE = {}

async def create_file_buttons(client, sent_message):
    buttons = []
    if sent_message.chat.username:
        message_link = f"https://t.me/{sent_message.chat.username}/{sent_message.id}"
        buttons.append([InlineKeyboardButton("🔗 View File", url=message_link)])
        return InlineKeyboardMarkup(buttons)
    else:
        channel_id = str(sent_message.chat.id).replace('-100', '')
        message_link = f"https://t.me/c/{channel_id}/{sent_message.id}"
    
    try:
        chat_id = sent_message.chat.id
        if chat_id not in INVITE_LINK_CACHE:
            chat = await client.get_chat(chat_id)
            if chat.username:
                INVITE_LINK_CACHE[chat_id] = f"https://t.me/{chat.username}"
            else:
                invite = await client.create_chat_invite_link(chat_id)
                INVITE_LINK_CACHE[chat_id] = invite.invite_link
        
        invite_link = INVITE_LINK_CACHE[chat_id]
        buttons.append([InlineKeyboardButton("📢 Join Channel to View", url=invite_link)])
        buttons.append([InlineKeyboardButton("🔗 View File", url=message_link)])
    except Exception as e:
        logger.error(f"Error creating invite: {e}")
        buttons.append([InlineKeyboardButton("🔗 View File", url=message_link)])
    
    return InlineKeyboardMarkup(buttons)

async def auto_delete_message(client, message, delay):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

async def auto_delete_file(client, message, delay):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

async def send_file_to_user(client, user_id, file_id, protect_content_flag, file_name=None, file_size=None, file_caption=None):
    try:
# 👇 PUDHU REPLACE LOGIC INGA START AAGUTHU 👇
        import re
        # "goku stark" illana "@goku stark" epdi irunthalum atha "@goku_stark" nu mathidum
        if file_name:
            file_name = re.sub(r'@?goku\s+stark', '@goku_stark', file_name, flags=re.IGNORECASE)
        if file_caption:
            file_caption = re.sub(r'@?goku\s+stark', '@goku_stark', file_caption, flags=re.IGNORECASE)
        # 👆 --------------------------------------- 👆
        caption = file_caption if file_caption else file_name
        if CUSTOM_FILE_CAPTION:
            try:
                caption = CUSTOM_FILE_CAPTION.format(file_name=file_name or "", file_size=file_size or "", file_caption=file_caption or "")
            except: pass

        if FILE_CHANNEL_SENDING_MODE and FILE_CHANNELS:
            channel_id = random.choice(FILE_CHANNELS)
            sent_message = await client.send_cached_media(chat_id=channel_id, file_id=file_id, caption=caption, protect_content=protect_content_flag)
            asyncio.create_task(auto_delete_file(client, sent_message, FILE_AUTO_DELETE_SECONDS))
            reply_markup = await create_file_buttons(client, sent_message)
            user_msg = await client.send_message(chat_id=user_id, text=f"**Your file is ready!**\n\nJoin the channel to view your file ", protect_content=True, reply_markup=reply_markup)
            asyncio.create_task(auto_delete_message(client, user_msg, AUTO_DELETE_SECONDS))
        else:
            msg = await client.send_cached_media(chat_id=user_id, file_id=file_id, caption=caption, protect_content=protect_content_flag)
            asyncio.create_task(auto_delete_file(client, msg, 120)) 
    except Exception as e:
        logger.error(f"File send error: {e}")

@Client.on_callback_query(filters.regex(r'^checksubp#') | filters.regex(r'^checksub#'))
async def checksub_callback(client, callback_query):
    await callback_query.answer("Sending File... ⏳", show_alert=False)
    data = callback_query.data
    pre, file_id = data.split('#', 1)
    user_id = callback_query.from_user.id
    protect_content_flag = True if pre == 'checksubp' else False

    files = await get_file_details(file_id)
    file_details = files[0] if files else None
    
    if await is_subscribed(user_id, client):
        try:
            await send_file_to_user(client, user_id, file_id, protect_content_flag, file_details.file_name if file_details else None, get_size(file_details.file_size) if file_details else None, file_details.caption if file_details else None)
            await callback_query.message.delete()
        except: pass
    else:
        links = await create_invite_links(client)
        btn = [[InlineKeyboardButton("🤖 Join Updates Channel", url=url)] for url in links.values()]
        btn.append([InlineKeyboardButton("🔄 Try Again", callback_data=data)])
        await callback_query.edit_message_text("**❌ You still haven't joined all channels!**\n\nPlease join and press Try Again:", reply_markup=InlineKeyboardMarkup(btn))


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [[InlineKeyboardButton("⛩️ ᴀɴɪᴍᴇ ᴡᴏʀʟᴅ", url="https://t.me/Anime_single"), InlineKeyboardButton(f'ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ', url='https://t.me/goku_stark'), InlineKeyboardButton("⚡ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ⚡", url="https://t.me/Tamilmovieslink_bot")]]
        await message.reply(script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME), reply_markup=InlineKeyboardMarkup(buttons))
        await asyncio.sleep(2)
        if not await db.get_chat(message.chat.id):     
            await db.add_chat(message.chat.id, message.chat.title)
        return 

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    if len(message.command) != 2:
        buttons = [
            [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴠɪʟʟᴀɢᴇ ➕", url=f"http://t.me/{BOT_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("📜 ᴊᴜᴛsᴜ (ʜᴇʟᴘ)", callback_data="help"), InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ ᴍᴇ", callback_data="about")],
            [InlineKeyboardButton("⛩️ ᴀɴɪᴍᴇ ᴡᴏʀʟᴅ", url="https://t.me/Anime_single"), InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇs", url="https://t.me/super_goku_god")],
            [InlineKeyboardButton("⚡ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ⚡", url="https://t.me/Tamilmovieslink_bot"), InlineKeyboardButton("💎 ᴘʀᴇᴍɪᴜᴍ", callback_data="premium_data")]
        ]
        await message.reply_photo(photo=random.choice(PICS), caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME), reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        return

    if len(message.command) == 2 and message.command[1].startswith('verify_'):
        try:
            link_parts = message.command[1].split("_", 2)
            if str(message.from_user.id) == link_parts[1]:
                await verify_user(message.from_user.id)
                v_msg = await message.reply_text("<b>✅ Verification Successful!</b>\n\n<i>File Uploading... Please wait...</i>", protect_content=True)
                await db.add_verified_user()
                asyncio.create_task(auto_delete_helper(v_msg, 10))
                if len(link_parts) > 2: message.command[1] = link_parts[2]
                else: return 
            else:
                return await message.reply_text("❌ Invalid Verification Link!")
        except Exception as e:
            return

    # 🟢 FIX: Immediate ACK message stops Telegram from repeating /start commands!
    data = message.command[1]
    ack_msg = await message.reply_text("<b>⏳ Fetching File... Please wait...</b>", parse_mode=enums.ParseMode.HTML)

    if not await is_subscribed(message.from_user.id, client):
        links = await create_invite_links(client)
        btn = [[InlineKeyboardButton("🤖 Join Updates Channel", url=url)] for url in links.values()]
        try:
            kk, file_id = data.split("_", 1)
            pre = 'checksubp' if kk == 'filep' else 'checksub'
            btn.append([InlineKeyboardButton("🔄 Try Again", callback_data=f"{pre}#{file_id}")])
        except:
            btn.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{temp.U_NAME}?start={data}")])
        
        await ack_msg.edit("**Please Join My Updates Channel to use this Bot!**", reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.MARKDOWN)
        return

    if IS_VERIFY:
        if not await check_verification(client, message.from_user.id):
            verify_url = await get_verify_link(message.from_user.id, data)
            file_name = "Requested File"
            file_size = "Unknown"
            try:
                temp_file_id = data.split('_', 1)[1] if "_" in data else data
                files_ = await get_file_details(temp_file_id)
                if files_:
                    file_name = files_[0].file_name
                    file_size = get_size(files_[0].file_size)
            except: pass

            buttons = [[InlineKeyboardButton("Click Here To Verify 🟢", url=verify_url)], [InlineKeyboardButton("How to Download 📥", url="https://t.me/howtoo1/7")]]
            await ack_msg.edit(f"<b>⚠️ நீங்க இன்னும் Verify பண்ணல!</b>\n\n<b>📂 File: {file_name}</b>\n<b>💾 Size: {file_size}</b>\n\n<i>கீழே உள்ள பட்டனை கிளிக் செய்து Verify பண்ணுங்க.</i>\n\n<b>⏳ Time Limit: 1 Hours!</b>", reply_markup=InlineKeyboardMarkup(buttons))
            return

    try: pre, file_id = data.split('_', 1)
    except: file_id = data; pre = ""
    
    if data.split("-", 1)[0] == "BATCH":
        await ack_msg.edit("Processing Batch...")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data: msgs=json.loads(file_data.read())
            except:
                return await ack_msg.edit("FAILED TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", f"{title}")
            try: await client.send_cached_media(chat_id=message.from_user.id, file_id=msg.get("file_id"), caption=f_caption, protect_content=msg.get('protect', False))
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await client.send_cached_media(chat_id=message.from_user.id, file_id=msg.get("file_id"), caption=f_caption, protect_content=msg.get('protect', False))
            except Exception: continue
            await asyncio.sleep(1) 
        await ack_msg.delete()
        return
    elif data.split("-", 1)[0] == "DSTORE":
        await ack_msg.edit("Processing DSTORE...")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try: f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                f_caption = getattr(msg, 'caption', getattr(media, 'file_name', ''))
                try: await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception: continue
            elif msg.empty: continue
            else:
                try: await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception: continue
            await asyncio.sleep(1) 
        return await ack_msg.delete()

    files_ = await get_file_details(file_id)           
    if not files_:
        return await ack_msg.edit('No such file exist.')
    
    files = files_[0]
    title = files.file_name
    size = get_size(files.file_size)
    f_caption = files.caption or title
    protect_content_flag = True if pre == 'filep' else False
    
    await send_file_to_user(client, message.from_user.id, file_id, protect_content_flag, title, size, f_caption)
    await ack_msg.delete()
                    
def is_admin(user) -> bool:
    return (user.id in ADMINS or (f"@{user.username}" in ADMINS if user.username else False))

@Client.on_message(filters.command("fsub") & filters.private)
async def set_auth_channels(client, message: Message):
    user = message.from_user
    if not is_admin(user): return await message.reply("🚫 Not authorized.")
    args = message.text.split()[1:]
    if not args: return await message.reply("Usage: /fsub (channel_id)")
    try:
        channels = [int(cid) for cid in args]
        await db.set_auth_channels(channels)
        await message.reply(f"✅ AUTH_CHANNELs updated:\n{channels}")
    except ValueError:
        await message.reply("❌ Invalid channel IDs.")

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
    text = f'📑 **Indexed channels/groups**\nTotal: {len(CHANNELS)}'
    await message.reply(text)

@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    try: await message.reply_document('TelegramBot.txt')
    except Exception as e: await message.reply(str(e))

@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text('This will delete all indexed files.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("YES", callback_data="autofilter_delete")], [InlineKeyboardButton("CANCEL", callback_data="close_data")]]))

@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.message.edit('Succesfully Deleted All.')

async def auto_delete_helper(msg, delay):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except: pass
