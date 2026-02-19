import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from info import LOG_CHANNEL

# --- HELPER FUNCTION FOR AUTO DELETE ---
async def auto_delete(message, time_seconds=10):
    await asyncio.sleep(time_seconds)
    try:
        await message.delete()
    except:
        pass

# Function to handle feedback and bug reporting
@Client.on_message(filters.command(["bug", "bugs", "feedback"]))
async def bug_handler(client: Client, message: Message):
    # 🟢 FIX 1: Anonymous Admin Check (Group la ID theriyathu, athanala crash aagum)
    if message.from_user:
        user_mention = message.from_user.mention
        user_id = message.from_user.id
    else:
        user_mention = "Anonymous Admin 🛡️"
        user_id = "Unknown"

    # 🟢 FIX 2: Chat Title Check (Private Chat la Title None ah irukkum)
    if message.chat.type != enums.ChatType.PRIVATE:
        chat_title = message.chat.title
    else:
        chat_title = "Private Chat"

    try:
        # Check if the command has additional arguments or a reply to a message
        if len(message.command) < 2:
            if message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
                bug_report = message.reply_to_message.text or message.reply_to_message.caption
            else:
                msg = await message.reply_text(
                    "<b>Useage:</b>\n"
                    "/bug <i>Your Report Here</i>\n"
                    "OR Reply to a message with /bug"
                )
                asyncio.create_task(auto_delete(msg, 10))
                return
        else:
            # 🟢 FIX 3: Caption Support (Photo ku keela command pota work aaganum)
            text_content = message.text or message.caption
            if text_content:
                bug_report = text_content.split(" ", 1)[1].strip()
            else:
                bug_report = ""

        # Check for empty bug reports
        if not bug_report:
            msg = await message.reply_text("The bug description cannot be empty. Please try again.")
            asyncio.create_task(auto_delete(msg, 10))
            return

        # Construct the acknowledgment message
        response_message = (
            f"Hi {user_mention},\n"
            "Thank you for reporting the issue. It has been forwarded to the developer."
        )
        
        msg = await message.reply_text(response_message)
        asyncio.create_task(auto_delete(msg, 20))

        # Log the bug report to the designated channel
        log_message = (
            f"#BugReport\n\n"
            f"**User:** {user_mention} ([User ID: {user_id}])\n"
            f"**Chat:** {chat_title}\n"
            f"**Chat ID:** {message.chat.id}\n"
            f"**Bug Description:**\n{bug_report}"
        )
        
        # 🟢 FIX 4: Log Channel Validation (Log channel illana crash aaga koodathu)
        if LOG_CHANNEL:
            try:
                await client.send_message(LOG_CHANNEL, text=log_message)
            except Exception as log_error:
                print(f"Failed to send log: {log_error}")
        
    except Exception as e:
        # Error handling and reporting to developers
        msg = await message.reply_text(
            "An unexpected error occurred while processing your request. Please try again later."
        )
        asyncio.create_task(auto_delete(msg, 10))
        
        # 🟢 FIX 5: Safe Error Logging (Error log pannum pothum crash aaga koodathu)
        if LOG_CHANNEL:
            try:
                error_message = (
                    f"#Error\n\n"
                    f"**Error occurred in bug handler:**\n{str(e)}\n\n"
                    f"**User:** {user_mention}\n"
                    f"**Chat ID:** {message.chat.id}"
                )
                await client.send_message(LOG_CHANNEL, text=error_message)
            except:
                pass
