from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import json, os, random, string, time
from datetime import timedelta

# ⚙️ แก้ไข: ปรับการดึงตำแหน่งโฟลเดอร์ static ให้ทำงานบนเซิร์ฟเวอร์ได้ถูกต้อง
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_url_path='', static_folder=current_dir)

CORS(app, supports_credentials=True)

app.secret_key = "mathgame_super_secret_key_999"
app.permanent_session_lifetime = timedelta(days=7)

ADMIN_USERNAME = "garfiw_dev"
ADMIN_PASSWORD = "vip888admin"
USERS_FILE  = "users.json"
CHAT_FILE   = "chat.json"
SYSTEM_FILE = "system.json"
VERSION     = "3.0.0"
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
RANK_MAX_EXP = 13245

TITLES = [
    {"name":"มือใหม่",              "emoji":"🌹",  "min":0},
    {"name":"เทพ",                  "emoji":"😎",  "min":500},
    {"name":"ฉลาด",                 "emoji":"💎",  "min":2000},
    {"name":"โหด",                  "emoji":"☠️",  "min":10000},
    {"name":"อัลเบิร์ต ไอน์สไตน์","emoji":"🧠🧠","min":100000},
]

THEMES = ["dark","ocean","neon","sunset","forest","royal"]

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

def load_json(path, default):
    if not os.path.exists(path): return default
    with open(path,"r",encoding="utf-8") as f: return json.load(f)

def save_json(path, data):
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def load_users():   return load_json(USERS_FILE, {})
def save_users(u):  save_json(USERS_FILE, u)
def load_chat():    return load_json(CHAT_FILE, [])
def save_chat(c):   save_json(CHAT_FILE, c)
def load_system():  return load_json(SYSTEM_FILE, {"reset_flag":False,"reset_time":0,"theme":"dark"})

# ⚙️ แก้ไข: เปลี่ยนจากเรียกชื่อฟังก์ชันตัวเอง (save_system) เป็น save_json เพื่อแก้บั๊กค้าง/Infinite Recursion
def save_system(s): save_json(SYSTEM_FILE, s)

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
        choices = [str(x) for x in choices]
        return {"question":f"{a}^{b} = ?","answer":str(ans),"choices":choices}
        
    elif op == "%":
        a = random.randint(10,999); b = random.randint(2,20); ans = a%b
        wrongs = set()
        while len(wrongs) < 3:
            w = random.randint(0,b-1)
            if w != ans: wrongs.add(w)
        choices = list(wrongs)+[ans]; random.shuffle(choices)
        choices = [str(x) for x in choices]
        return {"question":f"{a} mod {b} = ?","answer":str(ans),"choices":choices}
        
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
    
    choices = [str(x) for x in choices]
    return {"question":f"{a} {op_d} {b} = ?","answer":str(ans),"choices":choices}

# ⚙️ แก้ไข: เปลี่ยนการดึงไฟล์ index.html ให้เรียกจากตำแหน่งโฟลเดอร์ปัจจุบันของเซิร์ฟเวอร์แบบปลอดภัย
@app.route("/")
def index(): 
    return send_from_directory(current_dir, "index.html")

@app.route("/api/info")
def api_info(): return jsonify({"version":VERSION,"dev":DEV_NAME})

@app.route("/api/register",methods=["POST"])
def register():
    data = request.json
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    if not username or not password: return jsonify({"ok":False,"msg":"กรุณากรอกชื่อและรหัสผ่าน"}),400
    if len(username)<3: return jsonify({"ok":False,"msg":"ชื่อต้องมีอย่างน้อย 3 ตัวอักษร"}),400
    if len(password)<4: return jsonify({"ok":False,"msg":"รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร"}),400
    users = load_users()
    if username in users: return jsonify({"ok":False,"msg":"ชื่อผู้ใช้นี้มีอยู่แล้ว"}),409
    if username==ADMIN_USERNAME: return jsonify({"ok":False,"msg":"ชื่อนี้ไม่สามารถใช้ได้"}),403
    pin = gen_pin()
    users[username] = {"password":password,"pin":pin,"score":0,"games_played":0,"best_score":0,"exp":0,"rank_id":"wood"}
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
            session.permanent = True
            session["username"] = username
            session["pin"] = pin
            
            rank  = get_rank(info.get("exp",0))
            title = get_title(info.get("score",0))
            return jsonify({"ok":True,"username":username,"score":info["score"],
                "best_score":info["best_score"],"games_played":info["games_played"],
                "exp":info.get("exp",0),"rank":rank,"title":title})
    return jsonify({"ok":False,"msg":"PIN ไม่ถูกต้อง"}),401

@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    if "username" in session and "pin" in session:
        users = load_users()
        username = session["username"]
        if username in users:
            info = users[username]
            rank  = get_rank(info.get("exp",0))
            title = get_title(info.get("score",0))
            return jsonify({"logged_in":True,"username":username,"score":info["score"],
                "best_score":info["best_score"],"games_played":info["games_played"],
                "exp":info.get("exp",0),"rank":rank,"title":title})
    return jsonify({"logged_in":False}),200

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok":True,"msg":"ออกจากระบบเรียบร้อย"})

@app.route("/api/admin/login",methods=["POST"])
def admin_login():
    data = request.json
    if data.get("username")==ADMIN_USERNAME and data.get("password")==ADMIN_PASSWORD:
        return jsonify({"ok":True})
    return jsonify({"ok":False,"msg":"ชื่อหรือรหัสผ่านไม่ถูกต้อง"}),401

@app.route("/api/admin/users",methods=["POST"])
def admin_users():
    data = request.json
    if data.get("username")!=ADMIN_USERNAME or data.get("password")!=ADMIN_PASSWORD:
        return jsonify({"ok":False,"msg":"Unauthorized"}),403
    users = load_users(); result = []
    for uname,info in users.items():
        rank = get_rank(info.get("exp",0)); title = get_title(info.get("score",0))
        result.append({"username":uname,"pin":info["pin"],"score":info["score"],
            "best_score":info["best_score"],"games_played":info["games_played"],
            "exp":info.get("exp",0),"rank":rank["emoji"]+" "+rank["name"],
            "title":title["emoji"]+" "+title["name"]})
    result.sort(key=lambda x:x["best_score"],reverse=True)
    return jsonify({"ok":True,"users":result})

@app.route("/api/admin/reset-pin",methods=["POST"])
def admin_reset_pin():
    data = request.json
    if data.get("admin_user")!=ADMIN_USERNAME or data.get("admin_pass")!=ADMIN_PASSWORD:
        return jsonify({"ok":False,"msg":"Unauthorized"}),403
    target = data.get("username"); users = load_users()
    if target not in users: return jsonify({"ok":False,"msg":"ไม่พบผู้ใช้"}),404
    new_pin = gen_pin(); users[target]["pin"]=new_pin; save_users(users)
    return jsonify({"ok":True,"new_pin":new_pin})

@app.route("/api/admin/delete-user",methods=["POST"])
def admin_delete_user():
    data = request.json
    if data.get("admin_user")!=ADMIN_USERNAME or data.get("admin_pass")!=ADMIN_PASSWORD:
        return jsonify({"ok":False,"msg":"Unauthorized"}),403
    target = data.get("username"); users = load_users()
    if target not in users: return jsonify({"ok":False,"msg":"ไม่พบผู้ใช้"}),404
    del users[target]; save_users(users)
    return jsonify({"ok":True})

@app.route("/api/admin/reset-ranks",methods=["POST"])
def admin_reset_ranks():
    data = request.json
    if data.get("admin_user")!=ADMIN_USERNAME or data.get("admin_pass")!=ADMIN_PASSWORD:
        return jsonify({"ok":False,"msg":"Unauthorized"}),403
    users = load_users()
    for u in users: users[u]["exp"]=0; users[u]["rank_id"]="wood"
    save_users(users)
    sys = load_system(); sys["reset_flag"]=True; sys["reset_time"]=int(time.time()); save_system(sys)
    return jsonify({"ok":True})

@app.route("/api/admin/set-theme",methods=["POST"])
def admin_set_theme():
    data = request.json
    if data.get("admin_user")!=ADMIN_USERNAME or data.get("admin_pass")!=ADMIN_PASSWORD:
        return jsonify({"ok":False,"msg":"Unauthorized"}),403
    theme = data.get("theme","dark")
    if theme not in THEMES: return jsonify({"ok":False,"msg":"ธีมไม่ถูกต้อง"}),400
    sys = load_system(); sys["theme"]=theme; save_system(sys)
    return jsonify({"ok":True,"theme":theme})

@app.route("/api/system/status")
def system_status():
    sys = load_system()
    return jsonify(sys)

@app.route("/api/question",methods=["POST"])
def question():
    data = request.json
    diff = data.get("difficulty","easy")
    if diff not in ("easy","medium","hard","extreme"): diff="easy"
    return jsonify(generate_question(diff))

@app.route("/api/score",methods=["POST"])
def submit_score():
    data = request.json
    username = data.get("username"); new_score = data.get("score",0)
    users = load_users()
    if username not in users: return jsonify({"ok":False,"msg":"ไม่พบผู้ใช้"}),404
    users[username]["score"]+=new_score; users[username]["games_played"]+=1
    if new_score>users[username]["best_score"]: users[username]["best_score"]=new_score
    save_users(users)
    rank = get_rank(users[username].get("exp",0)); title = get_title(users[username]["score"])
    return jsonify({"ok":True,"total_score":users[username]["score"],
        "best_score":users[username]["best_score"],"rank":rank,"title":title})

