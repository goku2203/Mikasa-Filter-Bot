# Kanged From @TroJanZheX
#hyper link mode by mn-bots
import asyncio
import re
import ast
import math
import time
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty, ButtonUrlInvalid
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings, create_invite_links
from database.users_chats_db import db
from info import HYPER_MODE
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
import logging
import random
from info import PICS
import difflib

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUTTONS = {}
SPELL_CHECK = {}

# --- MISSING LOG SETTINGS ---
MISSING_LOG_CHANNEL = -1003555146843
LOG_COOLDOWN = 600
RECENT_REQUESTS = {}

@Client.on_message((filters.group | filters.private) & filters.text)
async def give_filter(client, message):
    try:
        await message.delete()
    except Exception as e:
        pass 

    k = await manual_filters(client, message)
    if k == False:
        await auto_filter(client, message)

@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer("**Search for Yourself**🔎", show_alert=True)

    try:
        offset = int(offset)
    except:
        offset = 0

    search = BUTTONS.get(key)
    if not search:
        await query.answer(script.OLD_MES, show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return

    settings = await get_settings(query.message.chat.id)
    if not settings:
        settings = {"button": True, "botpm": False, "file_secure": False, "imdb": False, "spell_check": False, "template": IMDB_TEMPLATE, "welcome": False}

    if HYPER_MODE:
        cap_lines = []
        for file in files:
            file_link = f"https://t.me/{temp.U_NAME}?start=file_{file.file_id}"
            cap_lines.append(f"📁 {get_size(file.file_size)} - [{file.file_name}]({file_link})")
        cap_text = "\n".join(cap_lines)
        btn = []
    else:
        if settings['button']:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"📂[{get_size(file.file_size)}] ➵ {file.file_name}", callback_data=f'files#{file.file_id}'
                    ),
                ]
                for file in files
            ]
        else:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"{file.file_name}", callback_data=f'files#{file.file_id}'
                    ),
                    InlineKeyboardButton(
                        text=f"{get_size(file.file_size)}", callback_data=f'files_#{file.file_id}'
                    ),
                ]
                for file in files
            ]

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10

    if n_offset == 0:
        btn.append(
            [
                InlineKeyboardButton("◀️ BACK", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"📃 {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages")
            ]
        )
    elif off_set is None:
        btn.append(
            [
                InlineKeyboardButton(f"📃 {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("NEXT ▶️", callback_data=f"next_{req}_{key}_{n_offset}")
            ]
        )
    else:
        btn.append(
            [
                InlineKeyboardButton("◀️ BACK", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"📃 {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("NEXT ▶️", callback_data=f"next_{req}_{key}_{n_offset}")
            ]
        )

    btn.append([InlineKeyboardButton("📝 Request Movie 📝", url="https://t.me/Tamilmovieslink_bot")])
    
    try:
        if HYPER_MODE:
            await query.edit_message_text(
                text=cap_text,
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        else:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(btn)
            )
    except MessageNotModified:
        pass

    await query.answer()

@Client.on_callback_query(filters.regex(r"^spol")) 
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("Search for Yourself🔎", show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer(script.OLD_MES, show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer(script.CHK_MOV_ALRT)
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await query.message.edit(script.MOV_NT_FND)
            await asyncio.sleep(10)
            await k.delete()

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()

    elif query.data == "premium_data":
        payment_link = "https://upi.pe/gokula8@ibl" 
        admin_link = "https://t.me/Screenshot_gk_bot"
        plan_image = "https://i.ibb.co/YFFY84YX/photo.jpg"

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
        
        buttons = [
            [
                InlineKeyboardButton("💳 Pay Now / QR Code", url=payment_link),
                InlineKeyboardButton("📸 Send Screenshot", url=admin_link)
            ],
            [
                InlineKeyboardButton("🏠 Home", callback_data="start_data")
            ]
        ]
        
        await query.message.edit_media(
            media=InputMediaPhoto(media=plan_image, caption=caption),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return await query.answer()

    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer('@Goku_Stark')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer('THIS IS A OPEN SOURCE PROJECT SEARCH SHOBANAFILTERBOT IN GITHUB ')

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('@Goku_Stark')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)

    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("That's not for you!!", show_alert=True)

    elif "groupcb" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer('@Goku_Stark')

    elif "connectcb" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer('@Goku_Stark')

    elif "disconnect" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('@Goku_Stark')

    elif "deletecb" in query.data:
        await query.answer()
        user_id = query.from_user.id
        group_id = query.data.split(":")[1]
        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('@Goku_Stark')

    elif query.data == "backcb":
        await query.answer()
        userid = query.from_user.id
        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('@Goku_Stark')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)

    elif query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        
        settings = await get_settings(query.message.chat.id)
        if not settings:
             settings = {"button": True, "botpm": False, "file_secure": False, "imdb": False, "spell_check": False, "template": IMDB_TEMPLATE, "welcome": False}

        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if not await is_subscribed(query.from_user.id, client):
                invite_links = await create_invite_links(client)
                first_link = next(iter(invite_links.values()), f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                await query.answer(url=first_link)
                return
            elif settings['botpm']:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except UserIsBlocked:
            await query.answer('Unblock the bot mahn !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")

    elif query.data.startswith("checksub"):
        if not await is_subscribed(query.from_user.id, client):
            await query.answer("I Like Your Smartness, But Don't Be Oversmart", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False
        )

    elif query.data == "pages":
        await query.answer()

    elif query.data == "esp":
        await query.answer(text=script.ENG_SPELL, show_alert="true")
    elif query.data == "msp":
        await query.answer(text=script.MAL_SPELL, show_alert="true")
    elif query.data == "hsp":
        await query.answer(text=script.HIN_SPELL, show_alert="true")
    elif query.data == "tsp":
        await query.answer(text=script.TAM_SPELL, show_alert="true")
        
    elif query.data == "start" or query.data == "start_data":
        buttons = [
            [
                InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴠɪʟʟᴀɢᴇ ➕", url=f"https://t.me/{temp.U_NAME}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📜 ᴊᴜᴛsᴜ (ʜᴇʟᴘ)", callback_data="help"),
                InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ ᴍᴇ", callback_data="about")
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
        
        try:
            txt = script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME)
        except:
            txt = script.START_TXT.format(query.from_user.mention)

        await query.message.edit_media(
            media=InputMediaPhoto(
                media=random.choice(PICS),
                caption=txt
            ),
            reply_markup=reply_markup
        )
        await query.answer('@Goku_Stark')

    elif query.data == "help":
        buttons = [
            [
                InlineKeyboardButton("🛠️ ᴍᴀɴᴜᴀʟ ғɪʟᴛᴇʀ", callback_data="manual_filter"),
                InlineKeyboardButton("🤖 ᴀᴜᴛᴏ ғɪʟᴛᴇʀ", callback_data="auto_filter")
            ],
            [
                InlineKeyboardButton("🔗 ᴄᴏɴɴᴇᴄᴛɪᴏɴs", callback_data="connection"),
                InlineKeyboardButton("🧩 ᴇxᴛʀᴀs", callback_data="extras")
            ],
            [
                InlineKeyboardButton("🔙 ʀᴇᴛᴜʀɴ", callback_data="start_data"),
                InlineKeyboardButton("💎 ᴘʀᴇᴍɪᴜᴍ", callback_data="premium_data")
            ],
            [
                InlineKeyboardButton("⚡ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ⚡", url="https://t.me/Tamilmovieslink_bot")
            ]
        ]
        
        # 👇 SECRET OWNER BUTTON (Admin ku mattum thaan theriyum) 👇
        if query.from_user.id in ADMINS:
            buttons.append([InlineKeyboardButton("👑 𝐎𝐰𝐧𝐞𝐫 𝐏𝐚𝐧𝐞𝐥 (𝐋𝐢𝐯𝐞 𝐒𝐭𝐚𝐭𝐬) 👑", callback_data="owner_panel")])
        # 👆 --------------------------------------------------- 👆

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
# 👇 PUTHU OWNER PANEL FUNCTION 👇
    elif query.data == "owner_panel":
        # Security Check
        if query.from_user.id not in ADMINS:
            return await query.answer("Kuthu Vangiruva! Ithu Owner ku mattum thaan! 😠", show_alert=True)
            
        import psutil
        from utils import get_size
        
        await query.answer("Fetching Live Stats... ⏳")
        
        # Database Stats
        total_users = await db.total_users_count()
        total_chats = await db.total_chat_count()
        total_files = await Media.count_documents()
        
        # Database Free Space Logic
        monsize = await db.get_db_size()
        free_db = 536870912 - monsize  # 512MB MongoDB Free Tier
        db_percent = round((monsize / 536870912) * 100, 2)
        
        # Hardware / Performance Stats
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # Monthly Verified Users (Temporary logic placeholder)
        verified_users = await db.get_verified_count() 
        
        text = (
            "<b>👑 <u>𝐎𝐖𝐍𝐄𝐑 𝐂𝐎𝐍𝐓𝐑𝐎𝐋 𝐏𝐀𝐍𝐄𝐋</u> 👑</b>\n\n"
            f"<i>Hi {query.from_user.mention}! Ithu unnoda secret dashboard. 😎</i>\n\n"
            "<b>📊 <u>𝐋𝐢𝐯𝐞 𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐬</u>:</b>\n"
            f"👤 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"👥 <b>Total Groups:</b> <code>{total_chats}</code>\n"
            f"📂 <b>Total Files:</b> <code>{total_files}</code>\n"
            f"✅ <b>Verified Users:</b> <code>~ {verified_users}</code>\n\n"
            "<b>🖥️ <u>𝐒𝐞𝐫𝐯𝐞𝐫 & 𝐇𝐚𝐫𝐝𝐰𝐚𝐫𝐞</u>:</b>\n"
            f"⚡ <b>CPU Usage:</b> <code>{cpu}%</code>\n"
            f"💽 <b>RAM Usage:</b> <code>{ram}%</code>\n"
            f"💿 <b>Storage:</b> <code>{disk}%</code>\n\n"
            "<b>💾 <u>𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐂𝐚𝐩𝐚𝐜𝐢𝐭𝐲</u>:</b>\n"
            f"📊 <b>Used:</b> <code>{db_percent}%</code>\n"
            f"🆓 <b>Free:</b> <code>{get_size(free_db)}</code>"
        )
        
        buttons = [
            [
                InlineKeyboardButton("♻️ Refresh Stats", callback_data="owner_panel")
            ],
            [
                InlineKeyboardButton("🔙 Back to Help", callback_data="help")
            ]
        ]
        
        await query.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='about'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "manual_filter":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot'),
            InlineKeyboardButton('ʙᴜᴛᴛᴏɴ', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MANUALFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "auto_filter":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "connection":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "extras":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('ᴀᴅᴍɪɴ', callback_data='admin'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=final_text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('♻️', callback_data='rfrsh'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('♻️', callback_data='rfrsh'),
            InlineKeyboardButton('⚡ Contact Admin', url='https://t.me/Tamilmovieslink_bot')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer('@Goku_Stark')

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer('@Goku_Stark')

async def auto_filter(client, msg, spoll=False):
    try:
        if not spoll:
            message = msg
            settings = await get_settings(message.chat.id)
            
            if not settings:
                settings = {"button": True, "botpm": False, "file_secure": False, "imdb": False, "spell_check": False, "template": IMDB_TEMPLATE, "welcome": False}

            if message.text.startswith("/"): return
            if re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
                return
            if 2 < len(message.text) < 100:
                search = message.text
                
                search_msg = await message.reply_text(
                    f"<b>🔍 Searching...</b>\n"
                    f"<code>[⬛⬛⬜⬜⬜⬜⬜⬜] 20%</code>"
                )
                await asyncio.sleep(0.5)
                await search_msg.edit(
                    f"<b>✅ Completed!</b>\n"
                    f"<code>[⬛⬛⬛⬛⬛⬛⬛⬛] 100%</code>\n\n"
                    f"<i>Here is your result 👇</i>"
                )
                
                files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
                
                if not files:
                    # --- MISSING LOG CODE ADDED HERE ---
                    clean_query = search.lower()
                    current_time = time.time()
                    
                    if clean_query not in RECENT_REQUESTS or (current_time - RECENT_REQUESTS.get(clean_query, 0)) >= LOG_COOLDOWN:
                        RECENT_REQUESTS[clean_query] = current_time
                        user_mention = message.from_user.mention if message.from_user else 'Anonymous'
                        user_id = message.from_user.id if message.from_user else 'Unknown'
                        
                        log_msg = (
                            f"⚠️ **Missing Movie Detected!**\n\n"
                            
                            f"🔍 **Query:** `{search}`\n"
                            f"👤 **User:** {user_mention}\n"
                            f"📁 **Group:** {message.chat.title}\n"
                            f"🆔 **User ID:** `{user_id}`\n\n"
                            f"Please upload this movie soon! #Missing_Request"
                        )
                        
                        if MISSING_LOG_CHANNEL:
                            try:
                                await client.send_message(
                                    chat_id=MISSING_LOG_CHANNEL, 
                                    text=log_msg, 
                                    disable_web_page_preview=True
                                )
                            except Exception as e:
                                print(f"Missing Log Error: {e}")
                    # --- MISSING LOG CODE END ---
                    
                    # 👇 PUDHU STYLE ANIMATION 👇
                    if settings["spell_check"]:
                        # Step 1: Animation 1
                        await search_msg.edit("<b>⚠️ Analyzing Database...</b>\n<code>[======>   ] 60%</code>")
                        await asyncio.sleep(0.5)
                        
                        # Step 2: Animation 2 (Error)
                        await search_msg.edit("<b>🔴 ERROR 404: Movie Not Found!</b>\n<code>[==========] 100%</code>")
                        await asyncio.sleep(0.8)
                        
                        # Step 3: Cool Tanglish Dialogue
                        await search_msg.edit(
                            f"<b>🤖 System Alert:</b>\n"
                            f"<i>En kitta '<b>{search}</b>' illa thalaiva! 🥺\n"
                            f"Wait... Google kitta spelling thedi paakuren... 🕵️‍♂️🌍</i>"
                        )
                        await asyncio.sleep(1.5) 
                        await search_msg.delete() 
                        return await advantage_spell_chok(client, msg)
                        
                    else:
                        # Oruvela spell check off la iruntha intha mass message + Button varum
                        req_btn = [[InlineKeyboardButton("📝 Request Movie", url="https://t.me/Tamilmovieslink_bot")]]
                        await search_msg.edit(
                            f"<b>🚫 MISSION FAILED!</b>\n\n"
                            f"🎬 <b>Movie:</b> <code>{search}</code>\n"
                            f"🤖 <b>Status:</b> <i>En kitta intha padam illa thalaiva! 🥺</i>\n\n"
                            f"💡 <b>Tips:</b>\n"
                            f"👉 Spelling correct-a check pannu.\n"
                            f"👉 Year illama verum pera mattum potu thedu.\n"
                            f"👉 Illana keezha irukka button click panni Admin kitta kelu!",
                            reply_markup=InlineKeyboardMarkup(req_btn)
                        )
                        await asyncio.sleep(15)
                        await search_msg.delete()
                        return
                    # 👆 PUDHU STYLE ANIMATION END 👆
                else:
                    await search_msg.delete() 
        else:
            settings = await get_settings(msg.message.chat.id)
            if not settings:
                 settings = {"button": True, "botpm": False, "file_secure": False, "imdb": False, "spell_check": False, "template": IMDB_TEMPLATE, "welcome": False}
            
            message = msg.message.reply_to_message
            search, files, offset, total_results = spoll

        pre = 'filep' if settings['file_secure'] else 'file'

        if HYPER_MODE:
            cap_lines = []
            for file in files:
                file_link = f"https://t.me/{temp.U_NAME}?start={pre}_{file.file_id}"
                cap_lines.append(f"📁 {get_size(file.file_size)} - [{file.file_name}]({file_link})")
            cap_text = "\n".join(cap_lines)

            btn = []
            if offset != "":
                key = f"{message.chat.id}-{message.id}"
                BUTTONS[key] = search
                req = message.from_user.id if message.from_user else 0
                btn.append([
                    InlineKeyboardButton(text=f"📃 1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
                    InlineKeyboardButton(text="NEXT ▶️", callback_data=f"next_{req}_{key}_{offset}")
                ])
            else:
                btn.append([InlineKeyboardButton(text="📃 1/1", callback_data="pages")])

            else:
            # 👇 🔥 INGA THAAN LOADING FIX PANNIRUKOM (callback pathila direct URL) 🔥 👇
            if settings["button"]:
                btn = [
                    [
                        InlineKeyboardButton(
                            text=f"📂[{get_size(file.file_size)}]--{file.file_name}", 
                            url=f"https://t.me/{temp.U_NAME}?start={pre}_{file.file_id}"
                        ),
                    ]
                    for file in files
                ]
            else:
                btn = [
                    [
                        InlineKeyboardButton(
                            text=f"{file.file_name}",
                            url=f"https://t.me/{temp.U_NAME}?start={pre}_{file.file_id}"
                        ),
                        InlineKeyboardButton(
                            text=f"{get_size(file.file_size)}",
                            url=f"https://t.me/{temp.U_NAME}?start={pre}_{file.file_id}"
                        ),
                    ]
                    for file in files
                ]
            # 👆 🔥 FIX END 🔥 👆
            if offset != "":
                key = f"{message.chat.id}-{message.id}"
                BUTTONS[key] = search
                req = message.from_user.id if message.from_user else 0
                btn.append([
                    InlineKeyboardButton(text=f"📃 1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
                    InlineKeyboardButton(text="NEXT ▶️", callback_data=f"next_{req}_{key}_{offset}")
                ])
            else:
                btn.append([InlineKeyboardButton(text="📃 1/1", callback_data="pages")])
                
        btn.append([InlineKeyboardButton("📝 Request Movie 📝", url="https://t.me/Tamilmovieslink_bot")])
        
        imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
        TEMPLATE = settings['template']
        if imdb:
            cap = TEMPLATE.format(
                query=search,
                title=imdb['title'],
                votes=imdb['votes'],
                aka=imdb["aka"],
                seasons=imdb["seasons"],
                box_office=imdb['box_office'],
                localized_title=imdb['localized_title'],
                kind=imdb['kind'],
                imdb_id=imdb["imdb_id"],
                cast=imdb["cast"],
                runtime=imdb["runtime"],
                countries=imdb["countries"],
                certificates=imdb["certificates"],
                languages=imdb["languages"],
                director=imdb["director"],
                writer=imdb["writer"],
                producer=imdb["producer"],
                composer=imdb["composer"],
                cinematographer=imdb["cinematographer"],
                music_team=imdb["music_team"],
                distributors=imdb["distributors"],
                release_date=imdb['release_date'],
                year=imdb['year'],
                genres=imdb['genres'],
                poster=imdb['poster'],
                plot=imdb['plot'],
                rating=imdb['rating'],
                url=imdb['url'],
                **locals()
            )
        else:
            mention = message.from_user.mention if message.from_user else "User"
            cap = script.RESULT_TXT.format(mention=mention, query=search)

        if imdb and imdb.get('poster'):
            try:
                if not spoll: await search_msg.delete()
                
                delauto = await message.reply_photo(
                    photo=imdb.get('poster'),
                    caption=cap[:1024],
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                await asyncio.sleep(60)
                await delauto.delete()
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                if not spoll: await search_msg.delete()
                pic = imdb.get('poster')
                poster = pic.replace('.jpg', "._V1_UX360.jpg")
                delau = await message.reply_photo(
                    photo=poster,
                    caption=cap[:1024],
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                await asyncio.sleep(60)
                await delau.delete()
            except Exception as e:
                if not spoll: await search_msg.delete()
                audel = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(60)
                await audel.delete()
        else:
            if not spoll: await search_msg.delete()
            
            if HYPER_MODE:
                autodel = await message.reply_text(
                    cap_text,
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode=enums.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            else:
                autodel = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))

            await asyncio.sleep(60)
            await autodel.delete()

        if spoll:
            await msg.message.delete()
            
    except ButtonUrlInvalid:
        logger.error("BUTTON URL INVALID ERROR: Kaila podra link sariya illa, check pannunga.")
    except Exception as final_error:
        logger.exception(f"CRITICAL ERROR IN AUTO_FILTER: {final_error}")

async def advantage_spell_chok(client, msg):
    mv_id = msg.id
    mv_rqst = msg.text
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1)
    
    settings = await get_settings(msg.chat.id)
    if not settings:
         settings = {"button": True, "botpm": False, "file_secure": False, "imdb": False, "spell_check": False, "template": IMDB_TEMPLATE, "welcome": False}

    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)
    
    query = query.strip()
    
    if query:
        search_query = query + " movie"
    else:
        search_query = msg.text

    try:
        movies = await get_poster(search_query, bulk=True)
    except Exception as e:
        logger.exception(e)
        movies = None

    movielist = []
    
    if movies:
        movielist += [movie.get('title') for movie in movies]

    if not movielist:
        try:
            first_char = query[0] if query else ""
            if first_char:
                cursor = Media.collection.find({"file_name": {"$regex": f"^{first_char}", "$options": "i"}}).limit(200)
                db_files = await cursor.to_list(length=200)
                db_names = [x['file_name'] for x in db_files]
                if db_names:
                    matches = difflib.get_close_matches(query, db_names, n=5, cutoff=0.5)
                    movielist += matches
        except Exception as e:
            logger.error(f"Fuzzy Error: {e}")

    if not movielist:
        reqst_gle = mv_rqst.replace(" ", "+")
        google_btn = [
            [InlineKeyboardButton('🔍 Check on Google 🔎', url=f"https://www.google.com/search?q={reqst_gle}")]
        ]
        k = await msg.reply_text(
            text=script.SPOLL_NOT_FND, 
            reply_markup=InlineKeyboardMarkup(google_btn),
            reply_to_message_id=msg.id
        )
        await asyncio.sleep(60)
        await k.delete()
        return

    movielist = list(dict.fromkeys(movielist)) 
    
    SPELL_CHECK[mv_id] = movielist
    
    btn = [
        [
            InlineKeyboardButton(
                text=movie_name.strip(),
                callback_data=f"spol#{reqstr1}#{k}",
            )
        ]
        for k, movie_name in enumerate(movielist)
    ]
    
    btn.append([InlineKeyboardButton(text="✖ Close", callback_data=f'spol#{reqstr1}#close_spellcheck')])
    
    spell_check_del = await msg.reply_text(
        text=f"<b>❌ Couldn't find '<code>{mv_rqst}</code>'\n\nDid you mean any of these? 👇</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        reply_to_message_id=msg.id
    )
    
    await asyncio.sleep(180)
    await spell_check_del.delete()

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(
                                group_id, 
                                reply_text, 
                                disable_web_page_preview=True,
                                reply_to_message_id=reply_id)
                        else:
                            button = eval(btn)
                            await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
