from flask import Flask, render_template, request, Response, redirect, jsonify
import json
import torch
import os
import threading
from model.model import *
from werkzeug.utils import secure_filename


app = Flask(__name__)
queue = []

# ===== Config =====
UPLOAD_FOLDER = "sources"
ALLOWED_EXTENSIONS = {"pdf", "txt"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ====== Delete existing files ======
sources_f = list(os.walk('sources'))[-1]
file_li = sources_f[-1]
root = sources_f[0]
for file in file_li:
    os.remove(root+'//'+file)


# ===== Helper =====
def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    #vectorDb.truncate_db('pdf_collections')
    return render_template("index.html")

# ===== Upload Endpoint =====
@app.route("/add_text", methods=["POST"])
def add_text():
    inp = request.get_json().get('text',"").strip()
    print(inp)
    load_data(custom_text=inp)
    return jsonify({"status": "ok"}), 200


@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist("files")

    saved_files = []
    rejected_files = []
    repeated_files = []

    for file in files:
        file_li = list(os.walk('sources'))[-1][-1]
        print(file_li, file.filename)

        if file.filename == "":
            continue

        if file.filename in file_li:
            repeated_files.append(file.filename)
            continue

        if not allowed_file(file.filename):
            rejected_files.append(file.filename)
            continue

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)
        saved_files.append(filename)
    
        load_data(filename=filename)
    print({
        "uploaded": saved_files,
        "rejected": rejected_files,
        "already_uploaded": repeated_files,
    })

    return jsonify({
        "uploaded": saved_files,
        "rejected": rejected_files,
        "already_uploaded": repeated_files
    }), 200

@app.route("/generate")
def generate():
    prompt = request.args.get("prompt")

    with open('queries.txt','a') as f:
        f.write(prompt+"    ")

    answer, citation = get_answer(prompt=prompt)
    print({
    "answer": answer,
    "citation": citation
    })

    return jsonify({
    "answer": answer,
    "citation": citation
    })

if __name__ == "__main__":
    app.run(port=5000,debug=True, threaded=True,use_reloader=False)
