import os
import sqlite3
import asyncio
import random
import string
import requests
from flask import Flask, request
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = '8414508718:AAGCmAbABf8Cuo-jXyEOH_4DNLM1xpsbg14'
ADMIN_IDS = [7400310608, 7387728324]
PAY0_KEY = "277779abe3cbe0ca5dc04065b36e19e8"
PAY0_SALT = "IxxsM6jNL4844977725"
WEBHOOK_URL = "https://shein-auto-bot.onrender.com/webhook"

# --- FLASK SERVER (For Auto-Delivery) ---
app_flask = Flask('')
tg_app = None

@app_flask.route('/')
def home(): return "✨ Luxury Bot is Live!"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get('status') == 'COMPLETED':
        oid = data.get('order_id')
        cursor.execute("SELECT uid, ctype, qty FROM orders WHERE oid = ?", (oid,))
        order = cursor.fetchone()
        if order:
            uid, ctype, qty = order
            cursor.execute("SELECT id, code FROM inventory WHERE type=? LIMIT ?", (ctype, qty))
            rows = cursor.fetchall()
            if len(rows) >= qty:
                codes_text = "\n".join([f"💎 `{r[1]}`" for r in rows])
                msg = (
                    f"✨ **𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐂𝐎𝐍𝐅𝐈𝐑𝐌𝐄𝐃** ✨\n"
                    f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                    f"🎁 **𝐘𝐨𝐮𝐫 𝐒𝐇𝐄𝐈𝐍 𝐂𝐨𝐝𝐞𝐬:**\n\n{codes_text}\n\n"
                    f"✅ **𝐓𝐡𝐚𝐧𝐤𝐬 𝐟𝐨𝐫 𝐒𝐡𝐨𝐩𝐩𝐢𝐧𝐠!**"
                )
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(tg_app.bot.send_message(chat_id=uid, text=msg, parse_mode='Markdown'))
                cursor.executemany("DELETE FROM inventory WHERE id=?", [(r[0],) for r in rows])
                cursor.execute("DELETE FROM orders WHERE oid=?", (oid,))
                conn.commit()
    return "OK", 200

def run(): app_flask.run(host='0.0.0.0', port=8080)

# --- DATABASE ---
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, type TEXT, code TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS orders (oid TEXT PRIMARY KEY, uid INTEGER, ctype TEXT, qty INTEGER)')
conn.commit()

PRICES = {"500": 7, "1000": 70, "2000": 140, "4000": 300}

# --- START MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [['🛒 𝐁𝐮𝐲 𝐕𝐨𝐮𝐜𝐡𝐞𝐫𝐬', '📊 𝐒𝐭𝐨𝐜𝐤 𝐂𝐡𝐞𝐜𝐤'], ['📋 𝐓𝐞𝐫𝐦𝐬', '📞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭']]
    welcome = (
        "✨ **𝐋𝐔𝐗𝐔𝐑𝐘 𝐒𝐇𝐄𝐈𝐍 𝐒𝐓𝐎𝐑𝐄** ✨\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        "Welcome! Selection an option below to start shopping. 🛍️"
    )
    await update.message.reply_text(welcome, reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True), parse_mode='Markdown')

# --- HANDLERS ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if user_id in ADMIN_IDS and text and text.startswith('/add'):
        try:
            lines = text.split('\n')
            ctype = lines[0].split()[1]
            codes = [l.strip() for l in lines[1:] if l.strip()]
            for c in codes: cursor.execute('INSERT INTO inventory (type, code) VALUES (?, ?)', (ctype, c))
            conn.commit()
            await update.message.reply_text(f"✅ Added {len(codes)} codes to {ctype}.")
        except: await update.message.reply_text("Format: /add 500\ncode1")
        return

    if text == '🛒 𝐁𝐮𝐲 𝐕𝐨𝐮𝐜𝐡𝐞𝐫𝐬':
        keyboard = [[InlineKeyboardButton(f"🎫 𝐒𝐇𝐄𝐈𝐍 {k} ➜ ₹{v}", callback_data=f'buy_{k}')] for k, v in PRICES.items()]
        await update.message.reply_text("💎 **𝐒𝐞𝐥𝐞𝐜𝐭 𝐘𝐨𝐮𝐫 𝐏𝐚𝐜𝐤𝐚𝐠𝐞:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif text == '📊 𝐒𝐭𝐨𝐜𝐤 𝐂𝐡𝐞𝐜𝐤':
        stock = "📊 **𝐋𝐢𝐯𝐞 𝐒𝐭𝐨𝐜𝐤 𝐒𝐭𝐚𝐭𝐮𝐬:**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        for k in PRICES.keys():
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE type=?", (k,))
            stock += f"• 𝐒𝐇𝐄𝐈𝐍 {k}: `{cursor.fetchone()[0]}`\n"
        await update.message.reply_text(stock, parse_mode='Markdown')

    elif context.user_data.get('awaiting_qty') and text and text.isdigit():
        qty = int(text)
        ctype = context.user_data['selected_type']
        amt = PRICES[ctype] * qty
        oid = "SHN-" + ''.join(random.choices(string.digits, k=6))
        
        cursor.execute("INSERT INTO orders (oid, uid, ctype, qty) VALUES (?, ?, ?, ?)", (oid, user_id, ctype, qty))
        conn.commit()
        
        payload = {
            "api_key": PAY0_KEY, "password": PAY0_SALT, "order_id": oid, "amount": amt,
            "billing_name": str(user_id), "billing_phone": "9876543210", "billing_email": "a@b.com",
            "redirect_url": "https://t.me/your_bot_username", "webhook_url": WEBHOOK_URL
        }
        try:
            r = requests.post("https://api.pay0.world/order/create", json=payload).json()
            pay_url = r.get('payment_url')
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 𝐏𝐀𝐘 𝐍𝐎𝐖 (𝐀𝐮𝐭𝐨)", url=pay_url)]])
            invoice = (
                f"📝 **𝐈𝐍𝐕𝐎𝐈𝐂𝐄:** `{oid}`\n"
                f"💰 **𝐀𝐌𝐎𝐔𝐍𝐓:** ₹{amt}\n"
                f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                f"⚡ Payment confirm hote hi codes mil jayenge!"
            )
            await update.message.reply_text(invoice, reply_markup=kb, parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ **𝐆𝐚𝐭𝐞𝐰𝐚𝐲 𝐄𝐫𝐫𝐨𝐫!** Try again later.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith('buy_'):
        context.user_data['selected_type'] = query.data.split('_')[1]
        context.user_data['awaiting_qty'] = True
        await query.message.reply_text(f"🔢 **𝐄𝐧𝐭𝐞𝐫 𝐐𝐮𝐚𝐧𝐭𝐢𝐭𝐲:**")
    await query.answer()

def main():
    global tg_app
    Thread(target=run).start()
    tg_app = Application.builder().token(TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.TEXT, handle_message))
    tg_app.add_handler(CallbackQueryHandler(handle_callback))
    tg_app.run_polling()

if __name__ == '__main__': main()
    
