from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import os, random, string, time, requests
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
# 🔌 เชื่อมต่อฐานข้อมูล MongoDB Atlas
# -------------------------------------------------------------
MONGO_URI = "mongodb+srv://chnathip2555556_db_user:Mn2g8IG69NuRtfru@mathgame.n8hquki.mongodb.net/?appName=MathGame"

client = MongoClient(MONGO_URI)
db = client["MathGameDB"]       
db_users = db["users"]          
db_chat = db["chat"]            
db_system = db["system"]        
db_reports = db["reports"]  # 📦 ตารางใหม่สำหรับเก็บรายงานแจ้งปัญหา

ADMIN_USERNAME = "garfiw_dev"
ADMIN_PASSWORD = "vip888admin"
VERSION     = "4.1.0"        
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

def load_system():
    sys = db_system.find_one({"type": "config"})
    if not sys:
        return {"maintenance": False, "announcement": "ยินดีต้อนรับสู่ MathGame!", "theme": "dark"}
    return sys

def save_system(s):
    db_system.update_one({"type": "config"}, {"$set": s}, upsert=True)

def gen_pin():
    users = load_users()
    existing = {u["pin"] for u in users.values()}
    while True:
        pin = "".join(random.choices(string.digits, k=6))
        if pin not in existing: return pin

@app.route("/")
def index(): 
    sys = load_system()
    if sys.get("maintenance", False) and "username" not in session:
        return "<h1>🛠️ เซิร์ฟเวอร์กำลังปิดปรับปรุงชั่วคราวโดยแอดมิน</h1>", 503
    return send_from_directory(current_dir, "index.html")

@app.route("/admin")
def admin_page():
    return send_from_directory(current_dir, "admin.html")

# -------------------------------------------------------------
# 📩 API สำหรับผู้เล่นส่งข้อมูลแจ้งปัญหามาหลังบ้าน
# -------------------------------------------------------------
@app.route("/api/report/submit", methods=["POST"])
def submit_report():
    data = request.json
    username = data.get("username", "ไม่ระบุชื่อ (ผู้เยี่ยมชม)")
    report_type = data.get("type", "ทั่วไป")
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"ok": False, "msg": "กรุณากรอกข้อความรายละเอียดปัญหาก่อนส่ง"}), 400
        
    report_doc = {
        "username": username,
        "type": report_type,
        "message": message,
        "ts": int(time.time()),
        "status": "รอดำเนินการ"
    }
    db_reports.insert_one(report_doc)
    return jsonify({"ok": True, "msg": "ส่งรายงานปัญหาไปให้แอดมินเรียบร้อยแล้ว!"})

# -------------------------------------------------------------
# 🛠️ API ฝั่งระบบแอดมินควบคุม
# -------------------------------------------------------------
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    if data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "ชื่อหรือรหัสผ่านไม่ถูกต้อง"}), 401

@app.route("/api/admin/users", methods=["POST"])
def admin_users():
    data = request.json
    if data.get("username") != ADMIN_USERNAME or data.get("password") != ADMIN_PASSWORD:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    users = load_users(); result = []
    for uname, info in users.items():
        rank = get_rank(info.get("exp", 0)); title = get_title(info.get("score", 0))
        result.append({
            "username": info.get("display_name", uname), "raw_user": uname, "pin": info["pin"], "score": info["score"],
            "best_score": info["best_score"], "games_played": info["games_played"],
            "exp": info.get("exp", 0), "rank": rank["emoji"]+" "+rank["name"], "banned": info.get("banned", False)
        })
    result.sort(key=lambda x: x["best_score"], reverse=True)
    return jsonify({"ok": True, "users": result})

@app.route("/api/admin/reports", methods=["POST"])
def admin_get_reports():
    data = request.json
    if data.get("username") != ADMIN_USERNAME or data.get("password") != ADMIN_PASSWORD:
        return jsonify({"ok": False}), 403
    reports = list(db_reports.find().sort("ts", -1))
    for r in reports:
        if "_id" in r: r["_id"] = str(r["_id"])
    return jsonify({"ok": True, "reports": reports})

