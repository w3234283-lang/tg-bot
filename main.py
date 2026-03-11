import asyncio
import logging
import random
import sqlite3
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
 CallbackQuery,
 InlineKeyboardButton,
 InlineKeyboardMarkup,
 Message,
)

# CONFIG
BOT_TOKEN = "8325669732:AAGFvmLJMbAOilhKWElk43LG-FksHJpCfNk"
CRYPTO_TOKEN = "545475:AALkj6ssx8n0hVc2LR2ouWSat2YpoLCFUow"
ADMIN_ID = 7921743592
CRYPTO_API = "https://pay.crypt.bot/api"
МИНИМАЛЬНАЯ СТАВКА = 0,10
МАКСИМАЛЬНАЯ СТАВКА = 10,0
ВАЛЮТА = "USDT"
ИДЕНТИФИКАТОР КАНАЛА = Нет

ВЫИГРЫШНЫЕ ШАНСЫ = {
 "кубики": 1 / 6,
 "нечетные": 0,40,
 "баскетбол": 0,25,
 "футбол": 0,20,
 "боулинг": 0,25,
 "дартс": 0,15,
}

MULTIPLIERS = {
 "игральные кости": 5.0,
 "evenodd": 1.8,
 "баскетбол": 3.0,
 "футбол": 3.5,
 "боулинг": 2.5,
 "дартс": 5.0,
}

GAME_EMOJI = {
 "dice": "dice",
 "evenodd": "dice",
 "basketball": "basketball",
 "football": "football",
 "bowling": "bowling",
 "darts": "darts",
}

GAME_ICON = {
 "игральные кости": "игральные кости",
 "evenodd": "игральные кости",
 "баскетбол": "баскетбол",
 "футбол": "футбол",
 "боулинг": "боулинг",
 "дартс": "дартс",
}

DICE_EMOJI = {
 "dice": "dice",
 "evenodd": "dice",
 "basketball": "basketball",
 "football": "football",
 "bowling": "bowling",
 "darts": "darts",
}

ИМЕНА_ИГР = {
 "dice": "Кубик (точное число)",
 "evenodd": "Чет / Нечет",
 "basketball": "Баскетбол",
 "football": "Футбол",
 "bowling": "Боулинг",
 "darts": "Дартс",
}

EMOJI_MAP = {
 "dice": "dice",
 "evenodd": "dice",
 "basketball": "basketball",
 "football": "football",
 "bowling": "bowling",
 "darts": "darts",
}

TG_EMOJI = {
 "dice": "\U0001f3b2", 
 "evenodd": "\U0001f3b2", 
 "баскетбол": "U0001f3c0", 
 "футбол": "u26bd", 
 "боулинг": "U0001f3b3", 
 "дартс": "\U0001f3af",
}

ведение журнала.basicConfig(уровень = ведение журнала.ИНФОРМАЦИЯ)
logger = ведение журнала.getLogger(__имя__)


# БАЗА ДАННЫХ

определение init_db(): 
 con = sqlite3.connect("casino.db")
 con.executescript(
 "СОЗДАТЬ ТАБЛИЦУ, ЕСЛИ НЕ СУЩЕСТВУЕТ настроек (текст ключа, ПЕРВИЧНЫЙ КЛЮЧ, ТЕКСТ значения)";
 "CREATE TABLE IF NOT EXISTS treasury (id INTEGER PRIMARY KEY CHECK (id=1), balance REAL NOT NULL DEFAULT 0);"
 "INSERT OR IGNORE INTO treasury VALUES (1, 0);"
 "CREATE TABLE IF NOT EXISTS bets ("
 " id INTEGER PRIMARY KEY AUTOINCREMENT,"
 " user_id INTEGER NOT NULL,"
 " username TEXT,"
 " game TEXT NOT NULL,"
 " choice TEXT,"
 " amount REAL NOT NULL,"
 " won INTEGER,"
 " payout REAL DEFAULT 0,"
 " invoice_id TEXT,"
 " created_at TEXT DEFAULT (datetime('now'))"
 ");"
 "CREATE TABLE IF NOT EXISTS users ("
 " user_id INTEGER PRIMARY KEY,"
 " username TEXT,"
 " total_bets INTEGER DEFAULT 0,"
 " total_won INTEGER DEFAULT 0,"
 " total_lost INTEGER DEFAULT 0,"
 " total_wagered REAL DEFAULT 0,"
 " total_payout REAL DEFAULT 0"
 ");"
 ) 
 con.commit()
 con.close()


