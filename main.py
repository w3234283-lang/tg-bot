импорт asyncio 
импорт ведения журнала 
импорт случайным образом 
импорт sqlite3 
импорт aiohttp 
из datetime импорт datetime 
из aiogram импорт бота, диспетчера, типов, F 
из команды импорта aiogram.filters 
из команды импорта aiogram.types InlineKeyboardMarkup, InlineKeyboardButton 
из aiogram.fsm.context импортируйте FSMContext 
из aiogram.fsm.state импортировать State, StatesGroup 
из aiogram.fsm.storage.memory импортировать MemoryStorage

# ─────────────── НАСТРОЙКИ ───────────────
BOT_TOKEN = "8325669732:AAGFvmLJMbAOilhKWElk43LG-FksHJpCfNk"
CRYPTO_TOKEN = "545475:AALkj6ssx8n0hVc2LR2ouWSat2YpoLCFUow"
ADMIN_ID = 7921743592
CHANNEL_ID = "@your_channel" # ← замените на @username вашего канала или -100xxxxx
CRYPTO_API = "https://pay.crypt.bot/api"
MIN_BET = 0,10
MAX_BET = 10,0

# Шансы на победу (занижены)
WIN_CHANCES = {
 "кубик": 0,25, # 25% — кубик, угадай число
 "чет/нечет": 0,40, # 40% — чет/нечет
 "баскетбол": 0,30, # 30% — баскетбол (попадание)
 "футбол": 0,28, # 28% — футбол (гол)
 "дартс": 0,22, # 22% — дартс (в яблочко)
}

# Множители выигрыша
WIN_MULTIPLIERS = {
 "игральные кости": 4,5,
 "неравенство": 1,8,
 "баскетбол": 2,8,
 "футбол": 3,0,
 "дартс": 4,0,
}
logging.basicConfig(level=logging.INFO)
db = sqlite3.connect("casino.db", check_same_thread=False)

# ─────────────── БД ───────────────
def init_db():
 db.execute("""
 CREATE TABLE IF NOT EXISTS bets (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 username TEXT,
 game TEXT,
 choice TEXT,
 amount REAL,
 invoice_id TEXT,
 status TEXT DEFAULT 'ожидает',
 won INTEGER DEFAULT 0,
 payout REAL DEFAULT 0,
 created_at TEXT DEFAULT (datetime('now'))
 )
 """)
 db.execute("""
 CREATE TABLE IF NOT EXISTS treasury (
 id INTEGER PRIMARY KEY CHECK (id=1),
 balance REAL DEFAULT 0
 )
 """)
 db.execute("INSERT OR IGNORE INTO treasury (id, balance) VALUES (1, 0)")
 db.commit()

def add_bet(user_id, username, game, choice, amount, invoice_id):
 db.execute(
 "INSERT INTO bets (user_id, username, game, choice, amount, invoice_id) VALUES (?,?,?,?,?,?)",
 (user_id, username, game, choice, amount, invoice_id)
 )
 db.commit()

def get_bet_by_invoice(invoice_id):
 return db.execute("SELECT * FROM bets WHERE invoice_id=?", (invoice_id,)). fetchone()

def update_bet_status(invoice_id, status, won, payout):
 db.execute(
 "UPDATE bets SET status=?, won=?, payout=? WHERE invoice_id=?",
 (status, won, payout, invoice_id)
 )
 db.commit()

def get_treasury():
 return db.execute("SELECT balance FROM treasury WHERE id=1").fetchone()[0]

def update_treasury(delta):
 db.execute("UPDATE treasury SET balance=balance+? WHERE id=1", (delta,))
 db.commit()

def get_stats():
 total_bets = db.execute("SELECT COUNT(*) FROM bets WHERE status='paid'").fetchone()[0]
 total_wagered = db.execute("SELECT COALESCE(SUM(amount),0) FROM bets WHERE status='paid'").fetchone()[0]
 total_wins = db.execute("SELECT COUNT(*) FROM bets WHERE won=1").fetchone()[0] 
 total_paid_out = db.execute("ВЫБЕРИТЕ COALESCE(СУММА(выплаты),0) ИЗ ставок, ГДЕ выигрыш=1").fetchone()[0] 
 возвращает total_bets, total_wagered, total_wins, total_paid_out

# ─────────────── API КРИПТОБОТА ───────────────
асинхронное определение create_invoice(количество: float, полезная нагрузка: str) -> dict:
 асинхронно с aiohttp.ClientSession() as s:
 r = await s.post(f"{CRYPTO_API}/createInvoice", headers={
 "Crypto-Pay-API-Token": CRYPTO_TOKEN
 }, json={
 "актив": "USDT",
 "сумма": str(round(сумма, 2)),
 "полезная нагрузка": полезная нагрузка,
 "описание": f"Ставка в казино {сумма} USDT",
 "разрешить_комментарии": False,
 "разрешить_анонимность": False,
 "срок_действия": 600
 })
 data = await r.json()
 return data.get("result", {})

async def create_check(amount: float) -> dict:
 async with aiohttp.ClientSession() as s:
 r = await s.post(f"{CRYPTO_API}/createCheck", headers={
 "Crypto-Pay-API-Token": CRYPTO_TOKEN
 }, json={
 "актив": "USDT",
 "сумма": str(round(сумма, 2))
 })
 data = await r.json()
 return data.get("result", {})

async def get_invoices() -> list:
 async with aiohttp.ClientSession() as s:
 r = await s.get(f"{CRYPTO_API}/getInvoices", headers={
 "Crypto-Pay-API-Token": CRYPTO_TOKEN
 }, params={"status": "paid"})
 data = await r.json()
 return data.get("result", {}).get("items", [])

# ─────────────── FSM ───────────────
class BetState(StatesGroup):
 choosing_game = State()
 choosing_option = State()
 entering_amount = State()

class AdminState(StatesGroup):
 deposit_amount = State()
 withdraw_amount = State()

# ─────────────── КЛАВИАТУРЫ ───────────────
def games_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="🎲 Кубик (угадай число)", callback_data="game_dice")],
 [InlineKeyboardButton(text="⚡ Чёт / Нечет", callback_data="game_evenodd")],
 [InlineKeyboardButton(text="🏀 Баскетбол (попадание)", callback_data="game_basketball")],
 [InlineKeyboardButton(text="⚽ Футбол (гол)", callback_data="game_football")],
 [InlineKeyboardButton(text="🎯 Дартс (в яблочко)", callback_data="game_darts")],
 ])

def evenodd_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [
 InlineKeyboardButton(text="2️⃣ Чётное", callback_data="choice_even"),
 InlineKeyboardButton(text="1️⃣ Нечётное", callback_data="choice_odd"),
 ]
 ])

def dice_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [
 InlineKeyboardButton(текст="1️⃣", callback_data="choice_1"),
 InlineKeyboardButton(text="2️⃣", callback_data="choice_2"), 
 InlineKeyboardButton(text="3️⃣", callback_data="choice_3"), 
], 
[ 
 InlineKeyboardButton(текст="4️⃣", callback_data="choice_4"), 
 InlineKeyboardButton(текст="5️⃣", callback_data="choice_5"),
 InlineKeyboardButton(text="6️⃣", callback_data="choice_6"), 
], 
 ])

def sport_keyboard(game):
 yes_text = {"баскетбол": "🏀 Попал!", "футбол": "⚽ Гол!", "дартс": "🎯 В яблочко!"}
 no_text = {"баскетбол": "❌ Промах", "футбол": "❌ Мимо", "дартс": "❌ Мимо"}
 return InlineKeyboardMarkup(inline_keyboard=[
 [
 InlineKeyboardButton(text=yes_text[game], callback_data="choice_yes"),
 InlineKeyboardButton(text=no_text[game], callback_data="choice_no"),
 ]
 ])

def admin_keyboard():
 return InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
 [InlineKeyboardButton(text="💰 Пополнить казну", callback_data="admin_deposit")],
 [InlineKeyboardButton(text="💸 Вывести из казны", callback_data="admin_withdraw")],
 [InlineKeyboardButton(text="💼 Баланс казны", callback_data="admin_balance")],
 ])

# ─────────────── ЭМОДЗИ ДЛЯ ИГР ───────────────
GAME_EMOJI = {
 "dice": "🎲",
 "evenodd": "⚡",
 "basketball": "🏀",
 "football": "⚽",
 "darts": "🎯",
}
ИМЕНА ИГР = {
 "dice": "Кубик",
 "evenodd": "Чет/Нечет",
 "basketball": "Баскетбол",
 "football": "Футбол",
 "darts": "Дартс",
}

# ─────────────── КАРТА ЭМОДЗИ ДЛЯ ИГРЫ В ТЕЛЕГРАМ ───────────────
# Результаты игры в Telegram dice для каждой игры
SLOT_DICE = "🎲" # 1-6
SLOT_BBALL = "🏀" # 1-5; 4-5 = гол
SLOT_FOOT = "⚽" # 1-5; 3-5 = гол
SLOT_DARTS = "🎯" # 1-6; 6 = в яблочко

# ─────────────── ОПРЕДЕЛЕНИЕ ПОБЕДИТЕЛЯ ───────────────
def determine_win(game: str, choice: str, dice_value: int) -> bool:
 rnd = random.random()
 win_chance = WIN_CHANCES[game]

 if game == "dice":
 # Если угадал число И повезло
 if str(dice_value) == choice:
 возвращает rnd < win_chance 
 возвращает False

 elif game == "evenodd":
 is_even = dice_value % 2 == 0
 user_picked_even = выбор == "четный"
 если is_even == user_picked_even:
 возвращает rnd < win_chance 
 возвращает False

 elif game == "баскетбол":
 # В Telegram: 🏀 значение 4 или 5 = попадание
 did_score = dice_value в [4, 5]
 user_said_yes = выбор == "да"
 if did_score == user_said_yes:
 возвращает rnd < win_chance 
 возвращает False

 elif game == "футбол":
 # В Telegram: ⚽ значение 3,4,5 = гол
 did_score = dice_value в [3, 4, 5]
 user_said_yes = выбор == "да"
 если did_score == user_said_yes:
 возвращает rnd < win_chance 
 возвращает False

 elif game == "дартс":
 # В Telegram: 🎯 значение 6 = яблочко
 яблочко = dice_value == 6
 user_said_yes = выбор == "да"
 если яблочко == user_said_yes:
 возвращает rnd < win_chance 
 возвращает False

 возвращает False

def format_choice(game, choice):
 labels = {
 "even": "Чётное", "odd": "Нечётное",
 "yes": "Да", "no": "Нет",
 }
 if game == "dice":
 return f"Число {choice}"
 return labels.get(choice, choice)

# ─────────────── ИНИЦИАЛИЗАЦИЯ ───────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─────────────── ХЭНДЛЕРЫ ───────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
 await message.answer(
 "🎰 <b>Добро пожаловать в Казино!</b>\n\n"
 "Выбери игру, сделай ставку от <b>0,10 до 10 USDT</b> и испытай удачу!\n\n"
 "Оплата через <b>CryptoBot</b>. После оплаты ставка уходит в канал.\n"
 "При выигрыше чек приходит прямо в бот! 🤑\n\n"
 "👇 Нажмите кнопку ниже, чтобы начать:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="🎮 Играть!", callback_data="play")]
 ])
 )

@dp.callback_query(F.data == "play")
async def cb_play(call: types.CallbackQuery, state: FSMContext):
 await state.set_state(BetState.choosing_game)
 await call.message.edit_text(
 "🎮 <b>Выбери игру:</b>",
 parse_mode="HTML",
 reply_markup=games_keyboard()
 )

@dp.callback_query(F.data.startswith("game_"))
async def cb_choose_game(call: types.CallbackQuery, state: FSMContext):
 game = call.data.replace("game_", "")
 await state.update_data(game=game)
 await state.set_state(BetState.choosing_option)

 texts = {
 "dice": "🎲 <b>Кубик</b>\nУгадай число от 1 до 6:",
 "evenodd": "⚡ <b>Чёт / Нечет</b>\nВыбери:",
 "basketball": "🏀 <b>Баскетбол</b>\nПопадёт или промажет?",
 "football": "⚽ <b>Футбол</b>\nГол будет?",
 "darts": "🎯 <b>Дартс</b>\nПопадёт в яблочко?",
 }

 клавиатуры = {
 "кубики": dice_keyboard(),
 "evenodd": evenodd_keyboard(),
 "баскетбол": sport_keyboard("баскетбол"),
 "футбол": sport_keyboard("футбол"),
 "дартс": sport_keyboard("дартс"),
 }

 await call.message.edit_text(texts[game], parse_mode="HTML", reply_markup=keyboards[game])

@dp.callback_query(F.data.startswith("choice_"))
async def cb_choose_option(call: types.CallbackQuery, state: FSMContext):
 choice = call.data.replace("choice_", "")
 await state.update_data(choice=choice)
 await state.set_state(BetState.entering_amount)

 await call.message.edit_text(
 f"💵 <b>Введите сумму ставки</b>\n\n"
 f"От <b>0,10</b> до <b>10,00 USDT</b>:\n\n"
 f"Например: <code>1,5</code> или <code>5</code>",
 parse_mode="HTML"
 )

@dp.message(BetState.entering_amount)
async def process_amount(message: types.Message, state: FSMContext):
 попробуйте: 
 amount = float(сообщение.текст.полоса().заменить(",", "."))
 кроме ValueError:
 await message.answer("❌ Введи корректную сумму (например: <code>2.5</code>)", parse_mode="HTML")
 Возврат

 если сумма < MIN_BET:
 await message.answer(f"❌ Минимальная ставка — <b>{MIN_BET} USDT</b>", parse_mode="HTML")
 return
 if amount > MAX_BET:
 await message.answer(f"❌ Максимальная ставка — <b>{MAX_BET} USDT</b>", parse_mode="HTML")
 return

 данные = состояние ожидания.get_data()
 игра = данные["игра"]
 выбор = данные["выбор"]
 состояние ожидания.очистить ()

 пользователь = сообщение.от_user 
 имя пользователя = user.username или user.full_name

 # Создаём инвойс
 полезная нагрузка = f"{user.id}_{игра}_{выбор}_{количество}"
 попробуйте: 
 счет-фактура = ожидает create_invoice (сумма, полезная нагрузка)
 except Exception as e:
 await message.answer("⚠️ Ошибка создания счёта. Попробуй позже.")
 регистрация.ошибка (f"Ошибка счета: {e}")
 Возврат

 если нет счета-фактуры:
 await message.answer("⚠️ Ошибка создания счёта. Попробуй позже.")
 Возврат

 invoice_id = str(invoice.get("invoice_id", """))
 pay_url = invoice.get("pay_url", "")

 # Сохраняем ставку в БД
 add_bet(user.id, username, game, choice, amount, invoice_id)

 multiplier = WIN_MULTIPLIERS[game]
 potential_win = round(amount * multiplier, 2)
 chance_pct = int(WIN_CHANCES[game] * 100)

 await message.answer(
 f"🎰 <b>Счёт создан!</b>\n\n"
 f"{GAME_EMOJI[game]} Игра: <b>{GAME_NAMES[game]}</b>\n"
 f"🎯 Ставка: <b>{choice if game == 'dice' else format_choice(game, choice)}</b>\n"
 f"💵 Сумма: <b>{amount} USDT</b>\n"
 f"🏆 Выигрыш в случае победы: <b>{potential_win} USDT</b>\n\n"
 f"⚡ Оплатите в течение <b>10 минут</b>:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text=f"💳 Оплатить {amount} USDT", url=pay_url)]
 ])
 )

# ─────────────── ФОНОВАЯ ПРОВЕРКА ОПЛАТ ───────────────
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
 if bet[8] != 0 or bet[7] == "paid": # уже обработано
 continue

 # столбцы ставки: id, user_id, имя пользователя, игра, выбор, сумма, идентификатор счета, статус, выигрыш, выплата, дата создания
 bet_id, user_id, имя пользователя, игра, выбор, сумма, inv_id, статус, выигрыш, выплата, дата создания = ставка

 if status == "оплачено":
 continue

 # Отправляем игровой эмодзи в Telegram
 dice_type_map = {
 "dice": "🎲",
 "evenodd": "🎲",
 "basketball": "🏀",
 "football": "⚽",
 "darts": "🎯",
 }
 dice_emoji = dice_type_map[game]

 try:
 dice_msg = await bot.send_dice(chat_id=user_id, emoji=dice_emoji)
 dice_value = dice_msg.dice.value
 await asyncio.sleep(4) # Ждём анимацию
 except Exception as e:
 logging.error(f"Ошибка при отправке кубиков: {e}")
 значение_кубика = random.randint(1, 6)

 выигрыш = determine_win(игра, выбор, значение_кубика)
 выплата_за_выигрыш = round(сумма * WIN_MULTIPLIERS[игра], 2) if выигрыш else 0.0
 update_bet_status(invoice_id, "оплачено", 1, если is_win, иначе 0, win_payout)

 # Обновляем казну
 если is_win:
 update_treasury(-win_payout) # казна платит
 ещё:
 update_treasury(amount) # казна забирает ставку

 # Результат пользователю
 if is_win:
 result_text = (
 f"🏆 <b>ПОБЕДА!</b>\n\n"
 f"{GAME_EMOJI[game]} {GAME_NAMES[game]}\n"
 f"🎰 Выпал кубик: <b>{dice_value}</b>\n"
 f"🎯 Твоя ставка: <b>{format_choice(game, choice)}</b>\n"
 f"💰 Сумма ставки: <b>{amount} USDT</b>\n"
 f"🤑 Выигрыш: <b>+{win_payout} USDT</b>\n\n"
 f"Создаю чек... ⏳"
 )
 await bot.send_message(user_id, result_text, parse_mode="HTML")

 # Создаём чек
 try:
 check = await create_check(win_payout)
 check_url = check.get("bot_check_url", "")
 if check_url:
 await bot.send_message(
 user_id,
 f"🎁 <b>Твой выигрышный чек!</b>\n\n"
 f"💸 Сумма: <b>{win_payout} USDT</b>\n"
 f"Нажмите кнопку ниже, чтобы получить:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text=f"🎁 Получить {win_payout} USDT", url=check_url)]
 ])
 )
 except Exception as e:
 logging.error(f"Ошибка при создании чека: {e}")
 else:
 result_text = (
 f"😔 <b>Не повезло...</b>\n\n"
 f"{GAME_EMOJI[game]} {GAME_NAMES[game]}\n"
 f"🎰 Выпал кубик: <b>{dice_value}</b>\n"
 f"🎯 Твоя ставка: <b>{format_choice(game, choice)}</b>\n"
 f"💸 Потеряно: <b>{сумма} USDT</b>\n\n"
 f"Удачи в следующий раз! 🍀"
 )
 await bot.send_message(user_id, result_text, parse_mode="HTML")

 # Публикуем в канале
 channel_text = (
 f"{GAME_EMOJI[game]} <b>{'🏆 ВЫИГРЫШ' if is_win else '💸 ПРОИГРЫШ'}</b>\n\n"
 f"👤 @{username}\n"
 f"🎮 Игра: <b>{ИМЕНА_ИГР[игра]}</b>\n"
 f"🎯 Ставка: <b>{format_choice(игра, выбор)}</b>\n"
 f"💵 Сумма: <b>{сумма} USDT</b>\n"
 f"{'🤑 Выиграл: <b>+' + str(win_payout) + ' USDT</b>' if is_win else '❌ Проиграл'}\n"
 f"🎲 Значение: <b>{dice_value}</b>"
 )
 try:
 await bot.send_message(CHANNEL_ID, channel_text, parse_mode="HTML")
 except Exception as e:
 logging.warning(f"Ошибка публикации в канале: {e}")

 except Exception as e:
 logging.error(f"Ошибка при проверке платежа: {e}")

# ─────────────── АДМИН ───────────────

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
 if message.from_user.id != ADMIN_ID:
 await message.answer("⛔ Нет доступа.")
 return
 balance = get_treasury()
 await message.answer(
 f"🛠 <b>Панель администратора</b>\n\n"
 f"💼 Текущий баланс казны: <b>{round(balance, 2)} USDT</b>",
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
 f"📊 <b>Статистика казино</b>\n\n"
 f"🎮 Всего ставок: <b>{total_bets}</b>\n"
 f"💵 Обставлено: <b>{round(total_wagered, 2)} USDT</b>\n"
 f"🏆 Побед игроков: <b>{total_wins}</b> ({winrate}%)\n"
 f"💸 Выплачено: <b>{round(total_paid_out, 2)} USDT</b>\n"
 f"📈 Прибыль казино: <b>{profit} USDT</b>\n"
 f"💼 Баланс казны: <b>{round(balance, 2)} USDT</b>",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
 ])
 )

@dp.callback_query(F.data == "admin_balance")
async def admin_balance(call: types.CallbackQuery):
 if call.from_user.id != ADMIN_ID:
 return
 balance = get_treasury()
 await call.answer(f"💼 Баланс казны: {round(balance, 2)} USDT", show_alert=True)

@dp.callback_query(F.data == "admin_deposit")
async def admin_deposit_cb(call: types.CallbackQuery, state: FSMContext):
 if call.from_user.id != ADMIN_ID:
 return
 await state.set_state(AdminState.deposit_amount)
 await call.message.edit_text(
 "💰 Введите сумму для пополнения казны (USDT):",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
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
 f"✅ Казна пополнена на <b>{amount} USDT</b>\n"
 f"💼 Новый баланс: <b>{round(balance, 2)} USDT</b>",
 parse_mode="HTML",
 reply_markup=admin_keyboard()
 )
 except ValueError:
 await message.answer("❌ Введите корректную сумму.")

@dp.callback_query(F.data == "admin_withdraw")
async def admin_withdraw_cb(call: types.CallbackQuery, state: FSMContext):
 if call.from_user.id != ADMIN_ID:
 return
 await state.set_state(AdminState.withdraw_amount)
 balance = get_treasury()
 await call.message.edit_text(
 f"💸 Доступно для вывода: <b>{round(balance, 2)} USDT</b>\n\n"
 f"Введите сумму для вывода:",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
 ])
 )

@dp.message(AdminState.withdraw_amount)
async def admin_withdraw_amount(message: types.Message, state: FSMContext):
 if message.from_user.id != ADMIN_ID:
 return
 try:
 amount = float(message.text.strip())
 баланс = get_treasury()
 if amount > balance:
 await message.answer(f"❌ Недостаточно средств. Баланс: {round(balance, 2)} USDT")
 Возврат
 # Создаём чек для вывода
 попробуйте: 
 check = ожидание create_check(сумма) 
 check_url = check.get("bot_check_url", "")
 update_treasury(-сумма)
 await state.clear()
 balance_new = get_treasury()
 await message.answer(
 f"✅ Вывод <b>{amount} USDT</b> создан!\n"
 f"💼 Остаток казны: <b>{round(balance_new, 2)} USDT</b>",
 parse_mode="HTML",
 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text=f"💸 Получить {amount} USDT", url=check_url)]
 ])
 )
 except Exception as e:
 await message.answer(f"⚠️ Ошибка при создании чека: {e}")
 except ValueError:
 await message.answer("❌ Введите корректную сумму.")

@dp.callback_query(F.data == "admin_back")
async def admin_back(call: types.CallbackQuery, state: FSMContext):
 if call.from_user.id != ADMIN_ID:
 return
 await state.clear()
 balance = get_treasury()
 await call.message.edit_text(
 f"🛠 <b>Панель администратора</b>\n\n"
 f"💼 Текущий баланс казны: <b>{round(balance, 2)} USDT</b>",
 parse_mode="HTML",
 reply_markup=admin_keyboard()
 )

# ─────────────── ЗАПУСК ───────────────
async def main():
 init_db()
 asyncio.create_task(check_payments())
 await dp.start_polling(bot)

if __name__ == "__main__":
 asyncio.run(main())
