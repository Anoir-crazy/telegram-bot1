import logging, json, os, asyncio, nest_asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

# ───────── إعدادات عامة ─────────
TOKEN = "8491265818:AAH3J0n-pebSFQUXdITRqA4MQ7YzYUbXzkg"
DATA_FILE = "user_scores.json"
POINT_VALUE = 1      # نقطة لكل رسالة نصية (يمكنك تغييره هنا)

# ───────── إعداد سجلات اللوج ─────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ───────── تحميل/حفظ النقاط ─────────
def load_scores() -> dict:
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_scores(scores: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

user_scores: dict[str, int] = load_scores()

# ───────── حساب النقاط ─────────
def add_point(user_id: str) -> None:
    user_scores[user_id] = user_scores.get(user_id, 0) + POINT_VALUE
    save_scores(user_scores)

# ───────── أوامر البوت ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 أهلاً! أقيِّم نشاطكم تلقائيًا.\n"
        "/top • أفضل 10 أعضاء\n"
        "/myscore • نقاطك\n"
        "/myrank • ترتيبك حاليًا"
    )

async def myscore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    score = user_scores.get(uid, 0)
    await update.message.reply_text(f"📊 نقاطك: {score}")

async def myrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in user_scores:
        await update.message.reply_text("لم يُسجّل لك نشاط بعد.")
        return
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    rank = next(i for i, (u, _) in enumerate(sorted_users, 1) if u == uid)
    await update.message.reply_text(f"🎖️ ترتيبك: {rank} / {len(sorted_users)}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_scores:
        await update.message.reply_text("لا يوجد نشاط بعد.")
        return
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 أفضل الأعضاء:\n"
    for i, (uid, score) in enumerate(sorted_users, 1):
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(uid))
            name = member.user.first_name
        except Exception:
            name = "مستخدم مجهول"
        text += f"{i}. {name} — {score} نقطة\n"
    await update.message.reply_text(text)

# ───────── معالجة كل الرسائل (بدون ردّ) ─────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.message:
        add_point(str(update.effective_user.id))

# ───────── تصفير يومي للنقاط ─────────
def daily_reset():
    global user_scores
    if user_scores:
        logging.info("⏰ تصفير النقاط اليومي")
        user_scores = {}
        save_scores(user_scores)

scheduler = BackgroundScheduler()
scheduler.add_job(daily_reset, "cron", hour=0, minute=0)
scheduler.start()

# ───────── الدالة الرئيسية ─────────
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myscore", myscore))
    app.add_handler(CommandHandler("myrank", myrank))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت قيد التشغيل…")
    await app.run_polling()

# ───────── تشغيل البوت بأمان مع nest_asyncio ─────────
if __name__ == "__main__":
    nest_asyncio.apply()           # يسمح بإعادة استخدام الحدث على ويندوز/بيئات تفاعلية
    if asyncio.get_event_loop().is_running():
        # بيئة يوجد بها event loop مسبقًا (Jupyter مثلًا)
        asyncio.create_task(main())
    else:
        asyncio.run(main())
