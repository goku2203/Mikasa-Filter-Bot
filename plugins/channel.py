from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video | filters.audio


@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption
    # --- INGA MAATHUNGA ---
    
    # Unga Backup Tamil Movie Channel ID-a inga podunga
    MOVIE_CHANNEL_ID = -1001999941677  
    
    # Condition: Idhu Movie Channel-a iruntha mattum save pannu
    if message.chat.id == MOVIE_CHANNEL_ID:
        await save_file(media)
    
    # Anime channel-a iruntha 'save_file' run aagathu, so update-um pogathu.
