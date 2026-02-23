
from pyrogram import Client, filters, enums
from pyrogram.types import *

@Client.on_message(filters.command("echo") & filters.group)
async def echo(client, message):
    # 🟢 FIX 1: Anonymous Admin Check
    # Anonymous Admin-ku 'from_user' irukkathu. Avanga eppavum Admin thaan.
    if message.from_user:
        try:
            user = await client.get_chat_member(message.chat.id, message.from_user.id)
            if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                # Silent return (User ku theriyavenam) or Reply
                return
        except Exception as error:
            await message.reply_text(f"Error checking permissions: {error}")
            return
    else:
        # Anonymous Admin (Sender Chat irukkum) - Allow panralam
        pass

    # 🟢 FIX 2: Text Iruka nu Check Pannanum (IndexError Fix)
    if len(message.command) < 2:
        await message.reply_text(
            "<b>Usage:</b> <code>/echo [Your Message]</code>\n"
            "<i>Example: /echo Hello World</i>"
        )
        return

    # Text ah pirikkirom
    text = message.text.split(None, 1)[1]

    # 🟢 FIX 3: Reply Logic Improvement
    # Reply iruntha antha message-ku reply pannum.
    # Reply illana, Group-la normal ah message anuppum.
    if message.reply_to_message:
        await message.reply_to_message.reply_text(text)
    else:
        await message.reply_text(text)

    # Command message ah delete panrom
    try:
        await message.delete()
    except:
        pass

@Client.on_message(filters.command("echo") & filters.private)
async def echoptp(client, message):
    await message.reply_text("Sorry dude This command Only work in group 😊")
