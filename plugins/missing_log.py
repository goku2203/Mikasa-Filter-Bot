import time
import asyncio
from pyrogram import Client, filters
from database.ia_filterdb import get_search_results
from info import LOG_CHANNEL

# --- SETTINGS ---
LOG_COOLDOWN = 600  # 600 Seconds = 10 Minutes (Idha neenga mathikalam)
RECENT_REQUESTS = {}  # Inga than request save aagum

@Client.on_message(filters.group & filters.text & filters.incoming)
async def missing_movie_monitor(client, message):
    # 1. Basic Filters
    if message.text.startswith(("/", "#")):
        return
    
    query = message.text.strip()
    if len(query) < 3:
        return

    # 2. Check DUPLICATE (Spam Control)
    clean_query = query.lower() # Ellame chinna eluthu aakiduvom
    current_time = time.time()

    if clean_query in RECENT_REQUESTS:
        last_time = RECENT_REQUESTS[clean_query]
        # Time mudiyura varaikum wait pannum
        if (current_time - last_time) < LOG_COOLDOWN:
            return  # 10 nimisham aagala, so Log anuppa vendam. Stop here.

    try:
        # 3. Database Check
        results = await get_search_results(query)
        if isinstance(results, tuple):
            files = results[0]
        else:
            files = results

        # 4. If Movie MISSING -> Send Log
        if not files:
            # First, update time (Adutha 10 mins ku idhe padam log aagathu)
            RECENT_REQUESTS[clean_query] = current_time
            
            log_msg = (
                f"⚠️ **Missing Movie Detected!**\n\n"
                f"🔍 **Query:** {query}\n"
                f"👤 **User:** {message.from_user.mention}\n"
                f"📂 **Group:** {message.chat.title}\n"
                f"🆔 **User ID:** `{message.from_user.id}`\n\n"
                f"Please upload this movie soon! #Missing_Request"
            )
            
            if LOG_CHANNEL:
                await client.send_message(
                    chat_id=LOG_CHANNEL,
                    text=log_msg,
                    disable_web_page_preview=True
                )
                
    except Exception as e:
        print(f"Missing Log Error: {e}")
