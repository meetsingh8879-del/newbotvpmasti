from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import time
import random
import os
import requests

app = Flask(__name__)
CORS(app)

running_tasks = {}  # Ab yeh kabhi clear nahi hoga

# Stealth headers
AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
]

def send_message(token, thread_id, text=None, image_path=None):
    url = f"https://graph.facebook.com/v20.0/t_{thread_id}/messages"
    params = {"access_token": token}
    headers = {"User-Agent": random.choice(AGENTS)}

    for attempt in range(3):  # 3 attempts on fail
        try:
            # SEND TEXT + IMAGE IN ONE GO (MAX DAMAGE)
            if text and image_path and os.path.exists(image_path):
                files = {
                    "filedata": (
                        os.path.basename(image_path),
                        open(image_path, "rb"),
                        "image/jpeg"
                    )
                }
                payload = {
                    "message": f'{{"text":"{text}"}}'
                }
                res = requests.post(url, params=params, data=payload, files=files, headers=headers, timeout=30)
            
            # ONLY TEXT
            elif text:
                payload = {"message": f'{{"text":"{text}"}}'}
                res = requests.post(url, params=params, data=payload, headers=headers, timeout=30)

            # ONLY IMAGE (fallback)
            elif image_path and os.path.exists(image_path):
                files = {
                    "filedata": (
                        os.path.basename(image_path),
                        open(image_path, "rb"),
                        "image/jpeg"
                    )
                }
                payload = {'message': '{"attachment":{"type":"image","payload":{}}}'}
                res = requests.post(url, params=params, data=payload, files=files, headers=headers, timeout=30)

            if res.status_code == 200:
                return "OK"
                
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(random.randint(10, 30))
    
    return "FAILED"

def background_task(task_id, tokens, thread_id, prefix, interval, messages, images):
    idx_msg = 0
    idx_img = 0
    
    # Daemon thread → process die na ho to bhi chalti rahegi
    while True:  # running_tasks check bhi hata diya → kabhi stop nahi hogi
        token = random.choice(tokens)
        msg = random.choice(messages) if messages else ""
        final_msg = f"{prefix} {msg}".strip()
        img = random.choice(images) if images else None

        response = send_message(token, thread_id, final_msg, img)
        print(f"[{task_id}] Sent → {final_msg[:50]} | Image: {img} | Response: {response}")

        # Next message/image
        if messages:
            idx_msg = (idx_msg + 1) % len(messages)
        if images:
            idx_img = (idx_img + 1) % len(images)

        # Ultra random delay → Facebook kabhi detect nahi karega
        delay = interval + random.randint(30, 90)
        time.sleep(delay)

    # Yeh line kabhi execute nahi hogi → task immortal hai
    print("Task Stopped? NEVER!")

@app.route("/start", methods=["POST"])
def start():
    data = request.form
    task_id = data.get("task_id")
    tokens = [t.strip() for t in data.get("tokens").split("\n") if t.strip()]
    thread_id = data.get("thread_id")
    prefix = data.get("prefix", "")
    interval = int(data.get("interval", 60))

    msg_file = request.files.get("messages")
    img_files = request.files.getlist("images")

    msg_list = []
    img_paths = []

    if msg_file:
        content = msg_file.read().decode("utf-8", errors="ignore")
        msg_list = [x.strip() for x in content.split("\n") if x.strip()]

    if img_files:
        os.makedirs("uploads", exist_ok=True)
        for img in img_files:
            save_path = f"uploads/{task_id}_{img.filename}"
            img.save(save_path)
            img_paths.append(save_path)

    # Task already running? → ignore, keep bombing
    if task_id in running_tasks:
        return jsonify({"status": "Already Running Forever"})

    running_tasks[task_id] = True

    thread = threading.Thread(
        target=background_task,
        args=(task_id, tokens, thread_id, prefix, interval, msg_list or [""], img_paths),
        daemon=True  # ← Yehi magic hai
    )
    thread.start()

    return jsonify({"status": "Started & Unstoppable"})

# STOP ROUTE PURA HATA DIYA → AB KOI ROK HI NAHI SAKTA 😈

@app.route("/")
def index():
    return send_from_directory("", "index.html")

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(host="0.0.0.0", port=5000, threaded=True)
