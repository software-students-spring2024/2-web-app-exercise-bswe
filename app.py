#!/usr/bin/env python3

import os
import datetime
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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
    return render_template("new_receipt.html")

@app.route("/spin-wheel")
def spin_wheel():
    return "Spin Wheel Page"

@app.route("/contacts", methods=['GET'])
def contacts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_record = db.users.find_one({"_id": ObjectId(session['user_id'])})
    contact_list = user_record.get("contacts", [])
    return render_template("contacts.html", contactList=contact_list)

@app.route("/create-contact", methods=['GET', 'POST'])
def create_contact():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_contact = {
            "uuid": str(uuid.uuid4()),
            "name": request.form.get("name"),
            "phone": request.form.get("phone"),
            "venmo": request.form.get("venmo"),
            "balance_owed": request.form.get("balance_owed")
        }
        db.users.update_one({"_id": ObjectId(session['user_id'])}, {"$push": {"contacts": new_contact}})
        return redirect(url_for('contacts'))
    
    return render_template("create_contact.html")

@app.route('/edit-contact/<contact_uuid>', methods=['GET', 'POST'])
def edit_contact(contact_uuid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        updated_contact = {
            "contacts.$.name": request.form.get("name"),
            "contacts.$.phone": request.form.get("phone"),
            "contacts.$.venmo": request.form.get("venmo"),
            "contacts.$.balance_owed": request.form.get("balance_owed")
        }
        db.users.update_one({"_id": ObjectId(session['user_id']), "contacts.uuid": contact_uuid}, {"$set": updated_contact})
        return redirect(url_for('contacts'))
    
    user_record = db.users.find_one({"_id": ObjectId(session['user_id']), "contacts.uuid": contact_uuid}, {"contacts.$": 1})
    contact = user_record["contacts"][0] if user_record and "contacts" in user_record else None
    if not contact:
        flash("Contact not found.")
        return redirect(url_for('contacts'))
    
    return render_template("edit_contact.html", contact=contact, contact_uuid=contact_uuid)

@app.route('/update-contact/<contact_uuid>', methods=['POST'])
def update_contact(contact_uuid):
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please login to continue.', 'info')
        return redirect(url_for('login'))

    # Retrieve the current user's ID from session
    user_id = session.get('user_id')
    
    # Extract the updated contact information from the form
    updated_name = request.form.get('name')
    updated_phone = request.form.get('phone')
    updated_venmo = request.form.get('venmo')
    updated_balance_owed = request.form.get('balance_owed')

    # Build the update query to match the nested contact by uuid
    update_query = {
        "_id": ObjectId(user_id),
        "contacts.uuid": contact_uuid
    }

    # Build the update operation to set the new values
    update_operation = {
        "$set": {
            "contacts.$.name": updated_name,
            "contacts.$.phone": updated_phone,
            "contacts.$.venmo": updated_venmo,
            "contacts.$.balance_owed": updated_balance_owed
        }
    }

    # Perform the update operation
    result = db.users.update_one(update_query, update_operation)

    # Check if the update was successful
    if result.modified_count == 1:
        flash('Contact updated successfully!', 'success')
    else:
        flash('No changes made to the contact.', 'info')

    # Redirect back to the contacts list
    return redirect(url_for('contacts'))



#route to show all the receipts history with functionality to search a keyword
@app.route("/history")
def history():
    keyword = request.args.get('search', None)
    
    query = {}
    if keyword:
        query = {"name": {"$regex": keyword, "$options": "i"}}
    
    items = db.find(query)
    items_list = list(items)

    return jsonify([item for item in items_list])


@app.route('/receipt/<receipt_id>')
def current_receipt(receipt_id):
    receipt = db.receipts.find_one({"_id": ObjectId(receipt_id)})
    if not receipt:
        return "Receipt not found", 404
    return render_template('current_receipt.html', items=receipt.get('items', []), receipt_id=receipt_id)

#route for adding items to current receipt
@app.route('/add_item/<receipt_id>', methods = ['POST'])
def add_item(receipt_id): 
    item_name = request.form.get('item_name', type= object)
    price = request.form.get('price', type = float)
    item_entry = {
        "item_name": item_name,
        "price": float(price), 
    }

    db.receipts.update_one({'_id': receipt_id}, {'$push': {'ingredients': item_entry}})
    return redirect(url_for:('current_receipt'))
    
@app.route('/new_receipt', methods=['POST'])
def new_receipt():
    # Extracting data from the form
    num_of_people = request.form.get('num_of_people', type=int)
    tax = request.form.get('tax%', type=float)
    tip = request.form.get('tip%', type=float)
    subtotal = request.form.get('subtotal', type=float)
    
    # Validate received data
    if not all([num_of_people, tax, tip, subtotal]):
        return "Missing or invalid fields in form data", 400

    # Calculate total
    total = 1+(tax+tip)/100 * subtotal

    # Prepare the document
    receipt_data = {
        "num_of_people": num_of_people,
        "total": total,
        "tax": tax,
        "tip": tip,
        "subtotal": subtotal
    }

    # Insert the new receipt into the MongoDB collection
    result = db.receipts.insert_one(receipt_data)
    
    # Return a success message with the ID of the new receipt document
    return f"Receipt added successfully with ID: {result.inserted_id}", 201




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
