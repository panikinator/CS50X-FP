#importing all the needed libraries here
from flask import Flask, render_template, session, redirect, request, send_file
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.utils import secure_filename
from cs50 import SQL
import helpers
from helpers import login_required, create_code, makeRandomString, only_for_joined, hasAccessToClass, get_current_time, isTeacherOfclass
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
from io import BytesIO

db = SQL("sqlite:///database.db") #connecting to the sqlite3 database
helpers.db = db

#configuring the flask app
app = Flask(__name__)
Session(app)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "QY1MTUM907BSX17NHZKRA3KFGM23QZ"
Session(app)

io = SocketIO(app)

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
        session["username"] = rows[0]["username"]
        return redirect("/home")
    
    #route if user requests the webpage via GET
    else:
        return render_template("login.html")


@app.route("/")
def index():
    return render_template("index.html")


# user's home page where all the classes will be listed
@app.route("/home")
@login_required
def home():
    classes = db.execute("SELECT DISTINCT class_id FROM students WHERE student_id = :user_id", user_id = session['user_id'])
    class_info = []

    for class_ in classes:
        information = db.execute("SELECT class_name, subject_name, code FROM classes WHERE class_id = :class_id", class_id = class_["class_id"])
        class_info.append(information[0])

    return render_template("homepage.html", classes = class_info)


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
            return render_template("class.html", error="className", subject=subject)

        if not subject:
            return render_template("class.html", error="subject", className=className)

        classCode = create_code(db)
        # insert new row in classes table
        db.execute("INSERT INTO classes(class_name, subject_name, teacher_id, code) VALUES(:className, :subject, :user_id, :code)", className=className, subject=subject, user_id=session["user_id"], code=classCode)

        rows_of_classes = db.execute("SELECT * FROM classes WHERE code = :code", code = classCode)

        # inserts the user into class
        db.execute("INSERT INTO students(student_id, class_id) VALUES( :user_id, :class_id)", user_id=session["user_id"], class_id = rows_of_classes[0]['class_id'])


        return redirect("/class/"+classCode)

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
            return render_template("join.html", error="empty")

        #checking if class exists or not
        rows_of_classes = db.execute("SELECT * FROM classes WHERE code = :code", code = classCode)
        if len(rows_of_classes) < 1:
            return render_template("join.html", error="does_not_exist", classCode=classCode) #dis one

        # check if user is already a member of the given class
        alreadyMember = not(db.execute("SELECT * FROM students WHERE (class_id = :class_id AND student_id = :user_id)", class_id = rows_of_classes[0]['class_id'], user_id=session["user_id"]))

        if not alreadyMember:
            return render_template("join.html", error="alreadyMember", classCode=classCode)
        
        # add user to the class
        db.execute("INSERT INTO students(student_id, class_id) VALUES( :user_id, :class_id)", user_id=session["user_id"], class_id = rows_of_classes[0]['class_id'])

        # redirect user to the main page
        return redirect("/class/"+classCode)

    # if user requests the form via get
    if request.method == "GET":
        return render_template("join.html")


# route for leaving a class
@app.route("/leaveClass/<class_code>")
@login_required
@only_for_joined
def leaveClass(class_code):
    # get the class_id from the classes table
    class_id = db.execute("SELECT class_id FROM classes WHERE code = :class_code", class_code = class_code)

    # remove the current user from the class
    db.execute("DELETE FROM students WHERE student_id = :user_id AND class_id = :class_id", user_id = session['user_id'], class_id = class_id[0]['class_id'])

    # redirect user to the home page
    return redirect("/home")

#route for viewing the homepage of the class
@app.route("/class/<class_code>")
@login_required
@only_for_joined #this decorated function checks if the class exists and if the user is in the class
def classes(class_code):
    rows_of_classes = db.execute("SELECT * FROM classes WHERE code = :code", code = class_code)
    
    students = db.execute("SELECT username FROM users JOIN students ON id = students.student_id WHERE class_id = :class_id",class_id = rows_of_classes[0]['class_id'])

    teacher_id = db.execute("SELECT username FROM users WHERE id = :teacher_id", teacher_id = rows_of_classes[0]['teacher_id'])
    
    
    return render_template("viewclass.html", subject_name = rows_of_classes[0]['subject_name'], class_name = rows_of_classes[0]['class_name'], code = rows_of_classes[0]['code'], users = students, teacher_id = teacher_id[0]['username'])

