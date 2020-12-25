#importing all the needed libraries here
from flask import Flask, render_template, session, redirect, request
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
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
            return render_template("signup.html", error="username", password=password, re_password=re_password)
        if not password:
            return render_template("signup.html", error="password", username=name, re_password=re_password)
        if not re_password:
            return render_template("signup.html", error="re_password", username=name, password=password, re_password=re_password)
        
        username = name.lower()
        row = not db.execute("SELECT * FROM users WHERE username = :username",username = username)

        if not row:
            return render_template("signup.html", error="nameAlreadyTaken", username=name, password=password, re_password=re_password)

        if password != re_password:
            return render_template("signup.html", error="mismatch", username=name, password=password, re_password=re_password)

        db.execute("INSERT INTO users(username, hash) VALUES(:username, :hashed)", username = username, hashed = generate_password_hash(password))
        return redirect("/")
    
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
            return render_template("login.html", error="username", password=request.form.get("password"))

        elif not request.form.get("password"):
            return render_template("login.html", error="password", username=request.form.get("username"))

        #querying the database for user info
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        #checking if user exists and password is matching
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", error="invalid", password=request.form.get("password"), username=request.form.get("username"))

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

        #checking if class exists or not
        rows_of_classes = db.execute("SELECT * FROM classes WHERE code = :code", code = classCode)
        if len(rows_of_classes) < 1:
            return "class does not exist" #dis one

        # check if user is already a member of the given class
        alreadyMember = not(db.execute("SELECT * FROM students WHERE (class_id = :class_id AND student_id = :user_id)", class_id = rows_of_classes[0]['class_id'], user_id=session["user_id"]))

        if not alreadyMember:
            return "You are already a member of this class"
        
        # add user to the class
        db.execute("INSERT INTO students(student_id, class_id) VALUES( :user_id, :class_id)", user_id=session["user_id"], class_id = rows_of_classes[0]['class_id'])

        # redirect user to the main page
        return redirect("/")

    # if user requests the form via get
    if request.method == "GET":
        return render_template("join.html")

@app.route("/class/<class_code>")
@login_required
def classes(class_code):
    rows_of_classes = db.execute("SELECT * FROM classes WHERE code = :code", code = class_code)
    if len(rows_of_classes) < 1:
        return "class does not exist" #dis one
    isNotInClass = not(db.execute("SELECT * FROM students WHERE (class_id = :class_id AND student_id = :user_id)", class_id = rows_of_classes[0]['class_id'], user_id=session["user_id"]))
    if isNotInClass:
        return "you are not in the class" #dis one
    
    students = db.execute("SELECT username FROM users JOIN students ON id = students.student_id WHERE class_id = :class_id",class_id = rows_of_classes[0]['class_id'])
    print(students)
    return render_template("viewclass.html", subjects = rows_of_classes[0]['subject_name'], users = students)


#clears the session to logout the user
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return render_template("error.html", name=e.name, code=e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__": #checks if the code is executed directly or called as a module
    Flask.run(app)