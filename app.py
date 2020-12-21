#importing all the needed libraries here
from flask import Flask, render_template, session, redirect, request
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required
from cs50 import SQL

db = SQL("sqlite:///db.db") #connecting to the sqlite3 database


#configuring the flask app
app = Flask(__name__)
Session(app)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



#TODO: change all the error messages (with #dis one) with something better maybe
@app.route("/signup", methods=["GET", "POST"])
def signup():
    #route if user POSTs a request to submit a form
    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")
        re_password = request.form.get("re-password")
        userType = request.form.get("type")

        #checking for errors in form fields
        if not name:
            return "Must proivde username" #dis one
        if not password:
            return "Must proivde password" #dis one
        if password != re_password:
            return "Passwords Don't match!" #dis one
        print(userType)
        if not userType or (userType != "student" and userType != "teacher"):
            return "User Type Invalid"
        
        name = name.lower()
        row = db.execute("SELECT * FROM users WHERE username = :username",username = name)

        if not row:
            db.execute("INSERT INTO users(username, hash, type) VALUES(:username, :hashed, :userType)", username = name, hashed = generate_password_hash(password), userType = userType)
            return redirect("/")
        else:
            return "username already taken!" #dis one
    
    #route if user requests the webpage via GET
    else:
        return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    #route if user POSTs a request to submit a form
    if request.method == "POST":
        #checking for errors in fields
        if not request.form.get("username"):
            return "must provide username" #dis one

        elif not request.form.get("password"):
            return "must provide password" #dis one

        #querying the database for user info
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        #checking if user exists and password is matching
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return "invalid username and/or password" #dis one

        #setting the session's user id
        session["user_id"] = rows[0]["id"]
        session["type"] = rows[0]["type"]

        #redirecting on the basis of user is teacher or student
        if session["type"] == "student":
            return redirect("/teacher")
        else:
            return redirect("/student")
    
    #route if user requests the webpage via GET
    else:
        return render_template("login.html")


@app.route("/")
@login_required
def index():
    return render_template("index.html")


#TODO: complete the student route
@app.route("/student")
@login_required
def student():
    return "hello student"

#TODO: complete the teacher route
@app.route("/student")
@login_required
def teacher():
    return "hello teacher"



#clears the session to logout the user
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__": #checks if the code is executed directly or called as a module
    Flask.run(app)