"""
ربات تلگرامی جرعت یا حقیقت پارتنری (نسخه لابی گروهی داینامیک + محدودیت یک بازی همزمان)
"""
import os

# این کد خودکار فایل کانفیگ را روی سرور ریل‌وی می‌سازد
with open("config.py", "w", encoding="utf-8") as f:
    f.write('BOT_TOKEN = "8619031821:AAFhJQqzBZs-A0I8R5Kf6f2VySn0l81fQGk"\n')
    f.write('BOT_USERNAME = "Gotohag_bot"\n')
    f.write('DB_PATH = "bot.db"\n')

# --------------------------------------------------
# بقیه کدهای قبلی خودت از اینجا به بعد شروع می‌شوند:

import json
import logging
import secrets
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

import database as db
from config import BOT_TOKEN, BOT_USERNAME

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

MODE_LABELS = {
    "friendly": "😇 عادی و دوستانه",
    "romantic": "❤️ پارتنری عاشقانه",
    "nsfw": "🔥 پارتنری +18",
    "random": "🎲 انتخاب کاملاً رندوم"
}

TYPE_MAP = {"حقیقت": "truth", "جرعت": "dare"}
MODE_MAP = {"عادی": "friendly", "عاشقانه": "romantic", "+18": "nsfw"}
GENDER_MAP = {"پسر": "male", "دختر": "female", "هر دو": "both", "مشترک": "both"}

SECRET_ADMIN_CODE = "##Amir##15##@@"

def main_menu_keyboard(user_id: int):
    buttons = [
        [KeyboardButton("🔗 ساخت اتاق بازی"), KeyboardButton("👤 بازی با ناشناس")],
        [KeyboardButton("📝 ارسال سوال"), KeyboardButton("⚙️ پروفایل من")]
    ]
    if db.is_admin(user_id):
        buttons.append([KeyboardButton("👑 پنل مدیریت")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 تایید سوالات پیشنهادی", callback_data="admin_view_suggestions")],
        [InlineKeyboardButton("➕ افزودن سوال دسته‌جمعی پیشرفته", callback_data="admin_bulk_add")]
    ])

def is_profile_complete(user_id: int) -> bool:
    profile = db.get_user_profile(user_id)
    if profile and profile["gender"] and profile["age"] and profile["photo_id"]:
        return True
    return False

# ---------------------------------------------------------------------------
# ۱. مدیریت دستور /start و ورود به لابی
# ---------------------------------------------------------------------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # اگر کاربر از طریق لینک دعوت وارد شده باشد
    if args and args[0].startswith("room_"):
        room_id = args[0]
        
        # قانون ۱: بررسی محدودیت همزمانی بازی
        if db.is_user_in_active_game(user.id):
            await update.message.reply_text("❌ شما در حال حاضر در یک بازی فعال (یا لابی انتظار) حضور دارید! ابتدا باید آن بازی را به اتمام برسانید.")
            return

        if not is_profile_complete(user.id):
            context.user_data["pending_room"] = room_id
            await update.message.reply_text("⚠️ برای ورود به اتاق بازی باید ابتدا پروفایل خود را تکمیل کنید!")
            await start_registration_flow(update, context)
            return
        else:
            await join_room_process(update, context, room_id, user)
            return

    if is_profile_complete(user.id) or db.is_admin(user.id):
        await update.message.reply_text("🎉 به ربات جرعت یا حقیقت خوش آمدید! بخش مورد نظر را انتخاب کنید:", reply_markup=main_menu_keyboard(user.id))
    else:
        await start_registration_flow(update, context)

async def start_registration_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_step"] = "gender"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🙋‍♂️ پسر", callback_data="set_reg_gender:male"),
         InlineKeyboardButton("🙋‍♀️ دختر", callback_data="set_reg_gender:female")]
    ])
    await update.message.reply_text("لطفا ابتدا جنسیت خود را انتخاب کنید:", reply_markup=keyboard)