@app.route("/api/admin/delete-report", methods=["POST"])
def admin_delete_report():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD:
        return jsonify({"ok": False}), 403
    from bson import ObjectId
    db_reports.delete_one({"_id": ObjectId(data.get("report_id"))})
    return jsonify({"ok": True})

@app.route("/api/admin/manage-player", methods=["POST"])
def admin_manage_player():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD:
        return jsonify({"ok": False, "msg": "คุณไม่มีสิทธิ์"}), 403
        
    target_pin = data.get("target_pin", "").strip()
    action = data.get("action")
    value = data.get("value")
    
    users = load_users()
    target_username = None
    for uname, info in users.items():
        if info.get("pin") == target_pin:
            target_username = uname
            break
            
    if not target_username: return jsonify({"ok": False, "msg": "ไม่พบ PIN นี้"}), 404
    user_data = users[target_username]
    
    if action == "add_score":
        user_data["score"] += int(value)
        if user_data["score"] > user_data.get("best_score", 0): user_data["best_score"] = user_data["score"]
    elif action == "reduce_score":
        user_data["score"] = max(0, user_data["score"] - int(value))
    elif action == "add_exp":
        user_data["exp"] = user_data.get("exp", 0) + int(value)
    elif action == "reduce_exp":
        user_data["exp"] = max(0, user_data.get("exp", 0) - int(value))
    elif action == "set_rank":
        for rk in RANKS:
            if rk["id"] == value:
                user_data["rank_id"] = rk["id"]
                user_data["exp"] = rk["exp_need"]
                break
    elif action == "ban":
        user_data["banned"] = True
    elif action == "unban":
        user_data["banned"] = False
    elif action == "clear_stats":
        user_data["score"] = 0; user_data["best_score"] = 0; user_data["games_played"] = 0; user_data["exp"] = 0; user_data["rank_id"] = "wood"
    elif action == "reset_pin":
        user_data["pin"] = gen_pin()

    save_users(users)
    return jsonify({"ok": True, "msg": "จัดการข้อมูลสำเร็จ!"})

@app.route("/api/admin/toggle-maintenance", methods=["POST"])
def toggle_maintenance():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    sys = load_system()
    sys["maintenance"] = not sys.get("maintenance", False)
    save_system(sys)
    return jsonify({"ok": True, "maintenance": sys["maintenance"]})

@app.route("/api/admin/set-announcement", methods=["POST"])
def set_announcement():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    sys = load_system()
    sys["announcement"] = data.get("text", "")
    save_system(sys)
    return jsonify({"ok": True})

@app.route("/api/admin/clear-chat", methods=["POST"])
def clear_chat():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    db_chat.delete_many({})
    return jsonify({"ok": True})

@app.route("/api/admin/delete-player", methods=["POST"])
def delete_player():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    db_users.delete_one({"username": data.get("raw_user")})
    return jsonify({"ok": True})

@app.route("/api/admin/reset-all-ranks", methods=["POST"])
def reset_all_ranks():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    users = load_users()
    for u in users:
        users[u]["exp"] = 0
        users[u]["rank_id"] = "wood"
    save_users(users)
    return jsonify({"ok": True})

@app.route("/api/admin/set-global-theme", methods=["POST"])
def set_global_theme():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    sys = load_system()
    sys["theme"] = data.get("theme", "dark")
    save_system(sys)
    return jsonify({"ok": True})

# -------------------------------------------------------------
# 🎮 ระบบเกมหลักของผู้เล่น (สมัคร / ล็อกอิน / จัดการข้อมูล)
# -------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
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

@app.route("/api/login", methods=["POST"])
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
    return jsonify({"logged_in":False}), 200

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok":True,"msg":"ออกจากระบบเรียบร้อย"})

@app.route("/api/question", methods=["POST"])
def question():
    return jsonify(generate_question(request.json.get("difficulty","easy")))

@app.route("/api/score", methods=["POST"])
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

@app.route("/api/chat", methods=["GET"])
def chat_get(): return jsonify(db_chat.find().sort("ts", 1)[-80:])

@app.route("/api/chat", methods=["POST"])
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
    
    msg_doc = {"user":username,"text":text,"rank_emoji":rank_emoji,"title_emoji":title_emoji,"ts":int(time.time())}
    db_chat.insert_one(msg_doc)
    return jsonify({"ok":True})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