#route to upload documents and stuff
#this route will be restricted to the teacher of that class only
@app.route("/class/<class_code>/upload", methods=["GET", "POST"])
@login_required
@only_for_joined
def upload(class_code):
    if request.method == "POST":
        if not isTeacherOfclass(class_code):
            return render_template("error.html", name = "restricted to teachers")
        if "file" not in request.files:
            return "please provide an appropritae file file"
        File = request.files['file']
        if not File.filename:
            return "please provide an appropritae file file"
        if not request.form.get("comment"):
            comment = " "
        else:
            comment = request.form.get("comment")

        
        Filename = secure_filename(File.filename)
        FileData = File.read()

        db.execute("INSERT INTO files(file_name, time, comment, class_code, file_data) VALUES(:file_name, :time, :comment, :class_code, :file_data)",
                    file_name = Filename, time = get_current_time(), comment = comment, file_data = FileData, class_code = class_code)

        return redirect("/class/" + class_code)
    else:
        if not isTeacherOfclass(class_code):
            return render_template("error.html", name = "restricted to teachers")
        return render_template("upload.html")

@app.route("/class/<class_code>/documents")
@login_required
@only_for_joined
def documents(class_code):
    list_of_files = db.execute("SELECT file_id, file_name, time, comment FROM files WHERE class_code = :class_code", class_code = class_code)
    return render_template("documents.html", files = list_of_files, class_code = class_code)

@app.route("/class/<class_code>/files/<file_id>")
@login_required
@only_for_joined
def media(class_code, file_id):
    
    File = db.execute("SELECT file_name, file_data FROM files WHERE class_code = :class_code AND file_id = :file_id", class_code = class_code, file_id = file_id)[0]
    if not File:
        return "Not Found"
    return send_file(BytesIO(File['file_data']), attachment_filename= File['file_name'])

@app.route("/class/<class_code>/view")
@login_required
@only_for_joined
def view(class_code):
    link = request.args.get('link')
    return render_template("pdf.html", link = link)

@app.route("/class/<class_code>/chat")
@login_required
@only_for_joined
def chat(class_code):
    last_chat_id = db.execute("SELECT MAX(chat_id) FROM chats WHERE of_class_code = :classCode", classCode = class_code)[0]['MAX(chat_id)']
    return render_template("chat.html", theLast = last_chat_id)

#on getting a message the room of the user is identified and then message data is sent to that room
@io.on('message')
def handle_message(data):
    #getting the class code thorugh the URL

    classCode =  str(request.headers['Referer']).split("/")[4]
    message = data['text']
    current_time = get_current_time()

    last_chat_id = db.execute("INSERT INTO chats(of_class_code, sender_id, sender_name, message, time) VALUES(:classCode, :user_id, :username, :message, :time)", classCode=classCode, user_id = session.get('user_id'), username=session.get('username'), message=message, time=current_time)
    io.emit('send-message', {'sender_name' : session.get('username'), 'message' : message, 'time' : current_time, 'chat_id' : last_chat_id}, room=classCode)


#on connection checks if the user has access to the class 
#if user does not have access to class nothing is done
#if user has access, user is joined to the room and a message is also sent to the class
@io.on('connect')
def connect():
    classCode =  str(request.headers['Referer']).split("/")[4]
    print(classCode)
    if not hasAccessToClass(classCode):
        return  

    print("message sent")
    join_room(classCode)
    io.emit('someone-connected', {'sender_name' : session.get('username'), 'message' : session.get('username') + " has joined the chat", 'time' : get_current_time()}, room=classCode)

@io.on('getMore')
def getMore(data):
    classCode =  str(request.headers['Referer']).split("/")[4]
    i = data['totalMessages'] 
    last_chat_id = data['lastID']
    chats = db.execute("SELECT sender_name, message, time, chat_id FROM chats WHERE of_class_code = :classCode AND chat_id <= :last_id ORDER BY chat_id DESC", classCode = classCode, last_id = last_chat_id)
    if len(chats) >= 10:
        chatsToSend = chats[i:i+10]
    else: 
        chatsToSend = chats[i:]

    print(json.dumps(chatsToSend))
    io.emit("giveMore", json.dumps(chatsToSend))
    



@io.on('disconnect')
def disconnect():
    classCode =  str(request.headers['Referer']).split("/")[4]
    leave_room(classCode)



#clears the session to logout the user
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    print(e)
    return render_template("error.html", name=e.name, code=e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__": #checks if the code is executed directly or called as a module
    io.run(app)