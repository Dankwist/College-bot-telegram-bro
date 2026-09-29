import os
import asyncio
from dotenv import load_dotenv

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Нет BOT_TOKEN в .env")

ADMIN_IDS = set()
raw_admins = os.getenv("ADMIN_IDS", "")
for x in raw_admins.split(","):
    x = x.strip()
    if x.isdigit():
        ADMIN_IDS.add(int(x))

DB_NAME = "hexlet.db"
INSTAGRAM_URL = "https://instagram.com/your_college_account"
DISCORD_URL = "https://discord.gg/wMtZasPGHT" 

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]

LOGIN_WAIT = set()
TEST_STATE: dict[int, dict] = {}
SCHEDULE_EDIT: dict[int, tuple[str, str]] = {}
UPLOAD_MODE: dict[int, tuple[str, str]] = {}
ANNOUNCE_WAIT: dict[int, str] = {}

QUESTIONS = [
    ("Что тебе реально интереснее делать чаще?", {
        "Писать код, решать задачи, делать приложения": "dev",
        "Настраивать компьютеры/сети, чинить и админить": "sis",
        "Делать дизайн сайтов, интерфейсы, баннеры": "webdesign",
        "Придумывать рекламу, продвигать, анализировать аудиторию": "marketing",
    }),
    ("Если бы дали проект на неделю, ты бы выбрал(а):", {
        "Сделать телеграм-бота/сайт и чтобы всё работало": "dev",
        "Поднять Wi-Fi/сеть, настроить сервер и безопасность": "sis",
        "Сделать красивый прототип сайта в Figma": "webdesign",
        "Сделать план продвижения и контент-стратегию": "marketing",
    }),
    ("Что тебя больше бесит/не нравится?", {
        "Когда не получается логика в коде (но хочется добить)": "dev",
        "Когда всё настроено, но «почему-то не работает»": "sis",
        "Когда дизайн некрасивый и «глаз режет»": "webdesign",
        "Когда продукт классный, но его никто не покупает": "marketing",
    }),
    ("Твои сильные стороны ближе к:", {
        "Логике и вниманию к деталям в коде": "dev",
        "Технике, аккуратной настройке и дисциплине": "sis",
        "Визуалу, вкусу, композиции": "webdesign",
        "Коммуникации, идеям, аналитике спроса": "marketing",
    }),
    ("Что для тебя важнее в результате?", {
        "Работает без ошибок и стабильно": "dev",
        "Надёжно, быстро, без сбоев": "sis",
        "Красиво, удобно и приятно": "webdesign",
        "Продаёт/привлекает людей": "marketing",
    }),
    ("С чем тебе комфортнее разбираться?", {
        "Алгоритмы, структуры данных, логика": "dev",
        "Железо, сети, ОС, настройки": "sis",
        "Типографика, цвета, UX/UI": "webdesign",
        "ЦА, конкуренты, воронка, SMM": "marketing",
    }),
    ("Что звучит интереснее как ежедневная работа?", {
        "Писать новые функции, улучшать продукт": "dev",
        "Поддерживать инфраструктуру, устранять проблемы": "sis",
        "Создавать макеты, улучшать интерфейсы": "webdesign",
        "Запускать кампании, считать результаты, улучшать": "marketing",
    }),
    ("Как ты относишься к математике/логике?", {
        "Норм/люблю, мне это заходит": "dev",
        "Ок, если это помогает в технике": "sis",
        "Не главное, важнее визуал и удобство": "webdesign",
        "Ок, если это про аналитику и цифры": "marketing",
    }),
    ("Где ты чаще залипаешь?", {
        "В обучалках по коду, GitHub, задачах": "dev",
        "В настройках, сборках, тех-видео": "sis",
        "В дизайне, Figma, Pinterest/Behance": "webdesign",
        "В соцсетях, трендах, рекламе, кейсах": "marketing",
    }),
    ("Что тебе ближе по стилю мышления?", {
        "Сделать систему и логику": "dev",
        "Сделать всё, чтобы работало стабильно": "sis",
        "Сделать красиво и понятно пользователю": "webdesign",
        "Сделать так, чтобы люди выбрали именно это": "marketing",
    }),
    ("Если бы нужно было улучшить сайт колледжа, ты бы:", {
        "Добавил(а) новый раздел и функционал": "dev",
        "Ускорил(а) загрузку/настроил(а) сервер": "sis",
        "Переделал(а) дизайн и удобство": "webdesign",
        "Продвинул(а) сайт и поднял(а) охваты": "marketing",
    }),
    ("Что из этого тебе кажется самым «своим»?", {
        "Разработчик программного обеспечения": "dev",
        "Техник информационных систем": "sis",
        "Web-Дизайнер": "webdesign",
        "Маркетинг (по отраслям)": "marketing",
    }),
]

