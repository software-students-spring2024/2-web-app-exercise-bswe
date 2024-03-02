#!/usr/bin/env python3

import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# from markupsafe import escape
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
load_dotenv()  # take environment variables from .env.

# instantiate the app
app = Flask(__name__)
app.secret_key = 'a_unique_and_secret_key'
# # turn on debugging if in development mode
# if os.getenv("FLASK_ENV", "development") == "development":
#     # turn on debugging, if in development
#     app.debug = True  # debug mnode

# connect to the database
cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the database

# the following try/except block is a way to verify that the database connection is alive (or not)
try:
    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" *", "Connected to MongoDB!")  # if we get here, the connection worked!
except Exception as e:
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug

# set up the routes
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.users.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            return redirect(url_for('home'))
        else:
            pass
    return render_template('login.html')


@app.route("/authenticate", methods=["POST"])
def authenticate():
    username = request.form.get("username")
    password = request.form.get("password")
    user = db.users.find_one({"username": username})

    if user and check_password_hash(user["password"], password):
        return redirect(url_for("home"))
    else:
        return "Invalid login"

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    email = request.form.get("email")
    phone = request.form.get("phone")
    venmo = request.form.get("venmo")

    user_exists = db.users.find_one({"username": username})
    
    if user_exists:
        return "User already exists"

    hashed_password = generate_password_hash(password)

    result = db.users.insert_one({
        "username": username,
        "password": hashed_password,
        "email": email,
        "phone": phone,
        "venmo": venmo
    })
    
    # Check if the user was successfully inserted
    if result.inserted_id:
        session['user_id'] = str(result.inserted_id)
        return redirect(url_for("login"))
    else:
        return "Registration failed", 400
    
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.users.find_one({"_id": ObjectId(user_id)})
    editing_field = request.args.get('edit')

    if request.method == 'POST':
        # Handling the save operation
        if request.form.get('save'):
            field_to_update = request.form['save']
            new_value = request.form[field_to_update]
            # Add conditional for password hashing
            if field_to_update == 'password':
                new_value = generate_password_hash(new_value)
            db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {field_to_update: new_value}})
            flash(f'{field_to_update.capitalize()} updated successfully.')
            return redirect(url_for('settings'))
        else:
            pass

    return render_template('settings.html', user=user, editing_field=editing_field)

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/home")
def home():
    return render_template("create_receipt.html")

@app.route("/spin-wheel")
def spin_wheel():
    return "Spin Wheel Page"

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/history")
def history():
    # Your logic to fetch any data if necessary
    return render_template("history.html")

# route to handle any errors
@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # use the PORT environment variable, or default to 5000
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")

    # import logging
    # logging.basicConfig(filename='/home/ak8257/error.log',level=logging.DEBUG)
    app.run(port=FLASK_PORT)
