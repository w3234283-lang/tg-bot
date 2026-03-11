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
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

BOT_TOKEN = "8325669732:AAGFvmLJMbAOilhKWElk43LG-FksHJpCfNk"
CRYPTO_TOKEN = "545475:AALkj6ssx8n0hVc2LR2ouWSat2YpoLCFUow"
ADMIN_ID = 7921743592
CRYPTO_API = "https://pay.crypt.bot/api"
ВАЛЮТА = "USDT"
MIN_BET = 0,10
MAX_BET = 10,0
CHANNEL_ID = None

MULTIPLIERS = {"dice": 5.0, "evenodd": 1.8, "basketball": 3.0, "football": 3.5, "bowling": 2.5, "darts": 5.0}
WIN_CHANCES = {"dice": 1/6, "evenodd": 0.40, "basketball": 0.25, "football": 0.20, "bowling": 0.25, "darts": 0.15}
GAME_NAMES = {"dice": "Кубик", "evenodd": "Чет/Нечет", "basketball": "Баскетбол", "football": "Футбол", "bowling": "Боулинг", "darts": "Дартс"}
TG_ICON = {"кости": "\U0001f3b2", "evenodd": "\U0001f3b2", "баскетбол": "\U0001f3c0", "футбол": "\u26bd", "боулинг": "\U0001f3b3", "дартс": "\U0001f3af"}
TG_DICE_EMOJI = {"кости": "\U0001f3b2", "evenodd": "\U0001f3b2", "баскетбол": "\U0001f3c0", "футбол": "\u26bd", "боулинг": "\U0001f3b3", "дартс": "\U0001f3af"}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---- БД ----

def db():
 return sqlite3.connect("casino.db")

def init_db():
 c = db()
 c.executescript(
 "CREATE TABLE IF NOT EXISTS cfg (k TEXT PRIMARY KEY, v TEXT);"
 "CREATE TABLE IF NOT EXISTS treasury (id INTEGER PRIMARY KEY CHECK(id=1), bal REAL DEFAULT 0);"
 "INSERT OR IGNORE INTO treasury VALUES(1,0);"
 "CREATE TABLE IF NOT EXISTS bets (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, uname TEXT, game TEXT, choice TEXT, amount REAL, won INTEGER, payout REAL DEFAULT 0, inv_id TEXT, ts TEXT DEFAULT(datetime('now')));"
 "CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, uname TEXT, bets INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, wagered REAL DEFAULT 0, paid REAL DEFAULT 0);"
 )
 c.commit()
 c.close()

def cfg_get(k, d= Нет):
 c = db()
 r = c.выполнить("ВЫБРАТЬ v ИЗ cfg, ГДЕ k=?", (k,)).fetchone() 
 c.close()
 верните r[0], если r еще d

определение cfg_set(k, v):
 c = db()
 c.execute("INSERT OR REPLACE INTO cfg VALUES(?,?)", (k, str(v)))
 c.commit()
 c.close()

def treasury_get():
 c = db()
 v = c.execute("SELECT bal FROM treasury WHERE id=1").fetchone()[0]
 c.close()
 return v

def treasury_add(delta):
 c = db()
 c.execute("UPDATE treasury SET bal=bal+? WHERE id=1", (delta,))
 c.commit()
 c.close()

def bet_save(uid, uname, game, choice, amount, inv_id):
 c = db()
 cur = c.cursor() 
 cur.execute("ВСТАВИТЬ В ЗНАЧЕНИЯ ставок(uid, uname,game,choice,amount, inv_id)(?,?,?,?,?,?)", ( uid, uname, игра, выбор, сумма, inv_id))
 ставка = текущая.lastrowid 
 c.commit()
 c.close()
 вернуть ставку

определить bet_get(inv_id):
 c = db()
 r = c.выполнить("ВЫБРАТЬ * ИЗ ставок, ГДЕ inv_id=?", (inv_id,)).fetchone() 
 c.закрыть()
 вернуть r

