import uuid

from flask import Flask, render_template, request, Response, redirect, jsonify, session, make_response
import threading
from model.model import *
from werkzeug.utils import secure_filename
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests
from db.db import *
from utils.utils import *
from db.vector_db import *

app = Flask(__name__)

# ===== CONFIG =====
app.secret_key = os.environ.get("SECRET_KEY", "fallback_key")
app.config.update(
    SESSION_COOKIE_SECURE=True,      # Required for HTTPS
    SESSION_COOKIE_SAMESITE="None"   # Important for cross-origin
)
CORS(app)
upload_st = {}
UPLOAD_FOLDER = "sources"
user_chats = User_chat_db()
user_chats.create_table_if_not_exists()
userDb = user_db()
userDb.create_table_if_not_exists()
LTM = User_LTM_db()
LTM.create_table_if_not_exists()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ====== Delete existing files ======
def delete_source_file(user):
    sources_f = list(os.walk('sources'))[-1]
    file_li = sources_f[-1]
    root = sources_f[0]
    for file in file_li:
        print(file, user, str(file).startswith(user), flush=True)
        if str(file).startswith(user):
            os.remove(root + '//' + file)


@app.route("/")
def home():
    upload_st.clear()
    return render_template("index.html")


@app.route("/get_chat", methods=["POST"])
def get_chat():
    data = request.get_json()
    thread = data.get("thread")
    all_chats, citation = get_thread_chat(thread)
    return {'all_chats': all_chats, 'citation': citation}


@app.route("/check_auth")
def check_auth():
    token = request.cookies.get("auth_token")
    username = userDb.check_token(token)
    session['user'] = username
    print('username', username, token, flush=True)
    if username:
        return {"username": username}
    else:
        return {"username": None}


@app.route("/new_chat")
def new_chat():
    user = session['user']
    thread_id = user + str(uuid.uuid4())[-8:]
    user_chats.create_chat(thread_id, user, "New Chat")
    return {"thread": thread_id}


@app.route("/get_thread")
def get_thread():
    user = session['user']
    thread_li = user_chats.get_user_chats(user)
    thread_li = [list(i) for i in thread_li]
    return {"thread_li": thread_li}


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("email")
    password = data.get("password")

    session['user'] = username

    try:
        jwt_token = create_token(username)
        row = userDb.check_user(username, password)

        if row['count'] < 1:
            userDb.create_user(username, password, jwt_token)
        else:
            userDb.update_user(username, jwt_token)
        response = make_response(jsonify({"success": True, "user": username}))
        response.set_cookie("auth_token",
                            jwt_token,
                            httponly=True,
                            secure=True,
                            samesite="None",
                            max_age=60 * 60 * 1)
        return response

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("email")
    password = data.get("password")
    row = userDb.check_user(username, password)

    if row['count'] > 0:
        session['user'] = username
        userId = userDb.get_user(username, password)
        jwt_token = userId['token']
        response = make_response(jsonify({"success": True, "user": username}))
        response.set_cookie("auth_token",
                            jwt_token,
                            httponly=True,
                            secure=True,
                            samesite="None",
                            max_age=60 * 60 * 24)
        return response
    else:
        return jsonify({"success": False})


@app.route("/logout")
def logout():
    response = make_response("Logged out")

    response.set_cookie(
        "auth_token",
        "",
        httponly=True,
        secure=True,
        samesite="None",
        expires=0
    )
    vectorDb.truncate_user_data(session['user'])
    delete_source_file(session['user'])
    session['user'] = ''

    return response


# ===== GOOGLE SIGNUP =====
@app.route("/google_signup", methods=["POST"])
def google_signup():
    data = request.get_json()
    token = data.get("token")

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            os.getenv('GOOGLE_CLIENT_ID')
        )
        username = idinfo["email"]
        jwt_token = create_token(username)

        row = userDb.check_user(username)

        if row['count'] < 1:
            userDb.create_user(username, '', jwt_token)
        else:
            userDb.update_user(username, jwt_token)
        session['user'] = username
        response = make_response(jsonify({"success": True, "user": username}))
        response.set_cookie("auth_token",
                            jwt_token,
                            httponly=True,
                            secure=True,
                            samesite="None",
                            max_age=60 * 60 * 24)
        return response

    except Exception as e:
        print(e, flush=True)
        return make_response(jsonify({"success": False, "error": str(e)}))


# ===== Upload Endpoint =====
@app.route("/add_text", methods=["POST"])
def add_text():
    inp = request.get_json().get('text', "").strip()
    load_data(custom_text=inp, user_id=session['user'])
    return jsonify({"status": "ok"}), 200


@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist("files")

    rejected_files = []
    repeated_files = []
    upload_key_li = []

    for file in files:
        file_li = list(os.walk('sources'))[-1][-1]

        if file.filename == "":
            continue

        if file.filename in file_li:
            repeated_files.append(file.filename)
            continue

        if not allowed_file(file):
            rejected_files.append(file.filename)
            continue

        filename = session['user'] + secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        # load_data(filename=filename)
        upload_key = f'{uuid.uuid4().hex[:2]}_{filename}'
        upload_key_li.append(upload_key)
        upload_st[upload_key] = 'started'
        threading.Thread(
            target=load_data,
            kwargs={'user_id': session['user'], 'upload_st': upload_st, 'upload_key': upload_key, 'filename': filename}
        ).start()

    return jsonify({
        "uploaded": upload_key_li,
        "rejected": rejected_files,
        "already_uploaded": repeated_files
    }), 200


@app.route("/upload_status")
def upload_status():
    file_key = request.args.get("file")
    return jsonify({"upload_status": upload_st[file_key]})


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    prompt = data.get("prompt")
    mode = data.get("mode")
    thread = data.get("thread")

    with open('queries.txt', 'a') as f:
        f.write(prompt + " " + thread + "    ")

    answer, citation = get_answer(prompt=prompt, user=session['user'], thread=thread, mode=mode)

    return jsonify({
        "answer": answer,
        "citation": citation
    })


if __name__ == "__main__":
    app.run(port=7860, debug=True, threaded=True, use_reloader=False)