def get_setting(ключ, по умолчанию = Нет):
 con = sqlite3.connect("casino.db")
 row = con.execute("ВЫБРАТЬ значение ИЗ настроек, ГДЕ key=?", (ключ,)).fetchone() 
 con.close()
 возвращает строку[0], если по умолчанию используется строка else.


def set_setting(ключ, значение):
 con = sqlite3.connect("casino.db")
 con.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
 con.commit()
 con.close()


def get_treasury():
 con = sqlite3.connect("casino.db")
 bal = con.execute("SELECT balance FROM treasury WHERE id=1").fetchone()[0] 
 con.close()
 возвращает bal


значение adjust_treasury(дельта):
 con = sqlite3.connect("casino.db")
 con.execute("ОБНОВИТЬ УСТАНОВЛЕННЫЙ баланс казначейства=balance+? ГДЕ id=1", (дельта,))
 con.commit()
 con.close()


def save_bet(идентификатор пользователя, имя пользователя, игра, выбор, сумма, invoice_id):
 con = sqlite3.connect("casino.db")
 cur = con.cursor()
 cur.execute(
 "INSERT INTO bets (user_id,username,game,choice,amount,invoice_id) VALUES (?,?,?,?,?,?)",
 (user_id, username, game, choice, amount, invoice_id),
 )
 bid = cur.lastrowid
 con.commit()
 con.close()
 return bid


определение get_bet_by_invoice(invoice_id):
 con = sqlite3.connect("casino.db")
 строка = con.execute("ВЫБРАТЬ * ИЗ ставок, ГДЕ invoice_id=?", (invoice_id,)).fetchone() 
 con.close()
 вернуть строку


определение разрешающей ставки (invoice_id, выигранная сумма, выплата):
 con = sqlite3.connect("casino.db")
 cur = con.cursor()
 cur.execute(
 "UPDATE bets SET won=?,payout=? WHERE invoice_id=?",
 (1 if won else 0, payout, invoice_id),
 )
 row = cur.execute(
 "SELECT user_id,username,amount FROM bets WHERE invoice_id=?", (invoice_id,)
 ).fetchone()
 if row:
 uid, uname, amount = row
 cur.execute(
 "INSERT INTO users (user_id,username,total_bets,total_won,total_lost,total_wagered,total_payout) "
 "VALUES (?,?,1,?,?,?,?) "
 "ON CONFLICT(user_id) DO UPDATE SET "
 "username=excluded.username, "
 "total_bets=total_bets+1, "
 "total_won=total_won+excluded.total_won, "
 "total_lost=total_lost+excluded.total_lost, "
 "total_wagered=total_wagered+excluded.total_wagered, "
 "total_payout=total_payout+excluded.total_payout",
 (uid, uname, 1, если выиграл, 0, если проиграл, 0, сумма, выплата),
 )
 con.commit()
 con.close()
 return row