определение bet_resolve(inv_id, выигранный, выплата):
 c = db()
 cur = c.cursor() 
 cur.execute("ОБНОВИТЬ НАБОР выигранных ставок =?, выплату =? ГДЕ inv_id=?", (1, если выиграно, остальное 0, выплата, inv_id))
 r = cur.execute("SELECT uid,uname,amount FROM bets WHERE inv_id=?", (inv_id,)). fetchone()
 if r:
 uid, uname, amount = r
 cur.execute(
 "INSERT INTO users(uid,uname,bets,wins,losses,wagered,paid) VALUES(?,?,1,?,?,?,?) "
 "ON CONFLICT(uid) DO UPDATE SET uname=excluded.uname,bets=bets+1,wins=wins+excluded.wins,losses=losses+excluded.losses,wagered=wagered+excluded.wagered,paid=paid+excluded.paid",
 (uid, uname, 1 if won else 0, 0 if won else 1, amount, payout)
 )
 c.commit()
 c.close()
 return r

def stats_get():
 c = db()
 cur = c.cursor()
 total = cur.execute("SELECT COUNT(*) FROM bets WHERE won IS NOT NULL").fetchone()[0]
 wins = cur.execute("SELECT COUNT(*) FROM bets WHERE won=1").fetchone()[0]
 wagered = cur.execute("SELECT COALESCE(SUM(amount),0) FROM bets WHERE won IS NOT NULL").fetchone()[0]
 paid = cur.execute("SELECT COALESCE(SUM(payout),0) FROM bets WHERE won=1").fetchone()[0]
 bal = cur.execute("SELECT bal FROM treasury WHERE id=1").fetchone()[0]
 top = cur.execute("SELECT uname,bets,wins,wagered,paid FROM users ORDER BY wagered DESC LIMIT 5").fetchall()
 bygame = cur.execute("SELECT game,COUNT(*),SUM(won),COALESCE(SUM(amount),0) FROM bets WHERE won IS NOT NULL GROUP BY game"). fetchall()
 c.close()
 return {"total": total, "wins": wins, "wagered": wagered, "paid": paid, "bal": bal, "top": top, "bygame": bygame}

# ---- КРИПТОВАЛЮТА ----

async def api_post(endpoint, params):
 headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
 session = aiohttp.ClientSession()
 try:
 resp = await session.post(CRYPTO_API + "/" + endpoint, json=params, headers=headers)
 data = await resp.json()
 await session.close()
 if data.get("ok"):
 возвращаемые данные["результат"]
 журнал.ошибка("ошибка api_post %s: %s", конечная точка, данные)
 возвращает None 
 исключение, за исключением e: 
 log.error("исключение api_post %s: %s", конечная точка, e) 
 ожидает сеанса.close()
 возвращает None

асинхронный def api_get(конечная точка, параметры):
 headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
 session = aiohttp.ClientSession()
 try:
 resp = await session.get(CRYPTO_API + "/" + endpoint, params=params, headers=headers)
 data = await resp.json()
 await session.close()
 if data.get("ok"):
 возвращает данные ["результат"]
 не возвращает ничего 
 исключение, за исключением e: 
 log.error("api_get %s exception: %s", конечная точка, e) 
 ожидает сеанса.close()
 не возвращает ничего

асинхронное определение invoice_create(сумма, полезная нагрузка):
 return await api_post("createInvoice", {
 "asset": CURRENCY,
 "amount": str(round(amount, 2)),
 "payload": payload,
 "description": "Ставка в казино",
 "expires_in": 300
 })

async def check_create(amount):
 return await api_post("createCheck", {"asset": CURRENCY, "amount": str(round(amount, 2))})

async def invoices_paid():
 r = await api_get("getInvoices", {"asset": CURRENCY, "status": "paid", "count": 100})
 if r:
 return r.get("items", [])
 return []

async def transfer_admin(amount):
 spend_id = "wd_" + str(int(datetime.now().timestamp()))
 return await api_post("transfer", {"user_id": ADMIN_ID, "актив": ВАЛЮТА, "сумма": str(round(сумма, 2)), "spend_id": spend_id, "комментарий": "Вывод средств из казино"})

# ---- КЛАВИАТУРЫ ----

def kb_main():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(текст="\U0001f3b2 Кубик", callback_data="g: dice"), InlineKeyboardButton(текст="\U0001f3b2 Чет/Нечет", callback_data="g: evenodd")], 
 [InlineKeyboardButton(text="\U0001f3c0 Баскетбол", callback_data="g: баскетбол"), InlineKeyboardButton(text="\u26bd Футбол", callback_data="g: футбол")], 
 [InlineKeyboardButton(текст="\U0001f3b3 Боулинг", callback_data="g:боулинг"), InlineKeyboardButton(текст="\U0001f3af Дартс", callback_data="g: дартс")], 
 [InlineKeyboardButton(text="\U0001f4ca Моя статистика", callback_data="mystats")], 
 ])

def kb_back():
 return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f519 В меню", callback_data="menu")]])

def kb_amounts(game, choice):
 btns = []
 for a in [0.10, 0.25, 0.50, 1.0, 2.0, 5.0, 10.0]:
 btns.append(InlineKeyboardButton(text=str(a) + " " + CURRENCY, callback_data="bet:" + game + ":" + choice + ":" + str(a)))
 rows = [btns[0:4], btns[4:], [InlineKeyboardButton(text="\U0001f519 Назад", callback_data="menu")]]
 return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_dice_nums():
 nums = [InlineKeyboardButton(text=str(i), callback_data="ch:dice:" + str(i)) for i in range(1, 7)]
 return InlineKeyboardMarkup(inline_keyboard=[nums[:3], nums[3:], [InlineKeyboardButton(text="\U0001f519 Назад", callback_data="menu")]])

def kb_evenodd():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="Четное", callback_data="ch:evenodd:even"), InlineKeyboardButton(text="Нечетное", callback_data="ch:evenodd:odd")],
 [InlineKeyboardButton(text="\U0001f519 Назад", callback_data="menu")]
 ])

def kb_admin():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f4ca Статистика", callback_data="adm:stats")],
 [InlineKeyboardButton(text="\U0001f4b0 Пополнить казну", callback_data="adm:deposit")],
 [InlineKeyboardButton(text="\U0001f4b8 Вывести из казны", callback_data="adm:withdraw")],
 [InlineKeyboardButton(text="\U0001f4e2 Установить канал", callback_data="adm:channel")],
 [InlineKeyboardButton(text="\U0001f4b5 Баланс казны", callback_data="adm:balance")],
 ])

# ---- FSM ----

class Adm(StatesGroup):
 deposit = State()
 withdraw = State()
 channel = State()

# ---- МАРШРУТИЗАТОР ----

rt = Router()

@rt.message(Command("start"))
async def on_start(msg: Message):
 await msg.answer(
 "\U0001f3b0 Казино-бот\n\nМин.  ставка: " + str(MIN_BET) + " " + ВАЛЮТА + "\nМакс. ставка: " + str(MAX_BET) + " " + ВАЛЮТА + "\n\nВыбери игру:",
 reply_markup=kb_main()
 )

@rt.message(Command("admin"))
async def on_admin(msg: Message):
 if msg.from_user.id != ADMIN_ID:
 await msg.answer("Нет доступа.")
 return
 await msg.answer("Панель администратора:", reply_markup=kb_admin())

@rt.callback_query(F.data == "menu")
async def on_menu(cb: CallbackQuery, state: FSMContext):
 await state.clear()
 await cb.message.edit_text("Выбери игру:", reply_markup=kb_main())
 await cb.answer()

@rt.callback_query(F.data.startswith("g:"))
async def on_game(cb: CallbackQuery):
 game = cb.data[2:]
 icon = TG_ICON[game]
 name = GAME_NAMES[game]
 mult = MULTIPLIERS[game]
 if game == "dice":
 await cb.message.edit_text(icon + " " + name + "\nУгадай число от 1 до 6\nВыигрыш: x" + str(mult) + "\n\nВыбери число:", reply_markup=kb_dice_nums())
 elif game == "evenodd":
 await cb.message.edit_text(icon + " " + name + "\nВыигрыш: x" + str(mult) + "\n\nВыбери вариант:", reply_markup=kb_evenodd())
 else:
 await cb.message.edit_text(icon + " " + name + "\nВыигрыш: x" + str(mult) + "\n\nВыбери сумму ставки:", reply_markup=kb_amounts(game, "yes"))
 await cb.answer()