@app.route("/api/ranked/find",methods=["POST"])
def ranked_find():
    data = request.json; username = data.get("username")
    users = load_users()
    if username not in users: return jsonify({"ok":False,"msg":"ไม่พบผู้ใช้"}),404
    my_exp = users[username].get("exp",0); my_rank = get_rank(my_exp)
    candidates = [u for u in users if u!=username and get_rank(users[u].get("exp",0))["id"]==my_rank["id"]]
    if not candidates: candidates = [u for u in users if u!=username]
    if not candidates: return jsonify({"ok":False,"msg":"ไม่พบผู้แข่งขัน กรุณารอสักครู่"}),404
    opponent = random.choice(candidates)
    opp_rank = get_rank(users[opponent].get("exp",0))
    return jsonify({"ok":True,"opponent":opponent,"opponent_rank":opp_rank,"difficulty":my_rank["diff"]})

@app.route("/api/ranked/submit",methods=["POST"])
def ranked_submit():
    data = request.json
    winner=data.get("winner"); loser=data.get("loser")
    w_time=data.get("winner_time",99); w_score=data.get("winner_score",0)
    users = load_users()
    speed_bonus = max(0,int((15-w_time)*3))
    exp_gain = 60+speed_bonus+w_score*2
    if winner and winner in users:
        users[winner]["exp"]=users[winner].get("exp",0)+exp_gain
        users[winner]["rank_id"]=get_rank(users[winner]["exp"])["id"]
    if loser and loser in users:
        loser_exp=max(5,exp_gain//5)
        users[loser]["exp"]=users[loser].get("exp",0)+loser_exp
        users[loser]["rank_id"]=get_rank(users[loser]["exp"])["id"]
    save_users(users)
    new_rank = get_rank(users[winner]["exp"]) if winner and winner in users else {}
    return jsonify({"ok":True,"exp_gained":exp_gain,"new_rank":new_rank})

@app.route("/api/leaderboard")
def leaderboard():
    users = load_users(); board=[]
    for u,v in users.items():
        rank=get_rank(v.get("exp",0)); title=get_title(v.get("score",0))
        board.append({"username":u,"best_score":v["best_score"],"games_played":v["games_played"],
            "exp":v.get("exp",0),"rank_emoji":rank["emoji"],"rank_name":rank["name"],
            "title_emoji":title["emoji"],"title_name":title["name"]})
    board.sort(key=lambda x:x["best_score"],reverse=True)
    return jsonify(board[:20])

@app.route("/api/chat")
def chat_get():
    msgs = load_chat(); return jsonify(msgs[-80:])

@app.route("/api/chat",methods=["POST"])
def chat_post():
    data = request.json
    username=data.get("username","").strip(); text=data.get("text","").strip()
    if not username or not text: return jsonify({"ok":False}),400
    if len(text)>200: text=text[:200]
    users = load_users()
    if username not in users and username!=ADMIN_USERNAME:
        return jsonify({"ok":False,"msg":"ไม่พบผู้ใช้"}),403
    rank_emoji  = "👑" if username==ADMIN_USERNAME else get_rank(users.get(username,{}).get("exp",0))["emoji"]
    title_emoji = "⚙️" if username==ADMIN_USERNAME else get_title(users.get(username,{}).get("score",0))["emoji"]
    msgs=load_chat()
    msgs.append({"user":username,"text":text,"rank_emoji":rank_emoji,"title_emoji":title_emoji,"ts":int(time.time())})
    if len(msgs)>200: msgs=msgs[-200:]
    save_chat(msgs); return jsonify({"ok":True})

@app.route("/api/chat/delete",methods=["POST"])
def chat_delete():
    data = request.json
    if data.get("admin_user")!=ADMIN_USERNAME or data.get("admin_pass")!=ADMIN_PASSWORD:
        return jsonify({"ok":False,"msg":"Unauthorized"}),403
    save_chat([]); return jsonify({"ok":True})

# ⚙️ แก้ไข: ปรับระบบพอร์ตให้รับค่า Environment Variable จาก Render เพื่อแก้ปัญหาหน้าเว็บโหลดไม่ขึ้น (Not Found)
if __name__=="__main__":
    print("="*50)
    print(f"  MathGame Server v{VERSION}")
    print(f"  Dev: {DEV_NAME} | Admin: {ADMIN_USERNAME}")
    print("="*50)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
