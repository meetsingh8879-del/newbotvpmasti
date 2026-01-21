from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import time
import random
import os
import requests

app = Flask(__name__)
CORS(app)

running_tasks = {}

AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
]

def send_message(token, thread_id, text=None, image_path=None):
    url = f"https://graph.facebook.com/v20.0/t_{thread_id}/messages"
    params = {"access_token": token}
    headers = {"User-Agent": random.choice(AGENTS)}

    for attempt in range(3):
        try:
            # TEXT + IMAGE/STICKER (MAX DAMAGE)
            if text and image_path and os.path.exists(image_path):
                files = {"filedata": (os.path.basename(image_path), open(image_path, "rb"), "image/png")}
                payload = {"message": f'{{"text":"{text}"}}'}
                res = requests.post(url, params=params, data=payload, files=files, headers=headers, timeout=40)

            # ONLY TEXT
            elif text:
                payload = {"message": f'{{"text":"{text}"}}'}
                res = requests.post(url, params=params, data=payload, headers=headers, timeout=40)

            # ONLY IMAGE / STICKER
            elif image_path and os.path.exists(image_path):
                files = {"filedata": (os.path.basename(image_path), open(image_path, "rb"), "image/png")}
                payload = {'message': '{"attachment":{"type":"image","payload":{"is_reusable":true}}}'}
                res = requests.post(url, params=params, data=payload, files=files, headers=headers, timeout=40)

            if res.status_code == 200:
                return "OK"
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(random.randint(10, 25))

    return "FAILED"

def background_task(task_id, tokens, thread_id, prefix, interval, messages, media_files):
    while True:
        token = random.choice(tokens)
        msg = random.choice(messages) if messages else ""
        final_msg = f"{prefix} {msg}".strip().strip()

        # Randomly pick any media (image or sticker)
        media_path = random.choice(media_files) if media_files else None

        response = send_message(token, thread_id, final_msg if final_msg else None, media_path)
        print(f"[{task_id}] 💀 Sent → {final_msg[:40]} | Media: {os.path.basename(media_path) if media_path else 'None'} → {response}")

        delay = interval + random.randint(35, 100)
        time.sleep(delay)

@app.route("/start", methods=["POST"])
def start():
    data = request.form
    task_id = data.get("task_id", "beast_" + str(random.randint(1000,9999)))
    tokens = [t.strip() for t in data.get("tokens", "").split("\n") if t.strip()]
    thread_id = data.get("thread_id")
    prefix = data.get("prefix", "💀").strip()
    interval = int(data.get("interval", 70))

    if not tokens or not thread_id:
        return jsonify({"status": "Error: Tokens ya Thread ID missing hai!"})

    msg_file = request.files.get("messages")
    media_files_input = request.files.getlist("media")  # Yeh Images + Stickers dono accept karega

    messages = [""]
    media_paths = []

    # Messages from file or direct textarea
    if msg_file and msg_file.filename:
        content = msg_file.read().decode("utf-8", errors="ignore")
        messages = [line.strip() for line in content.split("\n") if line.strip()]
    else:
        direct_text = data.get("direct_messages", "")
        if direct_text.strip():
            messages = [line.strip() for line in direct_text.split("\n") if line.strip()]

    if not messages:
        messages = ["💀"]

    # Save all media (images + stickers) → supports .png, .gif, .jpg, .webp
    if media_files_input:
        os.makedirs("uploads", exist_ok=True)
        for file in media_files_input:
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    safe_name = f"{task_id}_{int(time.time())}_{file.filename}"
                    save_path = os.path.join("uploads", safe_name)
                    file.save(save_path)
                    media_paths.append(save_path)

    # If no media, add default skull
    if not media_paths:
        default_sticker = "uploads/default_skull.png"
        if not os.path.exists(default_sticker):
            # You can add a skull.png in uploads folder later
            pass
        else:
            media_paths.append(default_sticker)

    if task_id in running_tasks:
        return jsonify({"status": "Already Destroying This Thread 💀"})

    running_tasks[task_id] = True

    thread = threading.Thread(
        target=background_task,
        args=(task_id, tokens, thread_id, prefix, interval, messages, media_paths),
        daemon=True
    )
    thread.start()

    return jsonify({
        "status": "UNSTOPPABLE MODE ACTIVATED",
        "task_id": task_id,
        "messages": len(messages),
        "media": len(media_paths),
        "warning": "Ab isko rokna impossible hai"
    })

@app.route("/")
def index():
    return send_from_directory("public", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("public", filename)

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("public", exist_ok=True)
    app.run(host="0.0.0.0", port=5000, threaded=True)
