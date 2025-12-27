# websocket_bot.py
import asyncio
import json
import os
from websockets import serve
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, GROUP_ID, WS_PORT, TMP_DIR

os.makedirs(TMP_DIR, exist_ok=True)
bot = Bot(token=BOT_TOKEN)
VISITORS = {}

# Telegram handler
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.chat_id != GROUP_ID:
        return

    origin = msg.reply_to_message.text if msg.reply_to_message else msg.reply_to_message.caption if msg.reply_to_message else ""
    if "Visitor" not in origin:
        return

    session = origin.split("Visitor ")[1].split()[0]
    payload = {}

    if msg.text:
        payload = {"type": "text", "text": msg.text}
    if msg.voice:
        file = await bot.get_file(msg.voice.file_id)
        payload = {"type": "voice", "file_path": file.file_path}
    if msg.document:
        file = await bot.get_file(msg.document.file_id)
        payload = {"type": "file", "file_path": file.file_path}

    ws = VISITORS.get(session)
    if ws:
        await ws.send(json.dumps(payload))

# WebSocket handler
async def ws_handler(websocket):
    init = await websocket.recv()
    init_data = json.loads(init)
    session = init_data.get("session")
    if not session:
        await websocket.close()
        return

    VISITORS[session] = websocket
    await bot.send_message(chat_id=GROUP_ID, text=f"Visitor {session} connected")

    try:
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "text":
                await bot.send_message(chat_id=GROUP_ID, text=f"Visitor {session}\n\n{data['text']}")
            elif data["type"] == "voice":
                file_path = os.path.join(TMP_DIR, f"{session}.ogg")
                with open(file_path, "wb") as f:
                    f.write(bytes(data["file"]))
                await bot.send_voice(chat_id=GROUP_ID, voice=open(file_path, "rb"), caption=f"Visitor {session}")
            elif data["type"] == "file":
                filename = data.get("name", "file")
                file_path = os.path.join(TMP_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(bytes(data["file"]))
                await bot.send_document(chat_id=GROUP_ID, document=open(file_path, "rb"), caption=f"Visitor {session}")
    except Exception as e:
        print(f"Error session {session}: {e}")
    finally:
        if session in VISITORS:
            del VISITORS[session]

# Main
async def main():
    port = int(os.environ.get("PORT", WS_PORT))
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & (~filters.User(username=None)), handle_admin))
    ws_server = serve(ws_handler, "0.0.0.0", port)
    await asyncio.gather(ws_server, app.run_polling())

if __name__ == "__main__":
    asyncio.run(main())
