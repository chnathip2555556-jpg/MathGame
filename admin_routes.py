from flask import request, jsonify, send_from_directory
import time, random, string
from bson import ObjectId
from __main__ import app, db_users, db_system, ADMIN_USERNAME, ADMIN_PASSWORD, RANKS, current_dir, db_chat
from __main__ import get_rank, get_title, load_users, save_users, load_system, save_system, save_chat, gen_pin

@app.route("/admin")
def admin_page():
    return send_from_directory(current_dir, "admin.html")

# -------------------------------------------------------------
# 🛠️ แอดมินจัดการผู้เล่นและระบบหลัก (รวม 18 ฟังก์ชันแอดมิน)
# -------------------------------------------------------------

# 🌟 ระบบ 1: ล็อกอินแอดมิน
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    if data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "ชื่อหรือรหัสผ่านไม่ถูกต้อง"}), 401

# 🌟 ระบบ 2: ดึงรายชื่อและสถิติผู้เล่นทั้งหมด
@app.route("/api/admin/users", methods=["POST"])
def admin_users():
    data = request.json
    if data.get("username") != ADMIN_USERNAME or data.get("password") != ADMIN_PASSWORD:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    users = load_users()
    result = []
    for uname, info in users.items():
        rank = get_rank(info.get("exp", 0))
        title = get_title(info.get("score", 0))
        disp_name = info.get("display_name", uname)
        result.append({
            "username": disp_name, "raw_user": uname, "pin": info["pin"], "score": info["score"],
            "best_score": info["best_score"], "games_played": info["games_played"],
            "exp": info.get("exp", 0), "rank": rank["emoji"]+" "+rank["name"],
            "title": title["emoji"]+" "+title["name"], "banned": info.get("banned", False),
            "lucky_mode": info.get("lucky_mode", "normal") # เพิ่มสถานะโหมดพิเศษรายบุคคล
        })
    result.sort(key=lambda x: x["best_score"], reverse=True)
    return jsonify({"ok": True, "users": result})

# 🌟 ระบบ 3 ถึง 7: จัดการผู้เล่นรายบุคคล (เพิ่ม/ลดแต้ม, เพิ่ม/ลด EXP, ตั้งแรงค์, แบน/ปลดแบน, ล้างสถิติ, รีเซ็ต PIN)
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
        user_data["rank_id"] = get_rank(user_data["exp"])["id"]
    elif action == "reduce_exp":
        user_data["exp"] = max(0, user_data["exp", 0] - int(value))
        user_data["rank_id"] = get_rank(user_data["exp"])["id"]
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

# 🌟 ระบบ 8: ปิด/เปิด ปรับปรุงเซิร์ฟเวอร์
@app.route("/api/admin/toggle-maintenance", methods=["POST"])
def toggle_maintenance():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    sys = load_system()
    sys["maintenance"] = not sys.get("maintenance", False)
    save_system(sys)
    return jsonify({"ok": True, "maintenance": sys["maintenance"]})

# 🌟 ระบบ 9: แก้ไขคำประกาศประจำวันบนหน้าเว็บ
@app.route("/api/admin/set-announcement", methods=["POST"])
def set_announcement():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    sys = load_system()
    sys["announcement"] = data.get("text", "")
    save_system(sys)
    return jsonify({"ok": True})

# 🌟 ระบบ 10: ลบแชททั้งหมดในฐานข้อมูล
@app.route("/api/admin/clear-chat", methods=["POST"])
def clear_chat():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    save_chat([])
    return jsonify({"ok": True})

# 🌟 ระบบ 11: ลบผู้เล่นถาวรออกจากฐานข้อมูล
@app.route("/api/admin/delete-player", methods=["POST"])
def delete_player():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    db_users.delete_one({"username": data.get("raw_user")})
    return jsonify({"ok": True})

# 🌟 ระบบ 12: รีเซ็ตแรงค์ของทุกคนเป็น 0 พร้อมกัน (จัดซีซั่นใหม่)
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

# 🌟 ระบบ 13: เปลี่ยนธีมหน้าเว็บหลักแบบ Global (บังคับทุกคนใช้ธีมเดียวกัน)
@app.route("/api/admin/set-global-theme", methods=["POST"])
def set_global_theme():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    sys = load_system()
    sys["theme"] = data.get("theme", "dark")
    save_system(sys)
    return jsonify({"ok": True})

# ==========================================
# 🔥 🚀 ระบบแอดมินที่เพิ่มขึ้นมาใหม่ (ระบบที่ 14 - 18)
# ==========================================

