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
from info import CHANNELS, ADMINS, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, FILE_CHANNELS, FILE_CHANNEL_SENDING_MODE, FILE_AUTO_DELETE_SECONDS, IS_VERIFY, UPDATES_CHANNEL
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp, create_invite_links, get_verify_link, check_verification, verify_user
from database.connections_mdb import active_connection

logger = logging.getLogger(__name__)

BATCH_FILES = {}
AUTO_DELETE_SECONDS = 15

# Helper function to create buttons
async def create_file_buttons(client, sent_message):
    buttons = []
    if sent_message.chat.username:
        message_link = f"https://t.me/{sent_message.chat.username}/{sent_message.id}"
    else:
        channel_id = str(sent_message.chat.id).replace('-100', '')
        message_link = f"https://t.me/c/{channel_id}/{sent_message.id}"
    
    try:
        chat = await client.get_chat(sent_message.chat.id)
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        else:
            invite_link = (await client.create_chat_invite_link(
                sent_message.chat.id,
                name=f"FileAccess-{datetime.now().timestamp()}",
                expire_date=datetime.now() + timedelta(minutes=10),
                member_limit=1
            )).invite_link
        
        buttons.append([InlineKeyboardButton("📢 Join Channel", url=invite_link)])
        buttons.append([InlineKeyboardButton("🔗 View File", url=message_link)])
    except Exception as e:
        logger.error(f"Error creating invite: {e}")
        buttons.append([InlineKeyboardButton("🔗 View File", url=message_link)])
    
    return InlineKeyboardMarkup(buttons)

