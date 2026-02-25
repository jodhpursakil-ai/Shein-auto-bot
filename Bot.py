import sqlite3
import asyncio
import random
import string
import requests
import os
from flask import Flask, request
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = '8414508718:AAGCmAbABf8Cuo-jXyEOH_4DNLM1xpsbg14'
ADMIN_IDS = [7400310608, 7387728324]
PAY0_API_KEY = "277779abe3cbe0ca5dc04065b36e19e8"
SUPPORT_ID = "@XYNX_ORL"
WELCOME_PIC = "https://i.ibb.co/Lz0x9nZ/shein-banner.jpg"

# Database Setup
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, type TEXT, code TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS sales_history (id INTEGER PRIMARY KEY AUTOINCREMENT, amount INTEGER, date TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)')
conn.commit()

PRICES = {"500": 6, "1000": 60, "2000": 120, "4000": 190}

# --- WEBHOOK SERVER (FOR AUTO DELIVERY) ---
flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get('status') in ['COMPLETED', 'SUCCESS', 'success']:
        try:
            # extra_info format: UID|TYPE|QTY|OID
            extra = data.get('extra_info').split('|')
            uid, ctype, qty, oid = int(extra[0]), extra[1], int(extra[2]), extra[3]
            amount = data.get('amount')
            
            db = sqlite3.connect('shop.db')
            cur = db.cursor()
            cur.execute("SELECT id, code FROM inventory WHERE type=? LIMIT ?", (ctype, qty))
            rows = cur.fetchall()
            
            if len(rows) >= qty:
                codes_text = "\n".join([f"💎 `{r[1]}`" for r in rows])
                # Deliver to User
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={uid}&text=✅ **ᴏʀᴅᴇʀ ᴅᴇʟɪᴠᴇʀᴇᴅ**\n🆔 ɪᴅ: `{oid}`\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n🎁 ʏᴏᴜʀ ᴄᴏᴅᴇs:\n{codes_text}\n(ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ)&parse_mode=Markdown")
                
                # Notify Admin
                admin_report = f"💰 **Auto Sale!**\nID: `{oid}`\nPack: {ctype}\nQty: {qty}\nAmount: ₹{amount}\nCodes Sent Successfully!"
                for admin in ADMIN_IDS:
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={admin}&text={admin_report}&parse_mode=Markdown")
                
                # Update DB
                cur.execute("INSERT INTO sales_history (amount, date) VALUES (?, datetime('now'))", (int(amount),))
                cur.executemany("DELETE FROM inventory WHERE id=?", [(r[0],) for r in rows])
                db.commit()
            db.close()
        except Exception as e: print(f"Webhook Error: {e}")
    return "OK", 200

# --- BOT FUNCTIONS ---
async def is_banned(user_id):
    cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_banned(user_id): return
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    kbd = [['🛒 Buy Vouchers', '📊 Stock Check'], ['📋 Terms & Policies', '📞 Support']]
    markup = ReplyKeyboardMarkup(kbd, resize_keyboard=True)
    await update.message.reply_photo(photo=WELCOME_PIC, caption="✨ ʟᴜxᴜʀʏ sʜᴇɪɴ sᴛᴏʀᴇ ✨\nWelcome! Select an option below:", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if await is_banned(user_id): return

    # --- ADMINS ---
    if user_id in ADMIN_IDS and text:
        if text.startswith('/add'):
            try:
                lines = text.split('\n')
                ctype = lines[0].split()[1]
                codes = [l.strip() for l in lines[1:] if l.strip()]
                for c in codes: cursor.execute('INSERT INTO inventory (type, code) VALUES (?, ?)', (ctype, c))
                conn.commit()
                await update.message.reply_text(f"✅ Added {len(codes)} codes to {ctype}.")
            except: await update.message.reply_text("Format: /add 500\ncode1")
            return
        elif text.startswith('/bc'):
            msg = text.split(None, 1)[1] if len(text.split()) > 1 else None
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            for u in users:
                try: await context.bot.send_message(u[0], f"📢 **LOOT ALERT**\n\n{msg}", parse_mode='Markdown')
                except: pass
            return
        elif text == '/sales':
            cursor.execute("SELECT SUM(amount), COUNT(*) FROM sales_history")
            res = cursor.fetchone()
            await update.message.reply_text(f"📈 ꜱᴀʟᴇꜱ ʀᴇᴘᴏʀᴛ\n💰 Total: ₹{res[0] or 0}\n📦 Orders: {res[1] or 0}")
            return

    # --- USERS ---
    if text == '📊 Stock Check':
        stock_text = "📊 ʟɪᴠᴇ sᴛᴏᴄᴋ sᴛᴀᴛᴜs\n"
        for k in PRICES.keys():
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE type=?", (k,))
            stock_text += f"• SHEIN {k}: {cursor.fetchone()[0]}\n"
        await update.message.reply_text(stock_text)

    elif text == '🛒 Buy Vouchers':
        keyboard = [[InlineKeyboardButton(f"🎫 SHEIN {k} ➜ ₹{v}", callback_data=f'buy_{k}')] for k, v in PRICES.items()]
        await update.message.reply_text("💎 ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴘᴀᴄᴋᴀɢᴇ:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif context.user_data.get('awaiting_qty') and text.isdigit():
        qty, ctype = int(text), context.user_data['selected_type']
        total = PRICES[ctype] * qty
        oid = "SHN-" + "".join(random.choices(string.digits, k=6))
        
        # Pay0 API Call
        try:
            api_url = "https://api.pay0.world/v1/payment/create"
            payload = {
                "api_key": PAY0_API_KEY,
                "amount": total,
                "order_id": oid,
                "extra_info": f"{user_id}|{ctype}|{qty}|{oid}",
                "redirect_url": f"https://t.me/{(await context.bot.get_me()).username}"
            }
            res = requests.post(api_url, json=payload, timeout=20).json()
            pay_link = res.get('url') or res.get('payment_url')
            
            if pay_link:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 PAY NOW", url=pay_link)]])
                await update.message.reply_text(f"📝 **ɪɴᴠᴏɪᴄᴇ:** `{oid}`\n💰 **ᴛᴏᴛᴀʟ:** ₹{total}\n\nClick below to pay:", reply_markup=kb, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Gateway Error. Try again.")
        except: await update.message.reply_text("❌ Connection Fail.")
        context.user_data['awaiting_qty'] = False

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith('buy_'):
        context.user_data['selected_type'] = query.data.split('_')[1]
        context.user_data['awaiting_qty'] = True
        await query.message.reply_text("🔢 **Enter Quantity:**")
    await query.answer()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: flask_app.run(host='0.0.0.0', port=port)).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
  
