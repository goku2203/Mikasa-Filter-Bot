class script(object):
    START_TXT = """<b>👋 Hello {}!</b>
    
<b>I am an Advanced Auto-Filter Bot. 🤖</b>

<i>I can provide Movies, Series, and Anime directly in your groups with high speed! ⚡</i>

<b>👇 How to use me?</b>
1. Add me to your group.
2. Make me an <b>Admin</b>.
3. Enjoy unlimited files! 🎬

<i>Click the buttons below to explore more.</i>"""

    HELP_TXT = """<b>⚙️ Help & System Status</b>

<b>👤 User:</b> {}
<b>📡 Server:</b> Free Tier (Experimental) ⚠️

<i>I am currently running on a free server, so I might be a little slow. Please be patient! 🐢</i>

<b>🚫 Important:</b>
Please <b>Don't Spam</b> commands, or I might crash (die) 😵.

<b>👇 Choose a category below:</b>"""

    ABOUT_TXT = """<b>✯ 𝙼𝚈 𝙿𝚁𝙾𝙵𝙸𝙻𝙴 ✯</b>

<b>🤖 𝐍𝐚𝐦𝐞: {}</b>
<b>👑 𝐂𝐫𝐞𝐚𝐭𝐨𝐫: <a href="https://t.me/Goku_Stark">Goku Stark</a></b>
<b>💻 𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞: Python 3</b>
<b>💾 𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞: MongoDB</b>
<b>📡 𝐒𝐞𝐫𝐯𝐞𝐫: Koyeb</b>"""

    SOURCE_TXT = """<b>🛠️ Source Code</b>

<i>This project is Open Source. You can find the code below.</i>

<b>👨‍💻 Developer:</b> <a href="https://t.me/Goku_Stark">Goku Stark</a>
<b>📂 Repository:</b> <a href="https://t.me/Goku_Stark">Click Here</a>"""

    MANUALFILTER_TXT = """<b>🛠️ Manual Filters Help</b>

<i>Filters allow the bot to reply automatically when a specific keyword is detected.</i>

<b>📝 Rules:</b>
1. Bot must be an <b>Admin</b>.
2. Only Admins can set filters.
3. Buttons have a 64-character limit.

<b>🎮 Commands:</b>
• /filter - <code>Add a new filter</code>
• /filters - <code>List all active filters</code>
• /del - <code>Delete a specific filter</code>
• /delall - <code>Delete all filters (Owner only)</code>"""

    BUTTON_TXT = """<b>🔘 Button Formatting Help</b>

<i>I support both URL and Alert (Pop-up) buttons.</i>

<b>⚠️ Note:</b> Buttons must have content (text/media).

<b>1️⃣ URL Button Format:</b>
<code>[Button Text](buttonurl:https://t.me/Goku_Stark)</code>

<b>2️⃣ Alert Button Format:</b>
<code>[Button Text](buttonalert:This is a pop-up message!)</code>"""

    AUTOFILTER_TXT = """<b>🤖 Auto-Filter Guide</b>

<b>1️⃣ For Private Channels:</b>
• Make me an <b>Admin</b> in your channel.
• Ensure the channel has <b>NO</b> porn/fake files.
• Forward the last message from your channel to me (with quotes).
• I will index all files automatically! 📂

<b>2️⃣ For Groups:</b>
• Add me as an <b>Admin</b>.
• Use <code>/connect</code> to link your group to my PM.
• Use <code>/settings</code> in PM to enable Auto-Filter.
"""

    CONNECTION_TXT = """<b>🔗 Connection Manager</b>

<i>Connect your groups to my PM to manage filters easily and avoid spam.</i>

<b>🎮 Commands:</b>
• /connect - <code>Connect a group to PM</code>
• /disconnect - <code>Disconnect a group</code>
• /connections - <code>View active connections</code>"""

    EXTRAMOD_TXT = """<b>🧩 Extra Modules</b>

<i>Here are some cool extra features I offer!</i>

<b>🎮 Commands:</b>
• /id - <code>Get User ID</code>
• /info - <code>Get User Info</code>
• /imdb - <code>Search IMDb Details</code>
• /search - <code>Search across sources</code>
• /ping - <code>Check Bot Latency</code>
• /stats - <code>Check Bot Statistics</code>"""

    ADMIN_TXT = """<b>🛡️ Admin Control Panel</b>

<i>Commands strictly for Bot Admins only.</i>

<b>🎮 Commands:</b>
• /logs - <code>View Error Logs</code>
• /stats - <code>Database Statistics</code>
• /delete - <code>Delete file from DB</code>
• /users - <code>List all users</code>
• /chats - <code>List all groups</code>
• /ban - <code>Ban a user</code>
• /unban - <code>Unban a user</code>
• /broadcast - <code>Send message to all users</code>"""

    STATUS_TXT = """<b>📊 <u>Database Statistics</u></b>

<b>📂 Total Files:</b> <code>{}</code>
<b>👤 Total Users:</b> <code>{}</code>
<b>👥 Total Chats:</b> <code>{}</code>
<b>💾 Used Storage:</b> <code>{}</code>
<b>🆓 Free Storage:</b> <code>{}</code>"""

    LOG_TEXT_G = """<b>#NewGroupDetected 👥</b>
    
<b>🏷 Name:</b> {}
<b>🆔 ID:</b> <code>{}</code>
<b>🔢 Members:</b> <code>{}</code>
<b>👤 Added By:</b> {}"""

    LOG_TEXT_P = """<b>#NewUserDetected 👤</b>
    
<b>🆔 ID:</b> <code>{}</code>
<b>🏷 Name:</b> {}"""

    RESULT_TXT = """<blockquote><b>⚡ Found something for you!</b></blockquote>
<i>Check the results below:</i>"""

    CUSTOM_FILE_CAPTION = """<b>📂 File: {file_name}</b>
<b>💾 Size: {file_size}</b>

━━━━━━━━━━━━━━━━━━━━
<b>📢 Join Our Channels:</b>
🔥 [Anime Channel](https://t.me/Anime_single)
🤖 [Tech Channel](https://t.me/tamiltechgkofficial)
━━━━━━━━━━━━━━━━━━━━

<b>⚠️ COPYRIGHT WARNING ⚠️</b>
<blockquote>This message will <b>AUTO-DELETE</b> in <b>1 Minute</b> to prevent copyright strikes! ⏳
<b>Please forward or save this file immediately!</b></blockquote>"""

    RESTART_GC_TXT = """<b>♻️ System Restarted!</b>

<b>📅 Date:</b> <code>{}</code>
<b>⏰ Time:</b> <code>{}</code>
<b>🌐 Zone:</b> <code>Asia/Kolkata</code>
<b>🛠️ Version:</b> <code>v2.0 [Stable]</code>"""

    SPOLL_NOT_FND = """<b>❌ No Results Found</b>

<i>I couldn't find what you are looking for.</i> ☹️

<b>💡 Search Tips:</b>
1️⃣ Check your spelling.
2️⃣ Use format: <code>[Movie Name] [Year]</code>
3️⃣ Don't ask for unreleased movies.

<i>If you think this is an error, report to Admin using /bugs.</i>"""

    # SPELL CHECK LANGUAGES
    ENG_SPELL = """<b>💡 Spelling Check (English)</b>
    
1️⃣ Use correct spelling.
2️⃣ Check if the movie is released on OTT.
3️⃣ Try: <code>Movie Name Year</code>"""

    MAL_SPELL = """<b>💡 അക്ഷരത്തെറ്റ് പരിശോധന (Malayalam)</b>
    
1️⃣ ശരിയായ സ്പെല്ലിംഗ് ഉപയോഗിക്കുക.
2️⃣ OTT-യിൽ റിലീസ് ചെയ്തിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.
3️⃣ ശ്രമിക്കുക: <code>Movie Name Year</code>"""

    HIN_SPELL = """<b>💡 वर्तनी जाँच (Hindi)</b>
    
1️⃣ सही वर्तनी का प्रयोग करें।
2️⃣ जांचें कि क्या फिल्म ओटीटी पर रिलीज हुई है।
3️⃣ प्रयास करें: <code>Movie Name Year</code>"""

    TAM_SPELL = """<b>💡 எழுத்துப்பிழை சரிபார்ப்பு (Tamil)</b>
    
1️⃣ சரியான எழுத்துப்பிழையை பயன்படுத்தவும்.
2️⃣ படம் OTT இல் வெளியாகிவிட்டதா என சரிபார்க்கவும்.
3️⃣ முயற்சிக்கவும்: <code>Movie Name Year</code>"""

    CHK_MOV_ALRT = """<b>♻️ Checking Database... Please Wait! ♻️</b>"""

    OLD_MES = """<b>⚠️ Request Expired!</b>
    
<i>You are clicking an old message. Please request the file again.</i> 🔄"""

    MOV_NT_FND = """<b>❌ Movie Not Found!</b>

<i>This movie is not yet released or not added to my database.</i>

<pre>Use /bugs to request this movie.</pre>"""

    RESTART_TXT = """<b>✅ Bot Restarted Successfully!</b>"""
