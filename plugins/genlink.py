import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, VERIFY
# 👇 Mukkiyamaana Imports (Database & Utils)
from database.ia_filterdb import get_file_details, unpack_new_file_id
from utils import get_verify_status, get_shortlink, get_size, temp

# --- SETTINGS ---
# 3 Hours = 10800 Seconds
AUTO_DELETE_TIME = 10800 

# --- AUTO DELETE HELPER ---
async def auto_delete_file(message):
    try:
        await asyncio.sleep(AUTO_DELETE_TIME)
        await message.delete()
    except Exception as e:
        print(f"Error deleting file: {e}")

# --- MAIN GENERATOR HANDLER ---
@Client.on_message(filters.command(["start"]) & filters.private)
async def start_generator(client, message):
    if len(message.command) < 2:
        return # Normal start command, ignore

    data = message.command[1]

    # Handle both 'file_' and 'filep_'
    if data.startswith("file"):
        try:
            if "_" in data:
                _, file_id = data.split("_", 1)
            else:
                return

            # 1. Get File Details from Database
            file_details_list = await get_file_details(file_id)
            if not file_details_list:
                await message.reply_text("❌ File Not Found or Deleted!")
                return
            file_info = file_details_list[0]

            # -------------------------------------------------------------
            # 👇 CLICK TO VERIFY LOGIC (Add Panniyachu) 👇
            # -------------------------------------------------------------
            if VERIFY: # Info.py la VERIFY = True nu irukkanum
                # User Verify panni irukkara nu check panrom
                is_verified = await get_verify_status(message.from_user.id)
                
                if not is_verified:
                    # Verify pannalana, Shortlink create panrom
                    verify_link = await get_shortlink(f"https://t.me/{temp.U_NAME}?start={data}")
                    
                    btn = [
                        [InlineKeyboardButton("🟢 Click Here To Verify 🟢", url=verify_link)],
                        [InlineKeyboardButton("📂 How to Download", url="https://t.me/Tamilmovieslink_bot")]
                    ]
                    
                    # Verify Alert Message
                    await message.reply_text(
                        text=(
                            f"<b>⚠️ நீங்க இன்னும் Verify பண்ணல!</b>\n\n"
                            f"📁 <b>File:</b> {file_info.file_name}\n"
                            f"🔐 <b>Size:</b> {get_size(file_info.file_size)}\n\n"
                            f"<i>கீழே உள்ள பட்டனை கிளிக் செய்து Verify பண்ணுங்க. அப்போதான் படம் வரும்!</i>"
                        ),
                        reply_markup=InlineKeyboardMarkup(btn),
                        quote=True,
                        protect_content=True
                    )
                    return # Stop here! File anuppa koodathu.
            # -------------------------------------------------------------
            # 👆 VERIFY LOGIC END 👆
            # -------------------------------------------------------------

            # User Verified-a iruntha, inga varum:
            
            # Send the File
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                caption=f"📂 <b>{file_info.file_name}</b>\n\n<i>⚠️ This file will be deleted in 3 hours!</i>",
                protect_content=False 
            )

            # --- AUTO DELETE TASK START ---
            asyncio.create_task(auto_delete_file(msg))
            
            # Alert Message
            alert = await message.reply_text(
                f"⏳ <b>File Sent!</b>\n\n"
                f"⚠️ Indha file <b>3 Maninerathil (3 Hours)</b> automatic-a delete aagidum.\n"
                f"Udane forward panni vechukonga!"
            )
            asyncio.create_task(auto_delete_file(alert))

        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")
            print(f"Genlink Error: {e}")