def get_stats():
 con = sqlite3.connect("casino.db")
 cur = con.cursor()
 total_bets = cur.execute("SELECT COUNT(*) FROM bets WHERE won IS NOT NULL").fetchone()[0]
 total_won = cur.execute("SELECT COUNT(*) FROM bets WHERE won=1").fetchone()[0]
 total_wagered = cur.execute("SELECT COALESCE(SUM(amount),0) FROM bets WHERE won IS NOT NULL").fetchone()[0]
 total_payout = cur.execute("SELECT COALESCE(SUM(payout),0) FROM bets WHERE won=1").fetchone()[0]
 treasury = cur.execute("SELECT balance FROM treasury WHERE id=1").fetchone()[0]
 top_users = cur.execute(
 "SELECT username,total_bets,total_won,total_wagered,total_payout "
 "FROM users ORDER BY total_wagered DESC LIMIT 5"
 ).fetchall()
 game_stats = cur.execute(
 "SELECT game,COUNT(*) as cnt,SUM(won) as wins,COALESCE(SUM(amount),0) as wagered "
 "FROM bets WHERE won IS NOT NULL GROUP BY game"
 ).fetchall()
 con.close()
 return {
 "total_bets": total_bets,
 "total_won": total_won,
 "total_wagered": total_wagered,
 "total_payout": total_payout,
 "treasury": treasury,
 "top_users": top_users,
 "game_stats": game_stats,
 }


# API КРИПТОБОТА

async def create_invoice(amount, payload):
 url = CRYPTO_API + "/createInvoice"
 headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
 params = {
 "актив": ВАЛЮТА,
 "сумма": str(round(сумма, 2)),
 "полезная нагрузка": полезная нагрузка,
 "описание": "ставка в казино",
 "expires_in": 300,
 }
 try:
 async with aiohttp.ClientSession() as s:
 async with s.post(url, json=params, headers=headers) as r:
 data = await r.json()
 if data.get("ok"):
 возвращает data["результат"]
 исключение, за исключением e: 
 logger.error("ошибка create_invoice: %s", e) 
 возвращает None


асинхронное определение create_check(суммы):
 url = CRYPTO_API + "/createCheck"
 headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
 params = {"asset": CURRENCY, "amount": str(round(amount, 2))}
 try:
 async with aiohttp.ClientSession() as s:
 async with s.post(url, json=params, headers=headers) as r:
 data = await r.json()
 if data.get("ok"):
 return data["result"]
 except Exception as e:
 logger.error("Ошибка create_check: %s", e)
 return None


async def get_paid_invoices():
 url = CRYPTO_API + "/getInvoices"
 headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
 params = {"asset": CURRENCY, "status": "paid", "count": 100}
 try:
 async with aiohttp.ClientSession() as s:
 async with s.get(url, params=params, headers=headers) as r:
 data = await r.json()
 if data.get("ok"):
 return data["result"].get("items", [])
 except Exception as e:
 logger.error("Ошибка get_paid_invoices: %s", e)
 return []


async def transfer_to_admin(amount):
 url = CRYPTO_API + "/transfer"
 headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
 spend_id = "withdraw_" + str(int(datetime.now().timestamp()))
 params = {
 "user_id": ADMIN_ID,
 "asset": ВАЛЮТА,
 "amount": str(round(amount, 2)),
 "spend_id": spend_id,
 "comment": "Вывод средств из казино",
 }
 попробуйте: 
 выполнить синхронизацию с aiohttp.ClientSession() как s: 
 асинхронный с s.post(url, json=параметры, headers= заголовки) как r: 
 data = ожидание r.json()
 if data.get("ok"):
 возвращает data["результат"]
 исключение, за исключением e: 
 logger.error("ошибка передачи: %s", e) 
 возвращает None


# КЛАВИАТУРЫ

def main_menu_kb():
 return InlineKeyboardMarkup(
 inline_keyboard=[
 [
 InlineKeyboardButton(текст="\U0001f3b2 Кубик", callback_data="игра: кости"), 
 InlineKeyboardButton(текст="\U0001f3b2 Чет/Нечет", callback_data="игра: evenodd"), 
], 
[ 
 InlineKeyboardButton(текст="\U0001f3c0 Баскетбол", callback_data="игра: баскетбол"), 
 InlineKeyboardButton(текст="\u26bd Футбол", callback_data="игра: футбол"), 
], 
[ 
 InlineKeyboardButton(текст="\U0001f3b3 Боулинг", callback_data="игра: боулинг"), 
 InlineKeyboardButton(текст="\U0001f3af Дартс", callback_data="игра: дартс"), 
], 
 [InlineKeyboardButton(text="\U0001f4ca Моя статистика", callback_data="my_stats")], 
] 
 )