async def auto_delete_message(client, message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

async def auto_delete_file(client, message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
        logger.info(f"Deleted file from channel {message.chat.id}")
    except Exception as e:
        logger.error(f"Error deleting file: {e}")

async def send_file_to_user(client, user_id, file_id, protect_content_flag, file_name=None, file_size=None, file_caption=None):
    try:
        caption = None
        if CUSTOM_FILE_CAPTION:
            try:
                caption = CUSTOM_FILE_CAPTION.format(
                    file_name=file_name if file_name else "",
                    file_size=file_size if file_size else "",
                    file_caption=file_caption if file_caption else ""
                )
            except Exception as e:
                logger.error(f"Error formatting caption: {e}")
                caption = file_caption if file_caption else file_name
        else:
            caption = file_caption if file_caption else file_name

        if FILE_CHANNEL_SENDING_MODE and FILE_CHANNELS:
            channel_id = random.choice(FILE_CHANNELS)
            sent_message = await client.send_cached_media(
                chat_id=channel_id,
                file_id=file_id,
                caption=caption,
                protect_content=protect_content_flag
            )
            asyncio.create_task(auto_delete_file(client, sent_message, FILE_AUTO_DELETE_SECONDS))
            
            reply_markup = await create_file_buttons(client, sent_message)
            
            user_msg = await client.send_message(
                chat_id=user_id,
                text=f"**Your file is ready!**\n\nJoin the channel to view your file ",
                protect_content=True,
                reply_markup=reply_markup
            )
            asyncio.create_task(auto_delete_message(client, user_msg, AUTO_DELETE_SECONDS))
        else:
            msg = await client.send_cached_media(
                chat_id=user_id,
                file_id=file_id,
                caption=caption,
                protect_content=protect_content_flag,
            )
            asyncio.create_task(auto_delete_file(client, msg, 120)) 
            
    except Exception as e:
        logger.error(f"File send error: {e}")
        msg = await client.send_cached_media(
            chat_id=user_id,
            file_id=file_id,
            caption=caption,
            protect_content=protect_content_flag,
        )
        asyncio.create_task(auto_delete_file(client, msg, 120))

@Client.on_callback_query(filters.regex(r'^checksubp#') | filters.regex(r'^checksub#'))
async def checksub_callback(client, callback_query):
    data = callback_query.data
    pre, file_id = data.split('#', 1)
    user_id = callback_query.from_user.id
    protect_content_flag = True if pre == 'checksubp' else False

    files = await get_file_details(file_id)
    file_details = files[0] if files else None
    
    if await is_subscribed(user_id, client):
        try:
            await send_file_to_user(
                client=client,
                user_id=user_id,
                file_id=file_id,
                protect_content_flag=protect_content_flag,
                file_name=file_details.file_name if file_details else None,
                file_size=get_size(file_details.file_size) if file_details else None,
                file_caption=file_details.caption if file_details else None
            )
            await callback_query.message.delete()
        except Exception as e:
            logger.error(f"File send error in callback: {e}")
            await callback_query.answer("Failed to send file. Please try again later.", show_alert=True)
    else:
        links = await create_invite_links(client)
        btn = [[InlineKeyboardButton("🤖 Join Updates Channel", url=url)] for url in links.values()]
        btn.append([InlineKeyboardButton("🔄 Try Again", callback_data=data)])
        await callback_query.edit_message_text(
            text="**❌ You still haven't joined all channels!**\n\nPlease join and press Try Again:",
            reply_markup=InlineKeyboardMarkup(btn)
        )

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
            [
                InlineKeyboardButton("⛩️ ᴀɴɪᴍᴇ ᴡᴏʀʟᴅ", url="https://t.me/Anime_single"),
                InlineKeyboardButton(f'ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ', url='https://t.me/goku_stark'),
                InlineKeyboardButton("⚡ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ⚡", url="https://t.me/Tamilmovieslink_bot")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2)
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))        
            await db.add_chat(message.chat.id, message.chat.title)
        return 

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))

    if len(message.command) != 2:
        buttons = [
    [
        InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴠɪʟʟᴀɢᴇ ➕", url=f"http://t.me/{BOT_USERNAME}?startgroup=true")
    ],
    [
        InlineKeyboardButton("📜 ᴊᴜᴛsᴜ (ʜᴇʟᴘ)", callback_data="help_data"),
        InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ ᴍᴇ", callback_data="about_data")
    ],
    [
        InlineKeyboardButton("⛩️ ᴀɴɪᴍᴇ ᴡᴏʀʟᴅ", url="https://t.me/Anime_single"), 
        InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇs", url="https://t.me/super_goku_god")
    ],
    [
        InlineKeyboardButton("⚡ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ⚡", url="https://t.me/Tamilmovieslink_bot"),
        InlineKeyboardButton("💎 ᴘʀᴇᴍɪᴜᴍ", callback_data="premium_data")
    ]
]
        reply_markup = InlineKeyboardMarkup(buttons)
        # 1. Naruto Style Loading Effect
m = await message.reply_text(
    text="<b>🌀 𝐆𝐚𝐭𝐡𝐞𝐫𝐢𝐧𝐠 𝐂𝐡𝐚𝐤𝐫𝐚... ⏳</b>",
    parse_mode=enums.ParseMode.HTML
)

# 2. Wait for 1.5 seconds (Animation feel kidaikum)
await asyncio.sleep(1.5)

# 3. Loading text delete pannidunga
await m.delete()

