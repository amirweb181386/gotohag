# ربات تلگرامی جرعت یا حقیقت

ربات ساده و کامل جرعت/حقیقت برای گروه‌های تلگرام، با پایتون (`python-telegram-bot`) و دیتابیس SQLite.

## امکانات

- شروع بازی و پیوستن بازیکن‌ها با `/newgame` و `/join`
- نوبت‌بندی خودکار بازیکن‌ها
- دو دسته سوال: 😇 معمولی و 🔥 تند (با `/category` قابل تغییره)
- جدول امتیازات با `/score`
- افزودن سوال دلخواه توسط ادمین‌های گروه با `/addsoal`
- بدون تکرار سوال در یک دور بازی (تا وقتی سوالات آن دسته تموم بشه)

## دستورات

| دستور | توضیح |
|---|---|
| `/start` | راهنما |
| `/newgame` | ساخت بازی جدید در گروه |
| `/join` | پیوستن به بازی |
| `/begin` | شروع دور بازی (حداقل ۲ بازیکن) |
| `/category` | تغییر دسته سوالات |
| `/score` | نمایش جدول امتیازات |
| `/endgame` | پایان بازی |
| `/addsoal truth\|dare متن سوال` | افزودن سوال (فقط ادمین) |

## اجرا روی سیستم خودتون (تست محلی)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# فایل .env رو باز کن و BOT_TOKEN رو از @BotFather بگیر و بذار

python bot.py
```

## دیپلوی روی VPS (پیشنهادی: Ubuntu/Debian)

### ۱. آپلود پروژه

```bash
scp -r truth_or_dare_bot user@YOUR_SERVER_IP:/home/user/
ssh user@YOUR_SERVER_IP
cd /home/user/truth_or_dare_bot
```

### ۲. نصب پیش‌نیازها

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # BOT_TOKEN رو بذار
```

### ۳. تست سریع

```bash
python bot.py
# اگه پیام "ربات در حال اجراست..." رو دیدی، با Ctrl+C ببندش و برو مرحله بعد
```

### ۴. اجرای دائمی با systemd (پیشنهاد می‌شه، چون با ری‌استارت سرور هم بالا میاد)

فایل سرویس بساز:

```bash
sudo nano /etc/systemd/system/truth-or-dare-bot.service
```

این محتوا رو داخلش بذار (مسیرها رو با مسیر واقعی خودت جایگزین کن):

```ini
[Unit]
Description=Truth or Dare Telegram Bot
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/truth_or_dare_bot
ExecStart=/home/user/truth_or_dare_bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

سپس:

```bash
sudo systemctl daemon-reload
sudo systemctl enable truth-or-dare-bot
sudo systemctl start truth-or-dare-bot

# چک کردن وضعیت و لاگ‌ها:
sudo systemctl status truth-or-dare-bot
journalctl -u truth-or-dare-bot -f
```

از این به بعد ربات همیشه در پس‌زمینه اجراست، حتی بعد از ری‌استارت سرور.

## نکته درباره ربات قبلی‌تون

چون گفتید ربات قبلی «سر تا سر باگ» بود، این نسخه از صفر با ساختار تمیز نوشته شده:
- هر گروه، بازی و لیست بازیکن‌های مستقل خودش رو داره (دیتای گروه‌ها با هم قاطی نمیشه)
- فقط بازیکنی که نوبتشه می‌تونه دکمه جرعت/حقیقت رو بزنه (بقیه نمی‌تونن نوبت رو بدزدن)
- سوالات تکراری در یک دور بازی نمیان، و وقتی سوالات یک دسته تموم بشه، خودکار از اول شروع میشه به‌جای کرش کردن

اگه بعد از تست، باگ یا رفتار عجیبی دیدید، بهم بگید دقیقاً چه کاری کردید و چه اتفاقی افتاد تا رفعش کنم.