def back_kb():
 return InlineKeyboardMarkup(
 inline_keyboard=[[InlineKeyboardButton(text="\U0001f519 Назад", callback_data="back_to_menu")]]
 )


def bet_amount_kb(game, choice):
 amounts = [0,10, 0,25, 0,50, 1,0, 2,0, 5,0, 10,0]
 rows = []
 row = []
 for a in amounts:
 row.append(
 InlineKeyboardButton(
 text=str(a) + " " + ВАЛЮТА,
 callback_data="bet:" + game + ":" + choice + ":" + str(a),
 )
 )
 if len(row) == 4:
 rows.append(row)
 row = []
 if row:
 rows.append(row)
 rows.append([InlineKeyboardButton(text="\U0001f519 Назад", callback_data="back_to_menu")])
 return InlineKeyboardMarkup(inline_keyboard=rows)


def dice_choice_kb():
 nums = [
 InlineKeyboardButton(text=str(i), callback_data="choice:dice:" + str(i))
 for i in range(1, 7)
 ]
 return InlineKeyboardMarkup(
 inline_keyboard=[
 nums[:3],
 nums[3:],
 [InlineKeyboardButton(text="\U0001f519 Назад", callback_data="back_to_menu")],
 ]
 )


def evenodd_choice_kb():
 return InlineKeyboardMarkup(
 inline_keyboard=[
 [
 InlineKeyboardButton(text="Четное", callback_data="choice:evenodd:even"),
 InlineKeyboardButton(text="Нечетное", callback_data="choice:evenodd:odd"),
 ],
 [InlineKeyboardButton(text="\U0001f519 Назад", callback_data="back_to_menu")],
 ]
 )


def admin_menu_kb():
 return InlineKeyboardMarkup(
 inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f4ca Статистика", callback_data="adm:stats")],
 [InlineKeyboardButton(text="\U0001f4b0 Пополнить казну", callback_data="adm:deposit")],
 [InlineKeyboardButton(text="\U0001f4b8 Вывести из казны", callback_data="adm:withdraw")],
 [InlineKeyboardButton(text="\U0001f4e2 Установить канал", callback_data="adm:setchannel")],
 [InlineKeyboardButton(text="\U0001f4b5 Баланс казны", callback_data="adm:balance")],
 ]
 )


# FSM
class AdminFSM(StatesGroup):
 deposit = State()
 withdraw = State()
 setchannel = State()


# МАРШРУТИЗАТОР

router = Router()


