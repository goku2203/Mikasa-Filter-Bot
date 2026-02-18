import asyncio
from pyrogram import Client, filters
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
    try:
        # Check if the command has additional arguments or a reply to a message
        if len(message.command) < 2:
            if message.reply_to_message and message.reply_to_message.text:
                bug_report = message.reply_to_message.text.strip()
            else:
                # --- CHANGE 1: ERROR MESSAGE AUTO DELETE ---
                msg = await message.reply_text(
                    "Please reply to a text message or provide a description of the bug."
                )
                # 10 Seconds la delete aagum
                asyncio.create_task(auto_delete(msg, 10))
                return
        else:
            bug_report = message.text.split(" ", 1)[1].strip()

        # Check for empty bug reports
        if not bug_report:
            # --- CHANGE 2: EMPTY ERROR AUTO DELETE ---
            msg = await message.reply_text("The bug description cannot be empty. Please try again.")
            asyncio.create_task(auto_delete(msg, 10))
            return

        # Construct the acknowledgment message
        response_message = (
            f"Hi {message.from_user.mention},\n"
            "Thank you for reporting the issue. It has been forwarded to the developer."
        )
        
        # --- CHANGE 3: SUCCESS MESSAGE AUTO DELETE ---
        msg = await message.reply_text(response_message)
        # Idhu 20 seconds la delete aagum (User padikka time venum la)
        asyncio.create_task(auto_delete(msg, 20))

        # Log the bug report to the designated channel
        log_message = (
            f"#BugReport\n\n"
            f"**User:** {message.from_user.mention} ([User ID: {message.from_user.id}])\n"
            f"**Chat:** {message.chat.title if message.chat.type != 'private' else 'Private Chat'}\n"
            f"**Chat ID:** {message.chat.id}\n"
            f"**Bug Description:**\n{bug_report}"
        )
        await client.send_message(LOG_CHANNEL, text=log_message)

    except Exception as e:
        # Error handling and reporting to developers
        msg = await message.reply_text(
            "An unexpected error occurred while processing your request. Please try again later."
        )
        asyncio.create_task(auto_delete(msg, 10))
        
        error_message = (
            f"#Error\n\n"
            f"**Error occurred in bug handler:**\n{str(e)}\n\n"
            f"**User:** {message.from_user.mention} ([User ID: {message.from_user.id}])\n"
            f"**Chat ID:** {message.chat.id}"
        )
        await client.send_message(LOG_CHANNEL, text=error_message)