async def registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    gender = query.data.split(":")[1]
    context.user_data["reg_gender"] = gender
    context.user_data["reg_step"] = "age"
    await query.answer()
    await query.message.delete()
    await context.bot.send_message(chat_id=query.from_user.id, text="🔢 حالا لطفا سن خودت رو به عدد انگلیسی بفرست:")

# ---------------------------------------------------------------------------
# ۲. هندلر جامع متن‌ها و پردازش تفکیک دسته‌جمعی جدید (قانون ۳)
# ---------------------------------------------------------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    step = context.user_data.get("reg_step")

    if text == SECRET_ADMIN_CODE:
        db.add_admin(user.id)
        await update.message.reply_text("👑 رمز تایید شد! شما به مقام ادمین ارتقا یافتید.", reply_markup=main_menu_keyboard(user.id))
        return

    if step == "age":
        if not text.isdigit():
            await update.message.reply_text("❌ لطفا سن را به عدد وارد کنید:")
            return
        context.user_data["reg_age"] = int(text)
        context.user_data["reg_step"] = "photo"
        await update.message.reply_text("📸 حالا یک عکس برای پروفایلت بفرست:")
        return

    if context.user_data.get("waiting_for_question") == True:
        db.add_user_suggestion(user.id, text)
        context.user_data["waiting_for_question"] = False
        await update.message.reply_text("✅ پیشنهاد شما ثبت شد.", reply_markup=main_menu_keyboard(user.id))
        return

    # تفکیک سوالات بر اساس قالب جدید ادمین: ...نوع...مود...جنسیت...متن سوال...
    if context.user_data.get("waiting_bulk_add") == True and db.is_admin(user.id):
        lines = text.strip().split("\n")
        success_count = 0
        for line in lines:
            if not line: continue
            parts = line.split("...")
            if len(parts) >= 5:
                q_type = TYPE_MAP.get(parts[1].strip())
                mode = MODE_MAP.get(parts[2].strip())
                gender = GENDER_MAP.get(parts[3].strip(), "both")
                q_text = parts[4].strip()
                
                if q_type and mode and q_text:
                    db.add_bulk_question_advanced(q_type, mode, gender, q_text)
                    success_count += 1
                    
        context.user_data["waiting_bulk_add"] = False
        await update.message.reply_text(f"✅ تعداد {success_count} سوال با موفقیت تفکیک (نوع، مود، جنسیت) و اضافه شد.", reply_markup=main_menu_keyboard(user.id))
        return

    if not is_profile_complete(user.id) and not db.is_admin(user.id):
        await update.message.reply_text("⚠️ شما هنوز پروفایل خود را تکمیل نکرده‌اید!")
        return

    # دکمه‌های منوی اصلی کاربر
    if text == "👑 پنل مدیریت" and db.is_admin(user.id):
        await update.message.reply_text("🛠 به داشبورد مدیریت خوش آمدید:", reply_markup=admin_panel_keyboard())

    elif text == "🔗 ساخت اتاق بازی":
        if db.is_user_in_active_game(user.id):
            await update.message.reply_text("❌ شما در حال حاضر در یک بازی فعال حضور دارید!")
            return
            
        room_id = f"room_{secrets.token_hex(4)}"
        db.create_game_room(room_id, user.id)
        invite_link = f"https://t.me/{BOT_USERNAME}?start={room_id}"
        
        # بنر اولیه عضوگیری بدون هیچ تنظیماتی (قانون ۲)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛑 اتمام عضوگیری", callback_data=f"lobby_lock:{room_id}")],
            [InlineKeyboardButton("❌ لغو کامل بازی", callback_data=f"game_finish:{room_id}")]
        ])
        
        await update.message.reply_text(
            f"📢 **اتاق بازی ساخته شد! لابی انتظار هم‌اکنون باز است.**\n\n"
            f"👤 **اعضای فعلی لابی:**\n1. {user.first_name} (سازنده)\n\n"
            f"🔗 لینک دعوت برای افزودن اعضا:\n`{invite_link}`",
            reply_markup=keyboard, parse_mode="Markdown"
        )

    elif text == "👤 بازی با ناشناس":
        if db.is_user_in_active_game(user.id):
            await update.message.reply_text("❌ شما در حال حاضر در یک بازی فعال حضور دارید!")
            return
            
        await update.message.reply_text("🔍 در حال جستجوی پارتنر ناشناس...")
        stranger = db.find_available_stranger(user.id)
        if stranger:
            room_id = f"room_{secrets.token_hex(4)}"
            db.set_searching_status(stranger["user_id"], 0)
            
            # ثبت در دیتابیس بازی به عنوان شروع مستقیم دو نفره بدون لابی عمومی
            with db.get_conn() as conn:
                p_list = json.dumps([stranger["user_id"], user.id])
                conn.execute("INSERT INTO games (chat_id, creator_id, players_list, status, mode) VALUES (?, ?, ?, 'playing', 'friendly')", (room_id, stranger["user_id"], p_list))
            
            db.set_current_turn(room_id, 0)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❓ حقیقت", callback_data=f"turn_pick:truth:{room_id}"), InlineKeyboardButton("🎯 جرعت", callback_data=f"turn_pick:dare:{room_id}")]])
            await context.bot.send_message(chat_id=stranger["user_id"], text="🎉 پارتنر پیدا شد! نوبت شماست:", reply_markup=keyboard)
            await update.message.reply_text("🎉 پارتنر پیدا شد! منتظر حرکت بازیکن مقابل بمانید...")
        else:
            db.set_searching_status(user.id, 1)
            await update.message.reply_text("⏱ شما در صف انتظار غریبه‌ها قرار گرفتید.")

    elif text == "📝 ارسال سوال":
        context.user_data["waiting_for_question"] = True
        await update.message.reply_text("✍️ لطفا متن سوال خود را بنویسید:")

    elif text == "⚙️ پروفایل من":
        prof = db.get_user_profile(user.id)
        if prof:
            g_label = "🙋‍♂️ پسر" if prof["gender"] == "male" else "🙋‍♀️ دختر"
            await update.message.reply_photo(photo=prof["photo_id"], caption=f"👤 **پروفایل شما:**\n\n🔹 نام: {prof['first_name']}\n🔹 جنسیت: {g_label}\n🔹 سن: {prof['age']}", parse_mode="Markdown")

    else:
        # چت گروهی داخل بازی فعلی
        with db.get_conn() as conn:
            rooms = conn.execute("SELECT * FROM games WHERE status = 'playing'").fetchall()
            for r in rooms:
                p_list = json.loads(r["players_list"])
                if user.id in p_list:
                    for p_id in p_list:
                        if p_id != user.id:
                            try:
                                await context.bot.send_message(chat_id=p_id, text=f"💬 *{user.first_name}:* {text}", parse_mode="Markdown")
                            except Exception: pass
                    break

