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
        session['user_id'] = str(user['_id'])
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

    if user_id:
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
    else:
        return redirect(url_for('login'))

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


@app.route('/delete-contact/<contact_uuid>', methods=['POST'])
def delete_contact(contact_uuid):
    if 'user_id' not in session:
        flash("Please login to continue.", "info")
        return redirect(url_for('login'))

    user_id = session['user_id']
    # Attempt to pull (remove) the contact with the given UUID from the user's contacts array
    result = db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"contacts": {"uuid": contact_uuid}}}
    )

    if result.modified_count > 0:
        flash("Contact deleted successfully.", "success")
    else:
        flash("Failed to delete contact.", "error")

    return redirect(url_for('contacts'))

@app.route("/search_history")
def search_history():
    return render_template("search_history.html")


#route to show all the receipts history with functionality to search a keyword
@app.route("/history")
def history():
    keyword = request.args.get('search', None)
    
    query = {}
    if keyword:
        query = {"name": {"$regex": keyword, "$options": "i"}}
    
    items = db.receipts.find(query)
    items_list = list(items)

    return render_template("search_history.html", items=items_list)


@app.route('/receipt_details/<receipt_id>')
def receipt_details(receipt_id):
    receipt = db.receipts.find_one({"_id": ObjectId(receipt_id)})
    if not receipt:
        return "Receipt not found", 404
    return render_template('receipt_details.html', items=receipt.get('items', []), receipt_id=receipt_id)

#route for adding items to current receipt
@app.route('/add_item/<receipt_id>', methods=['POST'])
def add_item(receipt_id): 
    item_name = request.form.get('item_name')
    price = request.form.get('price', type=float)
    is_appetizer = request.form.get('is_appetizer') == 'on'  # Assuming a checkbox named 'is_appetizer'
    diner_name = request.form.get('diner_name') if not is_appetizer else None

    person_paying = db.users.find_one({"name": diner_name})['_id'] if diner_name else None

    item_entry = {
        "item_name": item_name,
        "price": price,
        "is_appetizer": is_appetizer,
        "person_paying": person_paying
    }

    db.receipts.update_one({'_id': ObjectId(receipt_id)}, {'$push': {'items': item_entry}})
    return redirect(url_for("receipt_details", receipt_id=receipt_id))
    
@app.route('/new_receipt', methods=['POST'])
def new_receipt():
    # Extracting data from the form
    receipt_name = request.form.get('receipt_name', type=str)  # Ensure this matches your form
    num_of_people = request.form.get('num_of_people', type=int)
    selected_contact_ids = request.form.getlist('selected_contacts')  # Assumes multi-select input for contacts
    subtotal = request.form.get('subtotal', type=float)
    tax = request.form.get('tax', type=float)
    tip = request.form.get('tip', type=float)
    
    # Fetch the selected contacts based on their IDs
    selected_contacts = db.users.find({"_id": {"$in": [ObjectId(id) for id in selected_contact_ids]}})

    # Validate there are enough contacts
    if selected_contacts.count() < num_of_people:
        flash(f"Not enough contacts selected. You selected {selected_contacts.count()}, but specified splitting with {num_of_people} people.", 'error')
        return redirect(url_for('new_receipt'))
    
    # Validate received data
    if not all([receipt_name, num_of_people, tax, tip, subtotal]):
        flash("Missing or invalid fields in form data", 'error')
        return redirect(url_for('new_receipt'))

    # Calculate total
    total = subtotal + (tax + tip) / 100 * subtotal

    # Prepare the document with selected contacts included
    receipt_data = {
        "receipt_name": receipt_name,
        "num_of_people": num_of_people,
        "selected_contacts": selected_contact_ids,  # Store the IDs of selected contacts
        "total": total,
        "tax": tax,
        "tip": tip,
        "subtotal": subtotal
    }

    # Insert the new receipt into the MongoDB collection
    result = db.receipts.insert_one(receipt_data)
    
    if result.inserted_id:
        flash("Receipt created successfully.", 'success')
    else:
        flash("Error creating the receipt.", 'error')

    return redirect(url_for('receipt_details', receipt_id=str(result.inserted_id)))



@app.route('/calculate_bill/<receipt_id>')
def calculate_bill(receipt_id):
    receipt = db.receipts.find_one({"_id": ObjectId(receipt_id)})
    if not receipt:
        return "Receipt not found", 404

    num_of_people = receipt['num_of_people']
    items = receipt['items']

    # Calculate total cost of appetizers and split equally
    appetizer_total = sum(item['price'] for item in items if item['is_appetizer'])
    appetizer_split = appetizer_total / num_of_people if num_of_people else 0

    # Initialize a dictionary to hold each diner's total, starting with the appetizer split
    diner_totals = {}

    # Calculate each diner's total for non-appetizer items
    for item in items:
        if not item['is_appetizer']:
            diner_id = item.get('person_paying')  # Assuming this is an ObjectId
            if diner_id:
                if diner_id not in diner_totals:
                    diner_totals[diner_id] = appetizer_split
                diner_totals[diner_id] += item['price']
    
    # Update each diner's balance owed in the users collection
    for diner_id, total in diner_totals.items():
        db.users.update_one({'_id': diner_id}, {'$inc': {'balance_owed': total}})

    return jsonify({str(diner_id): total for diner_id, total in diner_totals.items()})



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
