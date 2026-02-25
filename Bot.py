import os
import sqlite3
import asyncio
import random
import string
import requests
from flask import Flask, request, jsonify
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = '8414508718:AAGCmAbABf8Cuo-jXyEOH_4DNLM1xpsbg14'
ADMIN_IDS = [7400310608, 7387728324]
PAY0_KEY = "277779abe3cbe0ca5dc04065b36e19e8"  # Teri API Key
PAY0_SALT = "IxxsM6jNL4844977725"               # Tera Secret
PAY0_URL = "https://api.pay0.world/order/create"

# --- DATABASE SETUP ---
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, type TEXT, code TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS orders (oid TEXT PRIMARY KEY, uid INTEGER, ctype TEXT, qty INTEGER)')
conn.commit()

PRICES = {"500": 7, "1000": 70, "2000": 140, "4000": 300}

# --- FLASK SERVER & WEBHOOK ---
app_flask = Flask('')
tg_app = None # Global for webhook access

@app_flask.route('/')
def home(): return "Bot is Running!"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Pay0 status check
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
                msg = f"✅ **PAYMENT SUCCESSFUL**\n\n🎁 Your Codes:\n{codes_text}"
                
                # Async call to send message
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(tg_app.bot.send_message(chat_id=uid, text=msg, parse_mode='Markdown'))
                
                # Cleanup
                cursor.executemany("DELETE FROM inventory WHERE id=?", [(r[0],) for r in rows])
                cursor.execute("DELETE FROM orders WHERE oid=?", (oid,))
                conn.commit()
    return "OK", 200

def run(): app_flask.run(host='0.0.0.0', port=8080)

# --- PAY0 LINK GENERATOR ---
def get_pay0_link(oid, amount, user_id):
    payload = {
        "api_key": PAY0_KEY,
        "password": PAY0_SALT,
        "order_id": oid,
        "amount": amount,
        "billing_name": str(user_id),
        "billing_phone": "9876543210",
        "billing_email": "customer@store.com",
        "redirect_url": "https://t.me/your_bot_username", # <--- Apna Bot Username yahan dalo
        "webhook_url": "https://shein-aut-bot.onrender.com/webhook" # <--- Check if this is correct
    }
    try:
        r = requests.post(PAY0_URL, json=payload)
        return r.json().get('payment_url')
    except: return None

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [['🛒 Buy Vouchers', '📊 Stock Check'], ['📋 Terms & Policies', '📞 Support']]
    await update.message.reply_text("✨ **AUTOMATIC LUXURY STORE** ✨", reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🛒 Buy Vouchers':
        keyboard = [[InlineKeyboardButton(f"🎫 SHEIN {k} ➜ ₹{v}", callback_data=f'buy_{k}')] for k, v in PRICES.items()]
        await update.message.reply_text("💎 Select Package:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif context.user_data.get('awaiting_qty') and text and text.isdigit():
        qty = int(text)
        ctype = context.user_data['selected_type']
        amt = PRICES[ctype] * qty
        oid = "SHN-" + ''.join(random.choices(string.digits, k=6))
        
        # Save order info for webhook
        cursor.execute("INSERT INTO orders (oid, uid, ctype, qty) VALUES (?, ?, ?, ?)", (oid, user_id, ctype, qty))
        conn.commit()
        
        pay_link = get_pay0_link(oid, amt, user_id)
        if pay_link:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 PAY NOW (Automatic)", url=pay_link)]])
            await update.message.reply_text(f"📝 Order: `{oid}`\n💰 Total: ₹{amt}\n\nPayment karte hi codes mil jayenge!", reply_markup=kb, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Gateway Error. Try again later.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith('buy_'):
        context.user_data['selected_type'] = query.data.split('_')[1]
        context.user_data['awaiting_qty'] = True
        await query.message.reply_text(f"🔢 Enter Quantity:")
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
        
