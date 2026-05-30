from flask import Flask, render_template, request, jsonify
import csv
import os
import random
from datetime import datetime
from pathlib import Path
from filelock import FileLock

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
VERBS_FILE = BASE_DIR.parent / "verb_framing_keywords.csv"
RESPONSES_FILE = BASE_DIR / "responses.csv"
LOCK_FILE = BASE_DIR / "responses.csv.lock"

RESPONSE_FIELDS = ["username", "verb", "category_label", "subcluster_label", "response_time_ms", "timestamp"]


def load_verbs():
    with open(VERBS_FILE, newline="") as f:
        return [row["verb"] for row in csv.DictReader(f)]


def load_options():
    categories = []
    cat_subs = {}        # category -> ordered list of subclusters
    seen_cats = set()
    seen_subs_per = {}   # category -> set of seen subclusters

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
    done = set()
    if RESPONSES_FILE.exists():
        with open(RESPONSES_FILE, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("username") == username:
                    done.add(row["verb"])
    return done


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
    username        = (data.get("username") or "").strip()
    verb            = (data.get("verb") or "").strip()
    category        = (data.get("category") or "").strip()
    subcluster      = (data.get("subcluster") or "").strip()
    response_time_ms = data.get("response_time_ms", "")

    if not all([username, verb, category, subcluster]):
        return jsonify({"error": "Missing fields"}), 400

    lock = FileLock(str(LOCK_FILE))
    with lock:
        done = get_user_done(username)
        if verb in done:
            return jsonify({"ok": True, "skipped": True})

        file_exists = RESPONSES_FILE.exists()
        with open(RESPONSES_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=RESPONSE_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "username": username,
                "verb": verb,
                "category_label": category,
                "subcluster_label": subcluster,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat(),
            })

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
