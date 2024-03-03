#!/usr/bin/env python3

import os
import datetime
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# from markupsafe import escape
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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

@app.route("/contacts", methods=['GET', 'POST'])
def contacts():
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return redirect(url_for('login'))

    userRecord = db.users.find_one({"_id": ObjectId(user_id)})

    contactList = userRecord.get("contacts")

    if contactList is None:
        pass

    return render_template("contact.html", contactList=contactList)

@app.route("/create-contact", methods=['GET', 'POST'])
def create_contact():

    user_id = session.get('user_id')
    if 'user_id' not in session:
        return redirect(url_for('login'))

    criteria = {"_id": ObjectId(user_id)}

    defaultContact = {
        "uuid": str(uuid.uuid1()),
        "name": "Grace Hopper",
        "phone": "402-555-1212",
        "venmo": "rdmlhopper@example.com",
        "balance_owed": "1000000.00"
    }

    # Use $push with dot notation to specify the path to the nested list
    update_operation = {"$push": {"contacts": defaultContact}}

    # Perform the update
    result = db.users.update_one(criteria, update_operation, upsert=True)
    # Check if the user was successfully inserted
    if not result:
        return "Registration failed", 400
    
    # Assuming you want to display the contact immediately after creating it
    logger.info(defaultContact['uuid'])
    contact_record = db.users.find_one({"uuid": defaultContact['uuid']})

    logger.info(contact_record['uuid'])
    return render_template('edit_contact.html', contact=contact_record)

@app.route('/edit-contact/<contact_uuid>', methods=['GET'])
def edit_contact(contact_uuid):
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to login first.', 'error')
        return redirect(url_for('login'))
    
    user_record = db.users.find_one({"_id": ObjectId(user_id)})
    if not user_record or "contacts" not in user_record:
        flash('No contacts found.', 'error')
        return redirect(url_for('contacts'))
    
    # Find the specific contact by uuid
    contact_record = next((item for item in user_record["contacts"] if item["uuid"] == contact_uuid), None)
    
    if not contact_record:
        flash('Contact not found.', 'error')
        return redirect(url_for('contacts'))
    
    # Assuming contact_record is the dictionary you want to edit
    return render_template('edit_contact.html', contact=contact_record)

@app.route('/update-contact/<contact_uuid>', methods=['POST'])
def update_contact(contact_uuid):
    # Retrieve updated information from the form data
    updated_name = request.form.get('name')
    updated_phone = request.form.get('phone')
    updated_venmo = request.form.get('venmo')
    updated_balance_owed = request.form.get('balance_owed')

    # Validate the input (optional, but recommended step)
    # if not updated_name or not updated_phone or not updated_venmo or not updated_balance_owed:
        # Handle the case where one of the fields is missing
    #    flash('All fields are required!', 'error')
    #    return redirect(url_for('edit_contact', contact_id=contact_id))

    # Update the contact in the database
    
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return redirect(url_for('login'))

    criteria = {"_id": ObjectId(user_id)}

    updatedContact = {
        "uuid": contact_uuid,
        "name": updated_name,
        "phone": updated_phone,
        "venmo": updated_venmo,
        "balance_owed": updated_balance_owed
    }

    # Use $push with dot notation to specify the path to the nested list
    update_operation = {"$push": {"contacts": updatedContact}}

    # Perform the update
    result = db.users.update_one(criteria, update_operation)
    # Check if the user was successfully inserted
    if not result:
        return "Registration failed", 400

    if result.modified_count == 0:
        # Handle the case where the contact wasn't updated for some reason
        flash('No changes made to the contact.', 'info')
    else:
        flash('Contact updated successfully!', 'success')

    # Redirect back to the contacts list or the edit page, depending on your flow
    return redirect(url_for('contacts'))


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
