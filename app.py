from flask import Flask, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "change-this-secret-key-later"

DATABASE = "adreward.db"


# ================= DATABASE =================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            points INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ================= CURRENT USER =================

def get_current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    return user


# ================= HOME =================

@app.route("/")
def home():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>AdReward</title>

        <style>

            body {{
                font-family: Arial;
                background: #f4f6f8;
                text-align: center;
                padding-top: 70px;
            }}

            .card {{
                background: white;
                width: 420px;
                margin: auto;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }}

            .points {{
                font-size: 32px;
                font-weight: bold;
                margin: 25px;
            }}

            button {{
                background: #111;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 10px;
                font-size: 18px;
                cursor: pointer;
            }}

            a {{
                text-decoration: none;
            }}

            .link {{
                display: block;
                margin-top: 20px;
                color: #333;
            }}

            .logout {{
                color: #777;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>🎁 AdReward</h1>

            <h2>Welcome, {user["username"]}</h2>

            <div class="points">
                {user["points"]} Points
            </div>

            <a href="/watch">
                <button>▶ Watch Ad</button>
            </a>

            <a class="link" href="/history">
                📜 Transaction History
            </a>

            <a class="link logout" href="/logout">
                Logout
            </a>

        </div>

    </body>

    </html>
    """


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = ""

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        if len(username) < 3:

            error = "Username must be at least 3 characters."

        elif len(password) < 6:

            error = "Password must be at least 6 characters."

        else:

            hashed_password = generate_password_hash(password)

            conn = get_db()

            try:

                conn.execute(
                    """
                    INSERT INTO users
                    (username, password, points)
                    VALUES (?, ?, ?)
                    """,
                    (username, hashed_password, 0)
                )

                conn.commit()

                user = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

                session["user_id"] = user["id"]

                conn.close()

                return redirect(url_for("home"))

            except sqlite3.IntegrityError:

                conn.close()

                error = "Username already exists."

    return f"""
    <!DOCTYPE html>

    <html>

    <head>
        <title>Create Account</title>

        <style>

            body {{
                font-family: Arial;
                background: #f4f6f8;
                text-align: center;
                padding-top: 80px;
            }}

            .card {{
                background: white;
                width: 350px;
                margin: auto;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }}

            input {{
                width: 90%;
                padding: 12px;
                margin: 8px;
                border: 1px solid #ddd;
                border-radius: 8px;
            }}

            button {{
                margin-top: 15px;
                padding: 12px 30px;
                background: #111;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}

            .error {{
                color: red;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>🎁 AdReward</h1>

            <h2>Create Account</h2>

            <p class="error">{error}</p>

            <form method="POST">

                <input
                    type="text"
                    name="username"
                    placeholder="Username"
                    required
                >

                <br>

                <input
                    type="password"
                    name="password"
                    placeholder="Password"
                    required
                >

                <br>

                <button type="submit">
                    Create Account
                </button>

            </form>

            <p>
                Already have an account?
                <a href="/login">Login</a>
            </p>

        </div>

    </body>

    </html>
    """


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect(url_for("home"))

        error = "Invalid username or password."

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>Login</title>

        <style>

            body {{
                font-family: Arial;
                background: #f4f6f8;
                text-align: center;
                padding-top: 80px;
            }}

            .card {{
                background: white;
                width: 350px;
                margin: auto;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }}

            input {{
                width: 90%;
                padding: 12px;
                margin: 8px;
                border: 1px solid #ddd;
                border-radius: 8px;
            }}

            button {{
                margin-top: 15px;
                padding: 12px 30px;
                background: #111;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}

            .error {{
                color: red;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>🎁 AdReward</h1>

            <h2>Login</h2>

            <p class="error">{error}</p>

            <form method="POST">

                <input
                    type="text"
                    name="username"
                    placeholder="Username"
                    required
                >

                <br>

                <input
                    type="password"
                    name="password"
                    placeholder="Password"
                    required
                >

                <br>

                <button type="submit">
                    Login
                </button>

            </form>

            <p>
                Don't have an account?
                <a href="/register">Create one</a>
            </p>

        </div>

    </body>

    </html>
    """


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ================= WATCH AD =================

@app.route("/watch")
def watch():

    if not get_current_user():
        return redirect(url_for("login"))

    return """
    <!DOCTYPE html>

    <html>

    <head>
        <title>Watch Ad</title>
    </head>

    <body style="
        text-align:center;
        padding-top:100px;
        font-family:Arial;
    ">

        <h1>📺 Test Advertisement</h1>

        <p>This is a test advertisement.</p>

        <p>Please wait 5 seconds.</p>

        <div id="timer" style="font-size:50px;">
            5
        </div>

        <button id="claim" disabled>
            Complete the ad first
        </button>

        <script>

            let seconds = 5;

            const timer =
                document.getElementById("timer");

            const claim =
                document.getElementById("claim");

            const countdown = setInterval(() => {{

                seconds--;

                timer.innerText = seconds;

                if (seconds <= 0) {{

                    clearInterval(countdown);

                    timer.innerText = "✓";

                    claim.disabled = false;

                    claim.innerText =
                        "Claim 10 Points";

                }}

            }}, 1000);


            claim.onclick = function() {{

                window.location.href = "/claim";

            }};

        </script>

    </body>

    </html>
    """


# ================= CLAIM =================

@app.route("/claim")
def claim():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    reward = 10

    conn = get_db()

    conn.execute(
        """
        UPDATE users
        SET points = points + ?
        WHERE id = ?
        """,
        (reward, user["id"])
    )

    conn.execute(
        """
        INSERT INTO transactions
        (user_id, points, reason)
        VALUES (?, ?, ?)
        """,
        (
            user["id"],
            reward,
            "Test ad completion"
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ================= HISTORY =================

@app.route("/history")
def history():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    conn = get_db()

    transactions = conn.execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    rows = ""

    for transaction in transactions:

        rows += f"""
        <tr>

            <td>{transaction["points"]}</td>

            <td>{transaction["reason"]}</td>

            <td>{transaction["created_at"]}</td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="3">
                No transactions yet.
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>Transaction History</title>

        <style>

            body {{
                font-family: Arial;
                background: #f4f6f8;
                padding: 50px;
            }}

            .card {{
                background: white;
                max-width: 800px;
                margin: auto;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 25px;
            }}

            th, td {{
                padding: 15px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}

            th {{
                background: #111;
                color: white;
            }}

            .back {{
                display: inline-block;
                margin-top: 25px;
                text-decoration: none;
                color: #111;
                font-weight: bold;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>📜 Transaction History</h1>

            <h2>
                Current Balance:
                {user["points"]} Points
            </h2>

            <table>

                <tr>
                    <th>Points</th>
                    <th>Reason</th>
                    <th>Date</th>
                </tr>

                {rows}

            </table>

            <a class="back" href="/">
                ← Back to Dashboard
            </a>

        </div>

    </body>

    </html>
    """


# ================= START =================

init_db()

if __name__ == "__main__":
    app.run(debug=True)