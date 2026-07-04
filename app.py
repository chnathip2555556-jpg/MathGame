from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os, random, string, time
from datetime import timedelta
from pymongo import MongoClient

current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_url_path='', static_folder=current_dir)

CORS(app, supports_credentials=True)

app.secret_key = "mathgame_super_secret_key_999"
app.permanent_session_lifetime = timedelta(days=7)
app.config.update(
    SESSION_COOKIE_SECURE=True,      
    SESSION_COOKIE_HTTPONLY=True,    
    SESSION_COOKIE_SAMESITE='None',  
)

# -------------------------------------------------------------
# 🔌 เชื่อมต่อฐานข้อมูล MongoDB Atlas ออนไลน์
# -------------------------------------------------------------
MONGO_URI = "mongodb+srv://chnathip2555556_db_user:Mn2g8IG69NuRtfru@mathgame.n8hquki.mongodb.net/?appName=MathGame"

client = MongoClient(MONGO_URI)
db = client["MathGameDB"]       
db_users = db["users"]          
db_chat = db["chat"]            
db_system = db["system"]        

ADMIN_USERNAME = "garfiw_dev"
VERSION     = "4.0.0"        
DEV_NAME    = "garfiw_dev"

RANKS = [
    {"id":"wood",    "name":"แรงค์ไม้",      "emoji":"🪵", "exp_need":0,    "diff":"easy"},
    {"id":"iron",    "name":"แรงค์เหล็ก",   "emoji":"🗿", "exp_need":430,  "diff":"easy"},
    {"id":"silver",  "name":"แรงค์เงิน",    "emoji":"⚙️", "exp_need":730,  "diff":"medium"},
    {"id":"gold",    "name":"แรงค์ทอง",     "emoji":"🪙", "exp_need":999,  "diff":"medium"},
    {"id":"diamond", "name":"แรงค์เพชร",    "emoji":"💎", "exp_need":1567, "diff":"hard"},
    {"id":"purple",  "name":"แรงค์ม่วง",    "emoji":"♾️", "exp_need":3486, "diff":"hard"},
    {"id":"bigbrain","name":"แรงค์สมองใหญ่","emoji":"🧠", "exp_need":5567, "diff":"extreme"},
    {"id":"king",    "name":"แรงค์ KING",   "emoji":"🏅👑","exp_need":7679, "diff":"extreme"},
]

TITLES = [
    {"name":"มือใหม่",              "emoji":"🌹",  "min":0},
    {"name":"เทพ",                  "emoji":"😎",  "min":500},
    {"name":"ฉลาด",                 "emoji":"💎",  "min":2000},
    {"name":"โหด",                  "emoji":"☠️",  "min":10000},
    {"name":"อัลเบิร์ต ไอน์สไตน์","emoji":"🧠🧠","min":100000},
]

# ⚙️ Functions ส่วนกลางใช้งานร่วมกัน (และใช้แชร์ให้ไฟล์แอดมินเรียกข้ามมาได้)
def get_rank(exp):
    r = RANKS[0]
    for rk in RANKS:
        if exp >= rk["exp_need"]: r = rk
    return r

def get_title(score):
    t = TITLES[0]
    for ti in TITLES:
        if score >= ti["min"]: t = ti
    return t

def load_users():
    users = {}
    for u in db_users.find():
        users[u["username"]] = u["data"]
    return users

def save_users(users):
    for username, data in users.items():
        db_users.update_one({"username": username}, {"$set": {"data": data}}, upsert=True)

def load_chat():
    chats = list(db_chat.find().sort("ts", 1))
    for c in chats:
        if "_id" in c: del c["_id"]
    return chats

def save_chat(chat_list):
    db_chat.delete_many({})
    if chat_list:
        db_chat.insert_many(chat_list)

def load_system():
    sys = db_system.find_one({"type": "config"})
    if not sys:
        return {"reset_flag": False, "reset_time": 0, "theme": "dark", "maintenance": False, "announcement": "ยินดีต้อนรับสู่ MathGame!"}
    if "_id" in sys: del sys["_id"]
    return sys

def gen_pin():
    users = load_users()
    existing = {u["pin"] for u in users.values()}
    while True:
        pin = "".join(random.choices(string.digits, k=6))
        if pin not in existing: return pin

def generate_question(difficulty):
    if difficulty == "easy":      ops, r = ["+","-"], 20
    elif difficulty == "medium":  ops, r = ["+","-","*"], 50
    elif difficulty == "hard":    ops, r = ["+","-","*","/"], 100
    else:                         ops, r = ["+","-","*","/","**","%"], 999

    op = random.choice(ops)
    if op == "**":
        a = random.randint(2,9); b = random.randint(2,4); ans = a**b
        wrongs = set()
        while len(wrongs) < 3:
            w = ans + random.randint(-max(10,ans//5), max(10,ans//5))
            if w != ans and w > 0: wrongs.add(w)
        choices = list(wrongs)+[ans]; random.shuffle(choices)
        return {"question":f"{a}^{b} = ?","answer":str(ans),"choices":[str(x) for x in choices]}
    elif op == "%":
        a = random.randint(10,999); b = random.randint(2,20); ans = a%b
        wrongs = set()
        while len(wrongs) < 3:
            w = random.randint(0,b-1)
            if w != ans: wrongs.add(w)
        choices = list(wrongs)+[ans]; random.shuffle(choices)
        return {"question":f"{a} mod {b} = ?","answer":str(ans),"choices":[str(x) for x in choices]}
    elif op == "/":
        b = random.randint(2,10); ans = random.randint(1,10); a = b*ans
    elif op == "*":
        lim = 20 if difficulty=="extreme" else 12
        a = random.randint(2,lim); b = random.randint(2,lim); ans = a*b
    elif op == "-":
        a = random.randint(10,r); b = random.randint(1,a); ans = a-b
    else:
        a = random.randint(1,r); b = random.randint(1,r); ans = a+b

    wr = max(5, abs(ans)//4) if difficulty=="extreme" else 10
    wrongs = set()
    while len(wrongs) < 3:
        offset = random.randint(1,wr)
        w = ans+offset if random.random()<0.5 else ans-offset
        if w != ans and w > 0: wrongs.add(w)
    choices = list(wrongs)+[ans]; random.shuffle(choices)
    op_d = {"*":"×","/":"÷"}.get(op,op)
    return {"question":f"{a} {op_d} {b} = ?","answer":str(ans),"choices":[str(x) for x in choices]}

@app.route("/")
def index(): 
    sys = load_system()
    if sys.get("maintenance", False) and "username" not in session:
        return "<h1>🛠️ เซิร์ฟเวอร์กำลังปิดปรับปรุงชั่วคราวโดยแอดมิน กรุณาลองใหม่ภายหลัง</h1>", 503
    return send_from_directory(current_dir, "index.html")

@app.route("/api/info")
def api_info(): return jsonify({"version":VERSION,"dev":DEV_NAME})

# -------------------------------------------------------------
# 🎮 PLAYER API (เฉพาะระบบฝั่งคนเล่นเกม)
# -------------------------------------------------------------
@app.route("/api/register",methods=["POST"])
def register():
    data = request.json
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    if not username or not password: return jsonify({"ok":False,"msg":"กรุณากรอกชื่อและรหัสผ่าน"}),400
    users = load_users()
    if username in users: return jsonify({"ok":False,"msg":"ชื่อผู้ใช้นี้มีอยู่แล้ว"}),409
    pin = gen_pin()
    users[username] = {"password":password,"pin":pin,"score":0,"games_played":0,"best_score":0,"exp":0,"rank_id":"wood","banned":False}
    save_users(users)
    session.permanent = True
    session["username"] = username
    session["pin"] = pin
    return jsonify({"ok":True,"pin":pin,"msg":"สร้างบัญชีสำเร็จ"})

@app.route("/api/login",methods=["POST"])
def login():
    data = request.json
    pin = data.get("pin","").strip()
    users = load_users()
    for username, info in users.items():
        if info["pin"]==pin:
            if info.get("banned", False): return jsonify({"ok":False,"msg":"บัญชีนี้ถูกแบนโดยแอดมิน"}), 403
            session.permanent = True
            session["username"] = username
            session["pin"] = pin
            rank  = get_rank(info.get("exp",0))
            title = get_title(info.get("score",0))
            return jsonify({"ok":True,"username":info.get("display_name", username),"score":info["score"],"best_score":info["best_score"],"games_played":info["games_played"],"exp":info.get("exp",0),"rank":rank,"title":title})
    return jsonify({"ok":False,"msg":"PIN ไม่ถูกต้อง"}),401

@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    if "username" in session and "pin" in session:
        users = load_users()
        username = session["username"]
        if username in users:
            info = users[username]
            if info.get("banned", False): return jsonify({"logged_in":False}), 200
            rank  = get_rank(info.get("exp",0))
            title = get_title(info.get("score",0))
            return jsonify({"logged_in":True,"username":info.get("display_name", username),"score":info["score"],"best_score":info["best_score"],"games_played":info["games_played"],"exp":info.get("exp",0),"rank":rank,"title":title})
    return jsonify({"logged_in":False}),200

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok":True,"msg":"ออกจากระบบเรียบร้อย"})

@app.route("/api/question",methods=["POST"])
def question():
    return jsonify(generate_question(request.json.get("difficulty","easy")))

@app.route("/api/score",methods=["POST"])
def submit_score():
    data = request.json; username = data.get("username"); new_score = data.get("score",0)
    users = load_users(); user_key = username
    if username not in users:
        for k, v in users.items():
            if v.get("display_name") == username: user_key = k; break
    if user_key not in users: return jsonify({"ok":False,"msg":"ไม่พบผู้ใช้"}),404
    if users[user_key].get("banned", False): return jsonify({"ok":False,"msg":"คุณถูกแบน"}), 403
    users[user_key]["score"]+=new_score; users[user_key]["games_played"]+=1
    if new_score>users[user_key]["best_score"]: users[user_key]["best_score"]=new_score
    save_users(users)
    return jsonify({"ok":True,"total_score":users[user_key]["score"],"best_score":users[user_key]["best_score"],"rank":get_rank(users[user_key].get("exp",0)),"title":get_title(users[user_key]["score"])})

@app.route("/api/leaderboard")
def leaderboard():
    users = load_users(); board=[]
    for u,v in users.items():
        if v.get("banned", False): continue
        rank=get_rank(v.get("exp",0)); title=get_title(v.get("score",0))
        board.append({"username":v.get("display_name", u),"best_score":v["best_score"],"games_played":v["games_played"],"exp":v.get("exp",0),"rank_emoji":rank["emoji"],"rank_name":rank["name"],"title_emoji":title["emoji"],"title_name":title["name"]})
    board.sort(key=lambda x:x["best_score"],reverse=True)
    return jsonify(board[:20])

@app.route("/api/chat")
def chat_get(): return jsonify(load_chat()[-80:])

@app.route("/api/chat",methods=["POST"])
def chat_post():
    data = request.json; username=data.get("username","").strip(); text=data.get("text","").strip()
    if not username or not text: return jsonify({"ok":False}),400
    users = load_users(); user_key = username
    if username != ADMIN_USERNAME:
        for k, v in users.items():
            if v.get("display_name") == username or k == username: user_key = k; break
    if user_key not in users and username!=ADMIN_USERNAME: return jsonify({"ok":False}),403
    if users.get(user_key, {}).get("banned", False): return jsonify({"ok":False,"msg":"คุณถูกแบนแชท"}),403
    rank_emoji  = "👑" if username==ADMIN_USERNAME else get_rank(users.get(user_key,{}).get("exp",0))["emoji"]
    title_emoji = "⚙️" if username==ADMIN_USERNAME else get_title(users.get(user_key,{}).get("score",0))["emoji"]
    msgs=load_chat()
    msgs.append({"user":username,"text":text,"rank_emoji":rank_emoji,"title_emoji":title_emoji,"ts":int(time.time())})
    save_chat(msgs); return jsonify({"ok":True})

# นำโมดูลระบบแอดมินมาลงทะเบียนเชื่อมต่อเข้าไฟล์หลักตรงนี้
from admin_routes import admin_bp
app.register_blueprint(admin_bp)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
