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