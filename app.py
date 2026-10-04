import os
import sqlite3
import hmac
import hashlib
from functools import wraps
from urllib.parse import urlencode

from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")


# ============================================================
# DATABASE
# ============================================================

DATABASE = "adreward.db"


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            points REAL DEFAULT 0
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


init_db()


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


# ============================================================
# BASIC HTML STYLE
# ============================================================

BASE_STYLE = """
<style>
    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: #f5f7fb;
        color: #222;
    }

    .container {
        max-width: 1000px;
        margin: 40px auto;
        padding: 20px;
    }

    .card {
        background: white;
        border-radius: 14px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
    }

    h1, h2, h3 {
        margin-top: 0;
    }

    input {
        width: 100%;
        padding: 12px;
        margin: 8px 0 15px;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-size: 15px;
    }

    button,
    .btn {
        display: inline-block;
        padding: 12px 18px;
        background: #111827;
        color: white;
        border: none;
        border-radius: 8px;
        text-decoration: none;
        cursor: pointer;
        font-size: 15px;
    }

    .btn-primary {
        background: #2563eb;
    }

    .btn-success {
        background: #16a34a;
    }

    .btn-danger {
        background: #dc2626;
    }

    .nav {
        background: #111827;
        padding: 15px 20px;
    }

    .nav a {
        color: white;
        text-decoration: none;
        margin-right: 20px;
    }

    .points {
        font-size: 38px;
        font-weight: bold;
        color: #2563eb;
    }

    .error {
        background: #fee2e2;
        color: #991b1b;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 15px;
    }

    .success {
        background: #dcfce7;
        color: #166534;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 15px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
    }

    th, td {
        padding: 12px;
        border-bottom: 1px solid #eee;
        text-align: left;
    }

    .offerwall {
        width: 100%;
        height: 750px;
        border: none;
        border-radius: 12px;
    }

    .muted {
        color: #666;
    }
</style>
"""


# ============================================================
# HOME / DASHBOARD
# ============================================================

@app.route("/")
@login_required
def home():

    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    db.close()

    return render_template_string(
        BASE_STYLE + """
        <div class="nav">
            <a href="{{ url_for('home') }}">Dashboard</a>
            <a href="{{ url_for('offers') }}">View Offers</a>
            <a href="{{ url_for('history') }}">Transaction History</a>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>

        <div class="container">

            <div class="card">
                <h1>Welcome, {{ user["username"] }}</h1>

                <p>Your current balance:</p>

                <div class="points">
                    {{ "%.2f"|format(user["points"]) }} Points
                </div>
            </div>

            <div class="card">
                <h2>Earn Points</h2>

                <p>
                    Complete available offers and receive points
                    after the offer provider confirms the completion.
                </p>

                <a class="btn btn-primary"
                   href="{{ url_for('offers') }}">
                    View Offers
                </a>
            </div>

            <div class="card">
                <h2>Transaction History</h2>

                <a class="btn"
                   href="{{ url_for('history') }}">
                    View History
                </a>
            </div>

        </div>
        """,
        user=user
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."

        elif len(username) < 3:
            error = "Username must be at least 3 characters."

        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        else:

            db = get_db()

            existing = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if existing:
                error = "Username already exists."
                db.close()

            else:

                hashed_password = generate_password_hash(password)

                db.execute(
                    """
                    INSERT INTO users (username, password, points)
                    VALUES (?, ?, 0)
                    """,
                    (username, hashed_password)
                )

                db.commit()

                user = db.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

                db.close()

                session["user_id"] = user["id"]

                return redirect(url_for("home"))

    return render_template_string(
        BASE_STYLE + """
        <div class="container">

            <div class="card">

                <h1>Create Account</h1>

                {% if error %}
                    <div class="error">{{ error }}</div>
                {% endif %}

                <form method="POST">

                    <label>Username</label>
                    <input
                        type="text"
                        name="username"
                        required
                    >

                    <label>Password</label>
                    <input
                        type="password"
                        name="password"
                        required
                    >

                    <button type="submit">
                        Register
                    </button>

                </form>

                <br>

                <p>
                    Already have an account?
                    <a href="{{ url_for('login') }}">
                        Login
                    </a>
                </p>

            </div>

        </div>
        """,
        error=error
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        db.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]

            return redirect(url_for("home"))

        error = "Invalid username or password."

    return render_template_string(
        BASE_STYLE + """
        <div class="container">

            <div class="card">

                <h1>Login</h1>

                {% if error %}
                    <div class="error">{{ error }}</div>
                {% endif %}

                <form method="POST">

                    <label>Username</label>

                    <input
                        type="text"
                        name="username"
                        required
                    >

                    <label>Password</label>

                    <input
                        type="password"
                        name="password"
                        required
                    >

                    <button type="submit">
                        Login
                    </button>

                </form>

                <br>

                <p>
                    Don't have an account?
                    <a href="{{ url_for('register') }}">
                        Register
                    </a>
                </p>

            </div>

        </div>
        """,
        error=error
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ============================================================
# OFFERWALL
# ============================================================

@app.route("/offers")
@login_required
def offers():

    public_key = os.environ.get("OFFERWALL_PUBLIC_KEY")
    secret_key = os.environ.get("OFFERWALL_SECRET")

    if not public_key:
        return render_template_string(
            BASE_STYLE + """
            <div class="container">
                <div class="card">
                    <h1>Available Offers</h1>

                    <div class="error">
                        Offerwall public key is not configured.
                    </div>

                    <a class="btn"
                       href="{{ url_for('home') }}">
                        Back to Dashboard
                    </a>
                </div>
            </div>
            """
        )

    if not secret_key:
        return render_template_string(
            BASE_STYLE + """
            <div class="container">
                <div class="card">
                    <h1>Available Offers</h1>

                    <div class="error">
                        Offerwall secret key is not configured.
                    </div>

                    <p class="muted">
                        Add OFFERWALL_SECRET to the Render
                        environment variables before using
                        signed Offerwall links.
                    </p>

                    <a class="btn"
                       href="{{ url_for('home') }}">
                        Back to Dashboard
                    </a>
                </div>
            </div>
            """
        )

    user_id = str(session["user_id"])

    # Parameters required by Offerwall.GG
    params = {
        "appId": public_key,
        "userId": user_id
    }

    # Sort parameters alphabetically before signing.
    sorted_params = sorted(params.items())

    canonical = urlencode(sorted_params)

    signature = hmac.new(
        secret_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # User-facing Offerwall URL
    wall_params = {
        "userId": user_id,
        "signature": signature
    }

    wall_url = (
        "https://offerwall.gg/wall/"
        + public_key
        + "?"
        + urlencode(wall_params)
    )

    return render_template_string(
        BASE_STYLE + """
        <div class="nav">
            <a href="{{ url_for('home') }}">Dashboard</a>
            <a href="{{ url_for('history') }}">
                Transaction History
            </a>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>

        <div class="container">

            <div class="card">

                <h1>Available Offers</h1>

                <p class="muted">
                    Complete eligible offers to earn points.
                    Rewards are credited after the offer provider
                    confirms the completion.
                </p>

                <iframe
                    class="offerwall"
                    src="{{ wall_url }}"
                    title="Offerwall">
                </iframe>

            </div>

        </div>
        """,
        wall_url=wall_url
    )


# ============================================================
# DEVELOPMENT TEST REWARD
# ============================================================
#
# This is ONLY for local/development testing.
# It should NOT be used as a real advertising reward system.
#

@app.route("/watch")
@login_required
def watch():

    return render_template_string(
        BASE_STYLE + """
        <div class="container">

            <div class="card">

                <h1>Test Reward</h1>

                <p>
                    This page is for development testing only.
                </p>

                <form method="POST"
                      action="{{ url_for('claim') }}">

                    <button
                        class="btn btn-success"
                        type="submit">
                        Add Test Points
                    </button>

                </form>

                <br>

                <a class="btn"
                   href="{{ url_for('home') }}">
                    Back
                </a>

            </div>

        </div>
        """
    )


@app.route("/claim", methods=["POST"])
@login_required
def claim():

    # Development-only reward.
    test_points = 10

    db = get_db()

    db.execute(
        """
        UPDATE users
        SET points = points + ?
        WHERE id = ?
        """,
        (test_points, session["user_id"])
    )

    db.execute(
        """
        INSERT INTO transactions
        (user_id, points, reason)
        VALUES (?, ?, ?)
        """,
        (
            session["user_id"],
            test_points,
            "Development test reward"
        )
    )

    db.commit()
    db.close()

    return redirect(url_for("home"))


# ============================================================
# TRANSACTION HISTORY
# ============================================================

@app.route("/history")
@login_required
def history():

    db = get_db()

    transactions = db.execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template_string(
        BASE_STYLE + """
        <div class="nav">
            <a href="{{ url_for('home') }}">Dashboard</a>
            <a href="{{ url_for('offers') }}">View Offers</a>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>

        <div class="container">

            <div class="card">

                <h1>Transaction History</h1>

                {% if transactions %}

                <table>

                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Points</th>
                            <th>Reason</th>
                        </tr>
                    </thead>

                    <tbody>

                    {% for transaction in transactions %}

                        <tr>

                            <td>
                                {{ transaction["created_at"] }}
                            </td>

                            <td>
                                {{ "%.2f"|format(transaction["points"]) }}
                            </td>

                            <td>
                                {{ transaction["reason"] }}
                            </td>

                        </tr>

                    {% endfor %}

                    </tbody>

                </table>

                {% else %}

                    <p class="muted">
                        No transactions yet.
                    </p>

                {% endif %}

            </div>

        </div>
        """,
        transactions=transactions
    )


# ============================================================
# OFFERWALL CALLBACK / POSTBACK
# ============================================================

@app.route("/offerwall/callback", methods=["GET", "POST"])
def offerwall_callback():

    secret_key = os.environ.get("OFFERWALL_SECRET")

    if not secret_key:
        return "Server configuration error", 500

    # Offerwall.GG supports GET/POST postbacks.
    data = request.args if request.method == "GET" else request.form

    user_id = data.get("userId", "")
    transaction_id = data.get("transactionId", "")
    amount = data.get("currencyAmount", "")
    signature = data.get("signature", "")
    status = data.get("status", "")
    test = data.get("test", "0")

    # Required fields
    if not user_id or not transaction_id or not amount or not signature:
        return "Missing parameters", 400

    # Never credit dashboard test callbacks.
    if test == "1":
        return "TEST OK", 200

    # Validate numeric amount.
    try:
        amount_value = float(amount)
    except ValueError:
        return "Invalid amount", 400

    # Offerwall.GG signature:
    #
    # HMAC-SHA256(
    #     userId:transactionId:currencyAmount,
    #     secretKey
    # )
    #
    message = f"{user_id}:{transaction_id}:{amount}"

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison.
    if not hmac.compare_digest(
        signature.lower(),
        expected_signature.lower()
    ):
        return "Invalid signature", 403

    db = get_db()

    # Idempotency:
    # Don't process the same transaction twice.
    existing = db.execute(
        """
        SELECT id
        FROM transactions
        WHERE reason = ?
        """,
        (f"Offerwall transaction {transaction_id}",)
    ).fetchone()

    if existing:
        db.close()
        return "Already processed", 200

    # Positive amount = credit.
    # Negative amount = reversal.
    points = amount_value

    db.execute(
        """
        UPDATE users
        SET points = points + ?
        WHERE id = ?
        """,
        (points, user_id)
    )

    # Make sure the user actually exists.
    if db.total_changes == 0:
        db.close()
        return "User not found", 404

    reason = f"Offerwall transaction {transaction_id}"

    if status == "reversed":
        reason = f"Offerwall reversal {transaction_id}"

    db.execute(
        """
        INSERT INTO transactions
        (user_id, points, reason)
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            points,
            reason
        )
    )

    db.commit()
    db.close()

    return "OK", 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return "OK", 200


# ============================================================
# RUN LOCALLY
# ============================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )