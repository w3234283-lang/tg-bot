import asyncio
import logging
import random
import sqlite3
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8325669732:AAGFvmLJMbAOilhKWElk43LG-FksHJpCfNk"
CRYPTO_TOKEN = "545475:AALkj6ssx8n0hVc2LR2ouWSat2YpoLCFUow"
ADMIN_ID = 7921743592
CHANNEL_ID = "-1003842490996"

CRYPTO_API = "https://pay.crypt.bot/api"
MIN_BET = 0.10
MAX_BET = 10.0

WIN_CHANCES = {
 "dice": 0.25,
 "evenodd": 0.40,
 "basketball": 0.30,
 "football": 0.28,
 "darts": 0.22,
}

WIN_MULTIPLIERS = {
 "dice": 4.5,
 "evenodd": 1.8,
 "basketball": 2.8,
 "football": 3.0,
 "darts": 4.0,
}

logging.basicConfig(level=logging.INFO)
db = sqlite3.connect("casino.db", check_same_thread=False)

def init_db():
 db.execute('''
 CREATE TABLE IF NOT EXISTS bets (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 username TEXT,
 game TEXT,
 choice TEXT,
 amount REAL,
 invoice_id TEXT,
 status TEXT DEFAULT 'pending',
 won INTEGER DEFAULT 0,
 payout REAL DEFAULT 0,
 created_at TEXT DEFAULT (datetime('now'))
 )
 ''')
 db.execute('''
 CREATE TABLE IF NOT EXISTS treasury (
 id INTEGER PRIMARY KEY CHECK (id=1),
 balance REAL DEFAULT 0
 )
 ''')
 db.execute('INSERT OR IGNORE INTO treasury (id, balance) VALUES (1, 0)')
 db.commit()

def add_bet(user_id, username, game, choice, amount, invoice_id):
 db.execute(
 'INSERT INTO bets (user_id, username, game, choice, amount, invoice_id) VALUES (?,?,?,?,?,?)',
 (user_id, username, game, choice, amount, invoice_id)
 )
 db.commit()

def get_bet_by_invoice(invoice_id):
 return db.execute('SELECT * FROM bets WHERE invoice_id=?', (invoice_id,)).fetchone()

def update_bet_status(invoice_id, status, won, payout):
 db.execute(
 'UPDATE bets SET status=?, won=?, payout=? WHERE invoice_id=?',
 (status, won, payout, invoice_id)
 )
 db.commit()

def get_treasury():
 return db.execute('SELECT balance FROM treasury WHERE id=1').fetchone()[0]

def update_treasury(delta):
 db.execute('UPDATE treasury SET balance=balance+? WHERE id=1', (delta,))
 db.commit()

def get_stats():
 total_bets = db.execute("SELECT COUNT(*) FROM bets WHERE status='paid'").fetchone()[0]
 total_wagered = db.execute("SELECT COALESCE(SUM(amount),0) FROM bets WHERE status='paid'").fetchone()[0]
 total_wins = db.execute('SELECT COUNT(*) FROM bets WHERE won=1').fetchone()[0]
 total_paid_out = db.execute('SELECT COALESCE(SUM(payout),0) FROM bets WHERE won=1').fetchone()[0]
 return total_bets, total_wagered, total_wins, total_paid_out

async def create_invoice(amount, payload):
 s = aiohttp.ClientSession()
 try:
 r = await s.post(
 CRYPTO_API + "/createInvoice",
 headers={"Crypto-Pay-API-Token": CRYPTO_TOKEN},
 json={
 "asset": "USDT",
 "amount": str(round(amount, 2)),
 "payload": payload,
 "description": "Casino bet " + str(amount) + " USDT",
 "allow_comments": False,
 "allow_anonymous": False,
 "expires_in": 600
 }
 )
 data = await r.json()
 return data.get("result", {})
 except Exception as e:
 logging.error("create_invoice: %s", e)
 return {}
 finally:
 await s.close()

async def create_check(amount):
 s = aiohttp.ClientSession()
 try:
 r = await s.post(
 CRYPTO_API + "/createCheck",
 headers={"Crypto-Pay-API-Token": CRYPTO_TOKEN},
 json={"asset": "USDT", "amount": str(round(amount, 2))}
 )
 data = await r.json()
 return data.get("result", {})
 except Exception as e:
 logging.error("create_check: %s", e)
 return {}
 finally:
 await s.close()

async def get_invoices():
 s = aiohttp.ClientSession()
 try:
 r = await s.get(
 CRYPTO_API + "/getInvoices",
 headers={"Crypto-Pay-API-Token": CRYPTO_TOKEN},
 params={"status": "paid"}
 )
 data = await r.json()
 return data.get("result", {}).get("items", [])
 except Exception as e:
 logging.error("get_invoices: %s", e)
 return []
 finally:
 await s.close()

class BetState(StatesGroup):
 choosing_game = State()
 choosing_option = State()
 entering_amount = State()

class AdminState(StatesGroup):
 deposit_amount = State()
 withdraw_amount = State()

def games_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f3b2 \u041a\u0443\u0431\u0438\u043a (\u0443\u0433\u0430\u0434\u0430\u0439 \u0447\u0438\u0441\u043b\u043e)", callback_data="game_dice")],
 [InlineKeyboardButton(text="\u26a1 \u0427\u0451\u0442 / \u041d\u0435\u0447\u0435\u0442", callback_data="game_evenodd")],
 [InlineKeyboardButton(text="\U0001f3c0 \u0411\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b (\u043f\u043e\u043f\u0430\u0434\u0430\u043d\u0438\u0435)", callback_data="game_basketball")],
 [InlineKeyboardButton(text="\u26bd \u0424\u0443\u0442\u0431\u043e\u043b (\u0433\u043e\u043b)", callback_data="game_football")],
 [InlineKeyboardButton(text="\U0001f3af \u0414\u0430\u0440\u0442\u0441 (\u0432 \u044f\u0431\u043b\u043e\u0447\u043a\u043e)", callback_data="game_darts")],
 ])

def evenodd_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [
 InlineKeyboardButton(text="2\ufe0f\u20e3 \u0427\u0451\u0442\u043d\u043e\u0435", callback_data="choice_even"),
 InlineKeyboardButton(text="1\ufe0f\u20e3 \u041d\u0435\u0447\u0451\u0442\u043d\u043e\u0435", callback_data="choice_odd"),
 ]
 ])

def dice_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [
 InlineKeyboardButton(text="1\ufe0f\u20e3", callback_data="choice_1"),
 InlineKeyboardButton(text="2\ufe0f\u20e3", callback_data="choice_2"),
 InlineKeyboardButton(text="3\ufe0f\u20e3", callback_data="choice_3"),
 ],
 [
 InlineKeyboardButton(text="4\ufe0f\u20e3", callback_data="choice_4"),
 InlineKeyboardButton(text="5\ufe0f\u20e3", callback_data="choice_5"),
 InlineKeyboardButton(text="6\ufe0f\u20e3", callback_data="choice_6"),
 ],
 ])

def sport_keyboard(game):
 yes_map = {
 "basketball": "\U0001f3c0 \u041f\u043e\u043f\u0430\u0434\u0451\u0442!",
 "football": "\u26bd \u0413\u043e\u043b!",
 "darts": "\U0001f3af \u0412 \u044f\u0431\u043b\u043e\u0447\u043a\u043e!"
 }
 no_map = {
 "basketball": "\u274c \u041f\u0440\u043e\u043c\u0430\u0445",
 "football": "\u274c \u041c\u0438\u043c\u043e",
 "darts": "\u274c \u041c\u0438\u043c\u043e"
 }
 return InlineKeyboardMarkup(inline_keyboard=[
 [
 InlineKeyboardButton(text=yes_map[game], callback_data="choice_yes"),
 InlineKeyboardButton(text=no_map[game], callback_data="choice_no"),
 ]
 ])

def admin_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f4ca \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430", callback_data="admin_stats")],
 [InlineKeyboardButton(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u043a\u0430\u0437\u043d\u0443", callback_data="admin_deposit")],
 [InlineKeyboardButton(text="\U0001f4b8 \u0412\u044b\u0432\u0435\u0441\u0442\u0438 \u0438\u0437 \u043a\u0430\u0437\u043d\u044b", callback_data="admin_withdraw")],
 [InlineKeyboardButton(text="\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441 \u043a\u0430\u0437\u043d\u044b", callback_data="admin_balance")],
 ])

GAME_EMOJI = {
 "dice": "\U0001f3b2",
 "evenodd": "\u26a1",
 "basketball": "\U0001f3c0",
 "football": "\u26bd",
 "darts": "\U0001f3af",
}
GAME_NAMES = {
 "dice": "\u041a\u0443\u0431\u0438\u043a",
 "evenodd": "\u0427\u0451\u0442/\u041d\u0435\u0447\u0435\u0442",
 "basketball": "\u0411\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b",
 "football": "\u0424\u0443\u0442\u0431\u043e\u043b",
 "darts": "\u0414\u0430\u0440\u0442\u0441",
}

def determine_win(game, choice, dice_value):
 rnd = random.random()
 wc = WIN_CHANCES[game]
 if game == "dice":
 if str(dice_value) == choice:
 return rnd < wc
 return False
 elif game == "evenodd":
 is_even = dice_value % 2 == 0
 user_picked_even = choice == "even"
 if is_even == user_picked_even:
 return rnd < wc
 return False
 elif game == "basketball":
 did_score = dice_value in [4, 5]
 user_said_yes = choice == "yes"
 if did_score == user_said_yes:
 return rnd < wc
 return False
 elif game == "football":
 did_score = dice_value in [3, 4, 5]
 user_said_yes = choice == "yes"
 if did_score == user_said_yes:
 return rnd < wc
 return False
 elif game == "darts":
 bullseye = dice_value == 6
 user_said_yes = choice == "yes"
 if bullseye == user_said_yes:
 return rnd < wc
 return False
 return False

def format_choice(game, choice):
 labels = {
 "even": "\u0427\u0451\u0442\u043d\u043e\u0435",
 "odd": "\u041d\u0435\u0447\u0451\u0442\u043d\u043e\u0435",
 "yes": "\u0414\u0430",
 "no": "\u041d\u0435\u0442",
 }
 if game == "dice":
 return "\u0427\u0438\u0441\u043b\u043e " + choice
 return labels.get(choice, choice)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
 await message.answer(
 "\U0001f3b0 <b>\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 \u041a\u0430\u0437\u0438\u043d\u043e!</b>\n\n"
 "\u0412\u044b\u0431\u0435\u0440\u0438 \u0438\u0433\u0440\u0443, \u043f\u043e\u0441\u0442\u0430\u0432\u044c \u043e\u0442 <b>0.10 \u0434\u043e 10 USDT</b> \u0438 \u0438\u0441\u043f\u044b\u0442\u0430\u0439 \u0443\u0434\u0430\u0447\u0443!\n\n"
 "\u041e\u043f\u043b\u0430\u0442\u0430 \u0447\u0435\u0440\u0435\u0437 <b>CryptoBot</b>. \u041f\u043e\u0441\u043b\u0435 \u043e\u043f\u043b\u0430\u0442\u044b \u2014 \u0441\u0442\u0430\u0432\u043a\u0430 \u0443\u0445\u043e\u0434\u0438\u0442 \u0432 \u043a\u0430\u043d\u0430\u043b.\n"
 "\u041f\u0440\u0438 \u0432\u044b\u0438\u0433\u0440\u044b\u0448\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0448\u044c \u0447\u0435\u043a \u043f\u0440\u044f\u043c\u043e \u0432 \u0431\u043e\u0442! \U0001f911\n\n"
 "\U0001f447 \u041d\u0430\u0436\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0443 \u043d\u0438\u0436\u0435, \u0447\u0442\u043e\u0431\u044b \u043d\u0430\u0447\u0430\u0442\u044c:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f3ae \u0418\u0433\u0440\u0430\u0442\u044c!", callback_data="play")]
 ])
 )

@dp.callback_query(F.data == "play")
async def cb_play(call: types.CallbackQuery, state: FSMContext):
 await state.set_state(BetState.choosing_game)
 await call.message.edit_text(
 "\U0001f3ae <b>\u0412\u044b\u0431\u0435\u0440\u0438 \u0438\u0433\u0440\u0443:</b>",
 parse_mode="HTML",
 reply_markup=games_keyboard()
 )

@dp.callback_query(F.data.startswith("game_"))
async def cb_choose_game(call: types.CallbackQuery, state: FSMContext):
 game = call.data.replace("game_", "")
 await state.update_data(game=game)
 await state.set_state(BetState.choosing_option)
 texts = {
 "dice": "\U0001f3b2 <b>\u041a\u0443\u0431\u0438\u043a</b>\n\u0423\u0433\u0430\u0434\u0430\u0439 \u0447\u0438\u0441\u043b\u043e \u043e\u0442 1 \u0434\u043e 6:",
 "evenodd": "\u26a1 <b>\u0427\u0451\u0442 / \u041d\u0435\u0447\u0435\u0442</b>\n\u0412\u044b\u0431\u0435\u0440\u0438:",
 "basketball": "\U0001f3c0 <b>\u0411\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b</b>\n\u041f\u043e\u043f\u0430\u0434\u0451\u0442 \u0438\u043b\u0438 \u043f\u0440\u043e\u043c\u0430\u0436\u0435\u0442?",
 "football": "\u26bd <b>\u0424\u0443\u0442\u0431\u043e\u043b</b>\n\u0413\u043e\u043b \u0431\u0443\u0434\u0435\u0442?",
 "darts": "\U0001f3af <b>\u0414\u0430\u0440\u0442\u0441</b>\n\u041f\u043e\u043f\u0430\u0434\u0451\u0442 \u0432 \u044f\u0431\u043b\u043e\u0447\u043a\u043e?",
 }
 keyboards = {
 "dice": dice_keyboard(),
 "evenodd": evenodd_keyboard(),
 "basketball": sport_keyboard("basketball"),
 "football": sport_keyboard("football"),
 "darts": sport_keyboard("darts"),
 }
 await call.message.edit_text(texts[game], parse_mode="HTML", reply_markup=keyboards[game])

@dp.callback_query(F.data.startswith("choice_"))
async def cb_choose_option(call: types.CallbackQuery, state: FSMContext):
 choice = call.data.replace("choice_", "")
 await state.update_data(choice=choice)
 await state.set_state(BetState.entering_amount)
 await call.message.edit_text(
 "\U0001f4b5 <b>\u0412\u0432\u0435\u0434\u0438 \u0441\u0443\u043c\u043c\u0443 \u0441\u0442\u0430\u0432\u043a\u0438</b>\n\n"
 "\u041e\u0442 <b>0.10</b> \u0434\u043e <b>10.00 USDT</b>:\n\n"
 "\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: <code>1.5</code> \u0438\u043b\u0438 <code>5</code>",
 parse_mode="HTML"
 )

@dp.message(BetState.entering_amount)
async def process_amount(message: types.Message, state: FSMContext):
 try:
 amount = float(message.text.strip().replace(",", "."))
 except ValueError:
 await message.answer("\u274c \u0412\u0432\u0435\u0434\u0438 \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u0443\u044e \u0441\u0443\u043c\u043c\u0443 (\u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: <code>2.5</code>)", parse_mode="HTML")
 return
 if amount < MIN_BET:
 await message.answer("\u274c \u041c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u0442\u0430\u0432\u043a\u0430 \u2014 <b>" + str(MIN_BET) + " USDT</b>", parse_mode="HTML")
 return
 if amount > MAX_BET:
 await message.answer("\u274c \u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u0442\u0430\u0432\u043a\u0430 \u2014 <b>" + str(MAX_BET) + " USDT</b>", parse_mode="HTML")
 return
 data = await state.get_data()
 game = data["game"]
 choice = data["choice"]
 await state.clear()
 user = message.from_user
 username = user.username or user.full_name
 payload = str(user.id) + "_" + game + "_" + choice + "_" + str(amount)
 try:
 invoice = await create_invoice(amount, payload)
 except Exception as e:
 await message.answer("\u26a0\ufe0f \u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u044f \u0441\u0447\u0451\u0442\u0430. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u043f\u043e\u0437\u0436\u0435.")
 logging.error("Invoice error: %s", e)
 return
 if not invoice:
 await message.answer("\u26a0\ufe0f \u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u044f \u0441\u0447\u0451\u0442\u0430. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u043f\u043e\u0437\u0436\u0435.")
 return
 invoice_id = str(invoice.get("invoice_id", ""))
 pay_url = invoice.get("pay_url", "")
 add_bet(user.id, username, game, choice, amount, invoice_id)
 multiplier = WIN_MULTIPLIERS[game]
 potential_win = round(amount * multiplier, 2)
 ch_label = choice if game == "dice" else format_choice(game, choice)
 await message.answer(
 "\U0001f3b0 <b>\u0421\u0447\u0451\u0442 \u0441\u043e\u0437\u0434\u0430\u043d!</b>\n\n"
 + GAME_EMOJI[game] + " \u0418\u0433\u0440\u0430: <b>" + GAME_NAMES[game] + "</b>\n"
 "\U0001f3af \u0421\u0442\u0430\u0432\u043a\u0430: <b>" + ch_label + "</b>\n"
 "\U0001f4b5 \u0421\u0443\u043c\u043c\u0430: <b>" + str(amount) + " USDT</b>\n"
 "\U0001f3c6 \u0412\u044b\u0438\u0433\u0440\u044b\u0448 \u043f\u0440\u0438 \u043f\u043e\u0431\u0435\u0434\u0435: <b>" + str(potential_win) + " USDT</b>\n\n"
 "\u26a1 \u041e\u043f\u043b\u0430\u0442\u0438 \u0432 \u0442\u0435\u0447\u0435\u043d\u0438\u0435 <b>10 \u043c\u0438\u043d\u0443\u0442</b>:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f4b3 \u041e\u043f\u043b\u0430\u0442\u0438\u0442\u044c " + str(amount) + " USDT", url=pay_url)]
 ])
 )

async def check_payments():
 while True:
 await asyncio.sleep(10)
 try:
 paid_invoices = await get_invoices()
 for inv in paid_invoices:
 invoice_id = str(inv.get("invoice_id", ""))
 bet = get_bet_by_invoice(invoice_id)
 if not bet:
 continue
 bet_id, user_id, username, game, choice, amount, inv_id, status, won, payout, created_at = bet
 if status == "paid":
 continue
 dice_type_map = {
 "dice": "\U0001f3b2",
 "evenodd": "\U0001f3b2",
 "basketball": "\U0001f3c0",
 "football": "\u26bd",
 "darts": "\U0001f3af",
 }
 dice_emoji = dice_type_map[game]
 try:
 dice_msg = await bot.send_dice(chat_id=user_id, emoji=dice_emoji)
 dice_value = dice_msg.dice.value
 await asyncio.sleep(4)
 except Exception as e:
 logging.error("Dice error: %s", e)
 dice_value = random.randint(1, 6)
 is_win = determine_win(game, choice, dice_value)
 win_payout = round(amount * WIN_MULTIPLIERS[game], 2) if is_win else 0.0
 update_bet_status(invoice_id, "paid", 1 if is_win else 0, win_payout)
 if is_win:
 update_treasury(-win_payout)
 else:
 update_treasury(amount)
 ch_label = format_choice(game, choice)
 if is_win:
 await bot.send_message(
 user_id,
 "\U0001f3c6 <b>\u041f\u041e\u0411\u0415\u0414\u0410!</b>\n\n"
 + GAME_EMOJI[game] + " " + GAME_NAMES[game] + "\n"
 "\U0001f3b2 \u041a\u0443\u0431\u0438\u043a \u0432\u044b\u043f\u0430\u043b: <b>" + str(dice_value) + "</b>\n"
 "\U0001f3af \u0422\u0432\u043e\u044f \u0441\u0442\u0430\u0432\u043a\u0430: <b>" + ch_label + "</b>\n"
 "\U0001f4b0 \u0421\u0443\u043c\u043c\u0430 \u0441\u0442\u0430\u0432\u043a\u0438: <b>" + str(amount) + " USDT</b>\n"
 "\U0001f911 \u0412\u044b\u0438\u0433\u0440\u044b\u0448: <b>+" + str(win_payout) + " USDT</b>\n\n"
 "\u0421\u043e\u0437\u0434\u0430\u044e \u0447\u0435\u043a... \u23f3",
 parse_mode="HTML"
 )
 try:
 check = await create_check(win_payout)
 check_url = check.get("bot_check_url", "")
 if check_url:
 await bot.send_message(
 user_id,
 "\U0001f381 <b>\u0422\u0432\u043e\u0439 \u0432\u044b\u0438\u0433\u0440\u044b\u0448\u043d\u044b\u0439 \u0447\u0435\u043a!</b>\n\n"
 "\U0001f4b8 \u0421\u0443\u043c\u043c\u0430: <b>" + str(win_payout) + " USDT</b>\n"
 "\u041d\u0430\u0436\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0443 \u043d\u0438\u0436\u0435:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f381 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c " + str(win_payout) + " USDT", url=check_url)]
 ])
 )
 except Exception as e:
 logging.error("Check error: %s", e)
 else:
 await bot.send_message(
 user_id,
 "\U0001f614 <b>\u041d\u0435 \u043f\u043e\u0432\u0435\u0437\u043b\u043e...</b>\n\n"
 + GAME_EMOJI[game] + " " + GAME_NAMES[game] + "\n"
 "\U0001f3b2 \u041a\u0443\u0431\u0438\u043a \u0432\u044b\u043f\u0430\u043b: <b>" + str(dice_value) + "</b>\n"
 "\U0001f3af \u0422\u0432\u043e\u044f \u0441\u0442\u0430\u0432\u043a\u0430: <b>" + ch_label + "</b>\n"
 "\U0001f4b8 \u041f\u043e\u0442\u0435\u0440\u044f\u043d\u043e: <b>" + str(amount) + " USDT</b>\n\n"
 "\U0001f340 \u0423\u0434\u0430\u0447\u0438 \u0432 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0440\u0430\u0437!",
 parse_mode="HTML"
 )
 win_label = "\U0001f3c6 \u0412\u042b\u0418\u0413\u0420\u042b\u0428" if is_win else "\U0001f4b8 \u041f\u0420\u041e\u0418\u0413\u0420\u042b\u0428"
 win_line = "\U0001f911 \u0412\u044b\u0438\u0433\u0440\u0430\u043b: <b>+" + str(win_payout) + " USDT</b>" if is_win else "\u274c \u041f\u0440\u043e\u0438\u0433\u0440\u0430\u043b"
 channel_text = (
 GAME_EMOJI[game] + " <b>" + win_label + "</b>\n\n"
 "\U0001f464 @" + str(username) + "\n"
 "\U0001f3ae \u0418\u0433\u0440\u0430: <b>" + GAME_NAMES[game] + "</b>\n"
 "\U0001f3af \u0421\u0442\u0430\u0432\u043a\u0430: <b>" + ch_label + "</b>\n"
 "\U0001f4b5 \u0421\u0443\u043c\u043c\u0430: <b>" + str(amount) + " USDT</b>\n"
 + win_line + "\n"
 "\U0001f3b2 \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435: <b>" + str(dice_value) + "</b>"
 )
 try:
 await bot.send_message(CHANNEL_ID, channel_text, parse_mode="HTML")
 except Exception as e:
 logging.warning("Channel error: %s", e)
 except Exception as e:
 logging.error("Payment check error: %s", e)

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
 if message.from_user.id != ADMIN_ID:
 await message.answer("\u26d4 \u041d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430.")
 return
 balance = get_treasury()
 await message.answer(
 "\U0001f6e0 <b>\u041f\u0430\u043d\u0435\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430</b>\n\n"
 "\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441 \u043a\u0430\u0437\u043d\u044b: <b>" + str(round(balance, 2)) + " USDT</b>",
 parse_mode="HTML",
 reply_markup=admin_keyboard()
 )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
 if call.from_user.id != ADMIN_ID:
 return
 total_bets, total_wagered, total_wins, total_paid_out = get_stats()
 profit = round(total_wagered - total_paid_out, 2)
 winrate = round((total_wins / total_bets * 100) if total_bets > 0 else 0, 1)
 balance = get_treasury()
 await call.message.edit_text(
 "\U0001f4ca <b>\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u043a\u0430\u0437\u0438\u043d\u043e</b>\n\n"
 "\U0001f3ae \u0421\u0442\u0430\u0432\u043e\u043a: <b>" + str(total_bets) + "</b>\n"
 "\U0001f4b5 \u041e\u0431\u043e\u0440\u043e\u0442: <b>" + str(round(total_wagered, 2)) + " USDT</b>\n"
 "\U0001f3c6 \u041f\u043e\u0431\u0435\u0434 \u0438\u0433\u0440\u043e\u043a\u043e\u0432: <b>" + str(total_wins) + "</b> (" + str(winrate) + "%)\n"
 "\U0001f4b8 \u0412\u044b\u043f\u043b\u0430\u0447\u0435\u043d\u043e: <b>" + str(round(total_paid_out, 2)) + " USDT</b>\n"
 "\U0001f4c8 \u041f\u0440\u0438\u0431\u044b\u043b\u044c: <b>" + str(profit) + " USDT</b>\n"
 "\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: <b>" + str(round(balance, 2)) + " USDT</b>",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="admin_back")]
 ])
 )

@dp.callback_query(F.data == "admin_balance")
async def admin_balance(call: types.CallbackQuery):
 if call.from_user.id != ADMIN_ID:
 return
 balance = get_treasury()
 await call.answer("\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441 \u043a\u0430\u0437\u043d\u044b: " + str(round(balance, 2)) + " USDT", show_alert=True)

@dp.callback_query(F.data == "admin_deposit")
async def admin_deposit_cb(call: types.CallbackQuery, state: FSMContext):
 if call.from_user.id != ADMIN_ID:
 return
 await state.set_state(AdminState.deposit_amount)
 await call.message.edit_text(
 "\U0001f4b0 \u0412\u0432\u0435\u0434\u0438 \u0441\u0443\u043c\u043c\u0443 \u0434\u043b\u044f \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043a\u0430\u0437\u043d\u044b (USDT):",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\u274c \u041e\u0442\u043c\u0435\u043d\u0430", callback_data="admin_back")]
 ])
 )

@dp.message(AdminState.deposit_amount)
async def admin_deposit_amount(message: types.Message, state: FSMContext):
 if message.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(message.text.strip())
 update_treasury(amount)
 await state.clear()
 balance = get_treasury()
 await message.answer(
 "\u2705 \u041a\u0430\u0437\u043d\u0430 \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0430 \u043d\u0430 <b>" + str(amount) + " USDT</b>\n"
 "\U0001f4bc \u041d\u043e\u0432\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441: <b>" + str(round(balance, 2)) + " USDT</b>",
 parse_mode="HTML",
 reply_markup=admin_keyboard()
 )
 except ValueError
 await message.answer("\u274c \u0412\u0432\u0435\u0434\u0438 \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u0443\u044e \u0441\u0443\u043c\u043c\u0443.")

@dp.callback_query(F.data == "admin_withdraw")
async def admin_withdraw_cb(call: types.CallbackQuery, state: FSMContext):
 if call.from_user.id != ADMIN_ID:
 return
 await state.set_state(AdminState.withdraw_amount)
 balance = get_treasury()
 await call.message.edit_text(
 "\U0001f4b8 \u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e \u0434\u043b\u044f \u0432\u044b\u0432\u043e\u0434\u0430: <b>" + str(round(balance, 2)) + " USDT</b>\n\n"
 "\u0412\u0432\u0435\u0434\u0438 \u0441\u0443\u043c\u043c\u0443 \u0434\u043b\u044f \u0432\u044b\u0432\u043e\u0434\u0430:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\u274c \u041e\u0442\u043c\u0435\u043d\u0430", callback_data="admin_back")]
 ])
 )

@dp.message(AdminState.withdraw_amount)
async def admin_withdraw_amount(message: types.Message, state: FSMContext):
 if message.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(message.text.strip())
 balance = get_treasury()
 if amount > balance:
 await message.answer("\u274c \u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0441\u0440\u0435\u0434\u0441\u0442\u0432. \u0411\u0430\u043b\u0430\u043d\u0441: " + str(round(balance, 2)) + " USDT")
 return
 check = await create_check(amount)
 check_url = check.get("bot_check_url", "")
 update_treasury(-amount)
 await state.clear()
 balance_new = get_treasury()
 await message.answer(
 "\u2705 \u0412\u044b\u0432\u043e\u0434 <b>" + str(amount) + " USDT</b> \u0441\u043e\u0437\u0434\u0430\u043d!\n"
 "\U0001f4bc \u041e\u0441\u0442\u0430\u0442\u043e\u043a: <b>" + str(round(balance_new, 2)) + " USDT</b>",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="\U0001f4b8 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c " + str(amount) + " USDT", url=check_url)]
 ])
 )
 except ValueError:
 await message.answer("\u274c \u0412\u0432\u0435\u0434\u0438 \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u0443\u044e \u0441\u0443\u043c\u043c\u0443.")

@dp.callback_query(F.data == "admin_back")
async def admin_back(call: types.CallbackQuery, state: FSMContext):
 if call.from_user.id != ADMIN_ID:
 return
 await state.clear()
 balance = get_treasury()
 await call.message.edit_text(
 "\U0001f6e0 <b>\u041f\u0430\u043d\u0435\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430</b>\n\n"
 "\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: <b>" + str(round(balance, 2)) + " USDT</b>",
 parse_mode="HTML",
 reply_markup=admin_keyboard()
 )

async def main():
 init_db()
 asyncio.create_task(check_payments())
 await dp.start_polling(bot)

if __name__ == "__main__":
 asyncio.run(main())
