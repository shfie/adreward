import os
import hmac
import hashlib
import sqlite3

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template_string
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


app = Flask(__name__)

# Use the production secret from Render.
# The fallback is only for local development.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-only-secret-change-this"
)

DB_NAME = "adreward.db"


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            points REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    con.commit()
    con.close()


# --------------------------------------------------
# HOME / DASHBOARD
# --------------------------------------------------

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    con = get_db()

    user = con.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    con.close()

    if not user:
        session.clear()
        return redirect(url_for("login"))

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>AdReward</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            margin: 0;
            padding: 40px;
        }

        .container {
            max-width: 600px;
            margin: auto;
        }

        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }

        h1 {
            margin-top: 0;
        }

        .points {
            font-size: 35px;
            font-weight: bold;
        }

        a, button {
            display: inline-block;
            padding: 12px 18px;
            margin: 5px 5px 5px 0;
            border-radius: 8px;
            text-decoration: none;
            border: none;
            cursor: pointer;
            background: #111;
            color: white;
        }

        .secondary {
            background: #777;
        }
    </style>
</head>

<body>

<div class="container">

    <div class="card">

        <h1>AdReward</h1>

        <p>
            Welcome, <strong>{{ user["username"] }}</strong>
        </p>

        <p>Your balance:</p>

        <div class="points">
            {{ user["points"] }} points
        </div>

    </div>


    <div class="card">

        <h2>Earn Rewards</h2>

        <p>
            Complete available offers and earn rewards.
        </p>

        <a href="/offers">
            View Offers
        </a>

        <a href="/history" class="secondary">
            Transaction History
        </a>

    </div>


    <div class="card">

        <a href="/logout" class="secondary">
            Logout
        </a>

    </div>

</div>

</body>
</html>
    """, user=user)


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return """
                <h2>Username and password are required.</h2>
                <a href="/register">Go back</a>
            """

        if len(username) < 3:
            return """
                <h2>Username must be at least 3 characters.</h2>
                <a href="/register">Go back</a>
            """

        if len(password) < 6:
            return """
                <h2>Password must be at least 6 characters.</h2>
                <a href="/register">Go back</a>
            """

        hashed_password = generate_password_hash(password)

        con = get_db()

        try:

            cur = con.execute(
                """
                INSERT INTO users (username, password)
                VALUES (?, ?)
                """,
                (username, hashed_password)
            )

            user_id = cur.lastrowid

            con.commit()

        except sqlite3.IntegrityError:

            con.close()

            return """
                <h2>Username already exists.</h2>
                <a href="/register">Try another username</a>
            """

        con.close()

        session["user_id"] = user_id

        return redirect(url_for("home"))

    return """
<!DOCTYPE html>
<html>
<head>
    <title>Register - AdReward</title>

    <style>
        body {
            font-family: Arial;
            background: #f4f6f8;
            padding: 40px;
        }

        .box {
            max-width: 400px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
        }

        input {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            margin: 8px 0;
        }

        button {
            width: 100%;
            padding: 12px;
            background: #111;
            color: white;
            border: none;
            border-radius: 8px;
        }

        a {
            display: block;
            margin-top: 15px;
        }
    </style>
</head>

<body>

<div class="box">

    <h1>Create Account</h1>

    <form method="POST">

        <input
            type="text"
            name="username"
            placeholder="Username"
            required
        >

        <input
            type="password"
            name="password"
            placeholder="Password"
            required
        >

        <button type="submit">
            Register
        </button>

    </form>

    <a href="/login">
        Already have an account? Login
    </a>

</div>

</body>
</html>
    """


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        con = get_db()

        user = con.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        con.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect(url_for("home"))

        return """
            <h2>Invalid username or password.</h2>
            <a href="/login">Try again</a>
        """

    return """
<!DOCTYPE html>
<html>
<head>
    <title>Login - AdReward</title>

    <style>
        body {
            font-family: Arial;
            background: #f4f6f8;
            padding: 40px;
        }

        .box {
            max-width: 400px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
        }

        input {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            margin: 8px 0;
        }

        button {
            width: 100%;
            padding: 12px;
            background: #111;
            color: white;
            border: none;
            border-radius: 8px;
        }

        a {
            display: block;
            margin-top: 15px;
        }
    </style>
</head>

<body>

<div class="box">

    <h1>Login</h1>

    <form method="POST">

        <input
            type="text"
            name="username"
            placeholder="Username"
            required
        >

        <input
            type="password"
            name="password"
            placeholder="Password"
            required
        >

        <button type="submit">
            Login
        </button>

    </form>

    <a href="/register">
        Create an account
    </a>

</div>

</body>
</html>
    """


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# --------------------------------------------------
# OFFERS
# --------------------------------------------------

@app.route("/offers")
def offers():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Offerwall public key will be added later.
    public_key = os.environ.get("OFFERWALL_PUBLIC_KEY")

    if not public_key:

        return """
<!DOCTYPE html>
<html>
<head>
    <title>Offers - AdReward</title>
</head>

<body>

<h1>Offers</h1>

<p>
    The offerwall has not been configured yet.
</p>

<p>
    We will connect Offerwall.GG after the publisher account
    and placement are approved.
</p>

<a href="/">
    Back to Dashboard
</a>

</body>
</html>
        """

    # We will replace this section with the exact
    # Offerwall.GG integration URL after receiving
    # the current placement/public-key details.

    return """
