import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS
from database.ia_filterdb import get_file_details, unpack_new_file_id
from utils import temp

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

            # FIX: Using correct function name 'get_file_details'
            file_details_list = await get_file_details(file_id)
            
            if not file_details_list:
                await message.reply_text("❌ File Not Found or Deleted!")
                return

            # FIX: Get first item from list
            file_info = file_details_list[0]

            # Send the File
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                # FIX: Using .file_name (Object notation)
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

