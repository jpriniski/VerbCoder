from flask import Flask, render_template, request, jsonify
import csv
import os
import random
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

app = Flask(__name__, template_folder='../templates')

BASE_DIR = Path(__file__).parent.parent  # project root
VERBS_FILE = BASE_DIR / "verb_framing_keywords.csv"
RELIABILITY_FILE = BASE_DIR / "reliability_verbs.txt"


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
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    pass_num INT NOT NULL DEFAULT 1
                )
            """)
            cur.execute("""
                ALTER TABLE responses
                ADD COLUMN IF NOT EXISTS pass_num INT NOT NULL DEFAULT 1
            """)
    conn.close()


def _load_reliability_verbs():
    if not RELIABILITY_FILE.exists():
        return set()
    with open(RELIABILITY_FILE) as f:
        return {line.strip() for line in f if line.strip()}


RELIABILITY_VERBS = _load_reliability_verbs()

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


def get_user_submissions(username):
    """Returns {verb: submission_count} for this user."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT verb, COUNT(*) FROM responses WHERE username = %s GROUP BY verb",
                (username,)
            )
            return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/options")
def options():
    categories, cat_subs = load_options()
    total = len(load_verbs()) + len(RELIABILITY_VERBS)
    return jsonify({
        "categories": categories,
        "category_subclusters": cat_subs,
        "total": total,
    })


@app.route("/api/next")
def next_verb():
    username = request.args.get("user", "").strip()
    if not username:
        return jsonify({"error": "No username"}), 400

    verbs = load_verbs()
    submissions = get_user_submissions(username)
    total = len(verbs) + len(RELIABILITY_VERBS)
    done_count = sum(submissions.values())

    # Phase 1: any verb not yet seen (pass 1)
    phase1_remaining = [v for v in verbs if submissions.get(v, 0) == 0]
    if phase1_remaining:
        verb = random.choice(phase1_remaining)
        return jsonify({"verb": verb, "done": done_count, "total": total, "is_reliability": False})

    # Phase 2: reliability verbs seen exactly once (pass 2)
    phase2_remaining = [v for v in RELIABILITY_VERBS if submissions.get(v, 0) == 1]
    if phase2_remaining:
        verb = random.choice(phase2_remaining)
        return jsonify({"verb": verb, "done": done_count, "total": total, "is_reliability": True})

    return jsonify({"complete": True, "done": done_count, "total": total})


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

    max_passes = 2 if verb in RELIABILITY_VERBS else 1

    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM responses WHERE username = %s AND verb = %s",
                    (username, verb)
                )
                existing = cur.fetchone()[0]

                if existing >= max_passes:
                    return jsonify({"ok": True, "skipped": True})

                pass_num = existing + 1
                cur.execute(
                    """INSERT INTO responses
                       (username, verb, category_label, subcluster_label, response_time_ms, pass_num)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (username, verb, category, subcluster, response_time_ms, pass_num)
                )
    finally:
        conn.close()

    return jsonify({"ok": True})


# ── Dawid-Skene ───────────────────────────────────────────────────────────────

def _dawid_skene(annotations, K, n_iter=100, tol=1e-6):
    N, R = annotations.shape
    p = np.ones(K) / K
    pi = np.zeros((R, K, K))
    for r in range(R):
        pi[r] = np.eye(K) * 0.7 + np.ones((K, K)) * 0.3 / K

    T = np.zeros((N, K))
    prev_ll = -np.inf

    for _ in range(n_iter):
        log_T = np.tile(np.log(p + 1e-300), (N, 1))
        for r in range(R):
            log_pi_r = np.log(pi[r] + 1e-300)
            for i in range(N):
                obs = annotations[i, r]
                if obs >= 0:
                    log_T[i] += log_pi_r[:, obs]

        log_T -= log_T.max(axis=1, keepdims=True)
        T = np.exp(log_T)
        T /= T.sum(axis=1, keepdims=True)

        p = T.mean(axis=0)
        p /= p.sum()

        pi = np.zeros((R, K, K))
        for r in range(R):
            for i in range(N):
                obs = annotations[i, r]
                if obs >= 0:
                    pi[r, :, obs] += T[i]
        row_sums = pi.sum(axis=2, keepdims=True)
        pi /= np.where(row_sums == 0, 1, row_sums)

        ll = np.sum(np.log(np.maximum(T.max(axis=1), 1e-300)))
        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

    return T, p, pi


@app.route("/analysis")
def analysis_page():
    return render_template("analysis.html")


@app.route("/charts")
def charts_page():
    return render_template("charts.html")


@app.route("/api/charts-data")
def charts_data():
    rater_filter = request.args.getlist("raters") or ["Hunter", "Tatyana", "user1", "user3"]

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT username, verb, category_label, response_time_ms "
                "FROM responses WHERE username = ANY(%s)",
                (rater_filter,)
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return jsonify({"verbs": [], "categories": [], "pca_variance": []})

    verb_data = defaultdict(dict)
    verb_times = defaultdict(list)
    for r in rows:
        verb_data[r["verb"]][r["username"]] = r["category_label"]
        if r["response_time_ms"]:
            verb_times[r["verb"]].append(int(r["response_time_ms"]))

    cats = sorted(set(r["category_label"] for r in rows))
    cat_idx = {c: i for i, c in enumerate(cats)}
    verbs = sorted(verb_data.keys())
    K = len(cats)
    R = len(rater_filter)
    rater_idx = {r: i for i, r in enumerate(rater_filter)}
    N = len(verbs)

    annotations = np.full((N, R), -1, dtype=int)
    for i, verb in enumerate(verbs):
        for rater, cat in verb_data[verb].items():
            if rater in rater_idx:
                annotations[i, rater_idx[rater]] = cat_idx[cat]

    T, _p, _pi = _dawid_skene(annotations, K)
    predicted = np.argmax(T, axis=1)
    confidence = T.max(axis=1)

    # PCA on DS posteriors (3 components)
    V_centered = T - T.mean(axis=0)
    U, S, _ = np.linalg.svd(V_centered, full_matrices=False)
    coords = U[:, :3] * S[:3]
    total_var = float((S ** 2).sum())
    pca_variance = [float(s ** 2) / total_var for s in S[:3]]

    result = []
    for i, verb in enumerate(verbs):
        times = verb_times[verb]
        avg_ms = int(np.median(times)) if times else None
        result.append({
            "verb": verb,
            "ds_label": cats[int(predicted[i])],
            "confidence": round(float(confidence[i]), 4),
            "n_raters": sum(1 for r in rater_filter if r in verb_data[verb]),
            "pca_x": round(float(coords[i, 0]), 4),
            "pca_y": round(float(coords[i, 1]), 4),
            "pca_z": round(float(coords[i, 2]), 4),
            "avg_response_ms": avg_ms,
        })

    # Per-category Gaussian density ellipses (1σ and 2σ)
    theta = np.linspace(0, 2 * np.pi, 80)
    circle = np.array([np.cos(theta), np.sin(theta)])
    density_ellipses = {}
    for k, cat in enumerate(cats):
        mask = predicted == k
        if mask.sum() < 3:
            continue
        pts = coords[mask]
        mu = pts.mean(axis=0)
        cov = np.cov(pts.T) if pts.shape[0] > 1 else np.eye(2) * 1e-4
        try:
            evals, evecs = np.linalg.eigh(cov)
            evals = np.maximum(evals, 0)
            order = np.argsort(evals)[::-1]
            evals, evecs = evals[order], evecs[:, order]
            density_ellipses[cat] = {}
            for sigma in [1, 2]:
                ell = (evecs @ np.diag(np.sqrt(evals) * sigma) @ circle).T + mu
                density_ellipses[cat][f"sigma{sigma}"] = [
                    [round(float(p[0]), 4), round(float(p[1]), 4)] for p in ell
                ]
        except Exception:
            pass

    # 3D Gaussian parameters per category (eigenvectors + eigenvalues)
    density_3d = {}
    for k, cat in enumerate(cats):
        mask = predicted == k
        if mask.sum() < 4:
            continue
        pts3 = coords[mask, :3]
        mu3 = pts3.mean(axis=0)
        cov3 = np.cov(pts3.T)
        try:
            evals, evecs = np.linalg.eigh(cov3)
            evals = np.maximum(evals, 0)
            order = np.argsort(evals)[::-1]
            evals, evecs = evals[order], evecs[:, order]
            density_3d[cat] = {
                "mu": [round(float(x), 4) for x in mu3],
                "axes": [
                    [round(float(evals[i]), 6),
                     [round(float(evecs[j, i]), 4) for j in range(3)]]
                    for i in range(3)
                ],
            }
        except Exception:
            pass

    return jsonify({
        "verbs": result,
        "categories": cats,
        "pca_variance": pca_variance,
        "density_ellipses": density_ellipses,
        "density_3d": density_3d,
    })


@app.route("/api/ds-results")
def ds_results():
    rater_filter = request.args.getlist("raters") or ["Hunter", "Tatyana", "user1", "user3"]

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT username, verb, category_label, subcluster_label "
                "FROM responses WHERE username = ANY(%s)",
                (rater_filter,)
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return jsonify({"verbs": [], "categories": []})

    verb_data = defaultdict(dict)
    for r in rows:
        verb_data[r["verb"]][r["username"]] = r["category_label"]

    cats = sorted(set(r["category_label"] for r in rows))
    cat_idx = {c: i for i, c in enumerate(cats)}
    verbs = sorted(verb_data.keys())
    K = len(cats)
    R = len(rater_filter)
    rater_idx = {r: i for i, r in enumerate(rater_filter)}

    N = len(verbs)
    annotations = np.full((N, R), -1, dtype=int)
    for i, verb in enumerate(verbs):
        for rater, cat in verb_data[verb].items():
            if rater in rater_idx:
                annotations[i, rater_idx[rater]] = cat_idx[cat]

    T, _p, _pi = _dawid_skene(annotations, K)
    predicted = np.argmax(T, axis=1)
    confidence = T.max(axis=1)

    result = []
    for i, verb in enumerate(verbs):
        result.append({
            "verb": verb,
            "ds_label": cats[int(predicted[i])],
            "confidence": round(float(confidence[i]), 4),
            "posteriors": {cats[k]: round(float(T[i, k]), 4) for k in range(K)},
            "n_raters": sum(1 for r in rater_filter if r in verb_data[verb]),
        })

    return jsonify({"verbs": result, "categories": cats})
