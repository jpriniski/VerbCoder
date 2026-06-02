from flask import Flask, render_template, request, jsonify
import csv
import os
import random
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__, template_folder='../templates')

BASE_DIR = Path(__file__).parent.parent  # project root
VERBS_FILE = BASE_DIR / "verb_framing_keywords.csv"


def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_db()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    verb TEXT NOT NULL,
                    category_label TEXT NOT NULL,
                    subcluster_label TEXT NOT NULL,
                    response_time_ms BIGINT,
                    timestamp TIMESTAMPTZ DEFAULT NOW()
                )
            """)
    conn.close()


init_db()


def load_verbs():
    with open(VERBS_FILE, newline="") as f:
        return [row["verb"] for row in csv.DictReader(f)]


def load_options():
    categories = []
    cat_subs = {}
    seen_cats = set()
    seen_subs_per = {}

    with open(VERBS_FILE, newline="") as f:
        for row in csv.DictReader(f):
            cat = row["category_label"]
            sub = row["subcluster_label"]
            if cat not in seen_cats:
                categories.append(cat)
                seen_cats.add(cat)
                cat_subs[cat] = []
                seen_subs_per[cat] = set()
            if sub not in seen_subs_per[cat]:
                cat_subs[cat].append(sub)
                seen_subs_per[cat].add(sub)

    return categories, cat_subs


def get_user_done(username):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT verb FROM responses WHERE username = %s",
                (username,)
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/options")
def options():
    categories, cat_subs = load_options()
    return jsonify({
        "categories": categories,
        "category_subclusters": cat_subs,
        "total": len(load_verbs()),
    })


@app.route("/api/next")
def next_verb():
    username = request.args.get("user", "").strip()
    if not username:
        return jsonify({"error": "No username"}), 400

    verbs = load_verbs()
    done = get_user_done(username)
    remaining = [v for v in verbs if v not in done]

    if not remaining:
        return jsonify({"complete": True, "done": len(done), "total": len(verbs)})

    return jsonify({"verb": random.choice(remaining), "done": len(done), "total": len(verbs)})


@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.json or {}
    username         = (data.get("username") or "").strip()
    verb             = (data.get("verb") or "").strip()
    category         = (data.get("category") or "").strip()
    subcluster       = (data.get("subcluster") or "").strip()
    response_time_ms = data.get("response_time_ms")

    if not all([username, verb, category, subcluster]):
        return jsonify({"error": "Missing fields"}), 400

    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                # Skip if already submitted
                cur.execute(
                    "SELECT 1 FROM responses WHERE username = %s AND verb = %s",
                    (username, verb)
                )
                if cur.fetchone():
                    return jsonify({"ok": True, "skipped": True})

                cur.execute(
                    """INSERT INTO responses
                       (username, verb, category_label, subcluster_label, response_time_ms)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (username, verb, category, subcluster, response_time_ms)
                )
    finally:
        conn.close()

    return jsonify({"ok": True})
