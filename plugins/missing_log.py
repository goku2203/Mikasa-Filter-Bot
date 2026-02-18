import asyncio
from pyrogram import Client, filters, enums
from database.ia_filterdb import get_search_results
from info import LOG_CHANNEL

# Idhu Group-la vara message-a check pannum
@Client.on_message(filters.group & filters.text & filters.incoming)
async def missing_movie_monitor(client, message):
    # Commands (Example: /start, /help) vandha ignore pannidum
    if message.text.startswith("/") or message.text.startswith("#"):
        return
    
    query = message.text.strip()
    
    # Chinnatha irukkura words-a ignore pannalam (Optional)
    if len(query) < 3:
        return

    try:
        # Database la movie irukka nu check panrom
        # Note: get_search_results unga bot DB function
        results = await get_search_results(query)
        
        # Sila bots la (files, offset, total) nu return aagum.
        # So, adhai correct aana format la edukkurom.
        if isinstance(results, tuple):
            files = results[0]
        else:
            files = results

        # Padam illana mattum (If files list is empty)
        if not files:
            # Log Channel kku message anuppurom
            log_msg = (
                f"⚠️ **Missing Movie Detected!**\n\n"
                f"🔍 **Query:** {query}\n"
                f"👤 **User:** {message.from_user.mention}\n"
                f"📂 **Group:** {message.chat.title}\n"
                f"🆔 **User ID:** `{message.from_user.id}`\n\n"
                f"Please upload this movie soon! #Missing_Request"
            )
            
            # LOG_CHANNEL ID correct-a iruntha send aagum
            if LOG_CHANNEL:
                await client.send_message(
                    chat_id=LOG_CHANNEL,
                    text=log_msg,
                    disable_web_page_preview=True
                )
                
    except Exception as e:
        # Error vandha summa print pannum, bot stop aagathu
        print(f"Missing Log Error: {e}")
