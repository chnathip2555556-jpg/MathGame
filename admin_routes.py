from flask import Blueprint, request, jsonify, send_from_directory, current_app
import time

admin_bp = Blueprint('admin_routes', __name__)

def get_globals():
    return {
        "db_users": current_app.config.get('db_users'),
        "db_system": current_app.config.get('db_system'),
        "db_chat": current_app.config.get('db_chat'),
        "ADMIN_USERNAME": current_app.config.get('ADMIN_USERNAME'),
        "ADMIN_PASSWORD": current_app.config.get('ADMIN_PASSWORD'),
        "RANKS": current_app.config.get('RANKS'),
        "current_dir": current_app.config.get('CURRENT_DIR'),
        "get_rank": current_app.config.get('get_rank_func'),
        "get_title": current_app.config.get('get_title_func'),
        "load_users": current_app.config.get('load_users_func'),
        "save_users": current_app.config.get('save_users_func'),
        "load_system": current_app.config.get('load_system_func'),
        "save_system": current_app.config.get('save_system_func'),
        "save_chat": current_app.config.get('save_chat_func'),
        "gen_pin": current_app.config.get('gen_pin_func')
    }

@admin_bp.route("/admin")
def admin_page():
    g = get_globals()
    return send_from_directory(g["current_dir"], "admin.html")

@admin_bp.route("/api/admin/login", methods=["POST"])
def admin_login():
    g = get_globals()
    data = request.json
    if data.get("username") == g["ADMIN_USERNAME"] and data.get("password") == g["ADMIN_PASSWORD"]:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "ชื่อหรือรหัสผ่านไม่ถูกต้อง"}), 401

@admin_bp.route("/api/admin/users", methods=["POST"])
def admin_users():
    g = get_globals()
    data = request.json
    if data.get("username") != g["ADMIN_USERNAME"] or data.get("password") != g["ADMIN_PASSWORD"]:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    users = g["load_users"]()
    result = []
    for uname, info in users.items():
        rank = g["get_rank"](info.get("exp", 0))
        title = g["get_title"](info.get("score", 0))
        disp_name = info.get("display_name", uname)
        result.append({
            "username": disp_name, "raw_user": uname, "pin": info["pin"], "score": info["score"],
            "best_score": info["best_score"], "games_played": info["games_played"],
            "exp": info.get("exp", 0), "rank": rank["emoji"]+" "+rank["name"],
            "title": title["emoji"]+" "+title["name"], "banned": info.get("banned", False),
            "lucky_mode": info.get("lucky_mode", "normal")
        })
    result.sort(key=lambda x: x["best_score"], reverse=True)
    return jsonify({"ok": True, "users": result})

@admin_bp.route("/api/admin/manage-player", methods=["POST"])
def admin_manage_player():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]:
        return jsonify({"ok": False, "msg": "คุณไม่มีสิทธิ์"}), 403
        
    target_pin = data.get("target_pin", "").strip()
    action = data.get("action")
    value = data.get("value")
    
    users = g["load_users"]()
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
        user_data["rank_id"] = g["get_rank"](user_data["exp"])["id"]
    elif action == "reduce_exp":
        user_data["exp"] = max(0, user_data["exp", 0] - int(value))
        user_data["rank_id"] = g["get_rank"](user_data["exp"])["id"]
    elif action == "set_rank":
        for rk in g["RANKS"]:
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
        user_data["pin"] = g["gen_pin"]()

    g["save_users"](users)
    return jsonify({"ok": True, "msg": "จัดการข้อมูลสำเร็จ!"})

@admin_bp.route("/api/admin/toggle-maintenance", methods=["POST"])
def toggle_maintenance():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    sys = g["load_system"]()
    sys["maintenance"] = not sys.get("maintenance", False)
    g["save_system"](sys)
    return jsonify({"ok": True, "maintenance": sys["maintenance"]})

@admin_bp.route("/api/admin/set-announcement", methods=["POST"])
def set_announcement():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    sys = g["load_system"]()
    sys["announcement"] = data.get("text", "")
    g["save_system"](sys)
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/clear-chat", methods=["POST"])
def clear_chat():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    g["save_chat"]([])
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/delete-player", methods=["POST"])
def delete_player():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    g["db_users"].delete_one({"username": data.get("raw_user")})
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/reset-all-ranks", methods=["POST"])
def reset_all_ranks():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    users = g["load_users"]()
    for u in users:
        users[u]["exp"] = 0
        users[u]["rank_id"] = "wood"
    g["save_users"](users)
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/set-global-theme", methods=["POST"])
def set_global_theme():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    sys = g["load_system"]()
    sys["theme"] = data.get("theme", "dark")
    g["save_system"](sys)
    return jsonify({"ok": True})

@admin_bp.route("/api/admin/giveaway-all", methods=["POST"])
def admin_giveaway_all():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    give_type = data.get("type")
    amount = int(data.get("amount", 0))
    
    users = g["load_users"]()
    for uname in users:
        if give_type == "score":
            users[uname]["score"] += amount
            if users[uname]["score"] > users[uname].get("best_score", 0):
                users[uname]["best_score"] = users[uname]["score"]
        elif give_type == "exp":
            users[uname]["exp"] = users[uname].get("exp", 0) + amount
            users[uname]["rank_id"] = g["get_rank"](users[uname]["exp"])["id"]
            
    g["save_users"](users)
    return jsonify({"ok": True, "msg": f"แจกรางวัล {give_type} จำนวน {amount} ให้ผู้เล่นทุกคนแล้ว!"})

@admin_bp.route("/api/admin/server-stats", methods=["POST"])
def admin_server_stats():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    
    users = g["load_users"]()
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
        "db_chat_count": g["db_chat"].count_documents({})
    })

@admin_bp.route("/api/admin/send-system-chat", methods=["POST"])
def admin_send_system_chat():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    text = data.get("text", "").strip()
    if not text: return jsonify({"ok": False, "msg": "ไม่มีข้อความ"}), 400
    
    msg_doc = {
        "user": "[ระบบประกาศ]",
        "text": text,
        "rank_emoji": "📢",
        "title_emoji": "✨",
        "ts": int(time.time())
    }
    g["db_chat"].insert_one(msg_doc)
    return jsonify({"ok": True, "msg": "ส่งข้อความประกาศเข้าแชทเรียบร้อย!"})

@admin_bp.route("/api/admin/delete-chat-msg", methods=["POST"])
def admin_delete_chat_msg():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    msg_ts = data.get("ts")
    
    g["db_chat"].delete_one({"ts": int(msg_ts)})
    return jsonify({"ok": True, "msg": "ลบข้อความแชทดังกล่าวแล้ว"})

@admin_bp.route("/api/admin/set-player-luck", methods=["POST"])
def admin_set_player_luck():
    g = get_globals()
    data = request.json
    if data.get("admin_user") != g["ADMIN_USERNAME"] or data.get("admin_pass") != g["ADMIN_PASSWORD"]: return jsonify({"ok":False}), 403
    target_pin = data.get("target_pin", "").strip()
    mode = data.get("mode", "normal")
    
    users = g["load_users"]()
    target_username = None
    for uname, info in users.items():
        if info.get("pin") == target_pin:
            target_username = uname
            break
            
    if not target_username: return jsonify({"ok": False, "msg": "ไม่พบ PIN นี้"}), 404
    
    users[target_username]["lucky_mode"] = mode
    g["save_users"](users)
    return jsonify({"ok": True, "msg": f"เปลี่ยนโหมดผู้เล่นเป็น {mode} สำเร็จแล้ว!"})

