import os
import sqlite3
import asyncio
import random
import string
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- FLASK SERVER ---
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Luxury Bot is Live!"

def run(): app_flask.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = '8414508718:AAGCmAbABf8Cuo-jXyEOH_4DNLM1xpsbg14'
ADMIN_IDS = [7400310608, 7387728324]
UPI_ID = "sakildhawa1@fam"
SUPPORT_ID = "@xyxnSupportbot"

# Database Setup
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, type TEXT, code TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
conn.commit()

PRICES = {"500": 8, "1000": 75, "2000": 160, "4000": 300}

# --- START MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    kbd = [['🛒 𝐁𝐮𝐲 𝐕𝐨𝐮𝐜𝐡𝐞𝐫𝐬', '📊 𝐒𝐭𝐨𝐜𝐤 𝐂𝐡𝐞𝐜𝐤'], ['📋 𝐓𝐞𝐫𝐦𝐬 & 𝐏𝐨𝐥𝐢𝐜𝐢𝐞𝐬', '📞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭']]
    welcome = (
        "✨ 𝐋𝐔𝐗𝐔𝐑𝐘 𝐒𝐇𝐄𝐈𝐍 𝐒𝐓𝐎𝐑𝐄 ✨\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        "ᴡᴇʟᴄᴏᴍᴇ! sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ sʜᴏᴘᴘɪɴɢ. 🛍️"
    )
    await update.message.reply_text(welcome, reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True))

# --- MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # ADMIN: ADD STOCK
    if user_id in ADMIN_IDS and text and text.startswith('/add'):
        try:
            parts = text.split('\n')
            ctype = parts[0].split()[1]
            codes = [p.strip() for p in parts[1:] if p.strip()]
            for c in codes: cursor.execute('INSERT INTO inventory (type, code) VALUES (?, ?)', (ctype, c))
            conn.commit()
            await update.message.reply_text(f"✅ Added {len(codes)} codes to {ctype}.")
        except: await update.message.reply_text("Format: /add 500\ncode1")
        return

    # ADMIN: BROADCAST (/bc)
    if user_id in ADMIN_IDS and text and text.startswith('/bc'):
        msg = text[3:].strip()
        if not msg:
            await update.message.reply_text("Format: /bc Message")
            return
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        count = 0
        for u in users:
            try:
                await context.bot.send_message(chat_id=u[0], text=f"🔔 𝐀𝐍𝐍𝐎𝐔𝐍𝐂𝐄𝐌𝐄𝐍𝐓\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n{msg}")
                count += 1
            except: pass
        await update.message.reply_text(f"✅ Broadcast sent to {count} users.")
        return

    # USER MENU
    if text == '🛒 𝐁𝐮𝐲 𝐕𝐨𝐮𝐜𝐡𝐞𝐫𝐬':
        keyboard = [[InlineKeyboardButton(f"🎫 𝐒𝐇𝐄𝐈𝐍 {k} ➜ ₹{v}", callback_data=f'buy_{k}')] for k, v in PRICES.items()]
        await update.message.reply_text("💎 𝐒𝐞𝐥𝐞𝐜𝐭 𝐘𝐨𝐮𝐫 𝐏𝐚𝐜𝐤𝐚𝐠𝐞:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif text == '📊 𝐒𝐭𝐨𝐜𝐤 𝐂𝐡𝐞𝐜𝐤':
        stock = "📊 𝐋𝐢𝐯𝐞 𝐒𝐭𝐨𝐜𝐤 𝐒𝐭𝐚𝐭𝐮𝐬:\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        for k in PRICES.keys():
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE type=?", (k,))
            stock += f"• 𝐒𝐇𝐄𝐈𝐍 {k}: {cursor.fetchone()[0]}\n"
        await update.message.reply_text(stock)

    elif text == '📋 𝐓𝐞𝐫𝐦𝐬 & 𝐏𝐨𝐥𝐢𝐜𝐢𝐞𝐬':
        terms = (
            "📋 𝐓𝐞𝐫𝐦𝐬 & 𝐏𝐨𝐥𝐢𝐜𝐢𝐞𝐬\n"
            "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            "✅ Codes work after 15 minutes of delivery\n"
            "✅ Replacement possible but need video of buying to apply\n"
            "✅ Under 1 hour replacement only\n"
            "❌ No replacement for SHEIN 500 pack\n"
            "✅ Contact admin for any issues"
        )
        await update.message.reply_text(terms)

    elif text == '📞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭':
        await update.message.reply_text(f"📞 𝐂𝐨𝐧𝐭𝐚𝐜𝐭 𝐀𝐝𝐦𝐢𝐧: {SUPPORT_ID}")

    # QUANTITY & QR
    elif context.user_data.get('awaiting_qty') and text and text.isdigit():
        qty = int(text)
        ctype = context.user_data['selected_type']
        
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE type=?", (ctype,))
        available = cursor.fetchone()[0]
        
        if qty > available:
            await update.message.reply_text(f"❌ Sirf {available} quantity available hai.")
            return

        if ctype == "500" and qty < 5:
            await update.message.reply_text("❌ Minimum 5 quantity required for SHEIN 500.")
            return
            
        amt = PRICES[ctype] * qty
        oid = "SHN-" + ''.join(random.choices(string.digits, k=6))
        
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={UPI_ID}%26pn=LuxuryStore%26am={amt}%26cu=INR"
        invoice = (
            f"📝 𝐈𝐍𝐕𝐎𝐈𝐂𝐄: {oid}\n"
            f"💰 𝐓𝐎𝐓𝐀𝐋: ₹{amt}\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"📸 ᴘᴀʏᴍᴇɴᴛ ᴋᴇ ʙᴀᴀᴅ sᴄʀᴇᴇɴsʜᴏᴛ ʙʜᴇᴊɪᴇɴ!"
        )
        await update.message.reply_photo(photo=qr, caption=invoice)
        context.user_data['order_ready'] = {'type': ctype, 'qty': qty, 'amt': amt, 'oid': oid}
        context.user_data['awaiting_qty'] = False

    # SCREENSHOT HANDLER
    elif update.message.photo and 'order_ready' in context.user_data:
        order = context.user_data['order_ready']
        cb_data = f"apv_{order['type']}_{order['qty']}_{user_id}"
        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=cb_data),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
        ]])
        for admin in ADMIN_IDS:
            await context.bot.send_photo(
                chat_id=admin, 
                photo=update.message.photo[-1].file_id, 
                caption=f"🔔 𝐍𝐄𝐖 𝐎𝐑𝐃𝐄𝐑\n🆔 {order['oid']}\n💰 Amt: ₹{order['amt']}\n👤 User: {user_id}",
                reply_markup=admin_kb
            )
        await update.message.reply_text("🚀 𝐒𝐜𝐫𝐞𝐞𝐧𝐬𝐡𝐨𝐭 𝐒𝐞𝐧𝐭! ᴡᴀɪᴛ ғᴏʀ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ.")
        del context.user_data['order_ready']