# ---------------------------------------------------------------------------
# ۳. فرآیند پویای لابی عضوگیری و مدیریت کلیک دکمه‌ها
# ---------------------------------------------------------------------------

async def photo_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get("reg_step") == "photo":
        photo_id = update.message.photo[-1].file_id
        gender = context.user_data.get("reg_gender")
        age = context.user_data.get("reg_age")
        db.update_user_base_profile(user.id, user.username, user.first_name, gender, age)
        db.update_user_photo(user.id, photo_id)
        context.user_data["reg_step"] = None
        await update.message.reply_text("🎉 ثبت‌نام تکمیل شد!", reply_markup=main_menu_keyboard(user.id))
        
        if "pending_room" in context.user_data:
            await join_room_process(update, context, context.user_data.pop("pending_room"), user)

async def join_room_process(update: Update, context: ContextTypes.DEFAULT_TYPE, room_id: str, user):
    game = db.get_game_by_room(room_id)
    if not game:
        await context.bot.send_message(chat_id=user.id, text="❌ این اتاق دیگر وجود ندارد یا منقضی شده است.")
        return
    if game["status"] != "lobby":
        await context.bot.send_message(chat_id=user.id, text="🚫 ظرفیت این اتاق پر شده یا عضوگیری آن به پایان رسیده است!")
        return
        
    success = db.add_player_to_room(room_id, user.id)
    if success:
        # بروزرسانی داینامیک بنر لابی برای همه اعضا (قانون ۲)
        updated_game = db.get_game_by_room(room_id)
        p_list = json.loads(updated_game["players_list"])
        
        names_text = ""
        for i, p_id in enumerate(p_list, 1):
            prof = db.get_user_profile(p_id)
            name = prof["first_name"] if prof else "کاربر ربات"
            names_text += f"{i}. {name}\n"
            
        invite_link = f"https://t.me/{BOT_USERNAME}?start={room_id}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛑 اتمام عضوگیری", callback_data=f"lobby_lock:{room_id}")],
            [InlineKeyboardButton("❌ لغو کامل بازی", callback_data=f"game_finish:{room_id}")]
        ])
        
        # اطلاع‌رسانی و ویرایش پیام لابی برای کل اعضای حاضر
        for p_id in p_list:
            try:
                if p_id == game["creator_id"]:
                    # ویرایش پیام اصلی برای ادمینِ لابی
                    await context.bot.send_message(
                        chat_id=p_id,
                        text=f"📢 **یک عضو جدید وارد شد!**\n\n👤 **اعضای فعلی لابی:**\n{names_text}\n🔗 لینک دعوت:\n`{invite_link}`",
                        reply_markup=keyboard, parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_message(chat_id=p_id, text=f"🎉 شما وارد لابی بازی شدید. منتظر بمانید تا سازنده عضوگیری را ببندد.\n\n👤 **لیست هم‌تیمی‌ها:**\n{names_text}")
            except Exception: pass

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data.split(":")
    action = data[0]

    # قفل کردن لابی و تغییر بنر به تنظیمات انتخاب مود (قانون ۲)
    if action == "lobby_lock":
        room_id = data[1]
        game = db.get_game_by_room(room_id)
        if user_id != game["creator_id"]:
            await query.answer("❌ فقط سازنده اتاق می‌تواند عضوگیری را تمام کند!", show_alert=True)
            return
            
        db.lock_lobby_and_ready(room_id)
        p_list = json.loads(game["players_list"])
        
        names_str = ", ".join([db.get_user_profile(p)["first_name"] for p in p_list])
        
        # اعلان بسته شدن عضوگیری به کل اعضا
        for p_id in p_list:
            try:
                await context.bot.send_message(chat_id=p_id, text=f"🔒 عضوگیری به اتمام رسید! کاربران [ {names_str} ] وارد بازی شدند.")
            except Exception: pass
            
        # نمایش بنر جدید انتخاب تنظیمات مود برای سازنده بازی (قانون ۲)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("😇 عادی و دوستانه", callback_data=f"set_mode:friendly:{room_id}")],
            [InlineKeyboardButton("❤️ پارتنری عاشقانه", callback_data=f"set_mode:romantic:{room_id}")],
            [InlineKeyboardButton("🔥 پارتنری +18", callback_data=f"set_mode:nsfw:{room_id}")],
            [InlineKeyboardButton("🎲 حالت ترکیبی (رندوم سوالات)", callback_data=f"set_mode:random:{room_id}")]
        ])
        await query.edit_message_text("⚙️ **تنظیمات مود بازی:**\nلطفاً یکی از دسته‌بندی‌های زیر را جهت شروع چرخه سوالات انتخاب کنید:", reply_markup=keyboard, parse_mode="Markdown")

    elif action == "set_mode":
        mode, room_id = data[1], data[2]
        db.set_game_mode(room_id, mode)
        db.set_current_turn(room_id, 0)
        
        game = db.get_game_by_room(room_id)
        p_list = json.loads(game["players_list"])
        first_player = db.get_user_profile(p_list[0])
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❓ حقیقت", callback_data=f"turn_pick:truth:{room_id}"), InlineKeyboardButton("🎯 جرعت", callback_data=f"turn_pick:dare:{room_id}")]])
        
        for p_id in p_list:
            try:
                await context.bot.send_message(chat_id=p_id, text=f"🎮 بازی شروع شد!\n✨ مود تنظیم شده: {MODE_LABELS[mode]}\n\n🎲 اولین نوبت: **{first_player['first_name']}**", reply_markup=keyboard, parse_mode="Markdown")
            except Exception: pass
        await query.message.delete()

    elif action == "turn_pick":
        q_type, room_id = data[1], data[2]
        game = db.get_game_by_room(room_id)
        p_list = json.loads(game["players_list"])
        current_idx = game["current_turn"] % len(p_list)
        
        if user_id != p_list[current_idx]:
            await query.answer("الان نوبت تو نیست! 😅", show_alert=True)
            return
            
        current_user_prof = db.get_user_profile(user_id)
        used_q = json.loads(game["used_questions"])
        
        # فرستادن جنسیت بازیکن فعلی برای دریافت سوال تفکیک شده جنسیت (قانون ۳)
        question = db.get_random_question(q_type, game["mode"], current_user_prof["gender"], used_q)
        if not question:
            await query.answer("سوال جدیدی در این دسته‌بندی پیدا نشد!", show_alert=True)
            return
            
        used_q.append(question["id"])
        with db.get_conn() as conn:
            conn.execute("UPDATE games SET used_questions = ? WHERE chat_id = ?", (json.dumps(used_q), room_id))
            
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏭ نوبت بعدی", callback_data=f"next_turn:{room_id}")], [InlineKeyboardButton("🏳️ اتمام بازی", callback_data=f"game_finish:{room_id}")]])
        msg_text = f"🔥 نوبت: **{current_user_prof['first_name']}**\nبخش: {'❓ حقیقت' if q_type == 'truth' else '🎯 جرعت'}\n\n📌 `{question['text']}`"
        
        for p_id in p_list:
            try:
                await context.bot.send_message(chat_id=p_id, text=msg_text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception: pass
        await query.message.delete()

    elif action == "next_turn":
        room_id = data[1]
        game = db.get_game_by_room(room_id)
        p_list = json.loads(game["players_list"])
        
        new_turn = game["current_turn"] + 1
        db.set_current_turn(room_id, new_turn)
        
        next_player = db.get_user_profile(p_list[new_turn % len(p_list)])
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❓ حقیقت", callback_data=f"turn_pick:truth:{room_id}"), InlineKeyboardButton("🎯 جرعت", callback_data=f"turn_pick:dare:{room_id}")]])
        turn_text = f"🎲 نوبت بازیکن: **{next_player['first_name']}**\nجرعت یا حقیقت؟ 😉"
        
        for p_id in p_list:
            try:
                await context.bot.send_message(chat_id=p_id, text=turn_text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception: pass
        await query.message.delete()

    elif action == "game_finish":
        room_id = data[1]
        game = db.get_game_by_room(room_id)
        db.finish_game(room_id)
        p_list = json.loads(game["players_list"])
        
        for p_id in p_list:
            try:
                await context.bot.send_message(chat_id=p_id, text="🚪 این اتاق بازی به پایان رسید. هم‌اکنون می‌توانید وارد بازی جدیدی شوید.")
            except Exception: pass
        await query.answer("بازی خاتمه یافت.")

    # پنل مدیریت
    elif action == "admin_bulk_add" and db.is_admin(user_id):
        context.user_data["waiting_bulk_add"] = True
        template = "...حقیقت...عادی...پسر...متن سوال برای پسران\n...جرعت...عاشقانه...دختر...متن سوال برای دختران\n...حقیقت...+18...مشترک...متن سوال بدون تفکیک"
        await query.edit_message_text(f"✍️ سوالات را طبق قالب ۵ بخشی زیر (هر سوال در یک خط) بفرستید:\n\n`{template}`", parse_mode="Markdown")

# ---------------------------------------------------------------------------
# ۴. اجرای برنامه
# ---------------------------------------------------------------------------

def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(registration_callback, pattern="^set_reg_gender:"))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(lobby_lock|set_mode|turn_pick|next_turn|game_finish|admin_)"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_registration_handler))

    logger.info("🚀 ربات لابی گروهی و داینامیک روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()