@rt.callback_query(F.data.startswith("ch:"))
async def on_choice(cb: CallbackQuery):
 parts = cb.data.split(":")
 game = parts[1]
 choice = parts[2]
 icon = TG_ICON[game]
 name = GAME_NAMES[game]
 mult = MULTIPLIERS[game]
 cl = "Четное" if choice == "even" else ("Нечетное" if choice == "odd" else choice)
 await cb.message.edit_text(icon + " " + name + "\nВыбор: " + cl + "\nВыигрыш: x" + str(mult) + "\n\nВыбери сумму:", reply_markup=kb_amounts(game, choice))
 await cb.answer()

@rt.callback_query(F.data.startswith("bet:"))
async def on_bet(cb: CallbackQuery):
 parts = cb.data.split(":")
 game = parts[1]
 choice = parts[2]
 amount = float(parts[3])
 payload = game + "|" + choice + "|" + str(cb.from_user.id)
 inv = await invoice_create(amount, payload)
 if not inv:
 await cb.answer("Ошибка при создании счета. Попробуйте позже.", show_alert=True)
 return
 inv_id = str(inv.get("invoice_id", ""))
 pay_url = inv.get("bot_invoice_url", inv.get("pay_url", ""))
 uname = cb.from_user.username или cb.from_user.first_name или ("id" + str(cb.from_user.id))
 bet_save(cb.from_user.id, uname, game, choice, amount, inv_id)
 win_sum = round(amount * MULTIPLIERS[game], 2)
 cl = "Четное" if choice == "even" else ("Нечетное" if choice == "odd" else choice)
 текст = (
 "\U0001f4b3 Счет создан!\n\nИгра: " + TG_ICON[game] + " " + GAME_NAMES[game] + "\n" +
 "Ставка: " + str(amount) + " " + CURRENCY + "\nВыбор: " + cl + "\n" +
 "Выигрыш при победе: " + str(win_sum) + " " + CURRENCY + "\n\nСчет действует 5 минут"
 )
 await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="Оплатить " + str(amount) + " " + ВАЛЮТА, url=pay_url)],
[InlineKeyboardButton(text="\U0001f519 В меню", callback_data="menu")],
 ]))
 await cb.answer()

@rt.callback_query(F.data == "mystats")
async def on_mystats(cb: CallbackQuery):
 c = db()
 r = c.execute("SELECT bets,wins,losses,wagered,paid FROM users WHERE uid=?", (cb.from_user.id,)). fetchone()
 c.close()
 if not r:
 await cb.answer("Нет статистики.", show_alert=True)
 возврат 
 tb, tw, tl, twa, tp = r 
 текст = (
 "\U0001f4ca Твоя статистика\n\n" +
 "Ставок: " + str(tb) + "\nПобед: " + str(tw) + " | Поражений: " + str(tl) + "\n" +
 "Поставлено: " + str(round(twa, 2)) + " " + CURRENCY + "\n" +
 "Выиграно: " + str(round(tp, 2)) + " " + CURRENCY + "\n" +
 "Профит: " + str(round(tp - twa, 2)) + " " + CURRENCY
 )
 await cb.message.edit_text(text, reply_markup=kb_back())
 await cb.answer()

