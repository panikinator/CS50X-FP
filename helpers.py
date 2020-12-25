from flask import redirect, render_template, request, session
from functools import wraps
import random
import string



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def makeRandomString(l):
    random_string = ''.join(random.choices(string.ascii_uppercase +
                             string.digits, k = l))
    return random_string

#takes the database and returns a unique code
def create_code(database):
    already_taken = True
    code = ""
    while already_taken:
        code = makeRandomString(8)
        rows = database.execute("SELECT code FROM classes WHERE code = :code", code = code)
        if not len(rows) > 0:
            already_taken = False
    return code

#checks if the class exists and the user is in the class or not and returns an error message if not in the class
def only_for_joined(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        c = kwargs['class_code']
        rows_of_classes = db.execute("SELECT * FROM classes WHERE code = :code", code = c)
        if len(rows_of_classes) < 1:
            return "class does not exist"
        isNotInClass = not(db.execute("SELECT * FROM students WHERE (class_id = :class_id AND student_id = :user_id)", class_id = rows_of_classes[0]['class_id'], user_id=session["user_id"]))
        if isNotInClass:
            return "you are not in the class"

        return func(*args, **kwargs)
    return decorated_func
    