# 4. Main Bot Entry with Photo
await message.reply_photo(
    photo=random.choice(PICS),
    caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
    reply_markup=reply_markup,
    parse_mode=enums.ParseMode.HTML
)
return
    if not await is_subscribed(message.from_user.id, client):
        links = await create_invite_links(client)
        btn = [[InlineKeyboardButton("🤖 Join Updates Channel", url=url)] for url in links.values()]
        if len(message.command) == 2:
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub'
                btn.append([InlineKeyboardButton("🔄 Try Again", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        
        await client.send_message(
            chat_id=message.from_user.id,
            text="**Please Join My Updates Channel to use this Bot!**",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [[InlineKeyboardButton('ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘs', url=f'http://t.me/{temp.U_NAME}?startgroup=true')],[InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'),InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about')],[InlineKeyboardButton(f'Anime Channel​', url='https://t.me/Anime_single'),InlineKeyboardButton(f'ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ', url='https://t.me/goku_stark')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(photo=random.choice(PICS), caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        return
    
    if len(message.command) == 2 and message.command[1].startswith('mntgx'):
        searches = message.command[1].split("-", 1)[1] 
        search = searches.replace('-',' ')
        message.text = search 
        await auto_filter(client, message) 
        return

    if len(message.command) == 2 and message.command[1].startswith('verify_'):
        try:
            link_parts = message.command[1].split("_", 2)
            check_id = link_parts[1]
            
            if str(message.from_user.id) == check_id:
                await verify_user(message.from_user.id)
                
                # Inga thaan namba add panna code
                v_msg = await message.reply_text(
                    "<b>✅ Verification Successful!</b>\n\n<i>File Uploading... Please wait...</i>", 
                    protect_content=True
                )
                
                # Background delete task
                asyncio.create_task(auto_delete_helper(v_msg, 10))
                
                if len(link_parts) > 2:
                    message.command[1] = link_parts[2]
                else:
                    return 
            else:
                await message.reply_text("❌ Invalid Verification Link!")
                return
        except Exception as e:
            print(f"Verify Error: {e}")
            return

    data = message.command[1]

    if IS_VERIFY:
        if not await check_verification(client, message.from_user.id):
            verify_url = await get_verify_link(message.from_user.id, data)
            file_name = "Requested File"
            file_size = "Unknown"
            
            try:
                if "_" in data:
                    try:
                        _, temp_file_id = data.split('_', 1)
                    except:
                        temp_file_id = data
                else:
                    temp_file_id = data

                files_ = await get_file_details(temp_file_id)
                if files_:
                    file_name = files_[0].file_name
                    file_size = get_size(files_[0].file_size)
            except Exception as e:
                print(f"Error getting file details: {e}")

            buttons = [
                [InlineKeyboardButton("Click Here To Verify 🟢", url=verify_url)],
                [InlineKeyboardButton("How to Download 📥", url="https://t.me/howtoo1/3")]
            ]
            verify_msg = await message.reply_text(
                text=f"<b>⚠️ நீங்க இன்னும் Verify பண்ணல!</b>\n\n<b>📂 File: {file_name}</b>\n<b>💾 Size: {file_size}</b>\n\n<i>கீழே உள்ள பட்டனை கிளிக் செய்து Verify பண்ணுங்க.</i>\n\n<b>⏳ Time Limit: 1 Hours!</b>",
                reply_markup=InlineKeyboardMarkup(buttons),
                protect_content=True
            )
            asyncio.create_task(auto_delete_message(client, verify_msg, 3600))
            return

    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
    
    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("Please wait")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                logger.warning(f"Floodwait of {e.x} sec.")
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    )
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        return
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("Please wait")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                    except Exception as e:
                        logger.exception(e)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    media = getattr(msg, msg.media.value)
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            await asyncio.sleep(1) 
        return await sts.delete()
        

    files_ = await get_file_details(file_id)            
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        try:
            protect_content_flag = True if pre == 'filep' else False
            
            await send_file_to_user(
                client=client,
                user_id=message.from_user.id,
                file_id=file_id,
                protect_content_flag=protect_content_flag
            )
            return
        except:
            pass
        return await message.reply('No such file exist.')
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            logger.exception(e)
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"{files.file_name}"
    
    protect_content_flag = True if pre == 'filep' else False
    
    await send_file_to_user(
        client=client,
        user_id=message.from_user.id,
        file_id=file_id,
        protect_content_flag=protect_content_flag,
        file_name=title,
        file_size=size,
        file_caption=f_caption
    )
                    
def is_admin(user) -> bool:
    return (
        user.id in ADMINS or
        (f"@{user.username}" in ADMINS if user.username else False)
    )

@Client.on_message(filters.command("fsub") & filters.private)
async def set_auth_channels(client, message: Message):
    user = message.from_user
    if not is_admin(user):
        return await message.reply("🚫 You are not authorized to use this command.")

    args = message.text.split()[1:]
    if not args:
        return await message.reply("Usage: /fsub (channel_id1) (channel_id2) ...")

    try:
        channels = [int(cid) for cid in args]
        await db.set_auth_channels(channels)
        await message.reply(f"✅ AUTH_CHANNELs updated:\n{channels}")
    except ValueError:
        await message.reply("❌ Invalid channel IDs. Use numeric Telegram chat IDs.")

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
            
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.txt')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('File is successfully deleted from database')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('File is successfully deleted from database')
        else:
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('File is successfully deleted from database')
            else:
                await msg.edit('File not found in database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer('by tamiltechgk')
    await message.message.edit('Succesfully Deleted All The Indexed Files.')


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    settings = await get_settings(grp_id)

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Filter Button',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Single' if settings["button"] else 'Double',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Bot PM',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["botpm"] else '❌ No',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'File Secure',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["file_secure"] else '❌ No',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'IMDB',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["imdb"] else '❌ No',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Spell Check',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["spell_check"] else '❌ No',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Welcome',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["welcome"] else '❌ No',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply_text(
            text=f"<b>Change Your Settings for {title} As Your Wish ⚙</b>",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )



@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Checking template")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit("No Input!!")
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to\n\n{template}")

# Helper: Padam perai clean-a edukka (Smart Match-kaga)
def get_clean_name(name):
    # Quality & Junk words remove panrom to find match
    clean = re.sub(r"(\[.*?\]|\{.*?\}|\(.*?\)|720p|1080p|480p|HEVC|x264|x265|mkv|mp4|avi|www\.|@\w+)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.lower()

@Client.on_message(filters.command("plan") & filters.private)
async def premium_plans(client, message):
    try:
        # 1. Payment Link
        payment_link = "https://upi.pe/gokula8@ibl" 

        # 2. Admin Contact Link
        admin_link = "https://t.me/Screenshot_gk_bot" 

        # 3. Image URL
        plan_image = "https://i.ibb.co/YFFY84YX/photo.jpg"

        # 4. Stylish Caption
        caption = (
            "<b>💎 PREMIUM PLANS & PRICING 💎</b>\n\n"
            "Bot-a <b>Ads illama</b>, <b>High Speed-la</b> use panna virumbureengala?\n"
            "Keezha ulla Plans-la onna select pannunga! 👇\n\n"
            "<b>💸 CHEAPEST PRICES:</b>\n"
            "• 1️⃣ <b>1 Day:</b> ₹9 Only\n"
            "• 7️⃣ <b>7 Days:</b> ₹59 Only\n"
            "• ♾️ <b>24 Months:</b> ₹99 Only (Best Offer! 🔥)\n\n"
            "<b>💳 Eppadi Pay Panrathu?</b>\n"
            "1. Keezha ulla <b>'Pay Now'</b> button click pannunga.\n"
            "2. Payment pannitu, <b>Screenshot</b> edunga.\n"
            "3. <b>'Send Screenshot'</b> button click panni Admin-ku anuppunga.\n\n"
            "<i>✅ Verification mudinjanthum Premium activate aagidum!</i>"
        )

        # 5. Buttons
        buttons = [
            [
                InlineKeyboardButton("💳 Pay Now / QR Code", url=payment_link),
                InlineKeyboardButton("📸 Send Screenshot", url=admin_link)
            ],
            [
                InlineKeyboardButton("✖ Close", callback_data="close_data")
            ]
        ]

        # 6. Message Send Panrom
        await message.reply_photo(
            photo=plan_image,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )

    except Exception as e:
        print(f"Plan Command Error: {e}")

# Intha helper function-a file-oda end-la pottukonga
async def auto_delete_helper(msg, delay):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass
