import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "متغیر BOT_TOKEN تنظیم نشده. یک فایل .env بساز و توکن ربات رو توش بذار:\n"
        "BOT_TOKEN=xxxxxxxxx:yyyyyyyyyyyyyyyyyyyyyyyyyyyy"
    )

DB_PATH = os.getenv("DB_PATH", "bot.db")

# ⚠️ این خط رو حتماً اضافه کن و یوزرنیم رباتت رو بدون @ بنویس:
BOT_USERNAME = os.getenv("BOT_USERNAME", "Gotohag_bot")