<!DOCTYPE html>
<html>
<head>
    <title>Offers - AdReward</title>
</head>

<body>

<h1>Available Offers</h1>

<p>
    Offerwall integration is ready for configuration.
</p>

<a href="/">
    Back to Dashboard
</a>

</body>
</html>
    """


# --------------------------------------------------
# TEMPORARY TEST REWARD
# --------------------------------------------------

@app.route("/watch")
def watch():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return """
<!DOCTYPE html>
<html>

<head>
    <title>Test Reward</title>

    <script>

        let seconds = 5;

        function countdown() {

            document.getElementById("timer").innerText =
                seconds;

            if (seconds <= 0) {

                document.getElementById("claim")
                    .style.display = "block";

                document.getElementById("timer")
                    .innerText = "Complete";

                return;
            }

            seconds--;

            setTimeout(countdown, 1000);
        }

        window.onload = countdown;

    </script>

</head>

<body>

<h1>Test Advertisement</h1>

<p>
    This is only a development test.
</p>

<p>
    Time remaining:
    <strong id="timer">5</strong>
</p>

<a
    id="claim"
    href="/claim"
    style="display:none;"
>
    Claim 10 Test Points
</a>

</body>

</html>
    """


@app.route("/claim")
def claim():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    con = get_db()

    con.execute(
        """
        UPDATE users
        SET points = points + 10
        WHERE id = ?
        """,
        (user_id,)
    )

    con.execute(
        """
        INSERT INTO transactions
        (user_id, points, reason)
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            10,
            "Development test reward"
        )
    )

    con.commit()
    con.close()

    return redirect(url_for("home"))


# --------------------------------------------------
# TRANSACTION HISTORY
# --------------------------------------------------

@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    con = get_db()

    transactions = con.execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    con.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>

    <title>Transaction History</title>

    <style>

        body {
            font-family: Arial;
            background: #f4f6f8;
            padding: 40px;
        }

        .box {
            max-width: 700px;
            margin: auto;
            background: white;
            padding: 25px;
            border-radius: 15px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }

        a {
            display: inline-block;
            margin-top: 20px;
        }

    </style>

</head>

<body>

<div class="box">

    <h1>Transaction History</h1>

    {% if transactions %}

    <table>

        <tr>
            <th>Points</th>
            <th>Reason</th>
            <th>Date</th>
        </tr>

        {% for transaction in transactions %}

        <tr>

            <td>
                {{ transaction["points"] }}
            </td>

            <td>
                {{ transaction["reason"] }}
            </td>

            <td>
                {{ transaction["created_at"] }}
            </td>

        </tr>

        {% endfor %}

    </table>

    {% else %}

    <p>No transactions yet.</p>

    {% endif %}

    <a href="/">
        Back to Dashboard
    </a>

</div>

</body>

</html>
    """, transactions=transactions)


# --------------------------------------------------
# OFFERWALL SERVER-TO-SERVER CALLBACK
# --------------------------------------------------

@app.route("/offerwall/callback", methods=["GET", "POST"])
def offerwall_callback():

    data = (
        request.args
        if request.method == "GET"
        else request.form
    )

    user_id = data.get("userId", "")
    transaction_id = data.get("transactionId", "")
    amount = data.get("currencyAmount", "")
    signature = data.get("signature", "")
    status = data.get("status", "")
    test = data.get("test", "0")

    secret = os.environ.get("OFFERWALL_SECRET")

    # Secret has not been configured yet.
    if not secret:
        return "Server not configured", 500

    if not user_id or not transaction_id:
        return "BAD REQUEST", 400

    if not signature:
        return "FORBIDDEN", 403

    # --------------------------------------------------
    # IMPORTANT:
    # The exact signature construction must match the
    # current Offerwall.GG documentation.
    #
    # We will verify this against their current
    # callback documentation before enabling production
    # credits.
    # --------------------------------------------------

    message = f"{user_id}:{transaction_id}:{amount}"

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        signature
    ):
        return "FORBIDDEN", 403

    # Provider test callbacks must never create
    # real user rewards.
    if test == "1":
        return "OK", 200

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "BAD AMOUNT", 400

    con = get_db()

    user = con.execute(
        """
        SELECT id
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if not user:

        con.close()

        return "USER NOT FOUND", 404

    # Prevent duplicate callback processing.
    transaction_reason = (
        f"Offerwall:{transaction_id}:{status}"
    )

    existing = con.execute(
        """
        SELECT id
        FROM transactions
        WHERE user_id = ?
        AND reason = ?
        """,
        (
            user_id,
            transaction_reason
        )
    ).fetchone()

    if existing:

        con.close()

        return "OK", 200

    # Temporary conversion:
    # 1 provider currency unit = 1 platform point.
    #
    # We will replace this with the actual
    # owner/user revenue split after confirming
    # the provider's exact payout format.
    points = amount

    con.execute(
        """
        UPDATE users
        SET points = points + ?
        WHERE id = ?
        """,
        (
            points,
            user_id
        )
    )

    con.execute(
        """
        INSERT INTO transactions
        (user_id, points, reason)
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            points,
            transaction_reason
        )
    )

    con.commit()
    con.close()

    return "OK", 200


# --------------------------------------------------
# STARTUP
# --------------------------------------------------

# IMPORTANT:
# Gunicorn imports this file, so database initialization
# must happen outside the __main__ block.
init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )