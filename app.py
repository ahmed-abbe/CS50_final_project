import os

import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd, get_sum

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

current_date = datetime.datetime.today()
month = current_date.month
day = current_date.day
yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
yesterday = yesterday.day
db.execute("DELETE FROM list WHERE day = ?", yesterday)

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
    """Show portfolio"""
    # make sure the user log in already
    if not session["user_id"]:
        return redirect("/login")
    # Get first 5 from to do list  
    todo = db.execute("SELECT * FROM list WHERE user_id = ? ORDER BY id LIMIT 5;", session["user_id"])
    
    # Get budget  
    income = db.execute("SELECT * FROM income WHERE user_id = ?;", session["user_id"])
    withdraw = db.execute("SELECT * FROM withdraw WHERE user_id = ?;", session["user_id"])
    
    # Get the total of the money
    income_sum = get_sum(income)
    withdraw_sum = get_sum(withdraw)


    return render_template("index.html", todo=todo, income_sum=income_sum, withdraw_sum=(withdraw_sum * -1))


@app.route("/tdlist", methods=["GET", "POST"])
@login_required
def tdlist():
    """To-do list"""
    if request.method == "GET":
        
        table = db.execute("SELECT * FROM list WHERE user_id = ?;", session["user_id"])
        return render_template("tdlist.html", table=table)
    
    todo = request.form.get("todo")
    time = request.form.get("time")

    if not todo: 
        return apology("fill to-do list input")

    if not time:
        return apology("Choose time")

    if len(time) == 5 and time[2] == ":":
        # extract hour and minute values
        try:
            hour = int(time[:2])
            minute = int(time[3:])

        except ValueError:
            return apology("Invalid time")
        # convert hour to 12-hour format
        if hour == 0:
            hour_12 = 12
            period = "AM"
        elif hour > 12:
            hour_12 = hour - 12
            period = "PM"
        else:
            hour_12 = hour
            period = "AM"
        
        # return converted time string
        time = f"{hour_12}:{minute:02d} {period}"
    
    # if input time is already in 12-hour format, return it as it is

    db.execute("INSERT INTO list (user_id, todo, month, day, time) VALUES (?, ?, ?, ?, ?);", session["user_id"], todo, month, day, time)

    return redirect("/tdlist")



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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    """Get budget manager."""
    if request.method == "GET":
        # Get all the info for the table
        income = db.execute("SELECT * FROM income WHERE user_id = ?;", session["user_id"])
        withdraw = db.execute("SELECT * FROM withdraw WHERE user_id = ?;", session["user_id"])
        
        income_sum = get_sum(income)
        withdraw_sum = get_sum(withdraw)
        
        
        return render_template("budget.html", income=income, withdraw=withdraw, income_sum=income_sum, withdraw_sum=(withdraw_sum * -1))

    # If request is post
    item = request.form.get("item")
    typ = request.form.get("type")
    # Make sure they are integers whild converting them
    try:
        qun = int(request.form.get("qun"))

    except ValueError:
        return apology("Quantity Sould be a number")

    try:
        price = float(request.form.get("price"))

    except ValueError:
        return apology("Cost Sould be a number")

    # A list have all the types so we can check the input types is one of them
    types = [
        "income",
        "withdraw"
    ]

    # check the user fill all inputs
    if not item or not qun or not price or not typ:
        return apology("Must fill all inputs")
    
    # Check for positive numbers
    if price < 0.01:
        return apology("Price Sould be Positive")

    if qun < 1:
        return apology("Quantity Sould be Positive")

    # make sure the type the user choose in the types list
    if typ not in types:
        return apology("Sorry invalid type")

    # Insert into income/withdraw the values the user inputs
    if typ == "income":
        db.execute("INSERT INTO income (user_id, item, qun, price) VALUES (?, ?, ?, ?);", session["user_id"], item, qun, price)
    
    else:
        db.execute("INSERT INTO withdraw (user_id, item, qun, price) VALUES (?, ?, ?, ?);", session["user_id"], item, qun, price)

    # redirect to the budget page again
    return redirect("/budget")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    # When the method is post

    # get the name and password
    name = request.form.get("username")
    password = request.form.get("password")
    confirm = request.form.get("confirm")

    # if the user didn't fill all inputs
    if not name or not password or not confirm:
        return apology("Must fill all inputs")

    if password != confirm:
        return apology("Passwords don't match")

    # make sure username dosen't exist in the usernames    
    usernames = db.execute("SELECT * FROM users WHERE username = ?;", name)
    if len(usernames) != 0:
        return apology("username exist")

    # Insert into the table the name and the hashpassword
    hashpassword = generate_password_hash(password)
    db.execute("INSERT INTO users (username, hash) VALUES (?, ?);", name, hashpassword)

    # Make the user session = his/her id the redirct to the main page
    session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?;", name)[0]["id"]
    return redirect("/")


@app.route("/pmanager", methods=["GET", "POST"])
@login_required
def pmanager():
    """Password manager"""
    cards = db.execute("SELECT * FROM passwords WHERE user_id = ?;", session["user_id"])
    if request.method == "GET":
        return render_template("pmanager.html", cards=cards)
    
    # Get the user input
    name = request.form.get("name")
    password = request.form.get("password")
    link = request.form.get("link")

    # Check the user fill all required inputs
    if not name:
        return ("Missing website name")

    if not password:
        return ("Missing website name")

    # If link exist will insert it into the table and redirect to the password manager page
    if link:
        db.execute("INSERT INTO passwords (user_id, name, password, link) VALUES (?, ?, ?, ?);", session["user_id"], name, password, link)
        return redirect("/pmanager")
    
    # if link don't exist won't insert it and will redirect to password manager page
    db.execute("INSERT INTO passwords (user_id, name, password) VALUES (?, ?, ?);", session["user_id"], name, password)
    return redirect("/pmanager")



@app.route("/settings")
@login_required
def settings():
    """Settings page"""

    return render_template("settings.html")
    


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    list_id = request.form.get("id")

    if not list_id:
        return apology("Sorry somthing went wrong")
    
    check = db.execute("DELETE FROM list WHERE user_id = ? AND id = ?;", session["user_id"], list_id)
    if check:
        return redirect("/tdlist")
    else:
        return apology("Sorry somthing went wrong")


@app.route("/bdelete", methods=["POST"])
@login_required
def bdelete():
    """Delete Value from income / withdraw list"""
    item_id = request.form.get("item")

    if not item_id:
        return apology("Choose an item")

    deleted = db.execute("DELETE FROM income WHERE user_id = ? AND id = ?;", session["user_id"], item_id)
    
    if not deleted:
        deleted = db.execute("DELETE FROM withdraw WHERE user_id = ? AND id = ?;", session["user_id"], item_id)
    
    if not deleted:
        return apology("Invalid item")

    return redirect("/budget")


@app.route("/pdelete", methods=["POST"])
@login_required
def pdelete():
    pass_id = request.form.get("id")

    if not pass_id:
        return apology("Sorry Something went wrong")

    deleted = db.execute("DELETE FROM passwords WHERE user_id = ? AND id = ?;", session["user_id"], pass_id)

    if not deleted:
        return apology("Sorry Something went wrong")

    return redirect("/pmanager")




@app.route("/change", methods=["POST"])
@login_required
def change():
    # Get the user old and new password
    old_password = request.form.get("oldpassword")
    new_password = request.form.get("newpassword")
    confirm = request.form.get("confirm")

    # Check if user fill all inputs or not and confirmation = the new password
    if not old_password:
        return apology("Enter Your old password")
    
    if not new_password:
        return apology("Enter your new password")
    
    if not confirm:  
        return apology("Enter your password confirmation")

    if new_password != confirm:  
        return apology("Passwords don't match")

    # To get the old password and make sure it's equal the user input
    password = db.execute("SELECT * FROM users WHERE id = ?;", session["user_id"])


    if not check_password_hash(password[0]["hash"], old_password):
        return apology("Your old password is wrong")

    # hash the password and then update the user password
    hashpassword = generate_password_hash(new_password)

    db.execute("UPDATE users SET hash = ? WHERE id = ?", hashpassword, session["user_id"])

    return redirect("/")



@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    # Get user name and password
    name = request.form.get("name")
    password = request.form.get("password")

    # Get the user id, name, password and check them with the user input
    user = db.execute("SELECT * FROM users WHERE id = ? AND username = ?;", session["user_id"], name)

    if len(user) != 1 or not check_password_hash(user[0]["hash"], password):
        return apology("Invalid name and/or password")

    # if everthing is right delete everthing related to that user then delete him/her from users table
    db.execute("DELETE FROM income WHERE user_id = ?", session["user_id"])

    db.execute("DELETE FROM withdraw WHERE user_id = ?", session["user_id"])
    
    db.execute("DELETE FROM list WHERE user_id = ?", session["user_id"])

    db.execute("DELETE FROM passwords WHERE user_id = ?", session["user_id"])
    
    db.execute("DELETE FROM users WHERE id = ?", session["user_id"])
    
    return redirect("/logout")