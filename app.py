#importing all the needed libraries here
from flask import Flask, render_template, session, redirect, request
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required
from cs50 import SQL

from helpers import login_required, create_code, makeRandomString

db = SQL("sqlite:///database.db") #connecting to the sqlite3 database


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
        

        #checking for errors in form fields
        if not name:
            return "Must proivde username" #dis one
        if not password:
            return "Must proivde password" #dis one
        if password != re_password:
            return "Passwords Don't match!" #dis one
        
        name = name.lower()
        row = db.execute("SELECT * FROM users WHERE username = :username",username = name)

        if not row:
            db.execute("INSERT INTO users(username, hash) VALUES(:username, :hashed)", username = name, hashed = generate_password_hash(password))
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
        return redirect("/")
    
    #route if user requests the webpage via GET
    else:
        return render_template("login.html")


@app.route("/")
def index():
    return render_template("index.html")

# route fo creating a new class
@app.route("/createClass", methods=["GET", "POST"])
@login_required
def createClass():

    # if user submits the form via POST
    if request.method == "POST":

        # get values from the form
        className = request.form.get("className")
        subject = request.form.get("subject")

        # check for missing values
        if not className:
            return "Must provide classname"

        if not subject:
            return "Must provide subject"

        # insert new row in classes table
        db.execute("INSERT INTO classes(class_name, subject_name, teacher_id, code) VALUES(:className, :subject, :user_id, :code)", className=className, subject=subject, user_id=session["user_id"], code=create_code(db))

        return redirect("/")

    # if user requests the form via get
    if request.method == "GET":
        return render_template("class.html")


# route for joining a class
@app.route("/join", methods=["GET", "POST"])
@login_required
def join():

    # if user submits the form via get
    if request.method == "POST":

        # get values from the form
        classCode = request.form.get("classCode")

        # check for empty values
        if not classCode:
            return "Must Provide Invite Code"

        # check if user is already a member of the given class
        alreadyMember = not(db.execute("SELECT * FROM students WHERE (class_id = :classCode AND student_id = :user_id)", classCode=classCode, user_id=session["user_id"]))

        if not alreadyMember:
            return "You are already a member of this class"

        # add user to the class
        db.execute("INSERT INTO students(student_id, class_id) VALUES( :user_id, :classCode)", user_id=session["user_id"], classCode=classCode)

        # redirect user to the main page
        return redirect("/")

    # if user requests the form via get
    if request.method == "GET":
        return render_template("join.html")


#clears the session to logout the user
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__": #checks if the code is executed directly or called as a module
    Flask.run(app)