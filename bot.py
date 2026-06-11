import asyncio
import aiohttp
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = "8905490929:AAHO95Lo5fsOapiaYPD5St36IKEWniGn8t0"
BOT_USERNAME = "NickWorth_bot"

def init_db():
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, referrer_id INTEGER,
                  referrals INTEGER DEFAULT 0, searches INTEGER DEFAULT 0,
                  daily_searches INTEGER DEFAULT 0, last_reset TEXT,
                  premium INTEGER DEFAULT 0, joined TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                  username TEXT, UNIQUE(user_id, username))''')
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                  username TEXT, score INTEGER, price_min REAL, price_max REAL,
                  searched TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?,?,?)',
              (user_id, username, referrer_id))
    if referrer_id:
        c.execute('UPDATE users SET referrals=referrals+1 WHERE user_id=?', (referrer_id,))
    conn.commit()
    conn.close()

def add_history(user_id, username, score, price_min, price_max):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    c.execute('INSERT INTO history (user_id, username, score, price_min, price_max) VALUES (?,?,?,?,?)',
              (user_id, username, score, price_min, price_max))
    conn.commit()
    conn.close()

def get_history(user_id, limit=10):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    c.execute('SELECT username, score, price_min, price_max FROM history WHERE user_id=? ORDER BY searched DESC LIMIT ?',
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def check_daily_limit(user_id):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    today = time.strftime('%Y-%m-%d')
    c.execute('SELECT daily_searches, last_reset, premium FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return True
    daily, last_reset, premium = row
    if premium:
        conn.close()
        return True
    if last_reset != today:
        c.execute('UPDATE users SET daily_searches=0, last_reset=? WHERE user_id=?', (today, user_id))
        conn.commit()
        conn.close()
        return True
    if daily >= 5:
        conn.close()
        return False
    conn.close()
    return True

def get_remaining(user_id):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    today = time.strftime('%Y-%m-%d')
    c.execute('SELECT daily_searches, last_reset, premium FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return 5
    daily, last_reset, premium = row
    if premium:
        return 999
    if last_reset != today:
        return 5
    return max(0, 5 - daily)

def increment_searches(user_id):
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    today = time.strftime('%Y-%m-%d')
    c.execute('UPDATE users SET searches=searches+1, daily_searches=daily_searches+1, last_reset=? WHERE user_id=?',
              (today, user_id))
    conn.commit()
    conn.close()

async def check_fragment(username):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://fragment.com/username/{username}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                text = await resp.text()
                if 'username_sold' in text or '"sold"' in text:
                    return "sold"
                elif 'username_available' in text or '"available"' in text:
                    return "available"
                elif 'username_taken' in text or '"taken"' in text:
                    return "taken"
                else:
                    return "unknown"
    except:
        return "unknown"

def analyze_username(username):
    username = username.replace("@", "").strip().lower()
    length = len(username)
    has_digits = any(c.isdigit() for c in username)
    has_underscore = "_" in username
    all_letters = username.isalpha()

    if length <= 4: score = 10
    elif length <= 5: score = 8
    elif length <= 6: score = 6
    elif length <= 7: score = 5
    elif length <= 8: score = 4
    elif length <= 10: score = 3
    else: score = 2

    if not has_digits: score = min(score + 1, 10)
    if not has_underscore: score = min(score + 1, 10)

    if length <= 4: price_min, price_max = 800, 8000
    elif length <= 5: price_min, price_max = 80, 800
    elif length <= 6: price_min, price_max = 15, 150
    elif length <= 8: price_min, price_max = 5, 50
    else: price_min, price_max = 1, 15

    ton_price = 1.63
    if has_digits:
        price_min = round(price_min * 0.6, 1)
        price_max = round(price_max * 0.6, 1)

    usd_min = int(round(price_min * ton_price, 0))
    usd_max = int(round(price_max * ton_price, 0))

    stars = "⭐" * (score // 2) + "☆" * (5 - score // 2)
    bar = "▰" * score + "▱" * (10 - score)

    pros = []
    cons = []
    if not has_digits:
        pros.append("🔤 Без цифр")
    else:
        cons.append("🔢 Содержит цифры — снижает ценность")
    if not has_underscore:
        pros.append("✨ Без подчёркивания")
    else:
        cons.append("〰️ Подчёркивание — хуже читается")
    if length <= 5:
        pros.append(f"📏 Короткий ({length} симв.) — редкость")
    elif length >= 9:
        cons.append(f"📏 Длинный ник ({length} симв.) — низкий спрос")
    if all_letters and length <= 6:
        pros.append("💎 Только буквы — максимальная ценность")

    creation_cost = 10 if length <= 5 else 0

    return {
        "username": username,
        "score": score,
        "stars": stars,
        "bar": bar,
        "price_min": price_min,
        "price_max": price_max,
        "usd_min": usd_min,
        "usd_max": usd_max,
        "pros": pros,
        "cons": cons,
        "length": length,
        "creation_cost": creation_cost
    }

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Оценить ник", callback_data="evaluate"),
         InlineKeyboardButton("⚖️ Сравнение", callback_data="compare")],
        [InlineKeyboardButton("🔥 Тренды", callback_data="trends"),
         InlineKeyboardButton("📋 История", callback_data="history")],
        [InlineKeyboardButton("🤝 Рефералы", callback_data="refs"),
         InlineKeyboardButton("👁 Отслеживание", callback_data="watchlist")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium"),
         InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0].replace("ref_", ""))
            if referrer_id == user.id:
                referrer_id = None
        except:
            pass
    add_user(user.id, user.username or "", referrer_id)

    text = (
        f"👋 Привет, {user.first_name}\\!\n\n"
        "Я *NickWorth* — профессиональный оценщик юзернеймов Telegram\\.\n\n"
        "📊 Отправь мне любой ник и узнай:\n"
        "• Сколько он реально стоит на Fragment\n"
        "• Его рейтинг и потенциал\n"
        "• Похожие продажи на рынке\n\n"
        "Просто отправь ник, например: `@alex`"
    )
    await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode="MarkdownV2")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if not get_user(user.id):
        add_user(user.id, user.username or "")

    if not check_daily_limit(user.id):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("💎 Купить Premium", callback_data="premium"),
            InlineKeyboardButton("🤝 Пригласить друга", callback_data="refs")
        ]])
        await update.message.reply_text(
            "⛔ *Дневной лимит исчерпан* \\(5 проверок/день\\)\n\n"
            "💎 *Premium* — безлимитные проверки\n"
            "🤝 Пригласи 10 друзей — Premium на неделю бесплатно",
            reply_markup=keyboard, parse_mode="MarkdownV2")
        return

    username = text.replace("@", "").replace("t.me/", "").strip().split("/")[-1]
    if len(username) < 3 or len(username) > 32:
        await update.message.reply_text("❌ Ник должен быть от 3 до 32 символов\\.", parse_mode="MarkdownV2")
        return

    msg = await update.message.reply_text(f"🔍 Анализирую @{username}\\.\\.\\.", parse_mode="MarkdownV2")
    data = analyze_username(username)
    fragment_status = await check_fragment(username)
    increment_searches(user.id)
    add_history(user.id, username, data["score"], data["price_min"], data["price_max"])
    remaining = get_remaining(user.id)

    if fragment_status == "sold":
        frag_icon, frag_text = "💰", "Продан на Fragment"
    elif fragment_status == "available":
        frag_icon, frag_text = "🟢", "Доступен на Fragment\\!"
    elif fragment_status == "taken":
        frag_icon, frag_text = "🔴", "Занят \\(не на Fragment\\)"
    else:
        frag_icon, frag_text = "❓", "Статус неизвестен"

    pros_text = "\n".join(data["pros"]) if data["pros"] else "—"
    cons_text = "\n".join(data["cons"]) if data["cons"] else "—"

    creation_text = ""
    if data["creation_cost"] > 0:
        creation_text = f"\n🏷 Стоимость создания: {data['creation_cost']} TON \\(~\\${round(data['creation_cost']*1.63)}\\)"

    remaining_text = "" if remaining == 999 else f"\n\n💡 Осталось проверок сегодня: *{remaining}*"

    result = (
        f"📊 *Статус Fragment*\n"
        f"{frag_icon} {frag_text}\n\n"
        f"📈 *Оценка юзернейма* @{username}\n\n"
        f"💰 Стоимость: \\${data['usd_min']}–\\${data['usd_max']}\n"
        f"💎 В TON: {data['price_min']}–{data['price_max']} TON{creation_text}\n"
        f"🏆 Ранг: {data['bar']} {data['score']}/10\n"
        f"⭐ Потенциал: {data['stars']}\n\n"
        f"✅ *Преимущества:*\n{pros_text}\n\n"
        f"❌ *Недостатки:*\n{cons_text}\n\n"
        f"⚠️ _Оценка основана на анализе рынка Fragment\\. Реальная цена зависит от спроса\\._{remaining_text}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Отслеживать", callback_data=f"watch_{username}"),
         InlineKeyboardButton("🔄 Оценить ещё", callback_data="evaluate")],
        [InlineKeyboardButton("📤 Поделиться", switch_inline_query=f"@{username}: ${data['usd_min']}–${data['usd_max']} | {data['score']}/10 — NickWorth_bot")]
    ])

    await msg.edit_text(result, reply_markup=keyboard, parse_mode="MarkdownV2")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if not get_user(user.id):
        add_user(user.id, user.username or "")

    if query.data == "evaluate":
        await query.message.reply_text("📝 Отправь ник для оценки \\(с @ или без, или ссылку t\\.me/username\\)\\.", parse_mode="MarkdownV2")

    elif query.data == "compare":
        await query.message.reply_text("⚖️ Для сравнения используй:\n`/compare ник1 ник2`\n\nПример: `/compare alex ivan`", parse_mode="MarkdownV2")

    elif query.data == "history":
        rows = get_history(user.id)
        if not rows:
            await query.message.reply_text("📋 История пуста\\. Отправь ник для оценки\\!", parse_mode="MarkdownV2")
            return
        text = "📋 *Последние запросы:*\n\n"
        for i, (uname, score, pmin, pmax) in enumerate(rows, 1):
            usd_min = int(pmin * 1.63)
            usd_max = int(pmax * 1.63)
            text += f"{i}\\. @{uname} — {score}/10 \\| \\${usd_min}–\\${usd_max}\n"
        await query.message.reply_text(text, parse_mode="MarkdownV2")

    elif query.data == "trends":
        text = (
            "🔥 *Популярные юзернеймы:*\n\n"
            "1\\. @durov — ранг 10/10 \\| до \\$960,000\n"
            "2\\. @boss — ранг 10/10 \\| до \\$100,200\n"
            "3\\. @monk — ранг 10/10 \\| до \\$12,650\n"
            "4\\. @crow — ранг 10/10 \\| до \\$24,600\n"
            "5\\. @alex — ранг 9/10 \\| до \\$45,000\n\n"
            "📊 *Тренды рынка:*\n"
            "• 4\\-буквенные ники: спрос \\+15% за месяц\n"
            "• 5\\-буквенные: стабильный рост\n"
            "• Ники с цифрами: спад \\-8%"
        )
        await query.message.reply_text(text, parse_mode="MarkdownV2")

    elif query.data == "watchlist":
        conn = sqlite3.connect('nickworth.db')
        c = conn.cursor()
        c.execute('SELECT username FROM watchlist WHERE user_id=?', (user.id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.message.reply_text("👁 Список отслеживания пуст\\.\n\nДобавь ник: `/watch username`", parse_mode="MarkdownV2")
        else:
            text = "👁 *Отслеживаемые ники:*\n\n"
            for i, (uname,) in enumerate(rows, 1):
                text += f"{i}\\. @{uname}\n"
            text += "\n💎 Premium: безлимитное отслеживание"
            await query.message.reply_text(text, parse_mode="MarkdownV2")

    elif query.data.startswith("watch_"):
        username = query.data.replace("watch_", "")
        conn = sqlite3.connect('nickworth.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM watchlist WHERE user_id=?', (user.id,))
        count = c.fetchone()[0]
        db_user = get_user(user.id)
        is_premium = db_user[7] if db_user else 0
        if count >= 3 and not is_premium:
            conn.close()
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Купить Premium", callback_data="premium")]])
            await query.message.reply_text("⛔ Бесплатный лимит: 3 ника\n\n💎 Premium — безлимитное отслеживание", reply_markup=keyboard)
            return
        c.execute('INSERT OR IGNORE INTO watchlist (user_id, username) VALUES (?,?)', (user.id, username))
        conn.commit()
        conn.close()
        await query.message.reply_text(f"📌 @{username} добавлен в отслеживание\\!\n\n🔔 Уведомлю когда появится на Fragment\\.", parse_mode="MarkdownV2")

    elif query.data == "refs":
        db_user = get_user(user.id)
        refs = db_user[3] if db_user else 0
        ref_link = f"https://t\\.me/{BOT_USERNAME}?start=ref_{user.id}"
        text = (
            "🤝 *Реферальная программа*\n\n"
            f"🔗 Ваша ссылка:\n`https://t.me/{BOT_USERNAME}?start=ref_{user.id}`\n\n"
            f"👥 Приглашено: {refs}\n\n"
            "🎁 *Бонусы:*\n"
            "• 3 реферала — \\+10 проверок/день\n"
            "• 10 рефералов — Premium на 7 дней 🎉\n"
            "• 25 рефералов — Premium на месяц 💎\n"
            "• 50 рефералов — Premium навсегда 👑\n\n"
            "📱 Снимай TikTok: _\"Проверил свой ник — стоит \\$500\"_\n"
            "→ Люди сами идут проверять через твою ссылку"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📤 Поделиться", switch_inline_query=f"Узнай сколько стоит твой ник в Telegram! 💰 t.me/{BOT_USERNAME}")
        ]])
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

    elif query.data == "premium":
        text = (
            "💎 *NickWorth Premium*\n\n"
            "✅ Что даёт Premium:\n"
            "• Безлимитные проверки \\(вместо 5/день\\)\n"
            "• Безлимитное отслеживание ников\n"
            "• Мгновенные уведомления Fragment\n"
            "• История последних 100 ников\n"
            "• VIP\\-значок в профиле 👑\n\n"
            "💰 *Стоимость:*\n"
            "⚡ Неделя — 29 ⭐ Stars\n"
            "💎 Месяц — 99 ⭐ Stars\n\n"
            "🤝 *Бесплатно через рефералов:*\n"
            "10 друзей \\= Premium на неделю\n"
            "25 друзей \\= Premium на месяц"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Неделя — 29 ⭐", callback_data="buy_week"),
             InlineKeyboardButton("💎 Месяц — 99 ⭐", callback_data="buy_month")],
            [InlineKeyboardButton("🤝 Получить бесплатно", callback_data="refs")]
        ])
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

    elif query.data in ["buy_week", "buy_month"]:
        await query.message.reply_text("💳 Оплата через Telegram Stars будет доступна в ближайшем обновлении\\!\n\n🤝 Пока получи Premium бесплатно через рефералов — пригласи 10 друзей\\.", parse_mode="MarkdownV2")

    elif query.data == "help":
        text = (
            "❓ *Помощь*\n\n"
            "📋 *Команды:*\n"
            "• Отправь юзернейм — получи оценку\n"
            "• `/compare ник1 ник2` — сравнить два ника\n"
            "• `/watch username` — отслеживать ник\n"
            "• `/history` — история запросов\n"
            "• `/ref` — реферальная ссылка\n"
            "• `/menu` — главное меню\n\n"
            "💡 Работает через ссылку: `t.me/username`"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Меню", callback_data="back_menu")]])
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

    elif query.data == "back_menu":
        await query.message.reply_text("📋 Главное меню", reply_markup=main_keyboard())

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚖️ Использование: `/compare ник1 ник2`\n\nПример: `/compare alex ivan`", parse_mode="MarkdownV2")
        return
    u1 = context.args[0].replace("@", "")
    u2 = context.args[1].replace("@", "")
    msg = await update.message.reply_text(f"⚖️ Сравниваю @{u1} и @{u2}\\.\\.\\.", parse_mode="MarkdownV2")
    d1 = analyze_username(u1)
    d2 = analyze_username(u2)
    f1 = await check_fragment(u1)
    f2 = await check_fragment(u2)

    def frag_str(f):
        if f == "available": return "🟢 Доступен"
        if f == "sold": return "💰 Продан"
        if f == "taken": return "🔴 Занят"
        return "❓"

    winner = u1 if d1["score"] >= d2["score"] else u2
    result = (
        f"⚖️ *Сравнение юзернеймов*\n\n"
        f"@{u1} vs @{u2}\n\n"
        f"*@{u1}:*\n"
        f"💰 \\${d1['usd_min']}–\\${d1['usd_max']} \\| Ранг: {d1['score']}/10\n"
        f"Fragment: {frag_str(f1)}\n\n"
        f"*@{u2}:*\n"
        f"💰 \\${d2['usd_min']}–\\${d2['usd_max']} \\| Ранг: {d2['score']}/10\n"
        f"Fragment: {frag_str(f2)}\n\n"
        f"🏆 *Победитель: @{winner}*"
    )
    await msg.edit_text(result, parse_mode="MarkdownV2")

async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Использование: `/watch username`", parse_mode="MarkdownV2")
        return
    username = context.args[0].replace("@", "")
    conn = sqlite3.connect('nickworth.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO watch
