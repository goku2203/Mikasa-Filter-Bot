# ... (mel ulla imports matrum matha functions apdiye irukkatum)

# 👇👇 REPLACE ONLY THIS FUNCTION 👇👇
async def auto_filter(client, msg, spoll=False):
    try: # 🟢 ADDED TRY BLOCK TO CATCH THE EXACT ERROR
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
                
                print(f"✅ AUTO-FILTER STARTED FOR GROUP: {message.chat.title} | QUERY: {search}") # DEBUG PRINT
                
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
                    if settings["spell_check"]:
                        await search_msg.edit(f"<b>❌ Not Found in DB...</b>\n<i>Checking Google for Spelling... 🌏</i>")
                        await asyncio.sleep(0.5) 
                        await search_msg.delete() 
                        return await advantage_spell_chok(client, msg)
                    else:
                        await search_msg.edit(
                            f"<b>❌ No Results Found!</b>\n\n"
                            f"<i>Couldn't find '<b>{search}</b>' in my database.</i>\n"
                            f"Please check the spelling or Request to Admin."
                        )
                        await asyncio.sleep(10)
                        await search_msg.delete()
                        return
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
            if settings["button"]:
                btn = [
                    [
                        InlineKeyboardButton(
                            text=f"📂[{get_size(file.file_size)}]--{file.file_name}", callback_data=f'{pre}#{file.file_id}'
                        ),
                    ]
                    for file in files
                ]
            else:
                btn = [
                    [
                        InlineKeyboardButton(
                            text=f"{file.file_name}",
                            callback_data=f'{pre}#{file.file_id}',
                        ),
                        InlineKeyboardButton(
                            text=f"{get_size(file.file_size)}",
                            callback_data=f'{pre}#{file.file_id}',
                        ),
                    ]
                    for file in files
                ]
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

        print(f"✅ CAPTION READY: IMDB={bool(imdb)}") # DEBUG PRINT

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
                logger.exception(f"IMDB POSTER ERROR: {e}") # CHANGED TO SHOW ERROR
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
            
    except Exception as final_error:
         print(f"❌ CRITICAL ERROR IN AUTO_FILTER: {final_error}") # THIS WILL CATCH THE SILENT CRASH
         logger.exception(f"CRITICAL ERROR IN AUTO_FILTER: {final_error}")

# ... (keela ulla matha functions apdiye irukkatum)
