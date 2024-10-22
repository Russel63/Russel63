import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # home = request.form.get("home")
    # if home = "home":
    #     message = ""
    # else:
    message = session.get("message", None)
    name = db.execute("SELECT username FROM users WHERE id = ?;", session["user_id"])
    cash = db.execute("SELECT * FROM users WHERE id = ?;", session["user_id"])
    total_cash = cash[0]["cash"]

    pocket = db.execute(
        "SELECT sign, value FROM owners WHERE value > ? AND user_id = ?;",
        0,
        session["user_id"],
    )
    for row in pocket:
        info = lookup(row["sign"])
        row["price"] = info["price"]
        total = row["value"] * info["price"]
        row["total"] = total
        total_cash = total_cash + total

    # pocket =
    return render_template(
        "index.html",
        name=name,
        cash=cash,
        total_cash=total_cash,
        message=message,
        pocket=pocket,
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # get info about company share part
        sign = request.form.get("symbol")
        buy_value = request.form.get("shares")
        if not buy_value.isnumeric():
            return apology("Invalid buy value!", 400)

        info = lookup(sign)
        if not info:
            return apology("Invalid symbol", 400)

        # get data
        byer_id = session["user_id"]
        now = datetime.now()
        time = now.strftime("%Y-%m-%d %H:%M:%S")
        byer = db.execute("SELECT * FROM users WHERE id = ?", byer_id)
        byer_cash = byer[0]["cash"]

        # shares info
        info = lookup(sign)

        # make a deel
        cost = float(buy_value) * info["price"]
        if (byer_cash - cost) >= 0:
            byer_cash -= cost
            db.execute("UPDATE users SET cash = ? WHERE id = ?", byer_cash, byer_id)
            db.execute(
                "INSERT INTO transactions (user_id, sign, value, price, time) VALUES (?, ?, ?, ?, ?);",
                byer_id,
                sign,
                buy_value,
                info["price"],
                time,
            )
            sharevalue = db.execute(
                "SELECT value FROM owners WHERE sign = ? AND user_id = ?;",
                sign,
                byer_id,
            )
            if not sharevalue:
                db.execute(
                    "INSERT INTO owners (sign, user_id, value) VALUES (?, ?, ?)",
                    sign,
                    byer_id,
                    buy_value,
                )
            else:
                new_value = int(sharevalue[0]["value"]) + int(buy_value)
                db.execute(
                    "UPDATE owners SET value = ? WHERE sign = ? AND user_id = ?",
                    new_value,
                    sign,
                    byer_id,
                )

            session["message"] = "Bought!"
            return redirect("/")
        else:
            session["message"] = "Not enough currency"
            return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute(
        "SELECT * FROM transactions WHERE user_id = ?;", session["user_id"]
    )
    session["message"] = ""
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        session["message"] = "Hello " + request.form.get("username") + "!"
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        session["message"] = ""
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        currency = request.form.get("symbol")
        if not currency:
            return apology("Missing symbol", 400)

        info = lookup(currency)
        if not info:
            session["message"] = "symbol not found"
            return apology("Symbol not found", 400)
        else:
            session["message"] = ""
            return render_template("quoted.html", info=info)

    else:
        session["message"] = ""
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # return apology("TODO")
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password1 = request.form.get("password")
        password2 = request.form.get("confirmation")
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            return apology("Repeat your password", 400)

        elif password1 != password2:
            return apology("Passwords not identical", 400)

        # Check username in the data base
        matches = db.execute("SELECT COUNT(*) FROM users WHERE username = ?", username)
        if int(matches[0]["COUNT(*)"]) > 0:
            return apology("Username already exist", 400)

        # hash password
        password_hash = generate_password_hash(password1)

        # Query database to add new user
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)", username, password_hash
        )
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        session["message"] = "successfully registered"
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        session["message"] = ""
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # get info about company share part
        sign = request.form.get("symbol")
        shares = request.form.get("shares")
        value = int(shares)
        if not shares.isnumeric():
            return apology("Invalid sell value!", 400)

        if not sign or len(sign) != 4:
            return apology("Missing symbol", 400)

        info = lookup(sign)

        # get data
        user_id = session["user_id"]
        now = datetime.now()
        time = now.strftime("%Y-%m-%d %H:%M:%S")
        seller = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        share = db.execute(
            "SELECT value FROM owners WHERE sign = ? AND user_id = ?;", sign, user_id
        )
        sharevalue = int(share[0]["value"])
        user_cash = seller[0]["cash"]

        # shares info
        info = lookup(sign)

        # make a deel
        cost = float(value) * info["price"]
        user_cash += cost
        if not sharevalue:
            return apology("Shares was not found!", 400)

        elif sharevalue < value:
            return apology("Not enough share quantity!", 400)

        else:
            db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash, user_id)
            db.execute(
                "INSERT INTO transactions (user_id, sign, value, price, time) VALUES (?, ?, ?, ?, ?);",
                user_id,
                sign,
                -value,
                info["price"],
                time,
            )
            new_value = sharevalue - value
            db.execute(
                "UPDATE owners SET value = ? WHERE sign = ? AND user_id = ?",
                new_value,
                sign,
                user_id,
            )

            session["message"] = "Sold!"
            return redirect("/")

    else:
        pocket = db.execute(
            "SELECT sign FROM owners WHERE value > ? and user_id = ?;",
            0,
            session["user_id"],
        )
        return render_template("sell.html", pocket=pocket)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def setting():
    """Settings of current account"""
    if request.method == "POST":
        user_id = session["user_id"]
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        if not password1:
            message = "New password field is empty"
            return render_template("apology.html", message=message)

        if password1 != password2:
            message = "Not matching passwords"
            return render_template("apology.html", message=message)
        else:
            hash = generate_password_hash(password1)
            db.execute("UPDATE users SET hash = ? WHERE id = ?", hash, user_id)
        session["message"] = "Password successfully changed"
        return redirect("/")

    else:
        return render_template("settings.html")


@app.route("/discard", methods=["GET", "POST"])
@login_required
def discard():
    """Settings of current account"""
    user_id = session["user_id"]
    # if request.method=="POST":
    discard = request.form.get("discard")
    if discard.lower() == "yes" or "y":
        user_cash = 10000
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash, user_id)
        db.execute("UPDATE owners SET value = ? WHERE user_id = ?", 0, user_id)
        session["message"] = "all progress discarded"
        return redirect("/")
    else:
        return render_template("settings.html")
