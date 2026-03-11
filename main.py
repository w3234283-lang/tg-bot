import asyncio
import logging
import random
import sqlite3
import aiohttp
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
WIN_CHANCES = {"dice":0.25,"evenodd":0.40,"basketball":0.30,"football":0.28,"darts":0.22}
WIN_MULTIPLIERS = {"dice":4.5,"evenodd":1.8,"basketball":2.8,"football":3.0,"darts":4.0}
GAME_EMOJI = {"dice":"\U0001f3b2","evenodd":"\u26a1","basketball":"\U0001f3c0","football":"\u26bd","darts":"\U0001f3af"}
GAME_NAMES = {"dice":"\u041a\u0443\u0431\u0438\u043a","evenodd":"\u0427\u0451\u0442/\u041d\u0435\u0447\u0435\u0442","basketball":"\u0411\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b","football":"\u0424\u0443\u0442\u0431\u043e\u043b","darts":"\u0414\u0430\u0440\u0442\u0441"}
logging.basicConfig(level=logging.INFO)
db = sqlite3.connect("casino.db", check_same_thread=False)
def init_db():
    db.executescript("CREATE TABLE IF NOT EXISTS bets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, game TEXT, choice TEXT, amount REAL, invoice_id TEXT, status TEXT DEFAULT 'pending', won INTEGER DEFAULT 0, payout REAL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS treasury (id INTEGER PRIMARY KEY CHECK (id=1), balance REAL DEFAULT 0); INSERT OR IGNORE INTO treasury (id, balance) VALUES (1, 0);")
    db.commit()
def add_bet(uid, uname, game, choice, amount, inv_id):
    db.execute("INSERT INTO bets (user_id,username,game,choice,amount,invoice_id) VALUES (?,?,?,?,?,?)", (uid,uname,game,choice,amount,inv_id))
    db.commit()
def get_bet(inv_id):
    return db.execute("SELECT * FROM bets WHERE invoice_id=?", (inv_id,)).fetchone()
def paid_bet(inv_id, won, payout):
    db.execute("UPDATE bets SET status='paid', won=?, payout=? WHERE invoice_id=?", (won, payout, inv_id))
    db.commit()
def get_treasury():
    return db.execute("SELECT balance FROM treasury WHERE id=1").fetchone()[0]
def upd_treasury(delta):
    db.execute("UPDATE treasury SET balance=balance+? WHERE id=1", (delta,))
    db.commit()
def get_stats():
    tb = db.execute("SELECT COUNT(*) FROM bets WHERE status='paid'").fetchone()[0]
    tw = db.execute("SELECT COALESCE(SUM(amount),0) FROM bets WHERE status='paid'").fetchone()[0]
    tw2 = db.execute("SELECT COUNT(*) FROM bets WHERE won=1").fetchone()[0]
    tp = db.execute("SELECT COALESCE(SUM(payout),0) FROM bets WHERE won=1").fetchone()[0]
    return tb, tw, tw2, tp
async def api_post(endpoint, payload):
    s = aiohttp.ClientSession()
    r = await s.post(CRYPTO_API+"/"+endpoint, headers={"Crypto-Pay-API-Token":CRYPTO_TOKEN}, json=payload)
    data = await r.json()
    await s.close()
    return data.get("result", {})
async def api_get(endpoint, params):
    s = aiohttp.ClientSession()
    r = await s.get(CRYPTO_API+"/"+endpoint, headers={"Crypto-Pay-API-Token":CRYPTO_TOKEN}, params=params)
    data = await r.json()
    await s.close()
    return data.get("result", {})
async def create_invoice(amount, payload):
    return await api_post("createInvoice", {"asset":"USDT","amount":str(round(amount,2)),"payload":payload,"expires_in":600})
async def create_check(amount):
    return await api_post("createCheck", {"asset":"USDT","amount":str(round(amount,2))})
async def get_invoices():
    r = await api_get("getInvoices", {"status":"paid","asset":"USDT"})
    return r.get("items", [])
class BetState(StatesGroup):
    choosing_game = State()
    choosing_option = State()
    entering_amount = State()
class AdminState(StatesGroup):
    deposit_amount = State()
    withdraw_amount = State()
def kb_games():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f3b2 \u041a\u0443\u0431\u0438\u043a (\u0443\u0433\u0430\u0434\u0430\u0439 \u0447\u0438\u0441\u043b\u043e)",callback_data="game_dice")],
        [InlineKeyboardButton(text="\u26a1 \u0427\u0451\u0442 / \u041d\u0435\u0447\u0435\u0442",callback_data="game_evenodd")],
        [InlineKeyboardButton(text="\U0001f3c0 \u0411\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b (\u043f\u043e\u043f\u0430\u0434\u0430\u043d\u0438\u0435)",callback_data="game_basketball")],
        [InlineKeyboardButton(text="\u26bd \u0424\u0443\u0442\u0431\u043e\u043b (\u0433\u043e\u043b)",callback_data="game_football")],
        [InlineKeyboardButton(text="\U0001f3af \u0414\u0430\u0440\u0442\u0441 (\u0432 \u044f\u0431\u043b\u043e\u0447\u043a\u043e)",callback_data="game_darts")]
    ])
def kb_evenodd():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="2\ufe0f\u20e3 \u0427\u0451\u0442\u043d\u043e\u0435",callback_data="choice_even"),InlineKeyboardButton(text="1\ufe0f\u20e3 \u041d\u0435\u0447\u0451\u0442\u043d\u043e\u0435",callback_data="choice_odd")]])
def kb_dice():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="1\ufe0f\u20e3",callback_data="choice_1"),InlineKeyboardButton(text="2\ufe0f\u20e3",callback_data="choice_2"),InlineKeyboardButton(text="3\ufe0f\u20e3",callback_data="choice_3")],[InlineKeyboardButton(text="4\ufe0f\u20e3",callback_data="choice_4"),InlineKeyboardButton(text="5\ufe0f\u20e3",callback_data="choice_5"),InlineKeyboardButton(text="6\ufe0f\u20e3",callback_data="choice_6")]])
def kb_sport(game):
    yt = {"basketball":"\U0001f3c0 \u041f\u043e\u043f\u0430\u0434\u0451\u0442!","football":"\u26bd \u0413\u043e\u043b!","darts":"\U0001f3af \u0412 \u044f\u0431\u043b\u043e\u0447\u043a\u043e!"}
    nt = {"basketball":"\u274c \u041f\u0440\u043e\u043c\u0430\u0445","football":"\u274c \u041c\u0438\u043c\u043e","darts":"\u274c \u041c\u0438\u043c\u043e"}
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=yt[game],callback_data="choice_yes"),InlineKeyboardButton(text=nt[game],callback_data="choice_no")]])
def kb_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4ca \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430",callback_data="admin_stats")],
        [InlineKeyboardButton(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u043a\u0430\u0437\u043d\u0443",callback_data="admin_deposit")],
        [InlineKeyboardButton(text="\U0001f4b8 \u0412\u044b\u0432\u0435\u0441\u0442\u0438 \u0438\u0437 \u043a\u0430\u0437\u043d\u044b",callback_data="admin_withdraw")],
        [InlineKeyboardButton(text="\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441 \u043a\u0430\u0437\u043d\u044b",callback_data="admin_balance")]
    ])
def fmt(game, choice):
    m = {"even":"\u0427\u0451\u0442\u043d\u043e\u0435","odd":"\u041d\u0435\u0447\u0451\u0442\u043d\u043e\u0435","yes":"\u0414\u0430","no":"\u041d\u0435\u0442"}
    return "\u0427\u0438\u0441\u043b\u043e "+choice if game=="dice" else m.get(choice,choice)
def determine_win(game, choice, dv):
    r = random.random()
    wc = WIN_CHANCES[game]
    if game=="dice": return str(dv)==choice and r<wc
    if game=="evenodd": return (dv%2==0)==(choice=="even") and r<wc
    if game=="basketball": return (dv in [4,5])==(choice=="yes") and r<wc
    if game=="football": return (dv in [3,4,5])==(choice=="yes") and r<wc
    if game=="darts": return (dv==6)==(choice=="yes") and r<wc
    return False
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    await msg.answer("\U0001f3b0 <b>\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 \u041a\u0430\u0437\u0438\u043d\u043e!</b>\n\n\u0421\u0442\u0430\u0432\u044c \u043e\u0442 <b>0.10 \u0434\u043e 10 USDT</b>!\n\u041e\u043f\u043b\u0430\u0442\u0430 \u0447\u0435\u0440\u0435\u0437 <b>CryptoBot</b>.\n\u041f\u0440\u0438 \u0432\u044b\u0438\u0433\u0440\u044b\u0448\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0448\u044c \u0447\u0435\u043a \u0432 \u0431\u043e\u0442! \U0001f911", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f3ae \u0418\u0433\u0440\u0430\u0442\u044c!",callback_data="play")]]))
@dp.callback_query(F.data=="play")
async def cb_play(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(BetState.choosing_game)
    await call.message.edit_text("\U0001f3ae <b>\u0412\u044b\u0431\u0435\u0440\u0438 \u0438\u0433\u0440\u0443:</b>", parse_mode="HTML", reply_markup=kb_games())
@dp.callback_query(F.data.startswith("game_"))
async def cb_game(call: types.CallbackQuery, state: FSMContext):
    game = call.data.replace("game_","")
    await state.update_data(game=game)
    await state.set_state(BetState.choosing_option)
    txt={"dice":"\U0001f3b2 <b>\u041a\u0443\u0431\u0438\u043a</b>\n\u0423\u0433\u0430\u0434\u0430\u0439 \u0447\u0438\u0441\u043b\u043e \u043e\u0442 1 \u0434\u043e 6:","evenodd":"\u26a1 <b>\u0427\u0451\u0442/\u041d\u0435\u0447\u0435\u0442</b>\n\u0412\u044b\u0431\u0435\u0440\u0438:","basketball":"\U0001f3c0 <b>\u0411\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b</b>\n\u041f\u043e\u043f\u0430\u0434\u0451\u0442 \u0438\u043b\u0438 \u043f\u0440\u043e\u043c\u0430\u0436\u0435\u0442?","football":"\u26bd <b>\u0424\u0443\u0442\u0431\u043e\u043b</b>\n\u0413\u043e\u043b \u0431\u0443\u0434\u0435\u0442?","darts":"\U0001f3af <b>\u0414\u0430\u0440\u0442\u0441</b>\n\u041f\u043e\u043f\u0430\u0434\u0451\u0442 \u0432 \u044f\u0431\u043b\u043e\u0447\u043a\u043e?"}
    kb={"dice":kb_dice(),"evenodd":kb_evenodd(),"basketball":kb_sport("basketball"),"football":kb_sport("football"),"darts":kb_sport("darts")}
    await call.message.edit_text(txt[game],parse_mode="HTML",reply_markup=kb[game])
@dp.callback_query(F.data.startswith("choice_"))
async def cb_choice(call: types.CallbackQuery, state: FSMContext):
    choice=call.data.replace("choice_","")
    await state.update_data(choice=choice)
    await state.set_state(BetState.entering_amount)
    await call.message.edit_text("\U0001f4b5 <b>\u0412\u0432\u0435\u0434\u0438 \u0441\u0443\u043c\u043c\u0443 \u0441\u0442\u0430\u0432\u043a\u0438</b>\n\n\u041e\u0442 <b>0.10</b> \u0434\u043e <b>10.00 USDT</b>:\n\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: <code>1.5</code>",parse_mode="HTML")
@dp.message(BetState.entering_amount)
async def cb_amount(msg: types.Message, state: FSMContext):
    v=msg.text.strip().replace(',','.')
    ok=True
    amount=0.0
    if not all(c in '0123456789.' for c in v): ok=False
    if ok: amount=float(v)
    if not ok or amount<MIN_BET or amount>MAX_BET: await msg.answer("\u274c \u041d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u0441\u0443\u043c\u043c\u0430. \u041e\u0442 0.10 \u0434\u043e 10 USDT."); return
    data=await state.get_data()
    game=data["game"]; choice=data["choice"]
    await state.clear()
    user=msg.from_user
    uname=user.username or user.full_name
    payload=str(user.id)+"_"+game+"_"+choice+"_"+str(amount)
    inv=await create_invoice(amount,payload)
    if not inv: await msg.answer("\u26a0\ufe0f \u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u0447\u0451\u0442\u0430."); return
    inv_id=str(inv.get("invoice_id",""))
    pay_url=inv.get("pay_url","")
    add_bet(user.id,uname,game,choice,amount,inv_id)
    pw=round(amount*WIN_MULTIPLIERS[game],2)
    cl=choice if game=="dice" else fmt(game,choice)
    await msg.answer("\U0001f3b0 <b>\u0421\u0447\u0451\u0442 \u0441\u043e\u0437\u0434\u0430\u043d!</b>\n\n"+GAME_EMOJI[game]+" \u0418\u0433\u0440\u0430: <b>"+GAME_NAMES[game]+"</b>\n\U0001f3af \u0421\u0442\u0430\u0432\u043a\u0430: <b>"+cl+"</b>\n\U0001f4b5 \u0421\u0443\u043c\u043c\u0430: <b>"+str(amount)+" USDT</b>\n\U0001f3c6 \u0412\u044b\u0438\u0433\u0440\u044b\u0448 \u043f\u0440\u0438 \u043f\u043e\u0431\u0435\u0434\u0435: <b>"+str(pw)+" USDT</b>\n\n\u26a1 \u041e\u043f\u043b\u0430\u0442\u0438 \u0432 \u0442\u0435\u0447\u0435\u043d\u0438\u0435 <b>10 \u043c\u0438\u043d\u0443\u0442</b>:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f4b3 \u041e\u043f\u043b\u0430\u0442\u0438\u0442\u044c "+str(amount)+" USDT",url=pay_url)]]))
async def check_payments():
    while True:
        await asyncio.sleep(10)
        invs=await get_invoices()
        for inv in invs:
            inv_id=str(inv.get("invoice_id",""))
            bet=get_bet(inv_id)
            if not bet: continue
            bid,uid,uname,game,choice,amount,iid,status,won,payout,cat=bet
            if status=="paid": continue
            dmap={"dice":"\U0001f3b2","evenodd":"\U0001f3b2","basketball":"\U0001f3c0","football":"\u26bd","darts":"\U0001f3af"}
            dm=await bot.send_dice(chat_id=uid,emoji=dmap[game])
            dv=dm.dice.value
            await asyncio.sleep(4)
            win=determine_win(game,choice,dv)
            wp=round(amount*WIN_MULTIPLIERS[game],2) if win else 0.0
            paid_bet(inv_id,1 if win else 0,wp)
            if win: upd_treasury(-wp)
            else: upd_treasury(amount)
            cl=fmt(game,choice)
            if win:
                await bot.send_message(uid,"\U0001f3c6 <b>\u041f\u041e\u0411\u0415\u0414\u0410!</b>\n\n"+GAME_EMOJI[game]+" "+GAME_NAMES[game]+"\n\U0001f3b2 \u041a\u0443\u0431\u0438\u043a: <b>"+str(dv)+"</b>\n\U0001f3af \u0421\u0442\u0430\u0432\u043a\u0430: <b>"+cl+"</b>\n\U0001f4b0 \u0421\u0443\u043c\u043c\u0430: <b>"+str(amount)+" USDT</b>\n\U0001f911 \u0412\u044b\u0438\u0433\u0440\u044b\u0448: <b>+"+str(wp)+" USDT</b>\n\n\u0421\u043e\u0437\u0434\u0430\u044e \u0447\u0435\u043a... \u23f3",parse_mode="HTML")
                chk=await create_check(wp)
                curl=chk.get("bot_check_url","")
                if curl: await bot.send_message(uid,"\U0001f381 <b>\u0422\u0432\u043e\u0439 \u0447\u0435\u043a!</b>\n\U0001f4b8 \u0421\u0443\u043c\u043c\u0430: <b>"+str(wp)+" USDT</b>\n\u041d\u0430\u0436\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0443:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f381 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c "+str(wp)+" USDT",url=curl)]]))
            else:
                await bot.send_message(uid,"\U0001f614 <b>\u041d\u0435 \u043f\u043e\u0432\u0435\u0437\u043b\u043e...</b>\n\n"+GAME_EMOJI[game]+" "+GAME_NAMES[game]+"\n\U0001f3b2 \u041a\u0443\u0431\u0438\u043a: <b>"+str(dv)+"</b>\n\U0001f3af \u0421\u0442\u0430\u0432\u043a\u0430: <b>"+cl+"</b>\n\U0001f4b8 \u041f\u043e\u0442\u0435\u0440\u044f\u043d\u043e: <b>"+str(amount)+" USDT</b>\n\n\U0001f340 \u0423\u0434\u0430\u0447\u0438!",parse_mode="HTML")
            wl="\U0001f3c6 \u0412\u042b\u0418\u0413\u0420\u042b\u0428" if win else "\U0001f4b8 \u041f\u0420\u041e\u0418\u0413\u0420\u042b\u0428"
            wln="\U0001f911 \u0412\u044b\u0438\u0433\u0440\u0430\u043b: <b>+"+str(wp)+" USDT</b>" if win else "\u274c \u041f\u0440\u043e\u0438\u0433\u0440\u0430\u043b"
            cht=GAME_EMOJI[game]+" <b>"+wl+"</b>\n\n\U0001f464 @"+str(uname)+"\n\U0001f3ae \u0418\u0433\u0440\u0430: <b>"+GAME_NAMES[game]+"</b>\n\U0001f3af \u0421\u0442\u0430\u0432\u043a\u0430: <b>"+cl+"</b>\n\U0001f4b5 \u0421\u0443\u043c\u043c\u0430: <b>"+str(amount)+" USDT</b>\n"+wln+"\n\U0001f3b2 \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435: <b>"+str(dv)+"</b>"
            await bot.send_message(CHANNEL_ID,cht,parse_mode="HTML")
@dp.message(Command("admin"))
async def cmd_admin(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID: return
    bal=get_treasury()
    await msg.answer("\U0001f6e0 <b>\u041f\u0430\u043d\u0435\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430</b>\n\n\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: <b>"+str(round(bal,2))+" USDT</b>",parse_mode="HTML",reply_markup=kb_admin())
@dp.callback_query(F.data=="admin_stats")
async def adm_stats(call: types.CallbackQuery):
    if call.from_user.id!=ADMIN_ID: return
    tb,tw,tw2,tp=get_stats()
    profit=round(tw-tp,2)
    wr=round(tw2/tb*100,1) if tb else 0
    bal=get_treasury()
    await call.message.edit_text("\U0001f4ca <b>\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u043a\u0430\u0437\u0438\u043d\u043e</b>\n\n\U0001f3ae \u0421\u0442\u0430\u0432\u043e\u043a: <b>"+str(tb)+"</b>\n\U0001f4b5 \u041e\u0431\u043e\u0440\u043e\u0442: <b>"+str(round(tw,2))+" USDT</b>\n\U0001f3c6 \u041f\u043e\u0431\u0435\u0434: <b>"+str(tw2)+"</b> ("+str(wr)+"%)\n\U0001f4b8 \u0412\u044b\u043f\u043b\u0430\u0447\u0435\u043d\u043e: <b>"+str(round(tp,2))+" USDT</b>\n\U0001f4c8 \u041f\u0440\u0438\u0431\u044b\u043b\u044c: <b>"+str(profit)+" USDT</b>\n\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: <b>"+str(round(bal,2))+" USDT</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434",callback_data="admin_back")]]))
@dp.callback_query(F.data=="admin_balance")
async def adm_bal(call: types.CallbackQuery):
    if call.from_user.id!=ADMIN_ID: return
    await call.answer("\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: "+str(round(get_treasury(),2))+" USDT",show_alert=True)
@dp.callback_query(F.data=="admin_deposit")
async def adm_dep(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id!=ADMIN_ID: return
    await state.set_state(AdminState.deposit_amount)
    await call.message.edit_text("\U0001f4b0 \u0412\u0432\u0435\u0434\u0438 \u0441\u0443\u043c\u043c\u0443 \u0434\u043b\u044f \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043a\u0430\u0437\u043d\u044b (USDT):",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\u274c \u041e\u0442\u043c\u0435\u043d\u0430",callback_data="admin_back")]]))
@dp.message(AdminState.deposit_amount)
async def adm_dep_amt(msg: types.Message, state: FSMContext):
    if msg.from_user.id!=ADMIN_ID: return
    v=msg.text.strip()
    amount=float(v) if all(c in '0123456789.' for c in v) and v else 0
    if amount<=0: await msg.answer("\u274c \u041d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u0441\u0443\u043c\u043c\u0430."); return
    upd_treasury(amount)
    await state.clear()
    await msg.answer("\u2705 \u041a\u0430\u0437\u043d\u0430 \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0430 \u043d\u0430 <b>"+str(amount)+" USDT</b>\n\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: <b>"+str(round(get_treasury(),2))+" USDT</b>",parse_mode="HTML",reply_markup=kb_admin())
@dp.callback_query(F.data=="admin_withdraw")
async def adm_wd(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id!=ADMIN_ID: return
    await state.set_state(AdminState.withdraw_amount)
    bal=get_treasury()
    await call.message.edit_text("\U0001f4b8 \u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e: <b>"+str(round(bal,2))+" USDT</b>\n\n\u0412\u0432\u0435\u0434\u0438 \u0441\u0443\u043c\u043c\u0443 \u0432\u044b\u0432\u043e\u0434\u0430:",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\u274c \u041e\u0442\u043c\u0435\u043d\u0430",callback_data="admin_back")]]))
@dp.message(AdminState.withdraw_amount)
async def adm_wd_amt(msg: types.Message, state: FSMContext):
    if msg.from_user.id!=ADMIN_ID: return
    v=msg.text.strip()
    amount=float(v) if all(c in '0123456789.' for c in v) and v else 0
    if amount<=0: await msg.answer("\u274c \u041d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u0441\u0443\u043c\u043c\u0430."); return
    bal=get_treasury()
    if amount>bal: await msg.answer("\u274c \u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e. \u0411\u0430\u043b\u0430\u043d\u0441: "+str(round(bal,2))+" USDT"); return
    chk=await create_check(amount)
    curl=chk.get("bot_check_url","")
    upd_treasury(-amount)
    await state.clear()
    await msg.answer("\u2705 \u0412\u044b\u0432\u043e\u0434 <b>"+str(amount)+" USDT</b> \u0441\u043e\u0437\u0434\u0430\u043d!\n\U0001f4bc \u041e\u0441\u0442\u0430\u0442\u043e\u043a: <b>"+str(round(get_treasury(),2))+" USDT</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="\U0001f4b8 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c "+str(amount)+" USDT",url=curl)]]))
@dp.callback_query(F.data=="admin_back")
async def adm_back(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id!=ADMIN_ID: return
    await state.clear()
    bal=get_treasury()
    await call.message.edit_text("\U0001f6e0 <b>\u041f\u0430\u043d\u0435\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430</b>\n\n\U0001f4bc \u0411\u0430\u043b\u0430\u043d\u0441: <b>"+str(round(bal,2))+" USDT</b>",parse_mode="HTML",reply_markup=kb_admin())
async def main():
    init_db()
    asyncio.create_task(check_payments())
    await dp.start_polling(bot)
if __name__=="__main__":
    asyncio.run(main())