RESULTS = {
    "dev": (
        "✅ Тебе подходит: **Разработчик программного обеспечения**\n\n"
        "Почему: тебе нравится логика, создание функционала и решение задач.\n"
        "Что пробовать: Python, Git/GitHub, Telegram-боты, сайты (backend)."
    ),
    "sis": (
        "✅ Тебе подходит: **Техник информационных систем**\n\n"
        "Почему: тебе ближе техника, настройка, стабильность и поддержка систем.\n"
        "Что пробовать: сети (IP/Wi-Fi), Windows/Linux, администрирование, безопасность."
    ),
    "webdesign": (
        "✅ Тебе подходит: **Web-Дизайнер**\n\n"
        "Почему: тебе важны красота, удобство и визуальная часть.\n"
        "Что пробовать: Figma, UX/UI, типографика, адаптивные макеты."
    ),
    "marketing": (
        "✅ Тебе подходит: **Маркетинг (по отраслям)**\n\n"
        "Почему: тебе интересно продвижение, аудитория и результаты.\n"
        "Что пробовать: SMM, таргет, контент-план, аналитика, воронки продаж."
    ),
}



def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_menu(logged_in: bool) -> ReplyKeyboardMarkup:
    if logged_in:
        keyboard = [
            [KeyboardButton(text="🗓 Расписание"), KeyboardButton(text="🧪 Материалы")],
            [KeyboardButton(text="📢 Объявления"), KeyboardButton(text="❓ FAQ")],
            [KeyboardButton(text="🧭 Профориентация"), KeyboardButton(text="🧾 Info")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="🚪 Выйти")]
        ]
    else:
        keyboard = [
            [KeyboardButton(text="🔐 Войти"), KeyboardButton(text="❓ FAQ")],
            [KeyboardButton(text="🧭 Профориентация"), KeyboardButton(text="🧾 Info")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def help_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📷 Instagram (задать вопрос)", url=INSTAGRAM_URL))
    kb.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back:main"))
    return kb.as_markup()


def info_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="👩‍🏫 Учителя", callback_data="info:teachers")
    kb.button(text="🎓 Специальности", callback_data="info:specialties")
    kb.button(text="🏫 О колледже", callback_data="info:about")
    kb.button(text="🔗 Ссылки", callback_data="info:links")
    kb.button(text="🔙 Назад в меню", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()


def info_back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data="info:back")
    kb.button(text="🔙 Назад в меню", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()


def faq_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Как получить справку?", callback_data="faq:doc")
    kb.button(text="🏫 Где находится колледж?", callback_data="faq:address")
    kb.button(text="☎️ Контакты администрации", callback_data="faq:contacts")
    kb.button(text="📚 Как найти материалы?", callback_data="faq:materials")
    kb.button(text="🔙 Назад в меню", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()


def materials_kb(is_admin_user: bool):
    kb = InlineKeyboardBuilder()
    kb.button(text="🧪 Лабы", callback_data="mat:labs")
    kb.button(text="📚 Лекции", callback_data="mat:lectures")
    if is_admin_user:
        kb.button(text="🛠 Админ: загрузить файл", callback_data="admin:upload_menu")
        kb.button(text="🛠 Админ: расписание", callback_data="admin:schedule_menu")
        kb.button(text="🛠 Админ: объявление", callback_data="admin:announce_menu")
    kb.button(text="🔙 Назад в меню", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()


def group_choice_kb(groups: list[str], prefix: str, back_cb: str):
    kb = InlineKeyboardBuilder()
    for g in groups:
        kb.button(text=f"👥 {g}", callback_data=f"{prefix}:{g}")
    kb.button(text="🔙 Назад", callback_data=back_cb)
    kb.adjust(1)
    return kb.as_markup()


def days_kb():
    kb = InlineKeyboardBuilder()
    for d in DAYS:
        kb.button(text=d, callback_data=f"day:{d}")
    kb.button(text="🔙 Назад в меню", callback_data="back:main")
    kb.adjust(2)
    return kb.as_markup()


def schedule_days_admin_kb(group_name: str):
    kb = InlineKeyboardBuilder()
    for d in DAYS:
        kb.button(text=d, callback_data=f"admin:schedule_day:{group_name}:{d}")
    kb.button(text="🧹 Очистить расписание группы", callback_data=f"schedule_clear:{group_name}")
    kb.button(text="🔙 Назад", callback_data="admin:schedule_menu")
    kb.adjust(2)
    return kb.as_markup()


def schedule_admin_panel_kb(group_name: str, day: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить/добавить", callback_data=f"schedule_edit:{group_name}:{day}")
    kb.button(text="🗑 Удалить день", callback_data=f"schedule_del:{group_name}:{day}")
    kb.button(text="🔙 Назад к дням", callback_data=f"admin:schedule_group:{group_name}")
    kb.adjust(1)
    return kb.as_markup()


def upload_category_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🧪 Загрузить лабу", callback_data="admin:upload_cat:labs")
    kb.button(text="📚 Загрузить лекцию", callback_data="admin:upload_cat:lectures")
    kb.button(text="🔙 Назад", callback_data="back:materials")
    kb.adjust(1)
    return kb.as_markup()


def file_list_kb(rows: list[tuple[int, str]], category: str, admin: bool):
    kb = InlineKeyboardBuilder()
    for fid, title in rows[:30]:
        kb.button(text=f"📎 {title}", callback_data=f"file_send:{fid}")
        if admin:
            kb.button(text="🗑", callback_data=f"file_del:{fid}:{category}")
    kb.adjust(2 if admin else 1)
    kb.button(text="🔙 Назад", callback_data=f"mat:{category}")
    kb.adjust(1)
    return kb.as_markup()


def announcements_admin_kb(group_name: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Написать объявление", callback_data=f"announce_write:{group_name}")
    kb.button(text="🔙 Назад", callback_data="admin:announce_menu")
    kb.adjust(1)
    return kb.as_markup()


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS students(
            iin TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            group_name TEXT NOT NULL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_group(
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            group_name TEXT NOT NULL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS schedule(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            day TEXT NOT NULL,
            pairs TEXT NOT NULL,
            UNIQUE(group_name, day)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            file_id TEXT NOT NULL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS announcements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()


async def seed_demo_students():
    demo = [
        ("111111111111", "Глеб Шахворостов", "14-ТИС"),
        ("222222222222", "Максим Онипченко", "12-ТИС"),
        ("333333333333", "Егор Романов", "13-ТИС"),
        ("444444444444", "Тихонов Егор", "15-ТИС"),
    ]
    async with aiosqlite.connect(DB_NAME) as db:
        for iin, fio, grp in demo:
            await db.execute(
                "INSERT OR IGNORE INTO students(iin, full_name, group_name) VALUES(?, ?, ?)",
                (iin, fio, grp)
            )
        await db.commit()


async def get_student_by_iin(iin: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT full_name, group_name FROM students WHERE iin = ?", (iin,))
        return await cur.fetchone()


async def set_user_group(telegram_id: int, full_name: str, group_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_group(telegram_id, full_name, group_name) VALUES(?, ?, ?)",
            (telegram_id, full_name, group_name)
        )
        await db.commit()


async def clear_user_group(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM user_group WHERE telegram_id = ?", (telegram_id,))
        await db.commit()


async def get_user_group(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT full_name, group_name FROM user_group WHERE telegram_id = ?", (telegram_id,))
        return await cur.fetchone()


async def list_groups():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT DISTINCT group_name FROM students ORDER BY group_name")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def list_group_users(group_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT telegram_id FROM user_group WHERE group_name = ?", (group_name,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def set_schedule(group_name: str, day: str, pairs: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO schedule(group_name, day, pairs) VALUES(?, ?, ?)",
            (group_name, day, pairs)
        )
        await db.commit()


async def get_schedule(group_name: str, day: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT pairs FROM schedule WHERE group_name = ? AND day = ?",
            (group_name, day)
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def delete_schedule_day(group_name: str, day: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM schedule WHERE group_name = ? AND day = ?", (group_name, day))
        await db.commit()


async def clear_schedule_group(group_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM schedule WHERE group_name = ?", (group_name,))
        await db.commit()


async def add_file(group_name: str, category: str, title: str, file_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO files(group_name, category, title, file_id) VALUES(?, ?, ?, ?)",
            (group_name, category, title, file_id)
        )
        await db.commit()


async def list_files(group_name: str, category: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT id, title FROM files WHERE group_name = ? AND category = ? ORDER BY id DESC",
            (group_name, category)
        )
        return await cur.fetchall()


async def get_file(file_db_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT title, file_id FROM files WHERE id = ?", (file_db_id,))
        return await cur.fetchone()


async def delete_file(file_db_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM files WHERE id = ?", (file_db_id,))
        await db.commit()


async def add_announcement(group_name: str, text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO announcements(group_name, text) VALUES(?, ?)",
            (group_name, text)
        )
        await db.commit()


async def get_last_announcements(group_name: str, limit: int = 5):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT text, created_at FROM announcements WHERE group_name = ? ORDER BY id DESC LIMIT ?",
            (group_name, limit)
        )
        rows = await cur.fetchall()
        return rows


async def broadcast_to_group(group_name: str, text: str):
    user_ids = await list_group_users(group_name)
    sent = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 Объявление для {group_name}:\n\n{text}")
            sent += 1
        except Exception:
            pass
    return sent


@dp.message(Command("start"))
async def start(message: Message):
    ug = await get_user_group(message.from_user.id)
    if ug:
        fio, grp = ug
        await message.answer(f"✅ Ты вошёл(ла)\nФИО: {fio}\nГруппа: {grp}", reply_markup=main_menu(True))
    else:
        await message.answer("Привет! Нажми «🔐 Войти», чтобы видеть расписание и материалы своей группы.", reply_markup=main_menu(False))


@dp.callback_query(F.data == "back:main")
async def back_main(call: CallbackQuery):
    ug = await get_user_group(call.from_user.id)
    await call.answer()
    await call.message.answer("Меню:", reply_markup=main_menu(bool(ug)))


@dp.callback_query(F.data == "back:materials")
async def back_materials(call: CallbackQuery):
    ug = await get_user_group(call.from_user.id)
    await call.answer()
    if not ug:
        await call.message.answer("Сначала войди: 🔐 Войти", reply_markup=main_menu(False))
        return
    await call.message.answer("Материалы:", reply_markup=materials_kb(is_admin(call.from_user.id)))


@dp.message(F.text == "🔐 Войти")
@dp.message(Command("login"))
async def login_start(message: Message):
    LOGIN_WAIT.add(message.from_user.id)
    await message.answer(
        "Введи ИИН (демо, 12 цифр).\n"
        "Примеры:\n"
        "111111111111 (14-ТИС)\n"
        "222222222222 (12-ТИС)\n"
        "333333333333 (13-ТИС)\n"
        "444444444444 (15-ТИС)\n\n"
        "Чтобы отменить — напиши: отмена"
    )


@dp.message(F.text == "🚪 Выйти")
@dp.message(Command("logout"))
async def logout(message: Message):
    await clear_user_group(message.from_user.id)
    await message.answer("Ты вышел(ла).", reply_markup=main_menu(False))


@dp.message(F.text == "ℹ️ Помощь")
async def help_btn(message: Message):
    ug = await get_user_group(message.from_user.id)
    text = (
        "Команды:\n"
        "/start — меню\n"
        "/login — вход по ИИН (демо)\n"
        "/logout — выйти\n"
        "/test — профориентация\n\n"
        "Как скачать файл:\n"
        "Нажми на файл → скачать ⬇️\n\n"
        "Вопросы можно задать в Instagram."
    )
    await message.answer(text, reply_markup=help_kb())
    await message.answer("Меню:", reply_markup=main_menu(bool(ug)))


@dp.message(F.text == "🧾 Info")
async def info_menu(message: Message):
    await message.answer("Info-раздел:", reply_markup=info_kb())


@dp.callback_query(F.data == "info:back")
async def info_back(call: CallbackQuery):
    await call.answer()
    await call.message.answer("Info-раздел:", reply_markup=info_kb())


@dp.callback_query(F.data == "info:teachers")
async def info_teachers(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "👩‍🏫 Учителя\n\n"
        "• Калиаскаров Данияр Айтахметович\n"
        "• Светенко Мария Сергеевна\n"
        "• Дильман Дария Александровна\n"
        "• Шаблыгин Виктор Викторович\n"
        "• Ельчибаевна Райгуль Балабаевна\n"
        "• После его прихода,этот колледж стал легендой\n" \
        "Колледж принял новую форму жизни.Новый этап\n" \
        "Вот он - НАШ ЧЕМПИОН: Акихман Галымжан Ерланович",
        reply_markup=info_back_kb()
    )


@dp.callback_query(F.data == "info:specialties")
async def info_specialties(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "🎓 Специальности\n\n"
        "• Разработчик программного обеспечения\n"
        "• Техник информационных систем\n"
        "• Web-Дизайнер\n"
        "• Маркетинг(по отраслям)\n",
        reply_markup=info_back_kb()
    )


@dp.callback_query(F.data == "info:about")
async def info_about(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "🏫 О колледже\n\n"
        "Hexlet (Хекслет) — это международная образовательная платформа и онлайн-колледж \n" \
        "ориентированный на практическое обучение программированию и IT-профессиям.\n" \
        "Главная идея Hexlet — не просто давать теорию, а формировать реальные навыки, которые применяются непосредственно в работе. \n" \
        "Курсы построены на основе практических упражнений, проектов и реальных кейсов, что позволяет студентам учиться так, как работают настоящие разработчики.",
        reply_markup=info_back_kb()
    )


@dp.callback_query(F.data == "info:links")
async def info_links(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📷 Instagram", url=INSTAGRAM_URL))
    kb.row(InlineKeyboardButton(text="🎮 Discord", url=DISCORD_URL))
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="info:back"))
    kb.row(InlineKeyboardButton(text="🔙 В меню", callback_data="back:main"))
    await call.answer()
    await call.message.answer("🔗 Ссылки:", reply_markup=kb.as_markup())


@dp.message(F.text == "❓ FAQ")
async def faq_menu(message: Message):
    await message.answer("Часто задаваемые вопросы:", reply_markup=faq_kb())


@dp.callback_query(F.data.startswith("faq:"))
async def faq_answer(call: CallbackQuery):
    key = call.data.split(":", 1)[1]
    if key == "doc":
        text = "📄 Справки выдаются в администрации, либо у кураторов.\nОбычно срок: 1–3 рабочих дня."
    elif key == "address":
        text = "🏫 Адрес колледжа:\n Алмалинский район, улица Маметова, 67. \n https://go.2gis.com/RVYet"
    elif key == "contacts":
        text = "☎️ Контакты:\nТелефон: +7 707 014 1261 \nПочта: hexlet.ru\n"
    elif key == "materials":
        text = "📚 Материалы:\nВойди → «🧪 Материалы» → выбери «Лабы» или «Лекции»."
    else:
        text = "Не нашёл ответ."
    await call.answer()
    await call.message.answer(text, reply_markup=faq_kb())


@dp.message(Command("test"))
@dp.message(F.text == "🧭 Профориентация")
async def test_start(message: Message):
    TEST_STATE[message.from_user.id] = {"q": 0, "scores": {"dev": 0, "sis": 0, "webdesign": 0, "marketing": 0}
}
    await send_question(message.chat.id, message.from_user.id)


async def send_question(chat_id: int, user_id: int):
    state = TEST_STATE.get(user_id)
    if not state:
        return
    q_idx = state["q"]
    if q_idx >= len(QUESTIONS):
        scores = state["scores"]
        best = max(scores, key=scores.get)
        ug = await get_user_group(user_id)
        await bot.send_message(chat_id, "✅ Тест завершён!\n\nРезультат:\n" + RESULTS[best], reply_markup=main_menu(bool(ug)))
        TEST_STATE.pop(user_id, None)
        return
    question, options = QUESTIONS[q_idx]
    kb = InlineKeyboardBuilder()
    for opt_text, opt_key in options.items():
        kb.button(text=opt_text, callback_data=f"test:{opt_key}")
    kb.button(text="❌ Отмена", callback_data="test:cancel")
    kb.adjust(1)
    await bot.send_message(chat_id, f"Вопрос {q_idx + 1}/{len(QUESTIONS)}:\n{question}", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("test:"))
async def test_answer(call: CallbackQuery):
    user_id = call.from_user.id
    state = TEST_STATE.get(user_id)
    if not state:
        await call.answer("Тест не запущен.", show_alert=True)
        return
    key = call.data.split(":", 1)[1]
    if key == "cancel":
        TEST_STATE.pop(user_id, None)
        ug = await get_user_group(user_id)
        await call.answer("Отменено")
        await call.message.answer("Ок, тест отменён.", reply_markup=main_menu(bool(ug)))
        return
    state["scores"][key] += 1
    state["q"] += 1
    await call.answer()
    await send_question(call.message.chat.id, user_id)


@dp.message(F.text == "🗓 Расписание")
@dp.message(Command("schedule"))
async def schedule_menu(message: Message):
    ug = await get_user_group(message.from_user.id)
    if not ug:
        await message.answer("Сначала войди: 🔐 Войти", reply_markup=main_menu(False))
        return
    await message.answer("Выбери день недели:", reply_markup=days_kb())


@dp.callback_query(F.data.startswith("day:"))
async def schedule_day(call: CallbackQuery):
    ug = await get_user_group(call.from_user.id)
    if not ug:
        await call.answer()
        await call.message.answer("Сначала войди: /login", reply_markup=main_menu(False))
        return
    fio, grp = ug
    day = call.data.split(":", 1)[1]
    data = await get_schedule(grp, day)
    await call.answer()
    if not data:
        await call.message.answer(f"👥 {grp}\n🗓 {day}\n\nРасписание пока не добавлено.")
    else:
        await call.message.answer(f"👥 {grp}\n🗓 {day}\n\n{data}")
    if is_admin(call.from_user.id):
        await call.message.answer("Админ-панель:", reply_markup=schedule_admin_panel_kb(grp, day))


@dp.message(F.text == "🧪 Материалы")
async def materials_menu(message: Message):
    ug = await get_user_group(message.from_user.id)
    if not ug:
        await message.answer("Сначала войди: 🔐 Войти", reply_markup=main_menu(False))
        return
    await message.answer("Материалы:", reply_markup=materials_kb(is_admin(message.from_user.id)))


@dp.callback_query(F.data.startswith("mat:"))
async def materials_list(call: CallbackQuery):
    ug = await get_user_group(call.from_user.id)
    if not ug:
        await call.answer()
        await call.message.answer("Сначала войди: /login", reply_markup=main_menu(False))
        return
    fio, grp = ug
    key = call.data.split(":", 1)[1]
    category = "labs" if key == "labs" else "lectures"
    rows = await list_files(grp, category)
    await call.answer()
    if not rows:
        await call.message.answer(f"👥 {grp}\nПока файлов нет.")
        return
    await call.message.answer(f"👥 {grp}\nВыбери файл:", reply_markup=file_list_kb(rows, category, is_admin(call.from_user.id)))


@dp.callback_query(F.data.startswith("file_send:"))
async def file_send(call: CallbackQuery):
    file_db_id = int(call.data.split(":", 1)[1])
    row = await get_file(file_db_id)
    if not row:
        await call.answer("Файл не найден", show_alert=True)
        return
    title, tg_file_id = row
    await call.answer()
    await bot.send_document(call.message.chat.id, tg_file_id, caption=f"📎 {title}\n\n⬇️ Чтобы скачать: нажми на файл → скачать")


@dp.callback_query(F.data.startswith("file_del:"))
async def file_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    parts = call.data.split(":")
    file_db_id = int(parts[1])
    await delete_file(file_db_id)
    await call.answer("Удалено ✅")
    await call.message.answer("Файл удалён.")


@dp.message(F.text == "📢 Объявления")
async def announcements_view(message: Message):
    ug = await get_user_group(message.from_user.id)
    if not ug:
        await message.answer("Сначала войди: 🔐 Войти", reply_markup=main_menu(False))
        return
    fio, grp = ug
    rows = await get_last_announcements(grp, limit=7)
    if not rows:
        await message.answer(f"👥 {grp}\nОбъявлений пока нет.")
        return
    text = f"📢 Объявления для {grp}:\n\n"
    for i, (t, created) in enumerate(rows, 1):
        text += f"{i}) {t}\n"
    await message.answer(text)


@dp.callback_query(F.data == "admin:upload_menu")
async def admin_upload_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    await call.answer()
    await call.message.answer("Выбери, что загружаем:", reply_markup=upload_category_kb())


@dp.callback_query(F.data.startswith("admin:upload_cat:"))
async def admin_upload_choose_group(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    category = call.data.split(":")[-1]
    groups = await list_groups()
    await call.answer()
    await call.message.answer("Выбери группу:", reply_markup=group_choice_kb(groups, f"admin:upload_group:{category}", "admin:upload_menu"))


@dp.callback_query(F.data.startswith("admin:upload_group:"))
async def admin_upload_set_mode(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    parts = call.data.split(":")
    category = parts[2]
    group_name = parts[3]
    UPLOAD_MODE[call.from_user.id] = (category, group_name)
    await call.answer()
    await call.message.answer(
        f"✅ Режим загрузки\nГруппа: {group_name}\nКатегория: {category}\n\n"
        "Отправь файл документом и добавь подпись (название).\n"
        "Чтобы отменить — напиши: отмена"
    )


@dp.callback_query(F.data == "admin:schedule_menu")
async def admin_schedule_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    groups = await list_groups()
    await call.answer()
    await call.message.answer("Выбери группу для расписания:", reply_markup=group_choice_kb(groups, "admin:schedule_group", "back:main"))


@dp.callback_query(F.data.startswith("admin:schedule_group:"))
async def admin_schedule_days(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    group_name = call.data.split(":", 2)[2]
    await call.answer()
    await call.message.answer(f"👥 {group_name}\nВыбери день:", reply_markup=schedule_days_admin_kb(group_name))


@dp.callback_query(F.data.startswith("admin:schedule_day:"))
async def admin_schedule_show_day(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    _, _, group_name, day = call.data.split(":", 3)
    data = await get_schedule(group_name, day)
    await call.answer()
    if not data:
        await call.message.answer(f"👥 {group_name}\n🗓 {day}\n\nРасписания пока нет.")
    else:
        await call.message.answer(f"👥 {group_name}\n🗓 {day}\n\n{data}")
    await call.message.answer("Админ-панель:", reply_markup=schedule_admin_panel_kb(group_name, day))


@dp.callback_query(F.data.startswith("schedule_edit:"))
async def schedule_edit(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    _, group_name, day = call.data.split(":", 2)
    SCHEDULE_EDIT[call.from_user.id] = (group_name, day)
    await call.answer()
    await call.message.answer(
        f"✏️ Введи расписание для группы {group_name} на {day} одним сообщением.\n"
        "Чтобы отменить — напиши: отмена"
    )


@dp.callback_query(F.data.startswith("schedule_del:"))
async def schedule_del(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    _, group_name, day = call.data.split(":", 2)
    await delete_schedule_day(group_name, day)
    await call.answer("Удалено ✅")
    await call.message.answer(f"✅ Удалил расписание: {group_name} — {day}")


@dp.callback_query(F.data.startswith("schedule_clear:"))
async def schedule_clear(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    group_name = call.data.split(":", 1)[1]
    await clear_schedule_group(group_name)
    await call.answer("Очищено ✅")
    await call.message.answer(f"✅ Расписание группы {group_name} очищено.")


@dp.callback_query(F.data == "admin:announce_menu")
async def admin_announce_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    groups = await list_groups()
    await call.answer()
    await call.message.answer("Для какой группы объявление?", reply_markup=group_choice_kb(groups, "admin:announce_group", "back:materials"))


@dp.callback_query(F.data.startswith("admin:announce_group:"))
async def admin_announce_group(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    group_name = call.data.split(":", 2)[2]
    await call.answer()
    await call.message.answer(f"👥 {group_name}\nЧто делаем?", reply_markup=announcements_admin_kb(group_name))


@dp.callback_query(F.data.startswith("announce_write:"))
async def announce_write(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только админ.", show_alert=True)
        return
    group_name = call.data.split(":", 1)[1]
    ANNOUNCE_WAIT[call.from_user.id] = group_name
    await call.answer()
    await call.message.answer(
        f"✏️ Напиши текст объявления для группы {group_name}.\n"
        "Оно сохранится и сразу разошлётся всем вошедшим студентам этой группы.\n\n"
        "Чтобы отменить — напиши: отмена"
    )


@dp.message(Command("announce"))
async def announce_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Формат:\n"
        "ГРУППА; текст объявления\n\n"
        "Пример:\n"
        "14-ТИС; завтра первая пара отменена\n\n"
        "Чтобы отменить — напиши: отмена"
    )
    ANNOUNCE_WAIT[message.from_user.id] = "__freeform__"


@dp.message(F.document)
async def handle_document(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    if user_id not in UPLOAD_MODE:
        return
    category, group_name = UPLOAD_MODE[user_id]
    title = (message.caption or "").strip()
    if not title:
        await message.answer("Нужна подпись (название). Отправь файл ещё раз с подписью.")
        return
    await add_file(group_name, category, title, message.document.file_id)
    UPLOAD_MODE.pop(user_id, None)
    await message.answer(f"✅ Файл сохранён\nГруппа: {group_name}\nКатегория: {category}\nНазвание: {title}")


@dp.message()
async def text_router(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()

    if txt.lower() == "отмена":
        changed = False
        if uid in LOGIN_WAIT:
            LOGIN_WAIT.remove(uid)
            changed = True
        if uid in SCHEDULE_EDIT:
            SCHEDULE_EDIT.pop(uid, None)
            changed = True
        if uid in UPLOAD_MODE:
            UPLOAD_MODE.pop(uid, None)
            changed = True
        if uid in ANNOUNCE_WAIT:
            ANNOUNCE_WAIT.pop(uid, None)
            changed = True
        ug = await get_user_group(uid)
        if changed:
            await message.answer("Ок, отменил.", reply_markup=main_menu(bool(ug)))
            return

    if uid in ANNOUNCE_WAIT:
        group_name = ANNOUNCE_WAIT[uid]

        if group_name == "__freeform__":
            if ";" not in txt:
                await message.answer("Формат: ГРУППА; текст объявления")
                return
            g, t = txt.split(";", 1)
            g = g.strip()
            t = t.strip()
            if not g or not t:
                await message.answer("Формат: ГРУППА; текст объявления")
                return
            await add_announcement(g, t)
            sent = await broadcast_to_group(g, t)
            ANNOUNCE_WAIT.pop(uid, None)
            await message.answer(f"✅ Объявление добавлено для {g}\n📨 Разослал: {sent}")
            return

        if not txt:
            await message.answer("Напиши текст объявления или: отмена")
            return
        await add_announcement(group_name, txt)
        sent = await broadcast_to_group(group_name, txt)
        ANNOUNCE_WAIT.pop(uid, None)
        await message.answer(f"✅ Объявление добавлено для {group_name}\n📨 Разослал: {sent}")
        return

    if uid in LOGIN_WAIT:
        iin = txt
        if (not iin.isdigit()) or len(iin) != 12:
            await message.answer("ИИН должен быть 12 цифр. Попробуй ещё раз или напиши: отмена")
            return
        row = await get_student_by_iin(iin)
        if not row:
            await message.answer("Такого ИИН нет в демо-базе. Попробуй другой или напиши: отмена")
            return
        full_name, group_name = row
        await set_user_group(uid, full_name, group_name)
        LOGIN_WAIT.remove(uid)
        await message.answer(f"✅ Вход выполнен!\nФИО: {full_name}\nГруппа: {group_name}", reply_markup=main_menu(True))
        return

    if uid in SCHEDULE_EDIT:
        group_name, day = SCHEDULE_EDIT[uid]
        if not txt:
            await message.answer("Пусто. Отправь текст расписания или: отмена")
            return
        await set_schedule(group_name, day, txt)
        SCHEDULE_EDIT.pop(uid, None)
        ug = await get_user_group(uid)
        await message.answer(f"✅ Сохранил расписание\nГруппа: {group_name}\nДень: {day}", reply_markup=main_menu(bool(ug)))
        return

    if txt == "🧪 Материалы":
        await materials_menu(message)
        return
    if txt == "🗓 Расписание":
        await schedule_menu(message)
        return
    if txt == "🔐 Войти":
        await login_start(message)
        return
    if txt == "🚪 Выйти":
        await logout(message)
        return
    if txt == "📢 Объявления":
        await announcements_view(message)
        return
    if txt == "❓ FAQ":
        await faq_menu(message)
        return
    if txt == "ℹ️ Помощь":
        await help_btn(message)
        return
    if txt == "🧾 Info":
        await info_menu(message)
        return
    if txt == "🧭 Профориентация":
        await test_start(message)
        return

    ug = await get_user_group(uid)
    await message.answer("Я не понял 😅\nНажми кнопки меню 👇", reply_markup=main_menu(bool(ug)))


async def main():
    await init_db()
    await seed_demo_students()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