# 🌟 ระบบ 14: สุ่มแจก EXP/Score ให้ผู้เล่นทุกคนในเซิร์ฟเวอร์พร้อมกัน (กิจกรรมแจกโค้ด/แจกฟรี)
@app.route("/api/admin/giveaway-all", methods=["POST"])
def admin_giveaway_all():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    give_type = data.get("type") # "score" หรือ "exp"
    amount = int(data.get("amount", 0))
    
    users = load_users()
    for uname in users:
        if give_type == "score":
            users[uname]["score"] += amount
            if users[uname]["score"] > users[uname].get("best_score", 0):
                users[uname]["best_score"] = users[uname]["score"]
        elif give_type == "exp":
            users[uname]["exp"] = users[uname].get("exp", 0) + amount
            users[uname]["rank_id"] = get_rank(users[uname]["exp"])["id"]
            
    save_users(users)
    return jsonify({"ok": True, "msg": f"แจกรางวัล {give_type} จำนวน {amount} ให้ผู้เล่นทุกคนแล้ว!"})

# 🌟 ระบบ 15: สรุปสถิติเซิร์ฟเวอร์แบบภาพรวม (แดชบอร์ดแอดมินสำหรับดูว่าคนเล่นเยอะไหม)
@app.route("/api/admin/server-stats", methods=["POST"])
def admin_server_stats():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    
    users = load_users()
    total_players = len(users)
    total_games = sum(u.get("games_played", 0) for u in users.values())
    total_score = sum(u.get("score", 0) for u in users.values())
    banned_players = sum(1 for u in users.values() if u.get("banned", False))
    
    return jsonify({
        "ok": True,
        "total_players": total_players,
        "total_games_played": total_games,
        "total_score_pool": total_score,
        "banned_count": banned_players,
        "db_chat_count": db_chat.count_documents({})
    })

# 🌟 ระบบ 16: สั่งแอดมินส่งข้อความแชทประกาศสีทอง (Announce Chat) เข้ากล่องแชทผู้เล่นทันที
@app.route("/api/admin/send-system-chat", methods=["POST"])
def admin_send_system_chat():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    text = data.get("text", "").strip()
    if not text: return jsonify({"ok": False, "msg": "ไม่มีข้อความ"}), 400
    
    msg_doc = {
        "user": "[ระบบประกาศ]",
        "text": text,
        "rank_emoji": "📢",
        "title_emoji": "✨",
        "ts": int(time.time())
    }
    db_chat.insert_one(msg_doc)
    return jsonify({"ok": True, "msg": "ส่งข้อความประกาศเข้าแชทเรียบร้อย!"})

# 🌟 ระบบ 17: สั่งลบข้อความในแชทระบุเป็น "รายข้อความ" (กรณีมีคนพิมพ์จาบจ้วง หรือสแปมด่า)
@app.route("/api/admin/delete-chat-msg", methods=["POST"])
def admin_delete_chat_msg():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    msg_ts = data.get("ts") # อ้างอิงจากเวลาของข้อความนั้นๆ
    
    db_chat.delete_one({"ts": int(msg_ts)})
    return jsonify({"ok": True, "msg": "ลบข้อความแชทดังกล่าวแล้ว"})

# 🌟 ระบบ 18: ระบบล็อกผลคำตอบ หรือแกล้งผู้เล่น (โหมด Lucky / Bad-Luck ไว้ทดสอบเวลามีบั๊กส่งคำตอบ)
@app.route("/api/admin/set-player-luck", methods=["POST"])
def admin_set_player_luck():
    data = request.json
    if data.get("admin_user") != ADMIN_USERNAME or data.get("admin_pass") != ADMIN_PASSWORD: return jsonify({"ok":False}), 403
    target_pin = data.get("target_pin", "").strip()
    mode = data.get("mode", "normal") # ตัวเลือก: "normal" (ปกติ) | "always_easy" (ได้แต่โจทย์ง่าย) | "nerf" (หัก EXP แรงขึ้น)
    
    users = load_users()
    target_username = None
    for uname, info in users.items():
        if info.get("pin") == target_pin:
            target_username = uname
            break
            
    if not target_username: return jsonify({"ok": False, "msg": "ไม่พบ PIN นี้"}), 404
    
    users[target_username]["lucky_mode"] = mode
    save_users(users)
    return jsonify({"ok": True, "msg": f"เปลี่ยนโหมดผู้เล่นเป็น {mode} สำเร็จแล้วเอาไว้ทดสอบบั๊ก!"})
