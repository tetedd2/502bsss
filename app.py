from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace
import sqlite3
import os
from datetime import datetime

# ----------------------
# SETUP
# ----------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

model = YOLO("helmet.pt")
DB = "helmet.db"


# ----------------------
# DATABASE
# ----------------------

def db():
    return sqlite3.connect(DB)


def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        encoding BLOB,
        score INTEGER DEFAULT 100
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        helmet INTEGER,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ----------------------
# FACE MATCH
# ----------------------

def match_face(frame):

    temp = "temp.jpg"
    cv2.imwrite(temp, frame)

    conn = db()
    rows = conn.execute("SELECT id,name FROM users").fetchall()

    for uid, name in rows:
        ref = f"faces/{name}.jpg"
        if not os.path.exists(ref):
            continue

        try:
            result = DeepFace.verify(temp, ref, enforce_detection=False)

            if result["verified"]:
                conn.close()
                return uid
        except:
            pass

    conn.close()
    return None

# ----------------------
# ROUTES
# ----------------------

@app.route("/")
def index():
    return render_template("index.html")


# ======================
# REGISTER FACE
# ======================
@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    file = request.files["image"]

    os.makedirs("faces", exist_ok=True)
    path = f"faces/{name}.jpg"

    file.save(path)

    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO users(name,score) VALUES (?,100)",
        (name,)
    )
    conn.commit()
    conn.close()

    return "registered"

# ======================
# DETECT
# ======================
@app.route("/detect", methods=["POST"])
def detect():

    file = request.files["image"]
    img = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(img, cv2.IMREAD_COLOR)

    results = model(frame, conf=0.4)

    helmet_ok = True

    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            if label.lower() in ["no helmet", "without helmet", "no-helmet"]:
                helmet_ok = False

    user_id = match_face(frame)

    if user_id:
        conn = db()

        if not helmet_ok:
            conn.execute(
                "UPDATE users SET score = score - 5 WHERE id=?",
                (user_id,)
            )

        conn.execute(
            "INSERT INTO logs(user_id,helmet,time) VALUES (?,?,?)",
            (user_id, int(helmet_ok), datetime.now().isoformat())
        )

        conn.commit()
        conn.close()

    _, jpg = cv2.imencode(".jpg", frame)
    return jpg.tobytes(), 200, {"Content-Type": "image/jpeg"}


# ======================
# STATS
# ======================
@app.route("/stats")
def stats():

    conn = db()

    users = conn.execute(
        "SELECT name,score FROM users ORDER BY score DESC"
    ).fetchall()

    today = conn.execute("""
        SELECT COUNT(*) FROM logs
        WHERE helmet = 0 AND date(time)=date('now')
    """).fetchone()[0]

    conn.close()

    return jsonify({
        "users": [{"name":u[0],"score":u[1]} for u in users],
        "violations": today
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