# --- CALLBACKS ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    d = query.data.split('_')
    
    if d[0] == 'buy':
        ctype = d[1]
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE type=?", (ctype,))
        available = cursor.fetchone()[0]
        
        if available == 0:
            await query.answer("❌ Out of Stock! Abhi is pack ke codes nahi hain.", show_alert=True)
            return
            
        context.user_data['selected_type'] = ctype
        context.user_data['awaiting_qty'] = True
        await query.message.reply_text(f"🔢 𝐄𝐧𝐭𝐞𝐫 𝐐𝐮𝐚𝐧𝐭𝐢𝐭𝐲 (Available: {available}):")
    
    elif d[0] == 'apv':
        ctype, qty, uid = d[1], int(d[2]), int(d[3])
        cursor.execute("SELECT id, code FROM inventory WHERE type=? LIMIT ?", (ctype, qty))
        rows = cursor.fetchall()
        if len(rows) >= qty:
            codes = "\n".join([f"💎 {r[1]}" for r in rows])
            await context.bot.send_message(uid, f"✅ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐀𝐏𝐏𝐑𝐎𝐕𝐄𝐃\n\n{codes}")
            cursor.executemany("DELETE FROM inventory WHERE id=?", [(r[0],) for r in rows])
            conn.commit()
            await query.edit_message_caption("✅ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 & 𝐃𝐞𝐥𝐢𝐯𝐞𝐫𝐞𝐝!")
        else: await query.answer("❌ Out of Stock!", show_alert=True)
    
    elif d[0] == 'rej':
        await context.bot.send_message(int(d[1]), "❌ 𝐏𝐚𝐲𝐦𝐞𝐧𝐭 𝐑𝐞𝐣𝐞𝐜𝐭𝐞𝐝!")
        await query.edit_message_caption("❌ 𝐎𝐫𝐝𝐞𝐫 𝐑𝐞𝐣𝐞𝐜𝐭𝐞𝐝.")
    
    await query.answer()

def main():
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == '__main__': main()