@router.message(Command("start"))
async def cmd_start(msg: Message):
 text = (
 "\U0001f3b0 Добро пожаловать в Casino Bot!\n\n"
 "Минимальная ставка: " + str(MIN_BET) + " " + CURRENCY + "\n"
 "Максимальная ставка: " + str(MAX_BET) + " " + CURRENCY + "\n\n"
 "Выбери игру:"
 )
 await msg.answer(text, reply_markup=main_menu_kb())


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
 if msg.from_user.id != ADMIN_ID:
 await msg.answer("Нет доступа.")
 return
 await msg.answer("Панель администратора:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(cb: CallbackQuery, state: FSMContext):
 await state.clear()
 await cb.message.edit_text("Выбери игру:", reply_markup=main_menu_kb())
 await cb.answer()


@router.callback_query(F.data.startswith("game:"))
async def game_select(cb: CallbackQuery):
 game = cb.data.split(":")[1]
 icon = TG_EMOJI[game]
 name = GAME_NAMES[game]
 mult = MULTIPLIERS[game]

 if game == "dice":
 text = icon + " " + name + "\nУгадай число от 1 до 6\nВыигрыш: ставка x" + str(mult) + "\n\nВыбери число: "
 await cb.message.edit_text(text, reply_markup=dice_choice_kb())
 elif game == "evenodd":
 text = icon + " " + name + "\nВыигрыш: ставка x" + str(mult) + "\n\nВыбери вариант:"
 await cb.message.edit_text(text, reply_markup=evenodd_choice_kb())
 else:
 text = icon + " " + name + "\nВыигрыш: ставка x" + str(mult) + "\n\nВыбери сумму ставки:"
 await cb.message.edit_text(text, reply_markup=bet_amount_kb(game, "yes"))
 await cb.answer()


@router.callback_query(F.data.startswith("choice:"))
async def choice_select(cb: CallbackQuery):
 parts = cb.data.split(":")
 game = parts[1]
 choice = parts[2]
 icon = TG_EMOJI[game]
 name = GAME_NAMES[game]
 mult = MULTIPLIERS[game]
 if game == "evenodd":
 choice_label = "Четное" if choice == "even" else "Нечетное"
 else:
 choice_label = choice
 text = (
 icon + " " + name + "\n"
 "Твой выбор: " + choice_label + "\n"
 "Выигрыш: ставка x" + str(mult) + "\n\n"
 "Выбери сумму ставки:"
 )
 await cb.message.edit_text(text, reply_markup=bet_amount_kb(game, choice))
 await cb.answer()


@router.callback_query(F.data.startswith("bet:"))
async def place_bet(cb: CallbackQuery):
 parts = cb.data.split(":")
 game = parts[1]
 choice = parts[2]
 amount = float(parts[3])

 payload = game + "|" + choice + "|" + str(cb.from_user.id)
 invoice = await create_invoice(amount, payload)

 if not invoice:
 await cb.answer("Ошибка при создании счета. Попробуй позже.", show_alert=True)
 Возврат

 invoice_id = str(invoice.get("invoice_id", """))
 pay_url = invoice.get("bot_invoice_url", invoice.get("pay_url", ""))

 username = cb.from_user.username или cb.from_user.first_name или ("id" + str(cb.from_user.id))
 save_bet(cb.from_user.id, username, game, choice, amount, invoice_id)

 icon = TG_EMOJI[game]
 name = GAME_NAMES[game]
 mult = MULTIPLIERS[game]
 win_amount = round(amount * mult, 2)

 if game == "evenodd":
 choice_label = "Четное" if choice == "even" else "Нечетное"
 остальное: 
 выбранная метка = выбор

 текст = (
 "\U0001f4b3 Счет на оплату создан!\n\n"
 "Игра: " + icon + " " + name + "\n"
 "Ставка: " + str(amount) + " " + CURRENCY + "\n"
 "Выбор: " + choice_label + "\n"
 "Выигрыш при победе: " + str(win_amount) + " " + ВАЛЮТА + "\n\n"
 "Счет действителен в течение 5 минут"
 )
 kb = InlineKeyboardMarkup(
 inline_keyboard=[
 [InlineKeyboardButton(text="Оплатить " + str(amount) + " " + ВАЛЮТА, url=pay_url)],
 [InlineKeyboardButton(text="\U0001f519 В меню", callback_data="back_to_menu")],
 ]
 )
 await cb.message.edit_text(text, reply_markup=kb)
 await cb.answer()


@router.callback_query(F.data == "my_stats")
async def my_stats(cb: CallbackQuery):
 con = sqlite3.connect("casino.db")
 row = con.execute(
 "SELECT total_bets,total_won,total_lost,total_wagered,total_payout FROM users WHERE user_id=?",
 (cb.from_user.id,),
 ).fetchone()
 con.close()
 if not row:
 await cb.answer("У вас еще нет статистики.", show_alert=True)
 return
 tb, tw, tl, twa, tp = row
 profit = round(tp - twa, 2)
 text = (
 "\U0001f4ca Твоя статистика\n\n"
 "Всего ставок: " + str(tb) + "\n"
 "Побед: " + str(tw) + " | Поражений: " + str(tl) + "\n"
 "Поставлено: " + str(round(twa, 2)) + " " + ВАЛЮТА + "\n"
 "Выиграно: " + str(round(tp, 2)) + " " + ВАЛЮТА + "\n"
 "Прибыль: " + str(profit) + " " + ВАЛЮТА
 ) 
 кб = InlineKeyboardMarkup ( 
 inline_keyboard=[[InlineKeyboardButton(text="\U0001f519 В меню", callback_data="back_to_menu")]]
 ) 
 ожидает cb.message.edit_text(текст, reply_markup= кб)
 ожидает cb.answer()


# ОБРАТНЫЕ ВЫЗОВЫ АДМИНИСТРАТОРА

@router.callback_query(F.data.startswith("adm:"))
async def admin_cb(cb: CallbackQuery, state: FSMContext):
 if cb.from_user.id != ADMIN_ID:
 await cb.answer("Нет доступа.", show_alert=True)
 return
 action = cb.data.split(":")[1]
 cancel_kb = InlineKeyboardMarkup(
 inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="adm:back")]]
 )

 if action == "balance":
 bal = get_treasury()
 await cb.answer("Казна: " + str(round(bal, 2)) + " " + ВАЛЮТА, show_alert=True)

 elif action == "stats":
 s = get_stats()
 wr = round(s["total_won"] / s["total_bets"] * 100, 1) if s["total_bets"] else 0
 text = (
 "Статистика казино\n\n"
 "Казна: " + str(round(s["treasury"], 2)) + " " + ВАЛЮТА + "\n\n"
 "Всего ставок: " + str(s["total_bets"]) + "\n"
 "Побед игроков: " + str(s["total_won"]) + " (" + str(wr) + "%)\n"
 "Оборот: " + str(round(s["total_wagered"], 2)) + " " + CURRENCY + "\n"
 "Выплачено: " + str(round(s["total_payout"], 2)) + " " + ВАЛЮТА + "\n"
 "Доход казино: " + str(round(s["total_wagered"] - s["total_payout"], 2)) + " " + ВАЛЮТА + "\n"
 )
 if s["game_stats"]:
 text += "\nПо играм:\n"
 for g, cnt, wins, wag in s["game_stats"]:
 wr2 = round((wins or 0) / cnt * 100, 1) if cnt else 0
 text += TG_EMOJI.get(g, "") + " " + GAME_NAMES.get(g, g) + ": " + str(cnt) + " ставок, " + str(wr2) + "% побед\n"
 if s["top_users"]:
 text += "\nТоп игроков:\n"
 for i, row in enumerate(s["top_users"], 1):
 un, tb, tw, twa, tp = row
 text += str(i) + ". @" + str(un) + ": " + str(tb) + " ставок, " + str(round(twa, 2)) + " " + ВАЛЮТА + "\n"
 back_kb2 = InlineKeyboardMarkup(
 inline_keyboard=[[InlineKeyboardButton(text="\U0001f519 Назад", callback_data="adm:back")]]
 )
 await cb.message.edit_text(text, reply_markup=back_kb2)

 else if action == "deposit":
 await state.set_state(AdminFSM.deposit)
 await cb.message.edit_text("Введите сумму пополнения казны (" + ВАЛЮТА + "):", reply_markup=cancel_kb)

 elif action == "withdraw":
 bal = get_treasury()
 await state.set_state(AdminFSM.withdraw)
 await cb.message.edit_text(
 "Казна: " + str(round(bal, 2)) + " " + ВАЛЮТА + "\nВведите сумму вывода: ",
 reply_markup=cancel_kb,
 )

 elif action == "setchannel":
 await state.set_state(AdminFSM.setchannel)
 await cb.message.edit_text(
 "Отправьте сообщение из канала или введите его идентификатор (например, -1001234567890):",
 reply_markup=cancel_kb,
 )

 elif action == "back":
 await state.clear()
 await cb.message.edit_text("Панель администратора:", reply_markup=admin_menu_kb())

 await cb.answer()


@router.message(AdminFSM.deposit)
async def admin_deposit(msg: Message, state: FSMContext):
 if msg.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(msg.text.replace(",", "."))
 if amount <= 0:
 raise ValueError
 except Exception:
 await msg.answer("Неверная сумма. Введите число больше 0.")
 return
 adjust_treasury(amount)
 await state.clear()
 bal = get_treasury()
 await msg.answer(
 "Казна пополнена на " + str(amount) + " " + ВАЛЮТА + "\nБаланс: " + str(round(bal, 2)) + " " + ВАЛЮТА,
 reply_markup=admin_menu_kb(),
 )


@router.message(AdminFSM.withdraw)
async def admin_withdraw(msg: Message, state: FSMContext):
 if msg.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(msg.text.replace(",", "."))
 if amount <= 0:
 raise ValueError
 except Exception:
 await msg.answer("Неверная сумма.")
 return
 bal = get_treasury()
 if amount > bal:
 await msg.answer("Недостаточно средств. Казна: " + str(round(bal, 2)) + " " + ВАЛЮТА)
 return
 result = await transfer_to_admin(amount)
 if result:
 adjust_treasury(-amount)
 await msg.answer("Выведено " + str(amount) + " " + CURRENCY + " на ваш кошелек CryptoBot.", reply_markup=admin_menu_kb())
 else:
 await msg.answer("Ошибка перевода. Проверьте баланс CryptoBot.", reply_markup=admin_menu_kb())
 await state.clear()


@router.message(AdminFSM.setchannel)
async def admin_setchannel(msg: Message, state: FSMContext):
 if msg.from_user.id != ADMIN_ID:
 return
 global CHANNEL_ID
 if msg.forward_from_chat:
 CHANNEL_ID = msg.forward_from_chat.id
 else:
 try:
 CHANNEL_ID = int(msg.text.strip())
 except Exception:
 await msg.answer("Неверный формат. Введите числовой идентификатор канала.")
 возврат 
 set_setting("channel_id", str(CHANNEL_ID))
 состояние ожидания.очистить()
 await msg.answer("Канал установлен: " + str(CHANNEL_ID), reply_markup=admin_menu_kb())


# ОПРОСЧИК ПЛАТЕЖЕЙ

обработано: set = set()


асинхронный опрос_платежей с определением (бот: Bot):
 глобальный ИДЕНТИФИКАТОР КАНАЛА
 ch = get_setting("channel_id")
 if ch:
 CHANNEL_ID = int(ch)

 while True:
 try:
 paid = await get_paid_invoices()
 for inv in paid:
 inv_id = str(inv.get("invoice_id", ""))
 if not inv_id or inv_id in processed:
 continue
 bet = get_bet_by_invoice(inv_id)
 if bet is None:
 continue
 # столбцы: id, user_id, username, game, choice, amount, won, payout, invoice_id, created_at
 bet_user_id = bet[1]
 bet_username = bet[2]
 bet_game = bet[3]
 bet_choice = bet[4]
 bet_amount = ставка[5] 
 bet_won = ставка[6]

 если значение bet_won не равно None: 
 обработано.добавить (inv_id)
 продолжить

 обработано.добавить (inv_id)

 # отправить анимацию с игральными костями
 tg_dice_emoji = {
 "dice": "\U0001f3b2", 
 "evenodd": "\U0001f3b2", 
 "баскетбол": "U0001f3c0", 
 "футбол": "u26bd", 
 "боулинг": "U0001f3b3", 
 "дартс": "\U0001f3af",
 }
 dice_msg = await bot.send_dice(bet_user_id, emoji=tg_dice_emoji[bet_game])
 dice_val = dice_msg.dice.value

 won = False
 payout = 0.0
 result_text = ""

 if bet_game == "dice":
 won = (dice_val == int(bet_choice))
 result_text = "Выпало: " + str(dice_val) + " | Твой выбор: " + str(bet_choice)
 elif bet_game == "evenodd":
 actual = "четное" if dice_val % 2 == 0 else "нечетное"
 won = (actual == bet_choice)
 actual_label = "Четное" if actual == "even" else "Нечетное"
 choice_label = "Четное" if bet_choice == "even" else "Нечетное"
 result_text = "Выпало: " + str(dice_val) + " (" + actual_label + ") | Выбор: " + choice_label
 elif bet_game == "basketball":
 выигранный = random.random() < WIN_CHANCES["баскетбол"]
 result_text = "Гол!" if won else "Мимо"
 elif bet_game == "футбол":
 выиграл = random.random() < WIN_CHANCES["футбол"]
 result_text = "Гол!" if выиграл else "Мимо"
 elif bet_game == "боулинг":
 выиграл = (выпало 6)
 result_text = "Страйк!" if won else ("Результат: " + str(dice_val))
 elif bet_game == "дартс":
 won = (dice_val == 6)
 result_text = "В яблочко!" if won else ("Результат: " + str(dice_val))

 если выиграл:
 выплата = round(сумма_ставки * КОЭФФИЦИЕНТЫ[игра_ставки], 2)
 скорректировать_кассу(-выплата)

 разрешить_ставку(идентификатор_инвентаря, выигрыш, выплата)
 скорректировать_кассу(сумма_ставки)

 значок = TG_EMOJI[игра_ставки]
 название = НАЗВАНИЯ_ИГР[игра_ставки]
 uname_str = "@" + bet_username if bet_username else ("id" + str(bet_user_id))

 if won:
 check = await create_check(выплата)
 check_url = check["bot_check_url"] if check else ""
 user_text = (
 "\U0001f389 Победа!\n\n"
 "Игра: " + icon + " " + name + "\n"
 "Ставка: " + str(bet_amount) + " " + ВАЛЮТА + "\n"
 + result_text + "\n\n"
 "Выигрыш: +" + str(выплата) + " " + ВАЛЮТА + "\n\n"
 "Ваш чек на выигрыш:
 )
 user_kb = InlineKeyboardMarkup(
 inline_keyboard=[
 [InlineKeyboardButton(text="Получить " + str(выплата) + " " + ВАЛЮТА, url=check_url)],
 [InlineKeyboardButton(text="\U0001f3b0 Сыграть снова", callback_data="back_to_menu")],
 ]
 )
 await bot.send_message(bet_user_id, user_text, reply_markup=user_kb)
 channel_text = (
 "\U0001f3c6 " + uname_str + " выиграл!\n"
 "Игра: " + icon + " " + name + "\n"
 "Ставка: " + str(bet_amount) + " " + ВАЛЮТА + " -> Выигрыш: " + str(выплата) + " " + ВАЛЮТА + "\n"
 + результат_текст
 )
 else:
 user_text = (
 "\U0001f61e Не повезло...\n\n"
 "Игра: " + иконка + " " + название + "\n"
 "Ставка: " + str(bet_amount) + " " + ВАЛЮТА + "\n"
 + результат_текст + "\n\n"
 "Попробуй еще раз!"
 )
 user_kb = InlineKeyboardMarkup(
 inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f3b0 Сыграть снова", callback_data="back_to_menu")]
 ]
 )
 await bot.send_message(bet_user_id, user_text, reply_markup=user_kb)
 channel_text = (
 "\U0001f4b8 " + uname_str + " сделал ставку\n"
 "Игра: " + иконка + " " + название + "\n"
 "Ставка: " + str(bet_amount) + " " + ВАЛЮТА + " - Проигрыш\n"
 + result_text
 )

 if CHANNEL_ID:
 try:
 await bot.send_message(CHANNEL_ID, channel_text)
 except Exception as e:
 logger.warning("Не удалось опубликовать сообщение в канале: %s", e)

 за исключением исключения в виде e: 
 logger.error("ошибка опроса: %s", e)

 ожидание asyncio.sleep(5)


# MAIN

асинхронное определение main():
 init_db()
 bot = Бот(токен=BOT_TOKEN)
 dp = диспетчер (хранилище =MemoryStorage())
 dp.include_router(маршрутизатор)
 asyncio.create_task(опрос_платежей(бот))
 logger.info("Бот запущен")
 await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
 asyncio.run(main())
