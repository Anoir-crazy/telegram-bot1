from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler
import nest_asyncio
import logging
import asyncio
import json
import os

# التوكن الخاص بك
TOKEN = "8491265818:AAH3J0n-pebSFQUXdITRqA4MQ7YzYUbXzkg"

# إعدادات النقاط
POINTS_TEXT = 1
POINTS_STICKER = 2
POINTS_REPLY = 3

# مسار تخزين النقاط
SCORES_FILE = "user_scores.json"

# المتغير العالمي لحفظ النقاط
user_scores = {}

# تحميل النقاط من ملف خارجي (إن وجد)
def load_scores():
    global user_scores
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r") as f:
            user_scores.update(json.load(f))

# حفظ النقاط في ملف خارجي
def save_scores():
    with open(SCORES_FILE, "w") as f:
        json.dump(user_scores, f)

# تهيئة السجل
logging.basicConfig(level=logging.INFO)

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! هذا البوت يقوم بتقييم نشاط الأعضاء يوميًا في المجموعة.")

# أمر /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_scores:
        await update.message.reply_text("لا توجد نقاط بعد.")
        return

    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_scores[:5]

    msg = "🏆 أفضل 5 أعضاء اليوم:\n"
    for i, (user_id, score) in enumerate(top_users, 1):
        member = await context.bot.get_chat_member(update.effective_chat.id, int(user_id))
        username = member.user.first_name
        msg += f"{i}. {username} - {score} نقطة\n"

    await update.message.reply_text(msg)

# أمر /myrank
async def myrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_scores:
        await update.message.reply_text("ليس لديك نقاط حتى الآن.")
        return

    sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), None)
    score = user_scores[user_id]
    await update.message.reply_text(f"📊 ترتيبك: {rank}\n✨ نقاطك: {score}")

# أمر /reset للمشرفين فقط
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ فقط المشرفين يمكنهم تصفير النقاط.")
        return

    user_scores.clear()
    save_scores()
    await update.message.reply_text("✅ تم تصفير جميع النقاط بنجاح.")

# استقبال الرسائل وتسجيل النقاط
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    points = 0
    if update.message.text:
        points += POINTS_TEXT
    if update.message.sticker:
        points += POINTS_STICKER
    if update.message.reply_to_message:
        points += POINTS_REPLY

    user_scores[user_id] = user_scores.get(user_id, 0) + points
    save_scores()

# إرسال التقرير اليومي وإعادة تعيين النقاط
async def reset_scores_and_send_top(app):
    if not user_scores:
        return

    chat_ids = set()  # جمع كل المجموعات اللي تفاعل فيها البوت
    for update in app.update_queue.queue:
        if update.effective_chat:
            chat_ids.add(update.effective_chat.id)

    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_scores[:5]

    msg = "📅 تقرير النشاط اليومي:\n"
    for i, (user_id, score) in enumerate(top_users, 1):
        try:
            member = await app.bot.get_chat_member(list(chat_ids)[0], int(user_id))
            username = member.user.first_name
            msg += f"{i}. {username} - {score} نقطة\n"
        except:
            continue

    for chat_id in chat_ids:
        await app.bot.send_message(chat_id=chat_id, text=msg)

    user_scores.clear()
    save_scores()

# المهمة المجدولة يومياً
def schedule_daily_reset(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(reset_scores_and_send_top(app)),
        trigger="cron",
        hour=23,
        minute=55,
        id="daily_reset",
    )
    scheduler.start()

# الدالة الرئيسية
async def main():
    load_scores()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("myrank", myrank))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    schedule_daily_reset(app)
    await app.run_polling()

# تشغيل البوت
nest_asyncio.apply()
asyncio.run(main())