@rt.callback_query(F.data.startswith("adm:")) 
async def on_adm(cb: CallbackQuery, state: FSMContext):
 if cb.from_user.id != ADMIN_ID:
 await cb.answer("Нет доступа.", show_alert=True)
 return
 act = cb.data[4:]
 cancel = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="adm:back")]])
 if act == "balance":
 await cb.answer("Казна: " + str(round(treasury_get(), 2)) + " " + ВАЛЮТА, show_alert=True)
 elif act == "stats":
 s = stats_get()
 wr = round(s["wins"] / s["total"] * 100, 1) if s["total"] else 0
 текст = (
 "Статистика казино\n\nКазна: " + str(round(s["bal"], 2)) + " " + CURRENCY + "\n\n" +
 "Ставок: " + str(s["total"]) + "\nПобед игроков: " + str(s["wins"]) + " (" + str(wr) + "%)\n" +
 "Оборот: " + str(раунд(ы["поставленная ВАЛЮТА"], 2)) + " " + + "\n" +
 "Выплачено: " + str(round(s["paid"], 2)) + " " + CURRENCY + "\n" +
 "Доход: " + str(раунд(ы["поставлено"] - ы["оплачено""], 2)) + " " + ВАЛЮТА
 )
 if s["bygame"]:
 text += "\n\nПо играм:\n"
 for g, cnt, w, wag in s["bygame"]:
 wr2 = round((w or 0) / cnt * 100, 1) if cnt else 0
 text += TG_ICON.get(g, "") + " " + GAME_NAMES.get(g, g) + ": " + str(cnt) + " ст., " + str(wr2) + "% побед\n"
 if s["top"]:
 text += "\nТоп игроков:\n"
 for i, row in enumerate(s["top"], 1):
 un, tb, tw, twa, tp = row
 text += str(i) + ". @" + str(un) + ": " + str(round(twa, 2)) + " " + CURRENCY + "\n"
 await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f519 Назад", callback_data="adm:back")]]))
 elif act == "deposit":
 await state.set_state(Adm.deposit)
 await cb.message.edit_text("Введите сумму пополнения казны (" + ВАЛЮТА + "):", reply_markup=cancel)
 elif act == "withdraw":
 bal = treasury_get()
 await state.set_state(Adm.withdraw)
 await cb.message.edit_text("Казна: " + str(round(bal, 2)) + " " + ВАЛЮТА + "\nВведите сумму вывода:", reply_markup=cancel)
 elif act == "канал":
 await state.set_state(Adm.channel)
 await cb.message.edit_text("Отправьте сообщение из канала или введите его идентификатор:", reply_markup=cancel)
 elif act == "back":
 await state.clear()
 await cb.message.edit_text("Панель администратора:", reply_markup=kb_admin())
 await cb.answer()

@rt.message(Adm.deposit)
async def adm_deposit(msg: Message, state: FSMContext):
 if msg.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(msg.text.replace(",", "."))
 if amount <= 0:
 raise ValueError("negative")
 except Exception:
 await msg.answer("Неверная сумма.")
 return
 treasury_add(amount)
 await state.clear()
 await msg.answer("Казна пополнена на " + str(amount) + " " + ВАЛЮТА + "\nБаланс: " + str(round(treasury_get(), 2)) + " " + ВАЛЮТА, reply_markup=kb_admin())

@rt.message(Adm.withdraw)
async def adm_withdraw(msg: Message, state: FSMContext):
 if msg.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(msg.text.replace(",", "."))
 if amount <= 0:
 raise ValueError("negative")
 except Exception:
 await msg.answer("Неверная сумма.")
 return
 bal = treasury_get()
 if amount > bal:
 await msg.answer("Недостаточно средств. Казна: " + str(round(bal, 2)) + " " + ВАЛЮТА)
 return
 r = await transfer_admin(amount)
 if r:
 treasury_add(-amount)
 await msg.answer("Выведено " + str(amount) + " " + CURRENCY + " на ваш кошелек.", reply_markup=kb_admin())
 else:
 await msg.answer("Ошибка перевода.", reply_markup=kb_admin())
 await state.clear()

@rt.message(Adm.channel)
async def adm_channel(msg: Message, state: FSMContext):
 if msg.from_user.id != ADMIN_ID:
 return
 global CHANNEL_ID
 if msg.forward_from_chat:
 CHANNEL_ID = msg.forward_from_chat.id
 else:
 try:
 CHANNEL_ID = int(msg.text.strip())
 except Exception:
 await msg.answer("Неверный формат. Введите числовой идентификатор.")
 return
 cfg_set("channel_id", CHANNEL_ID)
 await state.clear()
 await msg.answer("Канал установлен: " + str(CHANNEL_ID), reply_markup=kb_admin())

# ---- ОПРОСЧИК ----

done_invs = set()

async def poller(bot: Bot):
 global CHANNEL_ID
 saved = cfg_get("channel_id")
 if saved:
 CHANNEL_ID = int(saved)
 while True:
 try:
 items = await invoices_paid()
 for inv in items:
 inv_id = str(inv.get("invoice_id", ""))
 if not inv_id or inv_id in done_invs:
 continue
 bet = bet_get(inv_id)
 if bet is None:
 continue
 # столбцы: id,uid,uname,game,choice,amount,won,payout,inv_id,ts
 uid = bet[1]
 uname = bet[2]
 game = bet[3]
 choice = bet[4]
 amount = bet[5]
 already_won = ставка[6]
 если already_won не равен None: 
 done_invs.add(inv_id)
 продолжить 
 done_invs.add(inv_id)

 dice_msg = ожидает бота.отправить_дайс(uid, эмодзи =TG_DICE_EMOJI[игра])
 dv = dice_msg.dice.value

 выигран = False 
 выплата = 0.0
 результат = ""

 if game == "dice":
 won = (dv == int(choice))
 result = "Выпало: " + str(dv) + " | Выбор: " + str(choice)
 elif game == "evenodd":
 actual = "even" if dv % 2 == 0 else "odd"
 won = (actual == choice)
 al = "Четное" if actual == "even" else "Нечетное"
 cl = "Четное" if choice == "even" else "Нечетное"
 result = "Выпало: " + str(dv) + " (" + al + ") | Выбор: " + cl
 elif game == "баскетбол":
 выиграл = random.random() < WIN_CHANCES["баскетбол"]
 результат = "Гол!" if выиграл else "Мимо"
 elif game == "футбол":
 выиграл = random.random() < WIN_CHANCES["футбол"]
 результат = "Гол!" if выиграл else "Мимо"
 elif game == "боулинг":
 выиграл = (dv == 6)
 результат = "Страйк!" if выиграл else ("Результат: " + str(dv))
 elif game == "дартс": 
 выиграл = (dv == 6)
 результат = "В яблочко!" if выиграл else ("Результат: " + str(dv))

 если выиграл:
 выплата = round(сумма * КОЭФФИЦИЕНТЫ[игра], 2)
 treasury_add(-выплата)

 bet_resolve(inv_id, выиграл, выплата)
 treasury_add(amount)

 icon = TG_ICON[game]
 name = GAME_NAMES[game]
 un = "@" + uname if uname else ("id" + str(uid))

 if won:
 chk = await check_create(payout)
 chk_url = chk["bot_check_url"] if chk else ""
 await bot.send_message(uid,
 "\U0001f389 Победа!\n\nИгра: " + icon + " " + name + "\nСтавка: " + str(amount) + " " + ВАЛЮТА + "\n" + result + "\n\nВыигрыш: +" + str(выплата) + " " + ВАЛЮТА + "\n\nТвой чек:",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="Получить " + str(выплата) + " " + ВАЛЮТА, url=chk_url)],
 [InlineKeyboardButton(text="\U0001f3b0 Играть снова", callback_data="menu")],
 ])
 )
 ch_text = "\U0001f3c6 " + un + " выиграл!\nИгра: " + icon + " " + name + "\nСтавка: " + str(amount) + " -> Выигрыш: " + str(payout) + " " + CURRENCY + "\n" + result
 else:
 await bot.send_message(uid,
 "\U0001f61e Не повезло...\n\nИгра: " + icon + " " + name + "\nСтавка: " + str(amount) + " " + ВАЛЮТА + "\n" + result + "\n\nПопробуй еще раз!",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f3b0 Играть снова", callback_data="menu")]
 ])
 )
 ch_text = "\U0001f4b8 " + un + " сделал ставку\nИгра: " + icon + " " + name + "\nСтавка: " + str(amount) + " " + ВАЛЮТА + " - Проигрыш\n" + result

 if CHANNEL_ID:
 try:
 await bot.send_message(CHANNEL_ID, ch_text)
 except Exception as e:
 log.warning("не удалось отправить сообщение в канал: %s", e)

 except Exception as e:
 log.error("ошибка опроса: %s", e)

 await asyncio.sleep(5)

# ---- ОСНОВНАЯ ПРОГРАММА ----

async def main():
 init_db()
 bot = Bot(token=BOT_TOKEN)
 dp = Dispatcher(storage=MemoryStorage())
 dp.include_router(rt)
 asyncio.create_task(poller(bot))
 log.info("started")
 await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
 asyncio.run(main())
