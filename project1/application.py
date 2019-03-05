import os

from flask import Flask, session, render_template, request, url_for, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def validate_register(username, password, password2):
    """ Function to validate Registration form on the server side """
    if (not username or not password) or not password2:
        return False, "Please fill all fields"
    elif password != password2:
        return False, "Passwords dont match!"
    elif len(password) < 5 or len(password2) < 5:
        return False, "Minimum length of password is 5 chars"
    return True, "Succesfully registered"


def validate_login(username, password):
    """ Validate credential before sending SQL requests """
    message = "Invalid username or password"
    if not username or not password:
        return False, message
    elif len(password) < 5:
        return False, message
    return True, "Welcome back"


@app.route("/", methods=["GET", "POST"])
def index():
    """ Landing Page, If user is logged in, he can search for books.
    Othervise he will be redirected to log in page."""

    if request.method == "POST":
        search = request.form["search"]

        rows = db.execute("""SELECT * FROM books WHERE UPPER(isbn)
                         LIKE :search OR UPPER(title)
                         LIKE :search OR UPPER(author)
                         LIKE :search""",
                          {"search": "%" + search.upper() + "%"}).fetchall()

        return render_template("index.html", user=True, rows=rows)

    else:
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        else:
            return render_template("index.html", user=True)


@app.route("/books/<string:isbn>")
def books(isbn):
    return "Hello " + isbn


@app.route("/register", methods=["GET", "POST"])
def register():
    """ Register User """
    if request.method == "POST":

        valid, message = validate_register(request.form["username"],
                                           request.form["password"],
                                           request.form["password2"])

        if valid:
            username = request.form["username"]
            password = generate_password_hash(request.form["password"],
                                              method='pbkdf2:sha256',
                                              salt_length=8)

            """ Check for if is username already in database,
            If yes, SQLAlchemy throws Integrity Error """
            try:
                user_query = db.execute("""INSERT INTO users (username, password)
                                        VALUES (:username, :password)
                                        RETURNING id""",
                                        {"username": username,
                                         "password": password})
                db.commit()

                user_id = user_query.fetchone()[0]
                session["user_id"] = user_id
                return redirect(url_for("index"))
            except IntegrityError:
                return render_template("register.html",
                                       alert="Username already exists")
        else:
            return render_template("register.html", alert=message)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """ Login user, uses Validation function and query database
    for check users credentials """

    session.clear()

    if request.method == "POST":
        username, password = request.form["username"], request.form["password"]
        valid, message = validate_login(username, password)

        if valid:

            user = db.execute("SELECT * FROM users WHERE username = :username",
                              {"username": username}).fetchone()

            if user:
                # Werukzeug function to safely compare passwords
                if check_password_hash(user[2], password):
                    session["user_id"] = user[0]
                    return redirect(url_for("index"))
                else:
                    # IF the password is invalid
                    return render_template("login.html",
                                           alert="""Invalid username
                                           or password""")

            else:
                # IF the username is invalid
                return render_template("login.html",
                                       alert="Invalid username or password")

        else:
            # IF invalid length or invalid input
            return render_template("login.html", alert=message)
    else:
        # IF GET method
        return render_template("login.html")


@app.route("/logout")
def logout():
    """ Remove user id from session """
    session.clear()
    return redirect(url_for("index"))
