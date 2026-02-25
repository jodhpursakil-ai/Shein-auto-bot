import os
import sqlite3
import asyncio
import random
import string
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- FLASK SERVER FOR RENDER ---
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is Running!"

def run():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = '8414508718:AAGCmAbABf8Cuo-jXyEOH_4DNLM1xpsbg14'
ADMIN_IDS = [7400310608, 7387728324]
UPI_ID = "sakildhawa1@fam"
SUPPORT_ID = "@XynxSupportbot"

# Database Setup
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, type TEXT, code TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS sales_history (id INTEGER PRIMARY KEY AUTOINCREMENT, amount INTEGER, date TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)')
conn.commit()

PRICES = {"500": 7, "1000": 70, "2000": 140, "4000": 300}

def generate_order_id():
    return "SHN-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

async def is_banned(user_id):
    cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# --- START MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_banned(user_id):
        await update.message.reply_text("❌ You are permanently banned.")
        return

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    kbd = [['🛒 Buy Vouchers', '📊 Stock Check'], ['📋 Terms & Policies', '📞 Support']]
    markup = ReplyKeyboardMarkup(kbd, resize_keyboard=True)
    
    welcome_text = "✨ ʟᴜxᴜʀʏ sʜᴇɪɴ sᴛᴏʀᴇ ✨\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\nWelcome! Select an option below:"
    await update.message.reply_text(welcome_text, reply_markup=markup)

# --- MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name

    if await is_banned(user_id): return

    # --- ADMIN COMMANDS ---
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
            if not msg:
                await update.message.reply_text("❌ Usage: /bc message")
                return
            cursor.execute("SELECT user_id FROM users")
            for u in cursor.fetchall():
                try:
                    await context.bot.send_message(chat_id=u[0], text=f"📢 **LOOT ALERT**\n\n{msg}", parse_mode='Markdown')
                except: continue
            await update.message.reply_text("✅ Broadcast Sent")
            return

    # --- USER MENU ---
    if text == '📋 Terms & Policies':
        await update.message.reply_text("📋 Terms & Conditions\n\n✅ USE QUICKLY\n✅ RECORD SCREEN FOR REPLACEMENT\n✅ SAME DAY REPLACEMENT ONLY")

    elif text == '🛒 Buy Vouchers':
        keyboard = [[InlineKeyboardButton(f"🎫 SHEIN {k} ➜ ₹{v}", callback_data=f'buy_{k}')] for k, v in PRICES.items()]
        await update.message.reply_text("💎 Select Package:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif text == '📊 Stock Check':
        stock_text = "📊 Live Stock Status\n"
        for k in PRICES.keys():
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE type=?", (k,))
            count = cursor.fetchone()[0]
            stock_text += f"{'✅' if count > 0 else '❌'} SHEIN {k}: {count}\n"
        await update.message.reply_text(stock_text)

    elif text == '📞 Support':
        await update.message.reply_text(f"📞 Contact Admin: {SUPPORT_ID}")

    # --- QTY HANDLING ---
    elif context.user_data.get('awaiting_qty') and text and text.isdigit():
        qty = int(text)
        ctype = context.user_data['selected_type']
        if ctype == "500" and qty < 5:
            await update.message.reply_text("❌ Minimum 5 required.")
            return
        
        total = PRICES[ctype] * qty
        oid = generate_order_id()
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={UPI_ID}%26am={total}%26cu=INR"
        invoice = f"📝 Invoice: `{oid}`\n💰 Total: ₹{total}\n🏦 UPI: `{UPI_ID}`\n📸 Send Screenshot Now!"
        
        await update.message.reply_photo(photo=qr, caption=invoice, parse_mode='Markdown')
        context.user_data['order_ready'] = {'oid': oid, 'type': ctype, 'qty': qty, 'amount': total, 'username': username}
        context.user_data['awaiting_qty'] = False

    # SCREENSHOT HANDLER
    elif update.message.photo and 'order_ready' in context.user_data:
        order = context.user_data['order_ready']
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"apv_{order['oid']}_{order['type']}_{order['qty']}_{user_id}_{order['amount']}_{username}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order['oid']}_{user_id}")]
        ])
        for admin in ADMIN_IDS:
            await context.bot.send_photo(chat_id=admin, photo=update.message.photo[-1].file_id, 
                                       caption=f"🔔 New Order: {order['oid']}\nUser: {order['username']}\nAmount: ₹{order['amount']}", 
                                       reply_markup=admin_kb)
        await update.message.reply_text("🚀 Screenshot Sent! Waiting for Admin.")
        del context.user_data['order_ready']

# --- CALLBACKS ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith('buy_'):
        ctype = query.data.split('_')[1]
        context.user_data['selected_type'] = ctype
        context.user_data['awaiting_qty'] = True
        await query.message.reply_text(f"🔢 Enter Quantity for SHEIN {ctype}:")
    
    elif query.data.startswith('apv_'):
        _, oid, ctype, qty, uid, amt, user = query.data.split('_')
        cursor.execute("SELECT id, code FROM inventory WHERE type=? LIMIT ?", (ctype, int(qty)))
        rows = cursor.fetchall()
        if len(rows) >= int(qty):
            codes = "\n".join([f"💎 `{r[1]}`" for r in rows])
            await context.bot.send_message(uid, f"✅ Order Delivered\nID: `{oid}`\n\n{codes}", parse_mode='Markdown')
            cursor.executemany("DELETE FROM inventory WHERE id=?", [(r[0],) for r in rows])
            conn.commit()
            await query.edit_message_caption(f"✅ Approved {oid}")
        else:
            await query.edit_message_caption("❌ Out of Stock")
    await query.answer()

def main():
    keep_alive() # Starts Flask Server
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == '__main__':
    main()
    
  
