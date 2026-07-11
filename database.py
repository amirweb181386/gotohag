import json
import random
import sqlite3
from contextlib import contextmanager
from config import DB_PATH

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        # ۱. جدول پروفایل کاربران
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                gender TEXT CHECK(gender IN ('male', 'female')),
                age INTEGER,
                photo_id TEXT,
                is_searching INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ۲. جدول ادمین‌ها
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ۳. جدول اتاق‌های بازی (پشتیبانی از لابی گروهی و وضعیت قفل)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                chat_id TEXT PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                players_list TEXT NOT NULL, -- ذخیره لیست آیدی بازیکنان به صورت JSON [id1, id2, ...]
                status TEXT NOT NULL DEFAULT 'lobby', -- lobby, playing, finished
                current_turn INTEGER NOT NULL DEFAULT 0,
                mode TEXT NOT NULL DEFAULT 'friendly', -- friendly, romantic, nsfw, random
                used_questions TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY(creator_id) REFERENCES users(user_id)
            );
        """)

        # ۴. جدول سوالات رسمی ربات (اضافه شدن فیلد جنسیت target_gender)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('truth', 'dare')),
                mode TEXT NOT NULL CHECK(mode IN ('friendly', 'romantic', 'nsfw')),
                target_gender TEXT NOT NULL DEFAULT 'both' CHECK(target_gender IN ('male', 'female', 'both')),
                text TEXT NOT NULL
            );
        """)

        # ۵. جدول سوالات پیشنهادی کاربران
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

# --- بررسی محدودیت همزمانی بازی (قانون ۱) ---
def is_user_in_active_game(user_id: int) -> bool:
    """بررسی می‌کند که آیا کاربر در حال حاضر در یک بازی فعال (لابی یا در حال بازی) حضور دارد یا خیر"""
    with get_conn() as conn:
        rooms = conn.execute("SELECT players_list FROM games WHERE status IN ('lobby', 'playing')").fetchall()
        for r in rooms:
            p_list = json.loads(r["players_list"])
            if user_id in p_list:
                return True
        return False

# --- توابع مدیریت ادمین ---
def add_admin(user_id: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))

def is_admin(user_id: int) -> bool:
    with get_conn() as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
        return res is not None

# --- تفکیک پیشرفته سوالات بر اساس قالب جدید ادمین (قانون ۳) ---
def add_bulk_question_advanced(q_type: str, mode: str, gender: str, text: str):
    with get_conn() as conn:
        conn.execute("INSERT INTO questions (type, mode, target_gender, text) VALUES (?, ?, ?, ?)", (q_type, mode, gender, text))

# --- مدیریت سیستم لابی و بازی ---
def create_game_room(room_id: str, creator_id: int):
    with get_conn() as conn:
        p_list = json.dumps([creator_id])
        conn.execute("INSERT INTO games (chat_id, creator_id, players_list, status) VALUES (?, ?, ?, 'lobby')", (room_id, creator_id, p_list))

def add_player_to_room(room_id: str, user_id: int) -> bool:
    with get_conn() as conn:
        game = conn.execute("SELECT * FROM games WHERE chat_id = ?", (room_id,)).fetchone()
        if game and game["status"] == 'lobby':
            p_list = json.loads(game["players_list"])
            if user_id not in p_list:
                p_list.append(user_id)
                conn.execute("UPDATE games SET players_list = ? WHERE chat_id = ?", (json.dumps(p_list), room_id))
                return True
        return False

def get_game_by_room(room_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM games WHERE chat_id = ?", (room_id,)).fetchone()

def lock_lobby_and_ready(room_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE games SET status = 'playing' WHERE chat_id = ?", (room_id,))

def set_game_mode(room_id: str, mode: str):
    with get_conn() as conn:
        conn.execute("UPDATE games SET mode = ? WHERE chat_id = ?", (mode, room_id))

def set_current_turn(room_id: str, index: int):
    with get_conn() as conn:
        conn.execute("UPDATE games SET current_turn = ? WHERE chat_id = ?", (index, room_id))

def finish_game(room_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE games SET status = 'finished' WHERE chat_id = ?", (room_id,))

def get_user_profile(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def update_user_base_profile(user_id: int, username: str, first_name: str, gender: str, age: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, gender, age) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, gender=excluded.gender, age=excluded.age
        """, (user_id, username, first_name, gender, age))

def update_user_photo(user_id: int, photo_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET photo_id = ? WHERE user_id = ?", (photo_id, user_id))

def set_searching_status(user_id: int, status: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_searching = ? WHERE user_id = ?", (status, user_id))

def find_available_stranger(exclude_user_id: int):
    with get_conn() as conn:
        # پیدا کردن غریبه‌ای که خودش در بازی فعلی نباشد
        rows = conn.execute("SELECT * FROM users WHERE is_searching = 1 AND user_id != ?", (exclude_user_id,)).fetchall()
        for row in rows:
            if not is_user_in_active_game(row["user_id"]):
                return row
        return None

def get_random_question(q_type: str, mode: str, target_gender: str, exclude_ids):
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in exclude_ids) if exclude_ids else None
        
        # تعیین مود بازی (اگر رندوم بود، یکی از ۳ مود را انتخاب کن)
        selected_mode = mode
        if mode == "random":
            selected_mode = random.choice(["friendly", "romantic", "nsfw"])

        query = "SELECT * FROM questions WHERE type = ? AND mode = ? AND (target_gender = ? OR target_gender = 'both')"
        params = [q_type, selected_mode, target_gender]
        
        if placeholders:
            query += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_ids)
            
        rows = conn.execute(query, params).fetchall()
        if not rows:
            # اگر سوالی با تفکیک جنسیت نبود، کل سوالات آن بخش را بدون در نظر گرفتن جنسیت جستجو کن
            query_fallback = "SELECT * FROM questions WHERE type = ? AND mode = ?"
            params_fallback = [q_type, selected_mode]
            if placeholders:
                query_fallback += f" AND id NOT IN ({placeholders})"
                params_fallback.extend(exclude_ids)
            rows = conn.execute(query_fallback, params_fallback).fetchall()
            
        if not rows:
            return None
        return random.choice(rows)

def add_user_suggestion(user_id: int, text: str):
    with get_conn() as conn:
        conn.execute("INSERT INTO user_suggestions (user_id, text) VALUES (?, ?)", (user_id, text))

def get_pending_suggestions():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM user_suggestions WHERE status = 'pending'").fetchall()

def update_suggestion_status(suggestion_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE user_suggestions SET status = ? WHERE id = ?", (status, suggestion_id))

def get_suggestion_by_id(suggestion_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM user_suggestions WHERE id = ?", (suggestion_id,)).fetchone()