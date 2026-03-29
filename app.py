from flask import Flask, render_template,send_file,abort, request, redirect, url_for, flash,session
from werkzeug.utils import secure_filename
import os
import re
import uuid
import yagmail
import random, string
import google.generativeai as genai
from flask import jsonify
from datetime import datetime
import uuid
# Firebase Admin SDK

import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
import uuid, json
from google.generativeai import configure, GenerativeModel
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import pandas as pd
import os
import numpy as np
import joblib
import warnings
import sys
import math
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO, StringIO
import json
import csv
import base64
import numpy as np
import pickle
from super_admin_routes import super_admin_bp
# Suppress warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
app.register_blueprint(super_admin_bp)
app.secret_key = "007219"  # CHANGE THIS
# Firebase setup

firebase_json = os.environ.get("FIREBASE_KEY")

if firebase_json:
    firebase_dict = json.loads(firebase_json)
    cred = credentials.Certificate(firebase_dict)

    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://sahara-app-d97e0-default-rtdb.firebaseio.com/',
        'storageBucket': 'your-bucket-name.appspot.com'
    })

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)  # Enable CORS for all routes
app.config['SECRET_KEY'] = 'multi-dataset-assessment-secret-key-2024'

# Home Route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/con')
def con():
    return render_template('con.html')

@app.route('/rom')
def rom():
    return render_template('rom.html')


@app.route('/user_signup')
def user():
    return render_template('signup.html')

@app.route('/mod')
def mod():
    return render_template('mod.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        def g(name, default=""):
            return request.form.get(name, default).strip()

        # --------- FIELDS ----------
        name = g('name')
        father_name = g('father_name')
        marital_status = g('marital_status')
        husband_name = g('husband_name') if marital_status == 'yes' else ''
        children = g('children')
        children_count = g('children_count') if children == 'yes' else ''
        gender = g('gender')
        age = g('age')
        cnic = g('cnic')
        current_location = g('current_location')
        description = g('description')
        contact_number = g('contact_number')
        email = g('email')
        username = g('username')
        address = g('address')
        counseling = request.form.getlist('counseling')
        categories = request.form.getlist('categories')

        # --------- VALIDATIONS ----------
        if not re.fullmatch(r"[A-Za-z\s]+", name):
            flash("Name must contain only alphabets.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"[A-Za-z\s]+", father_name):
            flash("Father Name must contain only alphabets.")
            return redirect(url_for('signup'))

        if not age.isdigit() or int(age) < 10:
            flash("Age must be a number and at least 10.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"\d{13}", cnic or ""):
            flash("CNIC must be exactly 13 digits.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email or ""):
            flash("Invalid email format.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"\d{11}", contact_number or ""):
            flash("Contact number must be exactly 11 digits.")
            return redirect(url_for('signup'))

        # --------- DUPLICATE CHECK ----------
        ref = db.reference('users')
        users_data = ref.get() or {}

        for uid_existing, user in users_data.items():
            if user.get('cnic') == cnic:
                flash("CNIC already registered!")
                return redirect(url_for('signup'))
            if user.get('email') == email:
                flash("Email already registered!")
                return redirect(url_for('signup'))
            if user.get('contact_number') == contact_number:
                flash("Phonenumber already registered!")
                return redirect(url_for('signup'))

        # --------- FILE UPLOADS ----------
        profile_img = request.files.get('profile_image')
        legal_docs = request.files.get('legal_docs')
        cnic_front = request.files.get('cnic_front')
        cnic_back = request.files.get('cnic_back')

        uid = str(uuid.uuid4())

        profile_img_path = ""
        legal_doc_path = ""
        cnic_front_path = ""
        cnic_back_path = ""

        # Root: D:\...\SahaaraX\static\uploads
        upload_root = os.path.join(app.root_path, "static", "uploads")
        os.makedirs(upload_root, exist_ok=True)

        # --- Profile image (required) ---
        if profile_img and profile_img.filename:
            safe_name = secure_filename(profile_img.filename)
            filename_profile = f"{uid}_profile_{safe_name}"
            full_path_profile = os.path.join(upload_root, filename_profile)
            profile_img.save(full_path_profile)

            # DB path (relative to static)
            profile_img_path = f"uploads/{filename_profile}"
        else:
            flash("Profile image is required.")
            return redirect(url_for('signup'))

        # --- Legal docs (optional) ---
        if legal_docs and legal_docs.filename:
            safe_name = secure_filename(legal_docs.filename)
            filename_legal = f"{uid}_legal_{safe_name}"
            full_path_legal = os.path.join(upload_root, filename_legal)
            legal_docs.save(full_path_legal)

            legal_doc_path = f"uploads/{filename_legal}"

        # --- CNIC FRONT (required) ---
        if not cnic_front or not cnic_front.filename:
            flash("Please upload the FRONT side of your National ID.")
            return redirect(url_for('signup'))

        safe_front = secure_filename(cnic_front.filename)
        filename_front = f"{uid}_cnic_front_{safe_front}"
        full_path_front = os.path.join(upload_root, filename_front)
        cnic_front.save(full_path_front)
        cnic_front_path = f"uploads/{filename_front}"

        # --- CNIC BACK (required) ---
        if not cnic_back or not cnic_back.filename:
            flash("Please upload the BACK side of your National ID.")
            return redirect(url_for('signup'))

        safe_back = secure_filename(cnic_back.filename)
        filename_back = f"{uid}_cnic_back_{safe_back}"
        full_path_back = os.path.join(upload_root, filename_back)
        cnic_back.save(full_path_back)
        cnic_back_path = f"uploads/{filename_back}"

        # --------- CHILDREN DETAILS ----------
        children_details = []
        if children == 'yes':
            names = request.form.getlist('child_name[]')
            relations = request.form.getlist('child_relation[]')
            ages = request.form.getlist('child_age[]')
            for nm, rel, ag in zip(names, relations, ages):
                if nm.strip():
                    if not ag.isdigit() or int(ag) >= 8:
                        flash("Each child's age must be less than 8.")
                        return redirect(url_for('signup'))
                    children_details.append({
                        'name': nm,
                        'relation': rel,
                        'age': ag
                    })

        # --------- SAVE TO FIREBASE ----------
        ref.child(uid).set({
            'name': name,
            'father_name': father_name,
            'marital_status': marital_status,
            'husband_name': husband_name,
            'legal_doc_path': legal_doc_path,
            'children': children,
            'children_count': children_count,
            'children_details': children_details,
            'gender': gender,
            'age': age,
            'cnic': cnic,
            'current_location': current_location,
            'description': description,
            'categories': categories,
            'counseling': counseling,
            'contact_number': contact_number,
            'email': email,
            'username': username,
            'address': address,
            'profile_image_path': profile_img_path,
            'cnic_front_path': cnic_front_path,
            'cnic_back_path': cnic_back_path,
            'status': 'Unapproved'
        })

        flash("Signup successful! Your data is pending approval.")
        return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        ref = db.reference("admin")
        admin_data = ref.get()
        if admin_data:
            # Single admin check
            if email == admin_data.get("email"):
                if password == admin_data.get("password"):
                    session["admin"] = email
                    flash("Login successful!", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Invalid password!", "error")
                    return redirect(url_for("admin_login"))
            else:
                flash("Admin email not found!", "error")
                return redirect(url_for("admin_login"))
        else:
            flash("No admin data found in Firebase!", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")



# Email Setup
yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")

def generate_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/view_users")
def view_users():
    # Get filters from query params
    filter_status = request.args.get("status", "").strip()
    filter_category = request.args.get("category", "").strip()
    filter_children = request.args.get("children", "").strip()
    search_username = request.args.get("username", "").strip().lower()
    search_email = request.args.get("email", "").strip().lower()

    ref = db.reference("users")
    users = ref.get() or {}

    approved = sum(1 for u in users.values() if u.get("status") == "Approved")
    rejected = sum(1 for u in users.values() if u.get("status") == "Rejected")
    unapproved = sum(1 for u in users.values() if u.get("status") == "Unapproved")

    pending_users = {uid: u for uid, u in users.items() if u.get("status") == "Unapproved"}

    filtered_users = {}

    for user_id, user in users.items():
        match = True

        # ✅ Status filter
        if filter_status and user.get("status", "").lower() != filter_status.lower():
            match = False

        # ✅ Category filter
        if filter_category and filter_category != "All":
            cats = user.get("categories", [])
            if isinstance(cats, str):  # convert to list if single string
                cats = [cats]
            cats = [c.lower() for c in cats]
            if filter_category.lower() not in cats:
                match = False

        # ✅ Children filter
        if filter_children == "with" and user.get("children", "").lower() != "yes":
            match = False
        if filter_children == "without" and user.get("children", "").lower() != "no":
            match = False

        # ✅ Username search
        if search_username and search_username not in user.get("username", "").lower():
            match = False

        # ✅ Email search
        if search_email and search_email not in user.get("email", "").lower():
            match = False

        if match:
            filtered_users[user_id] = user

    return render_template(
        "view_users.html",
        users=filtered_users,
        filter_status=filter_status,
        filter_category=filter_category,
        approved=approved,
        rejected=rejected,
        unapproved=unapproved,
        pending_users=pending_users,
        filter_children=filter_children
    )



# ---------------- APPROVE USER ----------------
@app.route("/approve_user/<user_id>")
def approve_user(user_id):
    ref = db.reference("users").child(user_id)
    user = ref.get()
    if not user:
        flash("User not found", "error")
        return redirect(url_for("view_users"))

    password = generate_password()
    ref.update({"status": "Approved", "password": password})

    subject = "SahaaraX Account Approved"
    body = f"""
    Dear {user['name']},

    Your account has been approved ✅

    Login credentials:
    Email: {user['email']}
    Password: {password}

    Regards,
    SahaaraX Team
    """
    yag.send(user["email"], subject, body)
    flash(f"User {user['name']} approved!", "success")
    return redirect(url_for("view_users"))


# ---------------- REJECT USER ----------------
@app.route("/reject_user/<user_id>")
def reject_user(user_id):
    ref = db.reference("users").child(user_id)
    user = ref.get()
    if not user:
        flash("User not found", "error")
        return redirect(url_for("view_users"))

    ref.update({"status": "Rejected"})

    subject = "SahaaraX Account Rejected"
    body = f"""
    Dear {user['name']},

    Unfortunately, your account has been rejected ❌
    Please contact our support team for more details.

    Regards,
    SahaaraX Team
    """
    yag.send(user["email"], subject, body)
    flash(f"User {user['name']} rejected!", "danger")
    return redirect(url_for("view_users"))


@app.route('/delete_user/<user_id>')
def delete_user(user_id):
    ref = db.reference('users').child(user_id)
    user = ref.get()
    if not user:
        flash("User not found", "error")
        return redirect(url_for('view_users'))

    ref.delete()
    flash(f"User {user['name']} has been permanently deleted.", "success")
    return redirect(url_for('view_users'))




@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("admin_login"))

    ref = db.reference("users")
    users = ref.get() or {}



    ref_room = db.reference("rooms")
    rooms = ref_room.get() or {}

    total_rooms = len(rooms)

    # Total beds (sum of bed_count from each room)
    total_beds = sum(int(room.get("bed_count", 0)) for room in rooms.values())
    print(total_beds)

    approved = sum(1 for u in users.values() if u.get("status") == "Approved")
    rejected = sum(1 for u in users.values() if u.get("status") == "Rejected")
    unapproved = sum(1 for u in users.values() if u.get("status") == "Unapproved")
    # ✅ Only approved users
    approved_users = {
        uid: u for uid, u in users.items()
        if u.get("status", "").lower() == "approved"
    }
    # ✅ Collect unapproved users
    pending_users = {uid: u for uid, u in users.items() if u.get("status") == "Unapproved"}
    # ✅ Stats counters
    stats = {
        "Domestic Violence": 0,
        "Sexual Abuse Support": 0,
        "Psychological Support": 0,
        "Self Awareness": 0,
        "Health Awareness": 0,
    }

    for uid, user in approved_users.items():
        counseling = user.get("counseling", [])
        if isinstance(counseling, str):
            counseling = [counseling]

        # Count for stats
        for c in counseling:
            if c in stats:
                stats[c] += 1
    return render_template(
        "dashboard.html",
        admin_email=session["admin"],
        approved=approved,
        rejected=rejected,
        unapproved=unapproved,
        pending_users=pending_users,
        total_beds=total_beds,
        stats=stats,
        total_rooms=total_rooms
    )







# ✅ FLOOR: ADD + LIST
@app.route("/add_floor", methods=["GET", "POST"])
def add_floor():
    floors_ref = db.reference("floors")

    if request.method == "POST":
        floor_name = (request.form.get("floor") or "").strip()

        if not floor_name:
            flash("Floor name is required.", "danger")
            return redirect(url_for("add_floor"))

        floors = floors_ref.get() or {}

        # Duplicate floor check (case-insensitive)
        for fid, f in floors.items():
            if isinstance(f, dict):
                existing_name = str(f.get("name") or f.get("number") or "").strip()
            else:
                existing_name = str(f or "").strip()

            if existing_name.lower() == floor_name.lower():
                flash("This floor already exists.", "danger")
                return redirect(url_for("add_floor"))

        # Save new floor
        floor_id = str(uuid.uuid4())
        floors_ref.child(floor_id).set({
            "name": floor_name
        })

        flash("Floor added successfully!", "success")
        return redirect(url_for("add_floor"))

    # GET → list floors
    floors_data = floors_ref.get() or {}

    floors_list = []
    for fid, f in floors_data.items():
        if isinstance(f, dict):
            name = f.get("name") or f.get("number") or ""
        else:
            name = f or ""
        name = str(name).strip()
        if name:
            floors_list.append({"id": fid, "name": name})

    floors_list = sorted(floors_list, key=lambda x: x["name"].lower())

    return render_template("add_floor.html", floors=floors_list)


# ✅ FLOOR: EDIT
@app.route("/edit_floor/<floor_id>", methods=["GET", "POST"])
def edit_floor(floor_id):
    floors_ref = db.reference("floors")
    floor_data = floors_ref.child(floor_id).get()

    if not floor_data:
        flash("Floor not found.", "danger")
        return redirect(url_for("add_floor"))

    # Old name
    if isinstance(floor_data, dict):
        old_name = str(floor_data.get("name") or floor_data.get("number") or "").strip()
    else:
        old_name = str(floor_data or "").strip()

    if request.method == "POST":
        new_name = (request.form.get("floor_name") or "").strip()

        if not new_name:
            flash("New floor name is required.", "danger")
            return redirect(url_for("edit_floor", floor_id=floor_id))

        floors = floors_ref.get() or {}

        # Duplicate check (except current floor)
        for fid, f in floors.items():
            if fid == floor_id:
                continue

            if isinstance(f, dict):
                existing_name = str(f.get("name") or f.get("number") or "").strip()
            else:
                existing_name = str(f or "").strip()

            if existing_name.lower() == new_name.lower():
                flash("This name is already used by another floor.", "danger")
                return redirect(url_for("edit_floor", floor_id=floor_id))

        # Update floor name
        floors_ref.child(floor_id).update({"name": new_name})

        # Update rooms that use this floor name
        rooms_ref = db.reference("rooms")
        rooms = rooms_ref.get() or {}

        for rid, room in rooms.items():
            room_floor = str(room.get("floor") or "").strip()
            if room_floor.lower() == old_name.lower():
                rooms_ref.child(rid).update({"floor": new_name})

        flash("Floor updated successfully. Linked rooms were updated too.", "success")
        return redirect(url_for("add_floor"))

    # GET
    return render_template("edit_floor.html", floor_name=old_name, floor_id=floor_id)


# ✅ FLOOR: DELETE
@app.route("/delete_floor/<floor_id>", methods=["POST"])
def delete_floor(floor_id):
    floors_ref = db.reference("floors")
    floor_data = floors_ref.child(floor_id).get()

    if not floor_data:
        flash("This floor is already deleted or does not exist.", "warning")
        return redirect(url_for("add_floor"))

    if isinstance(floor_data, dict):
        floor_name = str(floor_data.get("name") or floor_data.get("number") or "").strip()
    else:
        floor_name = str(floor_data or "").strip()

    rooms_ref = db.reference("rooms")
    rooms = rooms_ref.get() or {}

    # Check linked rooms
    linked_rooms = []
    for rid, room in rooms.items():
        r_floor = str(room.get("floor") or "").strip()
        if floor_name and r_floor.lower() == floor_name.lower():
            linked_rooms.append(rid)

    if linked_rooms:
        flash(
            "This floor cannot be deleted because there are rooms linked to it. "
            "Please delete or move those rooms first.",
            "danger",
        )
        return redirect(url_for("add_floor"))

    floors_ref.child(floor_id).delete()
    flash("Floor deleted successfully!", "success")
    return redirect(url_for("add_floor"))


# ✅ ROOM: ADD (select floor from dropdown)
@app.route("/add_room", methods=["GET", "POST"])
def add_room():
    floors_ref = db.reference("floors")
    floors_data = floors_ref.get() or {}

    floor_options = []
    for fid, f in floors_data.items():
        if isinstance(f, dict):
            floor_label = f.get("name") or f.get("number") or ""
        else:
            floor_label = f or ""
        floor_label = str(floor_label).strip()
        if floor_label:
            floor_options.append(floor_label)

    floor_options = sorted(set(floor_options), key=lambda x: x.lower())

    if request.method == "POST":
        floor = (request.form.get("floor") or "").strip()
        room_number = (request.form.get("room_number") or "").strip()
        bed_count_raw = (request.form.get("bed_count") or "").strip()

        if not floor or not room_number or not bed_count_raw:
            flash("All fields are required.", "danger")
            return redirect(url_for("add_room"))

        try:
            bed_count = int(bed_count_raw)
        except ValueError:
            flash("Number of beds must be a valid number.", "danger")
            return redirect(url_for("add_room"))

        ref = db.reference("rooms")
        rooms = ref.get() or {}

        # Duplicate room check
        for rid, room in rooms.items():
            r_floor = str(room.get("floor") or "").strip()
            r_room_no = str(room.get("room_number") or "").strip()

            if r_floor.lower() == floor.lower() and r_room_no.lower() == room_number.lower():
                flash("This room already exists on this floor.", "danger")
                return redirect(url_for("add_room"))

        # Images (max 3)
        images = [
            request.files.get("image1"),
            request.files.get("image2"),
            request.files.get("image3")
        ]
        img_paths = []

        for img in images:
            if img and img.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{img.filename}")
                save_dir = os.path.join("static", "room_photos")
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                img.save(save_path)
                img_paths.append(f"room_photos/{filename}")

        room_id = str(uuid.uuid4())
        ref.child(room_id).set({
            "floor": floor,
            "room_number": room_number,
            "bed_count": bed_count,
            "available_beds": bed_count,
            "images": img_paths
        })

        flash("Room added successfully!", "success")
        return redirect(url_for("view_rooms"))  # your existing route

    return render_template("add_room.html", floor_options=floor_options)


@app.route("/view_rooms", methods=["GET"])
def view_rooms():
    ref = db.reference("rooms")
    rooms = ref.get() or {}

    # ✅ Floor filter from query param
    selected_floor = request.args.get("floor", "").strip()

    filtered_rooms = {}
    for rid, room in rooms.items():
        if selected_floor and selected_floor != "All":
            if str(room.get("floor")) == selected_floor:
                filtered_rooms[rid] = room
        else:
            filtered_rooms[rid] = room

    total_rooms = len(filtered_rooms)
    total_available_beds = sum(int(room.get("available_beds", 0)) for room in filtered_rooms.values())

    # ✅ Get unique floors for dropdown
    unique_floors = sorted({str(room.get("floor")) for room in rooms.values() if room.get("floor")})

    return render_template(
        "view_rooms.html",
        rooms=filtered_rooms,
        total_rooms=total_rooms,
        total_available_beds=total_available_beds,
        selected_floor=selected_floor,
        unique_floors=unique_floors
    )

@app.route("/edit_room/<room_id>", methods=["GET", "POST"])
def edit_room(room_id):
    ref = db.reference("rooms").child(room_id)
    room = ref.get()

    if request.method == "POST":
        floor = request.form.get("floor")
        room_number = request.form.get("room_number")
        bed_count = int(request.form.get("bed_count"))

        # Existing images
        updated_images = room.get("images", [])

        # Handle new uploads (overwrite if new image provided)
        for i, field in enumerate(["image1", "image2", "image3"]):
            img = request.files.get(field)
            if img and img.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{img.filename}")
                save_path = os.path.join("static/room_photos", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                img.save(save_path)

                if len(updated_images) > i:
                    updated_images[i] = f"room_photos/{filename}"  # replace
                else:
                    updated_images.append(f"room_photos/{filename}")  # add new

        # Save updated data
        ref.update({
            "floor": floor,
            "room_number": room_number,
            "bed_count": bed_count,
            "available_beds": room.get("available_beds", bed_count),
            "images": updated_images[:3]  # ensure max 3
        })

        flash("Room updated successfully!", "success")
        return redirect(url_for("view_rooms"))

    return render_template("edit_room.html", room=room)


@app.route("/delete_room/<room_id>", methods=["GET", "POST"])
def delete_room(room_id):
    ref = db.reference("rooms").child(room_id)
    room = ref.get()

    if not room:
        flash("Room not found!", "error")
        return redirect(url_for("view_rooms"))

    # ✅ Check if room is assigned to any user
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    assigned_user = None
    for uid, user in users.items():
        if user.get("assigned_room") == room_id:  # check by room_id
            assigned_user = {
                "id": uid,
                "name": user.get("name"),
                "email": user.get("email"),
                "profile_image": user.get("profile_image_path"),
                "shelter_start_date": user.get("shelter_start_date"),
                "shelter_expiry_date": user.get("shelter_expiry_date"),
                "shelter_status": user.get("shelter_status")
            }
            break

    if assigned_user:
        # 🚨 Do not delete, show popup instead with shelter details
        return render_template("room_assigned_warning.html",
                               room=room,
                               user=assigned_user)

    # ✅ If no user assigned → Delete room + images
    for img in room.get("images", []):
        try:
            os.remove(os.path.join("static", img))  # delete from static
        except:
            pass

    ref.delete()
    flash("Room deleted successfully!", "success")
    return redirect(url_for("view_rooms"))



@app.route("/shelter", methods=["GET", "POST"])
def shelter():
    selected_category = request.args.get("category", "").strip()

    ref_users = db.reference("users")
    users = ref_users.get() or {}

    # ✅ Approved users only
    approved_users = {
        uid: u for uid, u in users.items() if u.get("status", "").lower() == "approved"
    }

    filtered_users = {}
    if selected_category and selected_category != "All":
        for uid, u in approved_users.items():
            cats = u.get("categories", [])
            if isinstance(cats, str):
                cats = [cats]
            cats = [c.lower().strip() for c in cats]
            if selected_category.lower() in cats:
                filtered_users[uid] = u
    else:
        filtered_users = approved_users

    # ✅ Handle Shelter Allotment
    if request.method == "POST":
        user_id = request.form.get("user_id")
        room_id = request.form.get("room_id")

        if not user_id or not room_id:
            flash("Invalid request! Please select a user and room.", "error")
            return redirect(url_for("shelter", category=selected_category))

        # Fetch user
        user = ref_users.child(user_id).get()
        if not user:
            flash("User not found!", "error")
            return redirect(url_for("shelter", category=selected_category))

        # Fetch room
        ref_rooms = db.reference("rooms")
        room = ref_rooms.child(room_id).get()
        if not room:
            flash("Room not found!", "error")
            return redirect(url_for("shelter", category=selected_category))

        # ✅ Check available beds
        bed_count = int(room.get("bed_count", 0))
        if bed_count <= 0:
            flash(f"Room {room.get('room_number')} is already FULL!", "danger")
            return redirect(url_for("shelter", category=selected_category))

        # ✅ Allot user under Shelter child
        ref_shelter = db.reference("Shelter").child(room_id).child(user_id)
        ref_shelter.set(user)

        # ✅ Reduce bed count by 1
        new_beds = bed_count - 1
        ref_rooms.child(room_id).update({"bed_count": new_beds})

        flash(f"User {user['name']} allotted to Room {room.get('room_number')} ✅ (Remaining Beds: {new_beds})", "success")
        return redirect(url_for("shelter", category=selected_category))

    # ✅ Get all rooms for dropdown
    ref_rooms = db.reference("rooms")
    rooms = ref_rooms.get() or {}

    return render_template(
        "shelter.html",
        selected_category=selected_category,
        users=filtered_users,
        rooms=rooms
    )

@app.route("/assign_shelter/<user_id>", methods=["GET", "POST"])
def assign_shelter(user_id):
    # --- Load user ---
    ref_users = db.reference("users").child(user_id)
    user = ref_users.get()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("shelter"))

    # --- Load rooms and normalize data ---
    ref_rooms = db.reference("rooms")
    rooms_raw = ref_rooms.get() or {}

    rooms = {}
    for rid, r in rooms_raw.items():
        if isinstance(r, dict):
            room_data = dict(r)
        else:
            room_data = {}

        # Safe numeric conversion
        try:
            bed_count = int(room_data.get("bed_count", 0))
        except (TypeError, ValueError):
            bed_count = 0

        try:
            available_beds = int(room_data.get("available_beds", 0))
        except (TypeError, ValueError):
            available_beds = 0

        room_data["bed_count"] = bed_count
        room_data["available_beds"] = available_beds
        rooms[rid] = room_data

    # --- Compute overall stats ---
    total_rooms = len(rooms)
    total_beds = sum(r["bed_count"] for r in rooms.values())
    total_available_beds = sum(r["available_beds"] for r in rooms.values())

    stats = {
        "total_rooms": total_rooms,
        "total_beds": total_beds,
        "total_available_beds": total_available_beds,
    }

    # --- Floor-wise summary (for hero overview) ---
    floors_summary = {}
    for rid, room in rooms.items():
        floor_name = str(room.get("floor", "Unknown"))
        summary = floors_summary.setdefault(
            floor_name,
            {"floor": floor_name, "rooms": 0, "available_beds": 0, "total_beds": 0},
        )
        summary["rooms"] += 1
        summary["available_beds"] += room["available_beds"]
        summary["total_beds"] += room["bed_count"]

    floors_summary_list = sorted(floors_summary.values(), key=lambda x: x["floor"])

    # --- POST handling ---
    if request.method == "POST":
        notify = request.form.get("notify")  # hidden field from "notify" button

        # If admin clicked "Notify user" when no beds
        if notify == "yes":
            subject = "SahaaraX - Shelter Request Pending"
            body = f"""Dear {user.get('name', 'Guest')},

Unfortunately, there are no beds available in the selected shelter at the moment.
Our team will notify you as soon as a bed becomes available.

Regards,
SahaaraX Team
"""
            try:
                yag.send(user["email"], subject, body)
                flash("User has been notified by email about bed unavailability.", "info")
            except Exception as e:
                # Optional: log e
                flash("Failed to send email notification. Please check email settings.", "danger")
            return redirect(url_for("shelter"))

        # Normal assign flow
        room_id = (request.form.get("room_id") or "").strip()
        start_date = (request.form.get("start_date") or "").strip()
        expiry_date = (request.form.get("expiry_date") or "").strip()

        if not room_id or not start_date or not expiry_date:
            flash("All fields are required.", "danger")
            return redirect(url_for("assign_shelter", user_id=user_id))

        # Check if user already has room
        if user.get("assigned_room"):
            flash("This user already has a room assigned.", "warning")
            return redirect(url_for("shelter"))

        room = rooms.get(room_id)
        if not room:
            flash("Selected room was not found. Please choose another room.", "danger")
            return redirect(url_for("assign_shelter", user_id=user_id))

        # Bed availability check (server-side safety)
        if int(room.get("available_beds", 0)) <= 0:
            flash("No beds available in this room. You can notify the user.", "warning")
            return render_template(
                "assign_shelter.html",
                user=user,
                user_id=user_id,
                rooms=rooms,
                no_beds=True,
                stats=stats,
                floors_summary=floors_summary_list,
            )

        # --- Assign room to user ---
        ref_users.update({
            "assigned_room": room_id,
            "shelter_start_date": start_date,
            "shelter_expiry_date": expiry_date,
            "shelter_status": "active",
        })

        # --- Decrease available beds ---
        new_bed_count = int(room["available_beds"]) - 1
        ref_rooms.child(room_id).update({"available_beds": new_bed_count})

        flash(f"Shelter assigned successfully. Room ID: {room_id}", "success")
        return redirect(url_for("shelter"))

    # --- GET: just show page ---
    return render_template(
        "assign_shelter.html",
        user=user,
        user_id=user_id,
        rooms=rooms,
        no_beds=False,
        stats=stats,
        floors_summary=floors_summary_list,
    )

@app.route("/check_shelter_expiry")
def check_shelter_expiry():
    ref_users = db.reference("users")
    users = ref_users.get() or {}

    now = datetime.now()

    for uid, user in users.items():
        expiry_str = user.get("shelter_expiry_date")
        if user.get("assigned_room") and expiry_str:
            expiry_date = None

            # ✅ Multiple formats handle karna
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    expiry_date = datetime.strptime(expiry_str, fmt)
                    break
                except ValueError:
                    continue

            if not expiry_date:
                continue  # Agar format hi galat hai, skip

            days_left = (expiry_date - now).days

            if days_left <= 2 and user.get("shelter_status") == "Active":
                subject = "⚠️ Shelter Expiry Alert"
                body = f"""
                Dear Admin,

                User {user['name']} ({user['email']})'s shelter is expiring soon.

                Room: {user['assigned_room']}
                Expiry Date: {expiry_str}

                Please take action.

                Regards,
                SahaaraX System
                """
                yag.send("admin_email@gmail.com", subject, body)
                flash(f"Expiry alert sent for {user['name']}", "info")

    return "Checked expiry and sent alerts."


@app.route("/check_expired_shelters")
def check_expired_shelters():
    ref_users = db.reference("users")
    users = ref_users.get() or {}

    ref_rooms = db.reference("rooms")
    ref_expired = db.reference("expired_shelters")

    today = datetime.today().date()

    for uid, user in users.items():
        expiry_date = user.get("shelter_expiry_date")
        room_id = user.get("assigned_room")
        status = user.get("shelter_status", "")

        if expiry_date and room_id and status == "active":
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            except ValueError:
                continue  # skip invalid dates

            # ✅ Check if expired
            if today >= expiry:
                # Move record to expired_shelters
                ref_expired.push({
                    "user_id": uid,
                    "room_id": room_id,
                    "start_date": user.get("shelter_start_date"),
                    "expiry_date": expiry_date
                })

                # Free the bed in that room
                room = ref_rooms.child(room_id).get()
                if room:
                    new_beds = int(room.get("bed_count", 0)) + 1
                    ref_rooms.child(room_id).update({"bed_count": new_beds})

                # Update user status
                ref_users.child(uid).update({
                    "shelter_status": "expired",
                    "assigned_room": None
                })

    flash("Expired shelters checked and updated.", "info")
    return redirect(url_for("shelter"))

@app.route("/assigned_shelters")
def assigned_shelters():
    # Get users + rooms
    users_ref = db.reference("users")
    rooms_ref = db.reference("rooms")

    users = users_ref.get() or {}
    rooms = rooms_ref.get() or {}

    assigned_users = {}

    for uid, user in users.items():
        room_id = user.get("assigned_room")
        if room_id:  # only users with assigned rooms
            room = rooms.get(room_id)
            if room:
                user["room_details"] = room  # attach room info
                assigned_users[uid] = user

    return render_template("assigned_shelters.html", users=assigned_users)




@app.route("/release_shelter/<user_id>")
def release_shelter(user_id):
    ref_users = db.reference("users").child(user_id)
    user = ref_users.get()

    if not user:
        flash("User not found!", "error")
        return redirect(url_for("assigned_shelters"))

    room_id = user.get("assigned_room")
    if not room_id:
        flash("This user does not have a room assigned!", "warning")
        return redirect(url_for("assigned_shelters"))

    # Room reference
    ref_rooms = db.reference("rooms").child(room_id)
    room = ref_rooms.get()

    if room:
        # Increase available beds back
        new_beds = int(room.get("available_beds", 0)) + 1
        ref_rooms.update({"available_beds": new_beds})

    # Reset user shelter details
    ref_users.update({
        "assigned_room": None,
        "shelter_start_date": None,
        "shelter_expiry_date": None,
        "shelter_status": "released"
    })

    # Send email
    subject = "SahaaraX - Thank You"
    body = f"""
    Dear {user['name']},

    Thank you for staying with SahaaraX Shelter. 
    We are glad to have supported you during this period. 

    Your shelter stay has now ended. 
    Wishing you the very best ahead!

    Regards,
    SahaaraX Team
    """
    try:
        yag.send(user["email"], subject, body)
    except Exception as e:
        print("Email error:", e)

    flash(f"Shelter released for {user['name']}. Room bed updated.", "success")
    return redirect(url_for("assigned_shelters"))




@app.route("/counseling", methods=["GET"])
def counseling():
    filter_counseling = request.args.get("counseling", "").strip()

    ref = db.reference("users")
    users = ref.get() or {}

    # ✅ Only approved users
    approved_users = {
        uid: u for uid, u in users.items()
        if u.get("status", "").lower() == "approved"
    }

    # Get counselor assignments
    assignment_ref = db.reference("assign_conseler")
    assignments = assignment_ref.get() or {}
    counselor_map = {}
    for aid, data in assignments.items():
        uid = data.get("user_id")
        if uid:
            counselor_map[uid] = {
                "name": data.get("counselor_name"),
                "email": data.get("counselor_email"),
                "category": data.get("counseling"),
                "timestamp": data.get("timestamp")
            }

    filtered_users = {}
    stats = {
        "Domestic Violence": 0,
        "Sexual Abuse Support": 0,
        "Psychological Support": 0,
        "Self Awareness": 0,
        "Health Awareness": 0,
    }

    for uid, user in approved_users.items():
        counseling = user.get("counseling", [])
        if isinstance(counseling, str):
            counseling = [counseling]

        # Stats
        for c in counseling:
            if c in stats:
                stats[c] += 1

        # Filter
        if filter_counseling and filter_counseling != "All":
            if filter_counseling in counseling:
                pass
            else:
                continue

        # Add assigned counselor info if exists
        if uid in counselor_map:
            user["assigned_counselor"] = counselor_map[uid]
        filtered_users[uid] = user

    return render_template(
        "counseling.html",
        users=filtered_users,
        filter_counseling=filter_counseling,
        stats=stats
    )


# ✅ Get Counselors Modal Data (AJAX)
@app.route("/get_counselors/<user_id>")
def get_counselors(user_id):
    user = db.reference("users").child(user_id).get()
    if not user:
        return {"error": "User not found"}, 404

    category = user.get("counseling")
    if isinstance(category, list):
        category = category[0]

    counselors = {}
    ref = db.reference("conseling_signup")
    all_counselors = ref.get() or {}
    for cid, cons in all_counselors.items():
        if cons.get("counseling") == category:
            counselors[cid] = cons

    return {"counselors": counselors, "category": category}

# ✅ Assign Counselor
@app.route("/assign_counselor", methods=["POST"])
def assign_counselor():
    user_id = request.form.get("user_id")
    counselor_id = request.form.get("counselor_id")

    user = db.reference("users").child(user_id).get()
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    if not user or not counselor:
        flash("User or counselor not found!", "error")
        return redirect(url_for("counseling"))

    # Save assignment in DB
    assign_id = str(uuid.uuid4())
    db.reference("assign_conseler").child(assign_id).set({
        "user_id": user_id,
        "user_name": user["name"],
        "user_email": user["email"],
        "counselor_id": counselor_id,
        "counselor_name": counselor["name"],
        "counselor_email": counselor["email"],
        "counseling": counselor["counseling"],
        "timestamp": str(datetime.now())
    })

    # Send email
    yag.send(
        user["email"],
        "Counselor Assigned - SahaaraX",
        f"""
        Dear {user['name']},

        A counselor has been assigned to you for {counselor['counseling']}.

        Counselor: {counselor['name']}
        Email: {counselor['email']}

        Regards,
        SahaaraX Team
        """
    )

    flash("Counselor assigned and email sent successfully!", "success")
    return redirect(url_for("counseling"))

@app.route("/conseling_signup", methods=["GET", "POST"])
def conseling_signup():
    if request.method == "POST":
        def is_alpha(value):
            return re.fullmatch(r"[A-Za-z\s]+", value)

        def is_valid_email(value):
            return re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value)

        def is_valid_phone(value):
            return re.fullmatch(r"\d{11}", value)

        # Get values
        name = request.form.get("name", "").strip()
        father_name = request.form.get("father_name", "").strip()
        email = request.form.get("email", "").strip()
        gender = request.form.get("gender", "")
        counseling = request.form.get("counseling", "")
        dob = request.form.get("dob", "")
        phone = request.form.get("phone", "")
        availability = request.form.get("availability", "")
        location = request.form.get("location", "")

        # 🔒 Validations
        if not is_alpha(name):
            flash("Name must contain only alphabets.", "danger")
            return redirect(url_for("conseling_signup"))

        if not is_alpha(father_name):
            flash("Father Name must contain only alphabets.", "danger")
            return redirect(url_for("conseling_signup"))

        if not is_valid_email(email):
            flash("Invalid email format.", "danger")
            return redirect(url_for("conseling_signup"))

        if not is_valid_phone(phone):
            flash("Phone number must be exactly 11 digits.", "danger")
            return redirect(url_for("conseling_signup"))

        if not dob:
            flash("Date of birth is required.", "danger")
            return redirect(url_for("conseling_signup"))

        try:
            datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            flash("Date of birth format should be YYYY-MM-DD.", "danger")
            return redirect(url_for("conseling_signup"))

        # 📸 Save profile image
        profile_img = request.files.get("profile_image")
        profile_img_path = ""
        if not profile_img or not profile_img.filename:
            flash("Profile image is required.", "danger")
            return redirect(url_for("conseling_signup"))

        if not profile_img.mimetype.startswith("image/"):
            flash("Only image files are allowed for profile image.", "danger")
            return redirect(url_for("conseling_signup"))

        filename = secure_filename(f"{uuid.uuid4()}_{profile_img.filename}")
        save_path = os.path.join("static/profile_photos", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        profile_img.save(save_path)
        profile_img_path = f"profile_photos/{filename}"

        # 📄 Save documents
        document = request.files.get("document")
        document_path = ""
        if document and document.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{document.filename}")
            save_path = os.path.join("static/conseling_documents", filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            document.save(save_path)
            document_path = f"conseling_documents/{filename}"

        # 🔐 Generate random password
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # 🔥 Save to Firebase
        uid = str(uuid.uuid4())
        db.reference("conseling_signup").child(uid).set({
            "name": name,
            "father_name": father_name,
            "email": email,
            "gender": gender,
            "counseling": counseling,
            "dob": dob,
            "phone": phone,
            "availability": availability,
            "location": location,
            "profile_image": profile_img_path,
            "document": document_path,
            "password": password
        })

        # 📧 Send email
        subject = "SahaaraX Counseling Signup - Login Credentials"
        body = f"""
        Dear {name},

        Your counseling signup was successful ✅

        Login Credentials:
        Email: {email}
        Password: {password}

        Regards,  
        SahaaraX Team
        """
        yag.send(email, subject, body)

        flash("Counseling Signup Successful! Login details sent to email.", "success")
        return redirect(url_for("conseling_signup"))

    return render_template("conseling_signup.html")
# Dataset configurations
db_type = None

DATASETS_yaki = {
    'sexual_abuse': {
        'name': 'Sexual Abuse Assessment',
        'file': 'Sexual_Abuse_Assessment_9000_FINAL.xlsx',
        'description': 'Comprehensive sexual abuse risk assessment and evaluation',
        'icon': '🚨',
        'model_prefix': 'sexual_abuse',
    },
    'domestic_violence': {
        'name': 'Domestic Violence Assessment',
        'file': 'Domestic_violence.csv',
        'description': 'Domestic violence risk assessment and safety evaluation',
        'icon': '🏠',
        'model_prefix': 'domestic_violence',
    },
    'psychological_support': {
        'name': 'Psychological Support Assessment',
        'file': 'Psychological_Support.csv',
        'description': 'Psychological support needs and mental health assessment',
        'icon': '🧠',
        'model_prefix': 'psychological_support'
    }
}
DATASETS = {}
def set_filtered_dataset(db_type):
    global DATASETS  # so we can modify it

    # Reset to empty every time to avoid leftovers
    DATASETS.clear()

    if db_type == "Domestic Violence":
        DATASETS['domestic_violence'] = DATASETS_yaki['domestic_violence']
    elif db_type == "Sexual Abuse Support":
        DATASETS['sexual_abuse'] = DATASETS_yaki['sexual_abuse']
    elif db_type == "Psychological Support":
        DATASETS['psychological_support'] = DATASETS_yaki['psychological_support']

# Global variable


# Global constant: all counseling types you support
COUNSELING_TYPES = [
    "Domestic Violence",
    "Sexual Abuse Support",
    "Psychological Support",
    "Self Awareness",
    "Health Awareness",
]

# ---------------- Counseling Sign In ----------------
@app.route("/counseling_signin", methods=["GET", "POST"])
def counseling_signin():
    global db_type  # if you really need it globally elsewhere

    # Always have these ready for template
    counseling_types = COUNSELING_TYPES
    current_year = datetime.now().year

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        selected_type = (request.form.get("counseling_type") or "").strip()

        # Basic validation
        if not email or not password or not selected_type:
            flash("Please enter email, password and counseling type.", "danger")
            return redirect(url_for("counseling_signin"))

        # NOTE: path name is 'conseling_signup' in your code – keeping it same
        ref = db.reference("conseling_signup")
        users = ref.get() or {}

        # Try to find user by email
        for uid, user in users.items():
            db_email = str(user.get("email", "")).strip().lower()
            db_password = str(user.get("password", "")).strip()

            # Counseling type in DB (adjust key name according to your DB)
            # If your field is 'counseling', this will work.
            db_type = str(
                user.get("counseling_type")
                or user.get("counseling")
                or ""
            ).strip()

            if db_email == email.lower():
                # First check counseling type
                if db_type != selected_type:
                    flash("Selected counseling type does not match this account.", "danger")
                    return redirect(url_for("counseling_signin"))

                # Then check password
                if db_password == password:
                    # Save session
                    session["counseling_user"] = uid
                    session["counseling_type"] = db_type

                    flash("Login successful!", "success")

                    # Dynamically set dataset based on type
                    # (assuming this function is defined elsewhere)
                    set_filtered_dataset(db_type)

                    # Redirect based on counseling type
                    if db_type in ["Domestic Violence", "Sexual Abuse Support", "Psychological Support"]:
                        return redirect(url_for("counseling_dashboard"))
                    elif db_type in ["Self Awareness", "Health Awareness"]:
                        return redirect(url_for("awareness_dashboard"))
                    else:
                        flash("Invalid counseling type in database.", "danger")
                        return redirect(url_for("counseling_signin"))
                else:
                    flash("Incorrect password.", "danger")
                    return redirect(url_for("counseling_signin"))

        # If loop finishes → no email matched
        flash("Email not found.", "danger")
        return redirect(url_for("counseling_signin"))

    # GET request – just show form
    return render_template(
        "counseling_signin.html",
        counseling_types=counseling_types,
        current_year=current_year,
    )
# Step 1: Forgot password (enter role & email)
@app.route("/counselor_forget", methods=["GET", "POST"])
def counselor_forget():
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not role or not email:
            flash("⚠️ Please select role and enter email.", "warning")
            return redirect(url_for("counselor_forget"))

        # Path check (Counseling vs Awareness)
        path = "conseling_signup" if role == "Counseling" else "awareness_signup"
        users = db.reference(path).get() or {}

        user_id, user_name = None, None
        for uid, user in users.items():
            db_email = str(user.get("email", "")).strip().lower()
            if db_email == email:
                user_id = uid
                user_name = user.get("name", "User")
                break

        if not user_id:
            flash("❌ Email not found!", "danger")
            return redirect(url_for("counselor_forget"))

        # Generate OTP
        otp = random.randint(100000, 999999)
        session["reset_user"] = {"id": user_id, "role": role, "email": email, "otp": str(otp)}

        # Send OTP email
        try:
            yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")
            yag.send(
                to=email,
                subject="Password Reset Code - SahaaraX",
                contents=f"Hello {user_name},\n\nYour verification code is: {otp}\n\nTeam SahaaraX"
            )
            flash("✅ Verification code sent to your email.", "success")
            return redirect(url_for("counselor_verify"))
        except Exception as e:
            print("Email error:", e)
            flash("⚠️ Failed to send email. Try again later.", "danger")
            return redirect(url_for("counselor_forget"))

    return render_template("counselor_forget.html")


# Step 2: Verify OTP
@app.route("/counselor_verify", methods=["GET", "POST"])
def counselor_verify():
    reset_info = session.get("reset_user")
    if not reset_info:
        flash("⚠️ Session expired, please try again.", "warning")
        return redirect(url_for("counselor_forget"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        if code == reset_info["otp"]:
            return redirect(url_for("counselor_reset"))
        else:
            flash("❌ Invalid verification code!", "danger")
            return redirect(url_for("counselor_verify"))

    return render_template("counselor_verify.html", email=reset_info["email"])


# Step 3: Reset Password
@app.route("/counselor_reset", methods=["GET", "POST"])
def counselor_reset():
    reset_info = session.get("reset_user")
    if not reset_info:
        flash("⚠️ Session expired, please try again.", "warning")
        return redirect(url_for("counselor_forget"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not password or not confirm:
            flash("⚠️ Please enter both fields.", "warning")
            return redirect(url_for("counselor_reset"))

        if password != confirm:
            flash("❌ Passwords do not match!", "danger")
            return redirect(url_for("counselor_reset"))

        path = "conseling_signup" if reset_info["role"] == "Counseling" else "awareness_signup"
        db.reference(path).child(reset_info["id"]).update({"password": password})

        session.pop("reset_user", None)
        flash("✅ Password reset successful! Please login.", "success")
        return redirect(url_for("counseling_signin"))

    return render_template("counselor_reset.html")



# ---------------- Counseling Dashboard ----------------
@app.route("/counseling_dashboard")
def counseling_dashboard():
    """
    Enhanced counseling dashboard with comprehensive user details and statistics
    """
    # ✅ Login check
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]

    # ✅ Get counselor data
    counselor_ref = db.reference("conseling_signup").child(counselor_id)
    counselor = counselor_ref.get()

    if not counselor:
        flash("❌ Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))

    # ✅ Get all assignments
    assignments_ref = db.reference("assign_conseler")
    assignments = assignments_ref.get() or {}

    # ✅ Get references for users, classes, and tests
    users_ref = db.reference("users")
    classes_ref_base = db.reference("counseling_classes").child(counselor_id)
    tests_ref_base = db.reference("counseling_tests")

    assigned_users_detail = []

    # ✅ Process each assignment
    for aid, assignment in assignments.items():
        if not isinstance(assignment, dict):
            continue

        # Only get assignments for this counselor
        if assignment.get("counselor_id") != counselor_id:
            continue

        user_id = assignment.get("user_id")
        if not user_id:
            continue

        # ✅ Get user data
        user_data = users_ref.child(user_id).get()
        if not user_data:
            continue

        # ✅ Get classes for this user
        classes_data = classes_ref_base.child(user_id).get() or {}
        total_classes = len(classes_data)
        completed_classes = 0

        for cid, cls in classes_data.items():
            if isinstance(cls, dict) and cls.get("status", "").lower() == "completed":
                completed_classes += 1

        # ✅ Check if tests are unlocked (need 3+ completed classes)
        test_unlocked = completed_classes >= 3

        # ✅ Get tests for this user
        user_tests = tests_ref_base.child(user_id).get() or {}
        tests_count = len(user_tests)
        completed_tests = 0
        last_test = None

        for tid, test in user_tests.items():
            if not isinstance(test, dict):
                continue

            if test.get("status", "").lower() == "completed":
                completed_tests += 1

            # Keep track of the last test
            test["test_id"] = tid
            last_test = test

        # ✅ Calculate completion percentage
        completion_percentage = 0
        if total_classes > 0:
            completion_percentage = int((completed_classes / total_classes) * 100)

        # ✅ Compile user detail
        user_detail = {
            "assignment_id": aid,
            "user_id": user_id,
            "assignment": assignment,
            "user": user_data,
            "total_classes": total_classes,
            "completed_classes": completed_classes,
            "completion_percentage": completion_percentage,
            "test_unlocked": test_unlocked,
            "tests_count": tests_count,
            "completed_tests": completed_tests,
            "last_test": last_test,
            "status": "Active" if total_classes > completed_classes else "Completed"
        }

        assigned_users_detail.append(user_detail)

    # ✅ Sort by most recent assignment first
    assigned_users_detail.sort(
        key=lambda x: x["assignment"].get("timestamp", ""),
        reverse=True
    )

    # ✅ Calculate overall statistics
    total_assigned = len(assigned_users_detail)
    total_all_classes = sum(u["total_classes"] for u in assigned_users_detail)
    total_completed_classes = sum(u["completed_classes"] for u in assigned_users_detail)
    total_tests = sum(u["tests_count"] for u in assigned_users_detail)
    total_completed_tests = sum(u["completed_tests"] for u in assigned_users_detail)

    stats = {
        "total_assigned": total_assigned,
        "total_classes": total_all_classes,
        "completed_classes": total_completed_classes,
        "total_tests": total_tests,
        "completed_tests": total_completed_tests
    }

    return render_template(
        "counseling_dashboard.html",
        user=counselor,
        assigned_users=assigned_users_detail,
        stats=stats
    )
@app.route("/awareness_dashboard")
def awareness_dashboard():
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    if not counselor:
        flash("Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))



    # ✅ Fetch awareness sessions directly
    all_sessions = db.reference("awareness_sessions").get() or {}
    sessions = {
        sid: sess for sid, sess in all_sessions.items()
        if isinstance(sess, dict) and sess.get("counselor_id") == counselor_id
    }

    return render_template(
        "awareness_dashboard.html",
        user=counselor,
        sessions=sessions
    )

# ---------------- Edit Awareness Profile ----------------
@app.route("/edit_awareness_profile", methods=["POST"])
def edit_awareness_profile():
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    user_id = session["counseling_user"]
    ref = db.reference("conseling_signup").child(user_id)

    user = ref.get()
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("awareness_dashboard"))

    # Get form data
    new_name = request.form.get("name", user.get("name"))
    new_password = request.form.get("password", "").strip()

    # Update fields
    updates = {"name": new_name}
    if new_password:
        updates["password"] = new_password

    # Handle profile image upload
    if "profile_image" in request.files:
        image = request.files["profile_image"]
        if image.filename:
            # Save image to static/uploads/
            upload_path = os.path.join("static/uploads", image.filename)
            image.save(upload_path)
            updates["profile_image"] = f"uploads/{image.filename}"

    # Push updates to Firebase
    ref.update(updates)

    flash("✅ Profile updated successfully!", "success")
    return redirect(url_for("awareness_dashboard"))

@app.route("/create_awareness_session", methods=["GET", "POST"])
def create_awareness_session():
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        details = request.form.get("details")
        zoom_link = request.form.get("zoom_link")

        image_url = None
        if "image" in request.files:
            img = request.files["image"]
            if img.filename:
                path = os.path.join("static/uploads", img.filename)
                img.save(path)
                image_url = f"uploads/{img.filename}"

        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "counselor_id": counselor_id,
            "counselor_name": counselor.get("name"),
            "counselor_email": counselor.get("email"),
            "title": title,
            "category": category,
            "details": details,
            "zoom_link": zoom_link,
            "image": image_url,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "attendance": {}
        }
        db.reference("awareness_sessions").child(session_id).set(session_data)

        # Send emails + create attendance entries
        subject = f"New Awareness Session: {title}"
        body = f"""
        Dear Participant,

        You are invited to join our awareness session.

        Title: {title}
        Category: {category}
        Details: {details}
        Zoom Link: {zoom_link}

        Counselor: {counselor.get("name")}

        Regards,
        SahaaraX Team
        """
        for uid, usr in users.items():
            try:
                yag.send(usr["email"], subject, body)
                db.reference("awareness_sessions").child(session_id).child("attendance").child(uid).set({
                    "user_name": usr.get("name"),
                    "user_email": usr.get("email"),
                    "status": "Not Present"
                })
            except Exception as e:
                print("Email error:", e)

        flash("✅ Session created and invitations sent!", "success")
        return redirect(url_for("awareness_dashboard"))

    # Show dashboard sessions
    sessions = db.reference("awareness_sessions").get() or {}
    return render_template("awareness_dashboard.html", sessions=sessions)




@app.route("/view_session/<session_id>")
def view_session(session_id):
    session_data = db.reference("awareness_sessions").child(session_id).get()
    if not session_data:
        flash("⚠️ Session not found!", "danger")
        return redirect(url_for("awareness_dashboard"))
    return render_template("view_session.html", session=session_data)

@app.route("/delete_session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    session_ref = db.reference("awareness_sessions").child(session_id)
    session_data = session_ref.get()

    if not session_data:
        return {"success": False, "message": "Session not found"}, 404

    session_ref.delete()
    return {"success": True, "message": "Session deleted successfully"}, 200


@app.route("/mark_attendance/<session_id>", methods=["POST"])
def mark_attendance(session_id):
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    selected_present = request.form.getlist("present")
    ref = db.reference("awareness_sessions").child(session_id).child("attendance")
    attendance = ref.get() or {}

    for uid, att in attendance.items():
        status = "Present" if uid in selected_present else "Not Present"
        ref.child(uid).update({"status": status})

    flash("✅ Attendance updated!", "success")
    return redirect(url_for("awareness_dashboard"))

# ---------------- Manage Classes ----------------
@app.route("/counselor_class/<user_id>", methods=["GET", "POST"])
def counselor_class(user_id):
    if "counseling_user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()
    user = db.reference("users").child(user_id).get()

    if not counselor or not user:
        return jsonify({"error": "Invalid user or counselor"}), 400

    # ✅ Fetch existing classes (consistent path)
    classes_ref = db.reference("counseling_classes").child(counselor_id).child(user_id)
    existing_classes = classes_ref.get() or {}

    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")

        if not date or not time:
            flash("⚠️ Please select date and time!", "danger")
            return redirect(url_for("counseling_dashboard"))

        class_id = str(uuid.uuid4())
        class_data = {
            "class_id": class_id,
            "counselor_id": counselor_id,
            "counselor_name": counselor.get("name"),
            "counselor_email": counselor.get("email"),
            "user_id": user_id,
            "user_name": user.get("name"),
            "user_email": user.get("email"),
            "date": date,
            "time": time,
            "status": "Scheduled",
            "start_time": None,
            "end_time": None,
            "attendance_count": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # ✅ Save class in proper structure
        db.reference("counseling_classes").child(counselor_id).child(user_id).child(class_id).set(class_data)

        # Send email to user
        subject = "New Counseling Class Scheduled"
        body = f"""
        Dear {user['name']},

        Your counseling class has been scheduled ✅

        Date: {date}  
        Time: {time}  
        Counselor: {counselor['name']}  

        Regards,  
        SahaaraX Team
        """
        try:
            yag.send(user["email"], subject, body)
        except Exception as e:
            print("Email error:", e)

        flash("Class scheduled and email sent!", "success")
        return redirect(url_for("counseling_dashboard"))

    return render_template("counselor_class_partial.html",
                           user=user,
                           counselor=counselor,
                           user_id=user_id,
                           classes=existing_classes)


# ---------------- Start Class ----------------
@app.route("/start_class/<counselor_id>/<user_id>/<class_id>")
def start_class(counselor_id, user_id, class_id):
    ref = db.reference("counseling_classes").child(counselor_id).child(user_id).child(class_id)
    class_data = ref.get()

    if not class_data:
        flash("Class not found!", "danger")
        return redirect(url_for("counseling_dashboard"))

    # ✅ Update start time
    ref.update({
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Ongoing"
    })

    flash(f"Class started with {class_data['user_name']}", "success")
    return redirect(url_for("counselor_class", user_id=user_id))


# ---------------- End Class ----------------
@app.route("/end_class/<counselor_id>/<user_id>/<class_id>")
def end_class(counselor_id, user_id, class_id):
    ref = db.reference("counseling_classes").child(counselor_id).child(user_id).child(class_id)
    class_data = ref.get()

    if not class_data:
        flash("Class not found!", "danger")
        return redirect(url_for("counseling_dashboard"))

    # ✅ Update end time + attendance
    attendance = class_data.get("attendance_count", 0) + 1
    ref.update({
        "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Completed",
        "attendance_count": attendance
    })

    flash(f"Class completed for {class_data['user_name']}. Attendance updated.", "success")
    return redirect(url_for("counselor_class", user_id=user_id))




@app.route("/attendance/<user_id>")
def attendance(user_id):
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    # ✅ Go directly to counselor_id → user_id → class list
    classes_ref = db.reference("counseling_classes").child(counselor_id).child(user_id)
    classes = classes_ref.get() or {}

    # ✅ Count completed classes
    attendance_count = sum(1 for cid, c in classes.items() if c.get("status") == "Completed")

    # ✅ Unlock test if 3+ completed
    test_unlocked = attendance_count >= 3

    return render_template(
        "attendance.html",
        user=counselor,
        classes=classes,
        user_id=user_id,
        test_unlocked=test_unlocked,
        attendance_count=attendance_count
    )




# ---------------- SUBMIT TEST ----------------
@app.route("/submit_test/<user_id>/<test_id>", methods=["POST"])
def submit_test(user_id, test_id):
    answers = {}
    for key, val in request.form.items():
        answers[key] = val

    # Get test details
    test_ref = db.reference("counseling_tests").child(user_id).child(test_id)
    test_data = test_ref.get()

    if not test_data:
        flash("Test not found!", "danger")
        return redirect(url_for("attendance", user_id=user_id))

    # Send answers to Gemini for evaluation
    prompt = f"""
    A patient has taken a counseling test on {test_data['category']}.
    Questions: {test_data['questions']}
    Answers: {answers}

    Based on the answers, provide:
    1. A short psychological evaluation.
    2. Recommendations: Should the patient continue counseling or take further actions?
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    result = model.generate_content(prompt)

    evaluation = result.text

    # Save result in Firebase
    test_ref.update({
        "answers": answers,
        "evaluation": evaluation,
        "status": "Completed"
    })
    return render_template("test_result.html",
                           user_id=user_id,
                           test_id=test_id,
                           evaluation=evaluation)

# ---------------- View Counseling Users ----------------
@app.route("/view_counseling", methods=["GET"])
def view_counseling():
    # Get filters from query params
    counseling_filter = request.args.get("counseling", "All")
    gender_filter = request.args.get("gender", "All")
    availability_filter = request.args.get("availability", "All")
    location_filter = request.args.get("location", "").strip()

    # Fetch users
    ref = db.reference("conseling_signup")
    all_users = ref.get() or {}

    filtered_users = {}
    for uid, user in all_users.items():
        # Skip incomplete data
        if not user.get("name") or not user.get("counseling"):
            continue

        # Apply filters
        if counseling_filter != "All" and user.get("counseling") != counseling_filter:
            continue
        if gender_filter != "All" and user.get("gender") != gender_filter:
            continue
        if availability_filter != "All" and user.get("availability") != availability_filter:
            continue
        if location_filter and location_filter.lower() not in user.get("location", "").lower():
            continue

        filtered_users[uid] = user

    return render_template(
        "view_counseling.html",
        users=filtered_users,
        filter_counseling=counseling_filter,
        filter_gender=gender_filter,
        filter_availability=availability_filter,
        filter_location=location_filter
    )

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/success-stories")
def gallery():
    return render_template("gallery.html")

@app.route("/gallery")
def gal():
    return render_template("gallery.html")

@app.route("/ripple")
def ripple():
    return render_template("ripple.html")
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not subject or not message:
            flash("⚠️ Please fill all fields.", "danger")
            return redirect(url_for("contact"))

        # ✅ Email Content
        email_subject = f"📩 New Contact Form Message: {subject}"
        email_body = f"""
        You have received a new message from the SahaaraX Contact Form.

        👤 Name: {name}
        📧 Email: {email}
        📝 Subject: {subject}
        💬 Message:
        {message}

        -----------------------------
        This email was sent automatically by SahaaraX system.
        """

        try:
            yag.send(
                to="saharaax2468@gmail.com",
                subject=email_subject,
                contents=email_body
            )
            flash("✅ Your message has been sent successfully! We will get back to you soon.", "success")
        except Exception as e:
            print("❌ Email error:", e)
            flash("⚠️ Failed to send message. Please try again later.", "danger")

        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/attendance_report")
def attendance_report():
    all_sessions = db.reference("awareness_sessions").get() or {}
    user_summary = {}

    total_present = 0
    total_absent = 0
    total_sessions = 0

    for session_id, sess in (all_sessions or {}).items():
        if not isinstance(sess, dict):
            continue

        session_title = sess.get("title", "Untitled Session")
        session_category = sess.get("category", "Unknown")
        attendance = sess.get("attendance", {})

        for uid, att in (attendance or {}).items():
            user_email = att.get("user_email", "unknown")
            user_name = att.get("user_name", "Unknown User")
            status = att.get("status", "Absent")

            if uid not in user_summary:
                user_summary[uid] = {
                    "name": user_name,
                    "email": user_email,
                    "total_sessions": 0,
                    "present_count": 0,
                    "absent_count": 0,
                    "sessions": []
                }

            # Update counts
            user_summary[uid]["total_sessions"] += 1
            total_sessions += 1

            if status == "Present":
                user_summary[uid]["present_count"] += 1
                total_present += 1
            else:
                user_summary[uid]["absent_count"] += 1
                total_absent += 1

            # Store session details
            user_summary[uid]["sessions"].append({
                "title": session_title,
                "category": session_category,
                "status": status,
                "created_at": sess.get("created_at", "")
            })

    # Highcharts summary data
    chart_data = {
        "total_sessions": total_sessions,
        "present": total_present,
        "absent": total_absent,
    }

    return render_template(
        "attendance_report.html",
        users=list(user_summary.values()),
        chart_data=chart_data
    )

@app.route("/admin_report")
def admin_report():
    # Awareness Sessions Attendance
    all_awareness = db.reference("awareness_sessions").get() or {}
    awareness_summary = {}
    total_awareness_present = total_awareness_absent = 0

    for session_id, sess in all_awareness.items():
        attendance = sess.get("attendance", {})
        for uid, att in attendance.items():
            name = att.get("user_name", "Unknown")
            email = att.get("user_email", "Unknown")
            status = att.get("status", "Not Present")

            if uid not in awareness_summary:
                awareness_summary[uid] = {
                    "name": name,
                    "email": email,
                    "sessions": 0,
                    "present": 0,
                    "absent": 0
                }

            awareness_summary[uid]["sessions"] += 1
            if status == "Present":
                awareness_summary[uid]["present"] += 1
                total_awareness_present += 1
            else:
                awareness_summary[uid]["absent"] += 1
                total_awareness_absent += 1

    # Counseling Classes
    counseling_data = db.reference("counseling_classes").get() or {}
    counseling_summary = {}
    total_classes = 0
    for counselor_id, users in counseling_data.items():
        for user_id, classes in users.items():
            for class_id, cls in classes.items():
                name = cls.get("user_name", "Unknown")
                email = cls.get("user_email", "Unknown")

                if user_id not in counseling_summary:
                    counseling_summary[user_id] = {
                        "name": name,
                        "email": email,
                        "classes": 0
                    }

                counseling_summary[user_id]["classes"] += 1
                total_classes += 1

    # Shelter Beds
    rooms = db.reference("rooms").get() or {}
    total_beds = available_beds = 0
    for room_id, room in rooms.items():
        total_beds += room.get("bed_count", 0)
        available_beds += room.get("available_beds", 0)
    occupied_beds = total_beds - available_beds

    # Other Counts
    total_users = len(db.reference("users").get() or {})
    total_counselors = len(db.reference("conseling_signup").get() or {})
    total_sessions = len(all_awareness)

    dashboard_counts = {
        "total_users": total_users,
        "total_counselors": total_counselors,
        "total_beds": total_beds,
        "available_beds": available_beds,
        "occupied_beds": occupied_beds,
        "total_awareness_sessions": total_sessions,
        "total_awareness_present": total_awareness_present,
        "total_awareness_absent": total_awareness_absent,
        "total_counseling_classes": total_classes,
    }

    # Chart Data for Highcharts
    chart_data = {
        "awareness": {
            "present": total_awareness_present,
            "absent": total_awareness_absent,
        },
        "beds": {
            "available": available_beds,
            "occupied": occupied_beds,
        }
    }

    return render_template(
        "admin_report.html",
        awareness_summary=awareness_summary,
        counseling_summary=counseling_summary,
        dashboard_counts=dashboard_counts,
        chart_data=chart_data
    )

@app.route("/user_progress")
def user_progress():
    # Awareness Sessions
    all_awareness = db.reference("awareness_sessions").get() or {}
    progress_summary = {}

    for session_id, sess in (all_awareness or {}).items():
        if not isinstance(sess, dict):
            continue

        session_title = sess.get("title", "Untitled Session")
        session_category = sess.get("category", "Unknown")
        attendance = sess.get("attendance", {})

        for uid, att in (attendance or {}).items():
            name = att.get("user_name", "Unknown")
            email = att.get("user_email", "unknown")
            status = att.get("status", "Not Present")

            if uid not in progress_summary:
                progress_summary[uid] = {
                    "name": name,
                    "email": email,
                    "sessions": 0,
                    "present": 0,
                    "absent": 0,
                    "details": []
                }

            progress_summary[uid]["sessions"] += 1
            if status == "Present":
                progress_summary[uid]["present"] += 1
            else:
                progress_summary[uid]["absent"] += 1

            progress_summary[uid]["details"].append({
                "session": session_title,
                "category": session_category,
                "status": status,
                "created_at": sess.get("created_at", "")
            })

    # Calculate progress percentage
    for uid, data in progress_summary.items():
        if data["sessions"] > 0:
            data["progress_percent"] = round((data["present"] / data["sessions"]) * 100, 1)
        else:
            data["progress_percent"] = 0

    return render_template("user_progress.html", users=progress_summary)


@app.route('/admin/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'admin' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('admin_login'))

    admin_email = session['admin'].strip()

    ref = db.reference('admin')
    admin_data = ref.get()  # {'email': ..., 'password': ...}

    if not isinstance(admin_data, dict):
        flash('Invalid admin data structure.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # ✅ Check if the session email matches Firebase email
    if admin_data.get('email', '').strip() != admin_email:
        flash('Session does not match admin data.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # ✅ If POST: update values
    if request.method == 'POST':
        updated_email = request.form.get('email', '').strip()
        updated_password = request.form.get('password', '').strip()

        if not updated_email or not updated_password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('edit_profile'))

        try:
            ref.update({
                'email': updated_email,
                'password': updated_password
            })
            session['admin'] = updated_email
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('edit_profile'))

    # ✅ GET request — render form
    return render_template('edit_profile.html', admin=admin_data)

@app.route("/all_counselors", methods=["GET", "POST"])
def all_counselors():
    ref = db.reference("conseling_signup")
    counselors = ref.get() or {}

    # Filters
    filter_type = request.args.get("type", "").strip()
    filter_gender = request.args.get("gender", "").strip()
    filter_location = request.args.get("location", "").strip()

    filtered = {}
    for cid, c in counselors.items():
        if not isinstance(c, dict):
            continue
        # Apply filters
        if filter_type and c.get("counseling") != filter_type:
            continue
        if filter_gender and c.get("gender") != filter_gender:
            continue
        if filter_location and filter_location.lower() not in c.get("location", "").lower():
            continue

        filtered[cid] = c

    return render_template(
        "all_counselors.html",
        counselors=filtered,
        filter_type=filter_type,
        filter_gender=filter_gender,
        filter_location=filter_location,
    )

@app.route("/donate", methods=["GET", "POST"])
def donate():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        amount = request.form.get("amount")
        message = request.form.get("message")

        if not name or not email or not amount:
            flash("⚠️ Please fill all required fields.", "danger")
            return redirect(url_for("donate"))

        # Save to Firebase
        ref = db.reference("donations")
        donation_id = str(uuid.uuid4())
        ref.child(donation_id).set({
            "name": name,
            "email": email,
            "phone": phone,
            "amount": amount,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash("✅ Thank you for your donation!", "success")
        return redirect(url_for("donate"))

    return render_template("donate.html")
@app.route("/volunteer", methods=["GET", "POST"])
def volunteer():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        skills = request.form.get("skills")
        availability = request.form.get("availability")
        message = request.form.get("message")

        if not name or not email or not phone:
            flash("⚠️ Please fill all required fields.", "danger")
            return redirect(url_for("volunteer"))

        ref = db.reference("volunteers")
        volunteer_id = str(uuid.uuid4())
        ref.child(volunteer_id).set({
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "availability": availability,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash("✅ Thank you for joining as a Volunteer!", "success")
        return redirect(url_for("volunteer"))

    return render_template("volunteer.html")



@app.route("/add_course", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not category:
            flash("⚠️ All fields are required!", "danger")
            return redirect(url_for("add_course"))

        # ✅ Dynamically collect lecture links
        lectures = []
        for key in request.form:
            if key.startswith("lecture_"):
                url = request.form.get(key).strip()
                if url:
                    lectures.append(url)

        if not lectures:
            flash("⚠️ Please add at least one lecture link.", "danger")
            return redirect(url_for("add_course"))

        # Save to Firebase
        course_id = str(uuid.uuid4())
        db.reference("courses").child(course_id).set({
            "title": title,
            "category": category,
            "lectures": lectures
        })

        flash("✅ Course added successfully!", "success")
        return redirect(url_for("view_courses"))

    return render_template("add_course.html")


@app.route("/view_courses")
def view_courses():
    ref = db.reference("courses")
    courses = ref.get() or {}

    return render_template("view_courses.html", courses=courses)
@app.route("/legal_support_cases")
def legal_support_cases():
    ref = db.reference("users")
    users = ref.get() or {}

    # Filter users who are approved AND have 'legal' in their categories
    legal_users = {
        uid: u for uid, u in users.items()
        if u.get("status") == "Approved" and "legal" in (u.get("categories") or [])
    }

    return render_template("legal_support_cases.html", users=legal_users)

@app.route("/assign_lawyer/<user_id>", methods=["GET", "POST"])
def assign_lawyer(user_id):
    user = db.reference("users").child(user_id).get()
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("legal_support_cases"))

    if request.method == "POST":
        lawyer_name = request.form.get("lawyer_name").strip()
        lawyer_email = request.form.get("lawyer_email").strip()

        if not lawyer_name or not lawyer_email:
            flash("Please enter both lawyer name and email.", "danger")
            return redirect(url_for("assign_lawyer", user_id=user_id))

        # Save assignment in Firebase
        assignment = {
            "user_id": user_id,
            "user_name": user["name"],
            "user_email": user["email"],
            "case_details": user["description"],
            "lawyer_name": lawyer_name,
            "lawyer_email": lawyer_email,
            "timestamp": str(datetime.now())
        }
        db.reference("assigned_lawyers").push(assignment)

        # Send email to user
        subject = "⚖️ Legal Support Assigned - SahaaraX"
        body = f"""
        Dear {user['name']},

        A legal support officer has been assigned to your case.

        🧑‍⚖️ Lawyer: {lawyer_name}  
        📧 Email: {lawyer_email}

        They will contact you soon regarding your legal support request.

        Regards,  
        SahaaraX Team
        """
        try:
            yag.send(user["email"], subject, body)
        except Exception as e:
            flash("⚠️ Failed to send email.", "warning")
            print("Email error:", e)

        flash("✅ Lawyer assigned and user notified.", "success")
        return redirect(url_for("legal_support_cases"))

    return render_template("assign_lawyer.html", user=user)


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()

    if not email:
        flash("⚠️ Please enter a valid email.", "danger")
        return redirect(request.referrer or url_for("home"))

    try:
        ref = db.reference("subscribers")
        subscribers = ref.get() or {}

        # ✅ Check if email already exists
        for sid, sub in subscribers.items():
            if sub.get("email") == email:
                flash("⚠️ This email is already subscribed!", "warning")
                return redirect(request.referrer or url_for("home"))

        # ✅ Add new subscriber
        subscriber_id = str(uuid.uuid4())
        ref.child(subscriber_id).set({
            "email": email,
            "subscribed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash("✅ Thank you for subscribing!", "success")
        return redirect(request.referrer or url_for("home"))

    except Exception as e:
        print("🔥 Firebase Error:", e)
        flash("⚠️ Could not connect to database. Try again later.", "danger")
        return redirect(request.referrer or url_for("home"))


@app.route("/subscribers", methods=["GET", "POST"])
def subscribers():
    ref = db.reference("subscribers")
    subscribers = ref.get() or {}

    total_subscribers = len(subscribers)

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not subject or not message:
            flash("⚠️ Please enter subject and message.", "danger")
            return redirect(url_for("subscribers"))

        emails = [sub.get("email") for sub in subscribers.values() if sub.get("email")]

        if not emails:
            flash("⚠️ No subscribers found!", "warning")
            return redirect(url_for("subscribers"))

        # ✅ Initialize yagmail once
        yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")

        sent_count = 0
        failed_count = 0

        for email in emails:
            try:
                yag.send(
                    to=email,
                    subject=subject,
                    contents=f"""
                    Dear Subscriber,

                    {message}

                    Regards,
                    SahaaraX Team
                    """
                )
                sent_count += 1
            except Exception as e:
                print(f"❌ Error sending to {email}: {e}")
                failed_count += 1

        flash(f"✅ Newsletter sent to {sent_count} subscribers! ❌ Failed: {failed_count}", "success")
        return redirect(url_for("subscribers"))

    return render_template("subscribers.html", subscribers=subscribers, total_subscribers=total_subscribers)

#---------------------------------------------------------------ai---------------------
# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'sexual_abuse_models')
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



# Target interpretations for each dataset
TARGET_INTERPRETATIONS = {
    'sexual_abuse': {
        0: {
            'name': 'Not Stable - Abuse indicators present',
            'description': 'Immediate intervention recommended. Multiple abuse indicators detected.',
            'color': 'danger',
            'icon': '🚨',
            'recommendation': 'Immediate professional intervention and safety planning required.'
        },
        1: {
            'name': 'Stable - No abuse indicators',
            'description': 'Patient appears to be in a safe environment. No immediate concerns.',
            'color': 'success',
            'icon': '✅',
            'recommendation': 'Continue regular monitoring and support.'
        },
        2: {
            'name': 'Further Session Needed',
            'description': 'Insufficient information or mixed indicators. Additional assessment required.',
            'color': 'warning',
            'icon': '⚠️',
            'recommendation': 'Schedule follow-up assessment for clearer evaluation.'
        }
    },
    'domestic_violence': {
        0: {
            'name': 'High Risk - Immediate Danger',
            'description': 'High risk of domestic violence detected. Immediate safety measures needed.',
            'color': 'danger',
            'icon': '🚨',
            'recommendation': 'Immediate safety planning and professional intervention required.'
        },
        1: {
            'name': 'Moderate Risk - Monitor Closely',
            'description': 'Moderate risk indicators present. Close monitoring recommended.',
            'color': 'warning',
            'icon': '⚠️',
            'recommendation': 'Enhanced monitoring and support services recommended.'
        },
        2: {
            'name': 'Low Risk - Stable Situation',
            'description': 'Low risk indicators. Situation appears stable.',
            'color': 'success',
            'icon': '✅',
            'recommendation': 'Continue with regular support and monitoring.'
        }
    },
    'psychological_support': {
        0: {
            'name': 'High Support Needs',
            'description': 'Significant psychological support needs identified.',
            'color': 'danger',
            'icon': '🚨',
            'recommendation': 'Immediate psychological intervention and support services needed.'
        },
        1: {
            'name': 'Moderate Support Needs',
            'description': 'Moderate psychological support requirements.',
            'color': 'warning',
            'icon': '⚠️',
            'recommendation': 'Regular psychological support and monitoring recommended.'
        },
        2: {
            'name': 'Low Support Needs',
            'description': 'Minimal psychological support needs at this time.',
            'color': 'success',
            'icon': '✅',
            'recommendation': 'Maintain current support level with periodic check-ins.'
        }
    }
}

# Global variables
datasets_data = {}
question_mappings = {}
models_loaded = {}
current_dataset = None


def convert_to_serializable(obj):
    """Convert numpy types to JSON serializable Python types"""
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    else:
        return obj


def create_fallback_encoders(dataset_key):
    """Create fallback encoders for datasets without trained encoders"""
    try:
        dataset_mappings = question_mappings.get(dataset_key, {})
        if not dataset_mappings:
            return None, None

        # Create category encoder
        category_encoder = LabelEncoder()
        categories = [q_info['category'] for q_info in dataset_mappings.values()]
        category_encoder.fit(categories)

        # Create cat_answer encoder
        cat_answer_encoder = LabelEncoder()
        cat_answer_combinations = []
        for q_info in dataset_mappings.values():
            category = q_info['category']
            for answer_value in q_info['meaning_map'].keys():
                cat_answer_combinations.append(f"{category}_{answer_value}")
        cat_answer_encoder.fit(cat_answer_combinations)

        return category_encoder, cat_answer_encoder

    except Exception as e:
        print(f"❌ Error creating fallback encoders for {dataset_key}: {str(e)}")
        return None, None


def load_dataset_data(dataset_key):
    """Load and prepare data for a specific dataset"""
    global datasets_data, question_mappings

    try:
        dataset_config = DATASETS[dataset_key]

        # Try multiple possible file paths
        possible_paths = [
            os.path.join(DATA_DIR, dataset_config['file']),
            os.path.join(BASE_DIR, 'data', dataset_config['file']),
            os.path.join(BASE_DIR, dataset_config['file']),
            r'C:\Users\computer\Desktop\saharax\data\\' + dataset_config['file']
        ]

        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                print(f"✅ Found {dataset_key} file at: {file_path}")
                break

        if not file_path:
            return False, f"{dataset_config['name']} file not found"

        # Load data based on file type
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        print(f"✅ {dataset_key} data loaded: {len(df)} rows, {len(df.columns)} columns")
        print(f"📊 Columns: {list(df.columns)}")

        # Store the dataframe
        datasets_data[dataset_key] = df

        # Create question mappings based on dataset structure
        question_mappings[dataset_key] = {}

        # Handle different dataset structures
        if dataset_key == 'sexual_abuse':
            # Sexual Abuse dataset structure
            for question_id in df['Question ID'].unique():
                question_data = df[df['Question ID'] == question_id]

                if len(question_data) == 0:
                    continue

                question_text = question_data['Question'].iloc[
                    0] if 'Question' in question_data.columns else f"Question {question_id}"
                category = question_data['Category'].iloc[0] if 'Category' in question_data.columns else "Unknown"

                if pd.isna(category):
                    category = "Uncategorized"

                answer_target_map = {}
                answer_meaning_map = {}

                for _, row in question_data.iterrows():
                    if pd.isna(row['Answer']) or pd.isna(row['Target']):
                        continue
                    try:
                        answer_val = int(float(row['Answer'])) if not pd.isna(row['Answer']) else 0
                        target_val = int(float(row['Target'])) if not pd.isna(row['Target']) else 0
                        answer_target_map[answer_val] = target_val

                        answer_meaning = row.get('Answer Meaning', f"Answer {answer_val}")
                        if pd.isna(answer_meaning):
                            answer_meaning = f"Answer {answer_val}"
                        answer_meaning_map[answer_val] = answer_meaning

                    except (ValueError, TypeError) as e:
                        print(f"⚠️ Warning: Could not process answer for Q{question_id}: {e}")
                        continue

                question_mappings[dataset_key][question_id] = {
                    'question': question_text,
                    'category': category,
                    'answer_map': answer_target_map,
                    'meaning_map': answer_meaning_map
                }

        else:
            # Domestic Violence and Psychological Support datasets
            # Assuming similar structure to sexual abuse dataset
            if 'Question ID' in df.columns:
                for question_id in df['Question ID'].unique():
                    question_data = df[df['Question ID'] == question_id]

                    if len(question_data) == 0:
                        continue

                    question_text = question_data['Question'].iloc[
                        0] if 'Question' in question_data.columns else f"Question {question_id}"
                    category = question_data['Category'].iloc[0] if 'Category' in question_data.columns else "Unknown"

                    if pd.isna(category):
                        category = "Uncategorized"

                    answer_target_map = {}
                    answer_meaning_map = {}

                    for _, row in question_data.iterrows():
                        if pd.isna(row['Answer']):
                            continue
                        try:
                            answer_val = int(float(row['Answer'])) if not pd.isna(row['Answer']) else 0
                            target_val = int(float(row['Target'])) if 'Target' in row and not pd.isna(
                                row['Target']) else 0
                            answer_target_map[answer_val] = target_val

                            answer_meaning = row.get('Answer Meaning', f"Answer {answer_val}")
                            if pd.isna(answer_meaning):
                                answer_meaning = f"Answer {answer_val}"
                            answer_meaning_map[answer_val] = answer_meaning

                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Warning: Could not process answer for Q{question_id}: {e}")
                            continue

                    question_mappings[dataset_key][question_id] = {
                        'question': question_text,
                        'category': category,
                        'answer_map': answer_target_map,
                        'meaning_map': answer_meaning_map
                    }
            else:
                # Alternative structure for datasets without Question ID
                for idx, row in df.iterrows():
                    question_id = f"Q{idx + 1:04d}"
                    question_text = row['Question'] if 'Question' in df.columns else f"Question {idx + 1}"

                    # Extract answer options and meanings
                    answer_target_map = {}
                    answer_meaning_map = {}

                    # Look for answer columns
                    answer_cols = [col for col in df.columns if 'Answer' in col or 'Option' in col]

                    if len(answer_cols) >= 1:
                        for i, answer_col in enumerate(answer_cols[:5]):
                            if not pd.isna(row[answer_col]):
                                answer_target_map[i] = i
                                answer_meaning_map[i] = str(row[answer_col])

                    # If no answer columns found, create default options
                    if not answer_target_map:
                        for i in range(0, 3):  # 0: No, 1: Yes, 2: Uncertain
                            answer_target_map[i] = i
                            answer_meaning_map[i] = ['No', 'Yes', 'Uncertain'][i]

                    category = row.get('Category', 'General')
                    if pd.isna(category):
                        category = "General"

                    question_mappings[dataset_key][question_id] = {
                        'question': question_text,
                        'category': category,
                        'answer_map': answer_target_map,
                        'meaning_map': answer_meaning_map
                    }

        print(f"✅ Created mappings for {len(question_mappings[dataset_key])} questions in {dataset_key}")
        return True, f"{dataset_config['name']} data loaded successfully"

    except Exception as e:
        print(f"❌ Error loading {dataset_key} data: {str(e)}")
        return False, f"Error loading {dataset_key} data: {str(e)}"


def load_models_for_dataset(dataset_key):
    """Load ML models for a specific dataset"""
    global models_loaded

    try:
        dataset_config = DATASETS[dataset_key]
        model_prefix = dataset_config['model_prefix']

        print(f"🔍 Loading models for {dataset_key} with prefix: {model_prefix}")

        # Model files for this dataset
        model_files = {
            'best_model': f'{model_prefix}_model.pkl',
            'category_encoder': f'{model_prefix}_category_encoder.pkl',
            'cat_answer_encoder': f'{model_prefix}_cat_answer_encoder.pkl'
        }

        # Check for missing files
        missing_files = []
        for name, filename in model_files.items():
            file_path = os.path.join(MODELS_DIR, filename)
            if not os.path.exists(file_path):
                missing_files.append(filename)
            else:
                print(f"✅ Found: {filename}")

        models = {}

        # Try to load the main model first
        main_model_path = os.path.join(MODELS_DIR, 'high_accuracy_assessment_model.pkl')
        if os.path.exists(main_model_path):
            models['best_model'] = joblib.load(main_model_path)
            print(f"✅ Loaded main model: high_accuracy_assessment_model.pkl")
        else:
            return False, "Main model file not found"

        # Handle encoders - use fallback if specific encoders don't exist
        if dataset_key == 'sexual_abuse':
            # For sexual abuse, use the trained encoders
            for encoder_name in ['category_encoder', 'cat_answer_encoder']:
                encoder_path = os.path.join(MODELS_DIR, f'{encoder_name}.pkl')
                if os.path.exists(encoder_path):
                    models[encoder_name] = joblib.load(encoder_path)
                    print(f"✅ Loaded {encoder_name}: {encoder_name}.pkl")
                else:
                    return False, f"Encoder {encoder_name} not found"
        else:
            # For other datasets, create fallback encoders
            print(f"🔄 Creating fallback encoders for {dataset_key}")
            category_encoder, cat_answer_encoder = create_fallback_encoders(dataset_key)
            if category_encoder and cat_answer_encoder:
                models['category_encoder'] = category_encoder
                models['cat_answer_encoder'] = cat_answer_encoder
                print(f"✅ Created fallback encoders for {dataset_key}")
            else:
                return False, f"Could not create fallback encoders for {dataset_key}"

        models_loaded[dataset_key] = models
        print(f"✅ All models loaded for {dataset_key}")
        return True, f"Models loaded for {dataset_key}"

    except Exception as e:
        print(f"❌ Error loading models for {dataset_key}: {str(e)}")
        return False, f"Error loading models for {dataset_key}: {str(e)}"


def predict_single_question(dataset_key, question_id, user_answer):
    """Make prediction for a single question"""
    if dataset_key not in models_loaded:
        return None, None, f"Models not loaded for {dataset_key}"

    if question_id not in question_mappings.get(dataset_key, {}):
        return None, None, f"Question ID {question_id} not found in {dataset_key}"

    try:
        q_info = question_mappings[dataset_key][question_id]
        category = q_info['category']
        question_text = q_info['question']
        models = models_loaded[dataset_key]

        # Convert inputs to features
        qid_encoded = int(question_id[1:]) if question_id.startswith('Q') else int(question_id)
        answer_value = int(user_answer)

        # Encode category - handle unseen labels
        try:
            category_encoded = int(models['category_encoder'].transform([category])[0])
        except ValueError:
            # If category not seen during training, use a default value
            print(f"⚠️ Category '{category}' not seen during training, using default encoding")
            category_encoded = 0  # Default encoding

        # Calculate question length
        question_length = int(len(question_text))

        # Create category-answer combination - handle unseen combinations
        cat_answer_combo = f"{category}_{user_answer}"
        try:
            cat_answer_encoded = int(models['cat_answer_encoder'].transform([cat_answer_combo])[0])
        except ValueError:
            # If combination not seen during training, use a default value
            print(f"⚠️ Combination '{cat_answer_combo}' not seen during training, using default encoding")
            cat_answer_encoded = 0  # Default encoding

        # Create feature vector
        features = np.array([[qid_encoded, answer_value, category_encoded, question_length, cat_answer_encoded]])

        # Make prediction
        prediction = int(models['best_model'].predict(features)[0])
        prediction_proba = [float(prob) for prob in models['best_model'].predict_proba(features)[0]]

        return prediction, prediction_proba, None

    except Exception as e:
        return None, None, f"Prediction error: {str(e)}"


def predict_assessment_session(dataset_key, user_responses):
    """Predict for complete assessment session"""
    if dataset_key not in models_loaded:
        return None, f"Models not loaded for {dataset_key}"

    try:
        predictions = []
        total_confidence = 0
        outcome_counts = {0: 0, 1: 0, 2: 0}

        for question_id, user_answer in user_responses.items():
            prediction, probabilities, error = predict_single_question(dataset_key, question_id, user_answer)

            if error:
                print(f"⚠️ Prediction error for {question_id}: {error}")
                continue

            confidence = float(max(probabilities))
            total_confidence += confidence
            outcome_counts[prediction] += 1

            predictions.append({
                'question_id': question_id,
                'question': question_mappings[dataset_key][question_id]['question'],
                'user_answer': int(user_answer),
                'answer_meaning': question_mappings[dataset_key][question_id]['meaning_map'].get(int(user_answer),
                                                                                                 f"Answer {user_answer}"),
                'prediction': int(prediction),
                'confidence': float(confidence),
                'interpretation': TARGET_INTERPRETATIONS[dataset_key][int(prediction)]['name']
            })

        if not predictions:
            return None, "No valid predictions could be made"

        # Determine overall assessment
        max_outcome = max(outcome_counts, key=outcome_counts.get)
        avg_confidence = float(total_confidence / len(predictions))

        overall_result = {
            'dataset': dataset_key,
            'dataset_name': DATASETS[dataset_key]['name'],
            'outcome': int(max_outcome),
            'outcome_name': TARGET_INTERPRETATIONS[dataset_key][int(max_outcome)]['name'],
            'outcome_description': TARGET_INTERPRETATIONS[dataset_key][int(max_outcome)]['description'],
            'outcome_icon': TARGET_INTERPRETATIONS[dataset_key][int(max_outcome)]['icon'],
            'outcome_color': TARGET_INTERPRETATIONS[dataset_key][int(max_outcome)]['color'],
            'recommendation': TARGET_INTERPRETATIONS[dataset_key][int(max_outcome)]['recommendation'],
            'confidence': float(avg_confidence),
            'outcome_breakdown': {int(k): int(v) for k, v in outcome_counts.items()},
            'total_questions': int(len(predictions)),
            'predictions': predictions,
            'assessment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return overall_result, None

    except Exception as e:
        return None, f"Assessment error: {str(e)}"


@app.route('/ai')
def ai():
    # Login check
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    if not counselor:
        flash("Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))

    # Get all assignments for this counselor
    assigned_ref = db.reference("assign_conseler")
    assignments = assigned_ref.get() or {}

    counselor_assignments = []
    counselor_datasets = set()  # Track unique datasets assigned to this counselor

    for aid, assign in assignments.items():
        if assign.get("counselor_id") != counselor_id:
            continue

        assign["assignment_id"] = aid
        dataset_key = assign.get("dataset_key")

        # Add dataset info if valid
        if dataset_key in DATASETS:
            assign["dataset_info"] = DATASETS[dataset_key]
            counselor_datasets.add(dataset_key)  # Track this dataset

        counselor_assignments.append(assign)

    # Get selected dataset from URL (e.g., /ai?dataset=domestic_violence)
    selected_dataset = request.args.get("dataset")

    # Validate selected dataset - must be in counselor's assigned datasets
    if selected_dataset and selected_dataset not in counselor_datasets:
        selected_dataset = None

    # If no valid selection, use first assigned dataset as default
    if not selected_dataset and counselor_datasets:
        selected_dataset = list(counselor_datasets)[0]

    # Filter assignments to show only selected dataset
    assigned_users = []
    for assign in counselor_assignments:
        if selected_dataset and assign.get("dataset_key") == selected_dataset:
            assigned_users.append(assign)

    # Only show datasets that are assigned to this counselor
    visible_datasets = {
        key: DATASETS[key]
        for key in counselor_datasets
    }

    return render_template(
        'ai.html',
        user=counselor,
        assigned_users=assigned_users,
        datasets=visible_datasets,  # Only counselor's datasets
        selected_dataset=selected_dataset
    )

@app.route('/api/datasets')
def get_datasets():
    """Get all available datasets"""
    try:
        datasets_list = []
        for key, config in DATASETS.items():
            datasets_list.append({
                'key': key,
                'name': config['name'],
                'description': config['description'],
                'icon': config['icon'],
                'loaded': key in datasets_data
            })

        return jsonify({
            'success': True,
            'datasets': datasets_list,
            'total_datasets': len(datasets_list)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/select-dataset', methods=['POST'])
def select_dataset():
    """Select and load a specific dataset"""
    global current_dataset

    try:
        data = request.get_json()
        dataset_key = data.get('dataset_key')

        if dataset_key not in DATASETS:
            return jsonify({'success': False, 'message': 'Invalid dataset selected'})

        print(f"🔄 Loading dataset: {dataset_key}")

        # Load dataset data
        success, message = load_dataset_data(dataset_key)
        if not success:
            return jsonify({'success': False, 'message': message})

        # Load models for this dataset
        success, message = load_models_for_dataset(dataset_key)
        if not success:
            return jsonify({'success': False, 'message': message})

        current_dataset = dataset_key
        session['current_dataset'] = dataset_key

        return jsonify({
            'success': True,
            'message': f"{DATASETS[dataset_key]['name']} loaded successfully",
            'dataset': {
                'key': dataset_key,
                'name': DATASETS[dataset_key]['name'],
                'description': DATASETS[dataset_key]['description'],
                'icon': DATASETS[dataset_key]['icon']
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/categories')
def get_categories():
    """Get categories for current dataset"""
    global current_dataset, question_mappings

    try:
        if not current_dataset:
            return jsonify({'success': False, 'message': 'No dataset selected'})

        dataset_mappings = question_mappings.get(current_dataset, {})
        if not dataset_mappings:
            return jsonify({'success': False, 'message': 'No questions loaded for current dataset'})

        # Extract unique categories
        categories = set()
        for q_info in dataset_mappings.values():
            category = q_info['category']
            if category is None:
                continue
            if isinstance(category, float) and math.isnan(category):
                continue
            if str(category).strip().lower() in ['nan', 'null', 'none', '']:
                continue
            categories.add(str(category).strip())

        categories_list = sorted(list(categories))
        print(f"📋 API: Returning {len(categories_list)} categories for {current_dataset}")

        return jsonify({
            'success': True,
            'categories': categories_list,
            'total_categories': len(categories_list),
            'dataset': current_dataset
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/questions')
def get_questions():
    """Get questions by category for current dataset"""
    global current_dataset, question_mappings

    try:
        category = request.args.get('category')
        if not category:
            return jsonify({'success': False, 'message': 'Category parameter required'})

        if not current_dataset:
            return jsonify({'success': False, 'message': 'No dataset selected'})

        dataset_mappings = question_mappings.get(current_dataset, {})
        if not dataset_mappings:
            return jsonify({'success': False, 'message': 'No questions loaded for current dataset'})

        category_questions = []
        for q_id, q_info in dataset_mappings.items():
            q_category = str(q_info['category']).strip() if q_info['category'] is not None else ""
            if q_category == category:
                response_options = []
                for answer_value, answer_meaning in q_info['meaning_map'].items():
                    response_options.append({
                        'value': int(answer_value),
                        'label': str(answer_meaning)
                    })

                # Sort response options by value
                response_options.sort(key=lambda x: x['value'])

                category_questions.append({
                    'question_id': q_id,
                    'question': q_info['question'],
                    'response_options': response_options
                })

        print(f"📝 API: Found {len(category_questions)} questions for category: {category} in {current_dataset}")
        return jsonify({
            'success': True,
            'questions': category_questions,
            'dataset': current_dataset
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/predict', methods=['POST'])
def predict():
    """Make prediction based on user responses"""
    global current_dataset

    try:
        if not current_dataset:
            return jsonify({'success': False, 'message': 'No dataset selected'})

        data = request.get_json()
        user_responses = data.get('responses', {})

        if not user_responses:
            return jsonify({'success': False, 'message': 'No responses provided'})

        print(f"🎯 Making prediction for {len(user_responses)} responses in {current_dataset}")

        # REPLACE THIS WITH YOUR ACTUAL PREDICTION LOGIC
        # This is sample data - replace with your model prediction
        result = generate_sample_result(user_responses)

        # Convert to JSON serializable format
        result_serializable = convert_to_serializable(result)

        # Store result in session for download
        session['last_result'] = result_serializable
        session['last_result_timestamp'] = datetime.now().isoformat()

        print("✅ Result stored in session successfully")

        return jsonify({
            'success': True,
            'result': result_serializable
        })

    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


def generate_sample_result(user_responses):
    """Generate sample result - REPLACE WITH YOUR ACTUAL MODEL"""
    predictions = []

    for question_id, response_value in user_responses.items():
        predictions.append({
            'question_id': question_id,
            'question': f'Question text for {question_id}',
            'user_response': response_value,
            'answer_meaning': 'Yes' if response_value == 1 else 'No' if response_value == 0 else 'Uncertain',
            'prediction': response_value,
            'confidence': 0.85
        })

    # Calculate outcome
    high_risk_count = sum(1 for p in predictions if p['prediction'] == 1)
    low_risk_count = sum(1 for p in predictions if p['prediction'] == 0)
    uncertain_count = sum(1 for p in predictions if p['prediction'] == 2)

    if high_risk_count > low_risk_count:
        outcome_name = 'High Risk - Immediate Intervention Required'
        outcome_color = 'danger'
        outcome_icon = '🚨'
        outcome_description = 'The assessment indicates high risk factors requiring immediate professional intervention.'
        recommendation = 'Immediate referral to mental health professional recommended. Do not leave patient unattended.'
    else:
        outcome_name = 'Low Risk - Continue Monitoring'
        outcome_color = 'success'
        outcome_icon = '✅'
        outcome_description = 'The assessment indicates low immediate risk, but continued monitoring is recommended.'
        recommendation = 'Continue regular check-ins. Monitor for any changes in behavior or symptoms.'

    result = {
        'dataset_name': current_dataset.title() if current_dataset else 'Assessment',
        'outcome_name': outcome_name,
        'outcome_color': outcome_color,
        'outcome_icon': outcome_icon,
        'outcome_description': outcome_description,
        'recommendation': recommendation,
        'confidence': 0.87,
        'total_questions': len(predictions),
        'assessment_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        'outcome_breakdown': [high_risk_count, low_risk_count, uncertain_count],
        'predictions': predictions
    }

    return result


@app.route('/api/download-report/<format_type>', methods=['GET'])
def download_report(format_type):
    """Download assessment report in specified format"""
    try:
        result = session.get('last_result')

        if not result:
            return jsonify({
                'success': False,
                'message': 'No assessment result available. Please complete an assessment first.'
            }), 404

        print(f"📥 Generating {format_type.upper()} report...")

        if format_type == 'pdf':
            return generate_pdf_report(result)
        elif format_type == 'json':
            return generate_json_report(result)
        elif format_type == 'csv':
            return generate_csv_report(result)
        else:
            return jsonify({
                'success': False,
                'message': f'Invalid format: {format_type}'
            }), 400

    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error generating report: {str(e)}'
        }), 500


def generate_pdf_report(result):
    """Generate comprehensive PDF report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        elements = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=15,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )

        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )

        # Title
        elements.append(Paragraph("Multi-Dataset Assessment Report", title_style))
        elements.append(Spacer(1, 20))

        # Assessment Info Box
        info_data = [
            ['Assessment Type:', result.get('dataset_name', 'N/A')],
            ['Assessment Date:', result.get('assessment_date', 'N/A')],
            ['Total Questions:', str(result.get('total_questions', 0))],
            ['Overall Outcome:', result.get('outcome_name', 'N/A')],
            ['Confidence Level:', f"{result.get('confidence', 0) * 100:.1f}%"]
        ]

        info_table = Table(info_data, colWidths=[2.5 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 25))

        # Outcome Description
        elements.append(Paragraph("Assessment Outcome", heading_style))
        outcome_text = result.get('outcome_description', 'No description available')
        elements.append(Paragraph(outcome_text, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Professional Recommendations
        elements.append(Paragraph("Professional Recommendations", heading_style))
        recommendation_text = result.get('recommendation', 'No recommendations available')
        elements.append(Paragraph(recommendation_text, styles['Normal']))
        elements.append(Spacer(1, 25))

        # Risk Breakdown
        elements.append(Paragraph("Risk Indicator Breakdown", heading_style))
        breakdown = result.get('outcome_breakdown', [0, 0, 0])

        breakdown_data = [
            ['Risk Level', 'Count', 'Description'],
            ['High Risk', str(breakdown[0]), 'Requires immediate attention'],
            ['Low Risk', str(breakdown[1]), 'Positive indicators'],
            ['Medium Risk/Uncertain', str(breakdown[2]), 'Needs monitoring']
        ]

        breakdown_table = Table(breakdown_data, colWidths=[2 * inch, 1.5 * inch, 3 * inch])
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fee2e2')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#d1fae5')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fef3c7')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8)
        ]))

        elements.append(breakdown_table)
        elements.append(PageBreak())

        # Detailed Question Analysis
        elements.append(Paragraph("Detailed Question Analysis", heading_style))
        elements.append(Spacer(1, 15))

        predictions = result.get('predictions', [])
        risk_labels = {0: 'High Risk', 1: 'Low Risk', 2: 'Medium Risk/Uncertain'}
        risk_colors = {
            0: colors.HexColor('#fee2e2'),
            1: colors.HexColor('#d1fae5'),
            2: colors.HexColor('#fef3c7')
        }

        for i, pred in enumerate(predictions):
            question_data = [
                [Paragraph(f"<b>Question {i + 1}: {pred.get('question', 'N/A')}</b>", styles['Normal'])],
                [f"Response: {pred.get('answer_meaning', 'N/A')}"],
                [
                    f"Risk Level: {risk_labels.get(pred.get('prediction', 2), 'Unknown')} | Confidence: {pred.get('confidence', 0) * 100:.1f}%"]
            ]

            question_table = Table(question_data, colWidths=[6.5 * inch])

            pred_value = pred.get('prediction', 2)
            bg_color = risk_colors.get(pred_value, colors.white)

            question_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), bg_color),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))

            elements.append(question_table)
            elements.append(Spacer(1, 12))

        # Footer
        elements.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            footer_style
        ))
        elements.append(Paragraph(
            "This report is confidential and intended for professional use only.",
            footer_style
        ))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        filename = f'assessment_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ PDF Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def generate_json_report(result):
    """Generate JSON report"""
    try:
        # Add metadata
        report = {
            'metadata': {
                'report_type': 'Multi-Dataset Assessment Report',
                'generated_at': datetime.now().isoformat(),
                'version': '1.0'
            },
            'assessment_data': result
        }

        json_data = json.dumps(report, indent=2, ensure_ascii=False)
        buffer = BytesIO(json_data.encode('utf-8'))
        buffer.seek(0)

        filename = f'assessment_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ JSON Generation Error: {str(e)}")
        raise


def generate_csv_report(result):
    """Generate CSV report"""
    try:
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Multi-Dataset Assessment Report'])
        writer.writerow(['Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Summary Section
        writer.writerow(['ASSESSMENT SUMMARY'])
        writer.writerow(['Field', 'Value'])
        writer.writerow(['Dataset', result.get('dataset_name', 'N/A')])
        writer.writerow(['Outcome', result.get('outcome_name', 'N/A')])
        writer.writerow(['Confidence', f"{result.get('confidence', 0) * 100:.1f}%"])
        writer.writerow(['Total Questions', result.get('total_questions', 0)])
        writer.writerow(['Assessment Date', result.get('assessment_date', 'N/A')])
        writer.writerow([])

        # Outcome Description
        writer.writerow(['OUTCOME DESCRIPTION'])
        writer.writerow([result.get('outcome_description', 'N/A')])
        writer.writerow([])

        # Recommendations
        writer.writerow(['PROFESSIONAL RECOMMENDATIONS'])
        writer.writerow([result.get('recommendation', 'N/A')])
        writer.writerow([])

        # Risk Breakdown
        writer.writerow(['RISK BREAKDOWN'])
        writer.writerow(['Risk Level', 'Count', 'Description'])
        breakdown = result.get('outcome_breakdown', [0, 0, 0])
        writer.writerow(['High Risk', breakdown[0], 'Requires immediate attention'])
        writer.writerow(['Low Risk', breakdown[1], 'Positive indicators'])
        writer.writerow(['Medium Risk/Uncertain', breakdown[2], 'Needs monitoring'])
        writer.writerow([])

        # Detailed Analysis
        writer.writerow(['DETAILED QUESTION ANALYSIS'])
        writer.writerow(['Question #', 'Question ID', 'Question', 'Response', 'Risk Level', 'Confidence'])

        predictions = result.get('predictions', [])
        risk_labels = {0: 'High Risk', 1: 'Low Risk', 2: 'Medium Risk/Uncertain'}

        for i, pred in enumerate(predictions):
            writer.writerow([
                i + 1,
                pred.get('question_id', 'N/A'),
                pred.get('question', 'N/A'),
                pred.get('answer_meaning', 'N/A'),
                risk_labels.get(pred.get('prediction', 2), 'Unknown'),
                f"{pred.get('confidence', 0) * 100:.1f}%"
            ])

        # Convert to bytes
        buffer = BytesIO(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel
        buffer.seek(0)

        filename = f'assessment_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return send_file(
            buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ CSV Generation Error: {str(e)}")
        raise


@app.route('/api/status')
def status():
    """Get application status"""
    global current_dataset, datasets_data, models_loaded

    try:
        status_info = {
            'current_dataset': current_dataset,
            'datasets_loaded': list(datasets_data.keys()),
            'models_loaded': list(models_loaded.keys()),
            'base_directory': BASE_DIR
        }

        if current_dataset:
            dataset_mappings = question_mappings.get(current_dataset, {})
            status_info['current_dataset_questions'] = len(dataset_mappings)

            if dataset_mappings:
                categories = set()
                for q_info in dataset_mappings.values():
                    category = q_info['category']
                    if category is None or (isinstance(category, float) and math.isnan(category)):
                        continue
                    if str(category).strip().lower() in ['nan', 'null', 'none', '']:
                        continue
                    categories.add(str(category).strip())

                status_info['current_dataset_categories'] = sorted(list(categories))
                status_info['current_dataset_categories_count'] = len(categories)

        print(f"📊 Status: Current={current_dataset}, Datasets={len(datasets_data)}, Models={len(models_loaded)}")
        return jsonify({'success': True, 'status': status_info})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/current-dataset')
def get_current_dataset():
    """Get current dataset information"""
    global current_dataset

    try:
        if not current_dataset:
            return jsonify({'success': False, 'message': 'No dataset selected'})

        dataset_config = DATASETS[current_dataset]
        return jsonify({
            'success': True,
            'dataset': {
                'key': current_dataset,
                'name': dataset_config['name'],
                'description': dataset_config['description'],
                'icon': dataset_config['icon']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/debug/data')
def debug_data():
    """Debug endpoint to check data loading"""
    global current_dataset, datasets_data, question_mappings

    try:
        if not current_dataset:
            return jsonify({'success': False, 'message': 'No dataset selected'})

        df = datasets_data.get(current_dataset)
        dataset_mappings = question_mappings.get(current_dataset, {})

        debug_info = {
            'current_dataset': current_dataset,
            'dataframe_shape': df.shape if df is not None else None,
            'dataframe_columns': list(df.columns) if df is not None else [],
            'question_mappings_count': len(dataset_mappings),
            'sample_questions': {}
        }

        if dataset_mappings:
            for i, (q_id, q_info) in enumerate(list(dataset_mappings.items())[:3]):
                debug_info['sample_questions'][q_id] = {
                    'category': q_info['category'],
                    'question_preview': q_info['question'][:100] + '...' if len(q_info['question']) > 100 else q_info[
                        'question'],
                    'available_answers': list(q_info['meaning_map'].items())
                }

        return jsonify({'success': True, 'debug_info': debug_info})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


def initialize_application():
    """Initialize the application on startup"""
    print("=" * 70)
    print("Multi-Dataset Assessment Dashboard - PRODUCTION")
    print("=" * 70)
    print(f"📁 Base directory: {BASE_DIR}")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"🤖 Models directory: {MODELS_DIR}")

    # Check available datasets
    print("\n📊 Checking available datasets...")
    for dataset_key, config in DATASETS.items():
        file_found = False
        possible_paths = [
            os.path.join(DATA_DIR, config['file']),
            os.path.join(BASE_DIR, 'data', config['file']),
            os.path.join(BASE_DIR, config['file']),
            r'C:\Users\computer\Desktop\saharax\data\\' + config['file']
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ {config['name']}: Found at {path}")
                file_found = True
                break

        if not file_found:
            print(f"❌ {config['name']}: File not found")

    print(f"\n🎯 Available datasets: {len(DATASETS)}")
    for key, config in DATASETS.items():
        print(f"   • {config['icon']} {config['name']}: {config['description']}")


# Manual test result files (PDF/CSV/images etc.)
TEST_UPLOAD_FOLDER = os.path.join("static", "test_results")
os.makedirs(TEST_UPLOAD_FOLDER, exist_ok=True)

@app.route("/counseling_user_tests/<user_id>", methods=["GET", "POST"])
def counseling_user_tests(user_id):
    # ✅ Login check
    if "counseling_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]

    # ✅ Counselor data
    counselor_ref = db.reference("conseling_signup").child(counselor_id)
    counselor = counselor_ref.get()
    if not counselor:
        flash("Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))

    # ✅ Check: kya yeh user is counselor ka assigned user hai?
    assignments_ref = db.reference("assign_conseler")
    assignments = assignments_ref.get() or {}

    is_assigned = False
    assignment_info = None

    for aid, a in assignments.items():
        if not isinstance(a, dict):
            continue

        if a.get("user_id") == user_id and a.get("counselor_id") == counselor_id:
            is_assigned = True
            assignment_info = a.copy()
            assignment_info["assignment_id"] = aid
            break

    if not is_assigned:
        flash("⚠️ You are not assigned to this user.", "danger")
        return redirect(url_for("counseling_dashboard"))

    # ✅ User data
    user_ref = db.reference("users").child(user_id)
    user = user_ref.get()
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("counseling_dashboard"))

    # ✅ Manual tests path:
    # manual_tests / counselor_id / user_id / test_id
    manual_tests_ref = db.reference("manual_tests").child(counselor_id).child(user_id)
    tests = manual_tests_ref.get() or {}

    saved = False  # front-end animation ke liye flag

    # ✅ Agar counselor naya result upload kare
    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        result_status = request.form.get("result_status", "").strip()  # clear / not_clear / continue

        file_obj = request.files.get("result_file")

        # Basic validation
        if not file_obj or not file_obj.filename:
            flash("⚠️ Please select a file to upload.", "warning")
            return redirect(url_for("counseling_user_tests", user_id=user_id))

        if not comment:
            flash("⚠️ Please write a comment for this test.", "warning")
            return redirect(url_for("counseling_user_tests", user_id=user_id))

        if not result_status:
            flash("⚠️ Please select a status.", "warning")
            return redirect(url_for("counseling_user_tests", user_id=user_id))

        # 📎 Save file
        original_name = file_obj.filename
        filename = secure_filename(original_name)
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{user_id}_{counselor_id}_{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(TEST_UPLOAD_FOLDER, unique_name)
        os.makedirs(TEST_UPLOAD_FOLDER, exist_ok=True)
        file_obj.save(save_path)

        file_rel_path = f"test_results/{unique_name}"  # static se relative

        # ✅ New manual test record
        test_id = str(uuid.uuid4())
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        manual_tests_ref.child(test_id).set({
            "test_id": test_id,
            "created_at": now_str,
            "status": result_status,                # clear / not_clear / continue
            "comment": comment,
            "file_path": file_rel_path,
            "file_original_name": original_name,
            "counselor_id": counselor_id,
            "counselor_name": counselor.get("name"),
        })

        flash("✅ Test file & comment saved successfully.", "success")
        saved = True

        # Refresh tests
        tests = manual_tests_ref.get() or {}

    # ✅ Tests ko list bana do (latest pehle)
    tests_list = []
    for tid, t in tests.items():
        if not isinstance(t, dict):
            continue
        item = t.copy()
        item["test_id"] = tid
        tests_list.append(item)

    tests_list.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    tests_count = len(tests_list)
    completed_tests = sum(1 for t in tests_list if str(t.get("status", "")).lower() == "clear")

    # ✅ Classes / attendance (yehi counselor + user)
    classes_ref = db.reference("counseling_classes").child(counselor_id).child(user_id)
    classes_data = classes_ref.get() or {}

    classes_list = []
    total_classes = 0
    completed_classes = 0

    for cid, c in classes_data.items():
        if not isinstance(c, dict):
            continue
        item = c.copy()
        item["class_id"] = cid
        classes_list.append(item)

        total_classes += 1
        if str(c.get("status", "")).lower() == "completed":
            completed_classes += 1

    classes_list.sort(
        key=lambda x: (x.get("date", ""), x.get("time", ""))
    )

    return render_template(
        "counseling_user_tests.html",
        counselor=counselor,
        user=user,
        user_id=user_id,
        assignment=assignment_info,
        tests=tests_list,
        tests_count=tests_count,
        completed_tests=completed_tests,
        classes=classes_list,
        total_classes=total_classes,
        completed_classes=completed_classes,
        saved=saved
    )


@app.route("/admin_results", methods=["GET", "POST"])
def admin_results():
    # ✅ Admin login check
    if "admin" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("admin_login"))

    admin_email = session["admin"]

    manual_ref = db.reference("manual_tests")
    final_ref = db.reference("final_results")

    # ------------------- POST: admin final result save karega -------------------
    if request.method == "POST":
        counselor_id = request.form.get("counselor_id", "").strip()
        user_id = request.form.get("user_id", "").strip()
        test_id = request.form.get("test_id", "").strip()
        final_status = request.form.get("final_status", "").strip()      # approve / flag / followup
        admin_comment = request.form.get("admin_comment", "").strip()

        if not counselor_id or not user_id or not test_id:
            flash("⚠️ Invalid test reference.", "danger")
            return redirect(url_for("admin_results"))

        if not final_status:
            flash("⚠️ Please select final status.", "warning")
            return redirect(url_for("admin_results"))

        if not admin_comment:
            flash("⚠️ Please write your final comment.", "warning")
            return redirect(url_for("admin_results"))

        # Manual test record read karo
        test_data = manual_ref.child(counselor_id).child(user_id).child(test_id).get()
        if not test_data:
            flash("⚠️ Test record not found.", "danger")
            return redirect(url_for("admin_results"))

        # ✅ User & Counselor detail fresh fetch (taake Unknown na aaye)
        users_data = db.reference("users").get() or {}
        counselors_data = db.reference("conseling_signup").get() or {}

        user_data = users_data.get(user_id, {})
        counselor_data = counselors_data.get(counselor_id, {})

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ------------------- final_results me push -------------------
        final_payload = {
            "user_id": user_id,
            "user_name": test_data.get("user_name") or user_data.get("name", "Unknown User"),
            "user_email": test_data.get("user_email") or user_data.get("email", ""),

            "counselor_id": counselor_id,
            "counselor_name": test_data.get("counselor_name") or counselor_data.get("name", "Unknown Counselor"),
            "counselor_email": counselor_data.get("email", ""),

            "test_id": test_id,
            "manual_status": test_data.get("status"),
            "manual_comment": test_data.get("comment"),
            "file_path": test_data.get("file_path"),
            "file_original_name": test_data.get("file_original_name"),

            "admin_final_status": final_status,           # approve / flag / followup
            "admin_comment": admin_comment,
            "admin_email": admin_email,

            "created_at": test_data.get("created_at"),
            "finalized_at": now_str,
        }

        # user ke final feed me push karo
        final_id = final_ref.child(user_id).push(final_payload).key

        # ------------------- manual_tests record update -------------------
        manual_ref.child(counselor_id).child(user_id).child(test_id).update({
            "finalized": True,
            "final_status": final_status,
            "finalized_at": now_str,
            "admin_email": admin_email,
            "admin_comment": admin_comment,
            "final_result_id": final_id,
        })

        flash("✅ Final result saved in admin feed.", "success")
        return redirect(url_for("admin_results"))

    # ------------------- GET: feed banaana -------------------
    manual_all = manual_ref.get() or {}

    # yahan se Unknown problem solve karenge:
    users_data = db.reference("users").get() or {}
    counselors_data = db.reference("conseling_signup").get() or {}

    feed = []
    total_tests = 0
    finalized_count = 0
    pending_count = 0

    for counselor_id, users_block in manual_all.items():
        if not isinstance(users_block, dict):
            continue

        for user_id, tests_block in users_block.items():
            if not isinstance(tests_block, dict):
                continue

            # related user & counselor info ek hi baar nikaal lo
            user_data = users_data.get(user_id, {})
            counselor_data = counselors_data.get(counselor_id, {})

            for test_id, t in tests_block.items():
                if not isinstance(t, dict):
                    continue

                item = t.copy()
                item["counselor_id"] = counselor_id
                item["user_id"] = user_id
                item["test_id"] = test_id

                # 🔁 Yahan pe guaranteed naam/email set kar rahe hain:
                item["user_name"] = item.get("user_name") or user_data.get("name", "Unknown User")
                item["user_email"] = item.get("user_email") or user_data.get("email", "")
                item["counselor_name"] = item.get("counselor_name") or counselor_data.get("name", "Unknown Counselor")
                item["counselor_email"] = counselor_data.get("email", "")

                finalized = bool(item.get("finalized"))
                item["is_finalized"] = finalized

                feed.append(item)
                total_tests += 1
                if finalized:
                    finalized_count += 1
                else:
                    pending_count += 1

    # Latest tests sab se upar
    feed.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return render_template(
        "admin_results.html",
        admin_email=admin_email,
        feed=feed,
        total_tests=total_tests,
        finalized_count=finalized_count,
        pending_count=pending_count
    )

@app.route("/child_awareness_signup", methods=["GET", "POST"])
def child_awareness_signup():

    if "admin" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("admin_login"))

    admin_email = session["admin"]

    if request.method == "POST":
        def is_alpha(value):
            return re.fullmatch(r"[A-Za-z\s]+", value)

        def is_valid_email(value):
            return re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value)

        def is_valid_phone(value):
            return re.fullmatch(r"\d{11}", value)

        # ------- Form values -------
        name = request.form.get("name", "").strip()
        father_name = request.form.get("father_name", "").strip()
        email = request.form.get("email", "").strip()
        gender = request.form.get("gender", "")
        awareness_area = request.form.get("awareness_area", "").strip()
        dob = request.form.get("dob", "")
        phone = request.form.get("phone", "").strip()
        availability = request.form.get("availability", "").strip()
        location = request.form.get("location", "").strip()

        # ------- Validations -------
        if not is_alpha(name):
            flash("Name must contain only alphabets.", "danger")
            return redirect(url_for("child_awareness_signup"))

        if not is_alpha(father_name):
            flash("Father Name must contain only alphabets.", "danger")
            return redirect(url_for("child_awareness_signup"))

        if not is_valid_email(email):
            flash("Invalid email format.", "danger")
            return redirect(url_for("child_awareness_signup"))

        if not is_valid_phone(phone):
            flash("Phone number must be exactly 11 digits.", "danger")
            return redirect(url_for("child_awareness_signup"))

        if not dob:
            flash("Date of birth is required.", "danger")
            return redirect(url_for("child_awareness_signup"))

        try:
            datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            flash("Date of birth format should be YYYY-MM-DD.", "danger")
            return redirect(url_for("child_awareness_signup"))

        if not awareness_area:
            flash("Please select awareness area.", "danger")
            return redirect(url_for("child_awareness_signup"))

        # ✅ Duplicate check (email / phone) in awareness_signup
        ref = db.reference("awareness_signup")
        existing = ref.get() or {}

        for uid, c in existing.items():
            if str(c.get("email", "")).strip().lower() == email.lower():
                flash("This email is already registered for awareness.", "danger")
                return redirect(url_for("child_awareness_signup"))
            if str(c.get("phone", "")).strip() == phone:
                flash("This phone is already registered for awareness.", "danger")
                return redirect(url_for("child_awareness_signup"))

        # ------- Profile Image -------
        profile_img = request.files.get("profile_image")
        profile_img_path = ""
        if not profile_img or not profile_img.filename:
            flash("Profile image is required.", "danger")
            return redirect(url_for("child_awareness_signup"))

        if not profile_img.mimetype.startswith("image/"):
            flash("Only image files are allowed for profile image.", "danger")
            return redirect(url_for("child_awareness_signup"))

        img_filename = secure_filename(f"{uuid.uuid4()}_{profile_img.filename}")
        img_save_path = os.path.join("static/awareness_profile_photos", img_filename)
        os.makedirs(os.path.dirname(img_save_path), exist_ok=True)
        profile_img.save(img_save_path)
        profile_img_path = f"awareness_profile_photos/{img_filename}"

        # ------- Supporting Document (optional) -------
        document = request.files.get("document")
        document_path = ""
        if document and document.filename:
            doc_filename = secure_filename(f"{uuid.uuid4()}_{document.filename}")
            doc_save_path = os.path.join("static/awareness_documents", doc_filename)
            os.makedirs(os.path.dirname(doc_save_path), exist_ok=True)
            document.save(doc_save_path)
            document_path = f"awareness_documents/{doc_filename}"

        # ------- Random password -------
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # ------- Save to Firebase (awareness_signup) -------
        uid = str(uuid.uuid4())
        ref.child(uid).set({
            "name": name,
            "father_name": father_name,
            "email": email,
            "gender": gender,
            "awareness_area": awareness_area,     # ⚠️ yeh field awareness ke liye
            "dob": dob,
            "phone": phone,
            "availability": availability,
            "location": location,
            "profile_image": profile_img_path,
            "document": document_path,
            "password": password,
            "role": "Child Awareness Counselor",
            "created_by": admin_email,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # ------- Email credentials -------
        subject = "SahaaraX Child Awareness – Counselor Login Credentials"
        body = f"""
        Dear {name},

        Your Child Awareness counselor account has been created ✅

        Login Credentials:
        Email: {email}
        Password: {password}

        You can use these credentials to sign in to your Child Awareness dashboard.

        Regards,
        SahaaraX Team
        """

        try:
            yag.send(email, subject, body)
        except Exception as e:
            print("Email error (child_awareness_signup):", e)

        flash("Child Awareness Counselor created successfully. Login details sent to email.", "success")
        return redirect(url_for("child_awareness_signup"))

    # GET
    return render_template("child_awareness_signup.html")
# ---------------- Child Awareness Dashboard ----------------
@app.route("/child_awareness_dashboard")
def child_awareness_dashboard():
    if "child_awareness_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["child_awareness_user"]

    # ✅ Counselor data (awareness_signup se)
    counselor_ref = db.reference("awareness_signup").child(counselor_id)
    counselor = counselor_ref.get()
    if not counselor:
        flash("Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))

    # ✅ Child awareness sessions
    sessions_ref = db.reference("child_awareness_sessions")
    all_sessions = sessions_ref.get() or {}

    sessions_list = []
    total_present_all = 0
    total_absent_all = 0

    for sid, sess in all_sessions.items():
        if not isinstance(sess, dict):
            continue
        if sess.get("counselor_id") != counselor_id:
            continue

        attendance = sess.get("attendance", {}) or {}
        total = len(attendance)
        present = sum(1 for uid, a in attendance.items()
                      if isinstance(a, dict) and a.get("status") == "Present")
        absent = total - present

        total_present_all += present
        total_absent_all += absent

        sess["session_id"] = sid
        sess["total_attendance"] = total
        sess["present_count"] = present
        sess["absent_count"] = absent
        sessions_list.append(sess)

    # Latest session upar
    sessions_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    dashboard_stats = {
        "total_sessions": len(sessions_list),
        "total_present": total_present_all,
        "total_absent": total_absent_all,
    }

    return render_template(
        "child_awareness_dashboard.html",
        user=counselor,
        sessions=sessions_list,
        stats=dashboard_stats
    )
@app.route("/child_awareness_create_session", methods=["GET", "POST"])
def child_awareness_create_session():
    if "child_awareness_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["child_awareness_user"]
    counselor = db.reference("awareness_signup").child(counselor_id).get()

    if not counselor:
        flash("Counselor not found!", "danger")
        return redirect(url_for("counseling_signin"))

    # ✅ Eligible users: approved + have children
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    eligible_users = {
        uid: u for uid, u in users.items()
        if isinstance(u, dict)
        and u.get("status", "").lower() == "approved"
        and str(u.get("children", "")).lower() == "yes"
    }

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        topic = request.form.get("topic", "").strip()  # Trauma / Stress / Behavioral Issues
        details = request.form.get("details", "").strip()
        zoom_link = request.form.get("zoom_link", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()

        if not title or not topic or not zoom_link:
            flash("⚠️ Title, Topic and Zoom Link are required.", "danger")
            return redirect(url_for("child_awareness_create_session"))

        image_url = None
        if "image" in request.files:
            img = request.files["image"]
            if img and img.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{img.filename}")
                save_path = os.path.join("static/child_awareness_uploads", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                img.save(save_path)
                image_url = f"child_awareness_uploads/{filename}"

        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "counselor_id": counselor_id,
            "counselor_name": counselor.get("name"),
            "counselor_email": counselor.get("email"),
            "title": title,
            "topic": topic,
            "details": details,
            "zoom_link": zoom_link,
            "date": date,
            "time": time,
            "image": image_url,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "attendance": {}
        }

        session_ref = db.reference("child_awareness_sessions").child(session_id)
        session_ref.set(session_data)

        # ✅ Email only to users WITH CHILDREN
        subject = f"Child Awareness Session: {title}"
        body_template = f"""
        Dear Parent/Guardian,

        You are invited to join our Child Awareness session for your child.

        Title: {title}
        Topic: {topic}
        Details: {details}

        Date: {date}
        Time: {time}
        Zoom Link: {zoom_link}

        Counselor: {counselor.get("name")}

        Regards,
        SahaaraX Child Awareness Team
        """

        sent_count = 0
        for uid, usr in eligible_users.items():
            try:
                yag.send(usr.get("email"), subject, body_template)
                session_ref.child("attendance").child(uid).set({
                    "user_name": usr.get("name"),
                    "user_email": usr.get("email"),
                    "status": "Not Present"
                })
                sent_count += 1
            except Exception as e:
                print("Email error (child awareness session):", e)

        flash(f"✅ Session created. Invitations sent to {sent_count} eligible users.", "success")
        return redirect(url_for("child_awareness_dashboard"))

    return render_template(
        "child_awareness_create_session.html",
        user=counselor,
        eligible_count=len(eligible_users)
    )
@app.route("/child_awareness_session/<session_id>")
def child_awareness_session(session_id):
    if "child_awareness_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["child_awareness_user"]
    counselor = db.reference("awareness_signup").child(counselor_id).get()

    session_ref = db.reference("child_awareness_sessions").child(session_id)
    session_data = session_ref.get()

    if not session_data:
        flash("⚠️ Session not found!", "danger")
        return redirect(url_for("child_awareness_dashboard"))

    # Safety: ensure session belongs to this counselor
    if session_data.get("counselor_id") != counselor_id:
        flash("⚠️ You are not authorized to view this session.", "danger")
        return redirect(url_for("child_awareness_dashboard"))

    attendance = session_data.get("attendance", {}) or {}

    return render_template(
        "child_view_session.html",
        user=counselor,
        session=session_data,
        attendance=attendance
    )


@app.route("/child_mark_child_attendance/<session_id>", methods=["POST"])
def child_mark_child_attendance(session_id):
    if "child_awareness_user" not in session:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    selected_present = request.form.getlist("present")

    ref = db.reference("child_awareness_sessions").child(session_id).child("attendance")
    attendance = ref.get() or {}

    for uid, att in attendance.items():
        status = "Present" if uid in selected_present else "Not Present"
        ref.child(uid).update({"status": status})

    flash("✅ Attendance updated!", "success")
    return redirect(url_for("child_awareness_session", session_id=session_id))
# ---------------- Child Awareness Counselor Sign In (awareness_signup) ----------------
@app.route("/child_awareness_signin", methods=["GET", "POST"])
def child_awareness_signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("⚠️ Please enter both email and password.", "danger")
            return redirect(url_for("child_awareness_signin"))

        ref = db.reference("awareness_signup")  # 👈 yahan se child awareness counselors
        users = ref.get() or {}

        for uid, user in users.items():
            db_email = str(user.get("email", "")).strip().lower()
            db_password = str(user.get("password", "")).strip()
            role = str(user.get("role", "")).strip()            # optional
            area = str(user.get("awareness_area", "")).strip()  # Trauma / Stress / Behavioral Issues, etc.

            if db_email == email:
                if db_password == password:
                    # ✅ Child Awareness counselor session
                    session["child_awareness_user"] = uid
                    session["child_awareness_role"] = role or "Child Awareness Counselor"
                    session["child_awareness_area"] = area
                    flash("✅ Child Awareness login successful!", "success")
                    return redirect(url_for("child_awareness_dashboard"))
                else:
                    flash("❌ Invalid password!", "danger")
                    return redirect(url_for("child_awareness_signin"))

        flash("❌ Email not found in Child Awareness counselors!", "danger")
        return redirect(url_for("child_awareness_signin"))

    return render_template("child_awareness_signin.html")
@app.route("/admin/user_reports", methods=["GET"])
def admin_user_reports():
    # ✅ Admin login check
    if "admin" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("admin_login"))

    # Filters
    search = request.args.get("search", "").strip().lower()
    status = request.args.get("status", "All")

    # Users
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    # Counselor assignment (assign_conseler)
    assign_ref = db.reference("assign_conseler")
    assignments = assign_ref.get() or {}

    # Map: user_id -> assignment info
    assignment_by_user = {}
    for aid, a in assignments.items():
        if not isinstance(a, dict):
            continue
        uid = a.get("user_id")
        if not uid:
            continue
        # agar multiple assignment hon to last wala overwrite ho jaayega (OK for now)
        assignment_by_user[uid] = a

    user_list = []

    for uid, u in users.items():
        if not isinstance(u, dict):
            continue

        # Status filter
        u_status = (u.get("status") or "").strip()
        if status != "All" and u_status != status:
            continue

        # Search filter (name + email + cnic + phone)
        if search:
            haystack = " ".join([
                str(u.get("name", "")),
                str(u.get("email", "")),
                str(u.get("cnic", "")),
                str(u.get("contact_number", "")),
            ]).lower()
            if search not in haystack:
                continue

        # Build row object
        row = {
            "user_id": uid,
            "name": u.get("name", "Unknown"),
            "email": u.get("email", "Unknown"),
            "status": u_status or "Unapproved",
            "gender": u.get("gender", ""),
            "categories": u.get("categories", []),
            "counseling": u.get("counseling", []),
            "has_children": (u.get("children", "").lower() == "yes"),
        }

        # Assigned counselor (if any)
        assign = assignment_by_user.get(uid)
        if assign:
            row["assigned_counselor_name"] = assign.get("counselor_name", "Unknown")
            row["assigned_counselor_email"] = assign.get("counselor_email", "")
            row["assigned_counseling_type"] = assign.get("counseling", "")
            row["assigned_at"] = assign.get("timestamp", "")
        else:
            row["assigned_counselor_name"] = None
            row["assigned_counselor_email"] = None
            row["assigned_counseling_type"] = None
            row["assigned_at"] = None

        user_list.append(row)

    # Sort by name
    user_list.sort(key=lambda x: x["name"].lower())

    return render_template(
        "admin_user_reports.html",
        users=user_list,
        search=search,
        status=status
    )

# ---------------- Admin: Overall User Report ----------------
@app.route("/admin/user_overall_report/<user_id>")
def admin_user_overall_report(user_id):
    # ✅ Admin login check (apni session key ke mutabiq adjust kar sakte ho)
    if "admin" not in session:
        flash("⚠️ Please log in as admin first.", "danger")
        return redirect(url_for("admin_signin"))

    # ✅ User basic info
    user_ref = db.reference("users").child(user_id)
    user = user_ref.get()
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("admin_dashboard"))

    # ✅ Room (shelter) details
    room_detail = None
    assigned_room_id = user.get("assigned_room")
    if assigned_room_id:
        room_detail = db.reference("rooms").child(assigned_room_id).get()

    # ✅ Counselor assignments (assign_conseler)
    assignments_all = db.reference("assign_conseler").get() or {}
    user_assignments = []
    for aid, a in assignments_all.items():
        if isinstance(a, dict) and a.get("user_id") == user_id:
            entry = a.copy()
            entry["assignment_id"] = aid
            user_assignments.append(entry)

    # ✅ Counseling classes (counseling_classes)
    classes_raw = db.reference("counseling_classes").get() or {}
    counseling_classes = []
    for counselor_id, users_map in classes_raw.items():
        if not isinstance(users_map, dict):
            continue
        if user_id in users_map:
            for class_id, cls in users_map[user_id].items():
                if not isinstance(cls, dict):
                    continue
                entry = cls.copy()
                entry["class_id"] = class_id
                counseling_classes.append(entry)

    counseling_classes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # ✅ Manual tests (manual_tests)
    manual_tests_all = db.reference("manual_tests").get() or {}
    manual_tests_list = []
    for counselor_id, users_map in manual_tests_all.items():
        if not isinstance(users_map, dict):
            continue
        if user_id in users_map:
            for test_id, t in users_map[user_id].items():
                if not isinstance(t, dict):
                    continue
                entry = t.copy()
                entry["test_id"] = entry.get("test_id", test_id)
                entry["counselor_id"] = counselor_id
                manual_tests_list.append(entry)

    manual_tests_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # ✅ Final results (final_results[user_id])
    final_results_list = []
    fr_all = db.reference("final_results").child(user_id).get() or {}
    for fr_id, data in fr_all.items():
        if not isinstance(data, dict):
            continue
        entry = data.copy()
        entry["result_id"] = fr_id
        final_results_list.append(entry)

    final_results_list.sort(
        key=lambda x: x.get("finalized_at", x.get("created_at", "")),
        reverse=True
    )

    # ✅ Legal aid (legal_aid_index + legal_aid)
    legal_case = None
    legal_idx = db.reference("legal_aid_index").child(user_id).get()
    if isinstance(legal_idx, dict):
        app_id = legal_idx.get("app_id")
        if app_id:
            legal_case = db.reference("legal_aid").child(app_id).get()

    # ✅ Training applications (training_index + training_applications)
    training_apps_summary = []
    training_idx = db.reference("training_index").child(user_id).get() or {}
    training_all = db.reference("training_applications").get() or {}

    if isinstance(training_idx, dict):
        for track_key, info in training_idx.items():
            if not isinstance(info, dict):
                continue
            app_id = info.get("app_id")
            if app_id and app_id in training_all:
                app = training_all[app_id].copy()
                app["app_id"] = app_id
                app["track"] = track_key
                training_apps_summary.append(app)

    # ✅ Children education (childern_education)
    children_edu_list = []
    children_edu_all = db.reference("childern_education").get() or {}
    for app_id, app in children_edu_all.items():
        if not isinstance(app, dict):
            continue
        if app.get("parent_id") == user_id:
            entry = app.copy()
            entry["app_id"] = app_id
            children_edu_list.append(entry)

    # ✅ Child awareness sessions (child_awareness_sessions)
    child_awareness_list = []
    cas_all = db.reference("child_awareness_sessions").get() or {}
    for sid, sess in cas_all.items():
        if not isinstance(sess, dict):
            continue
        attendance = sess.get("attendance", {})
        if isinstance(attendance, dict) and user_id in attendance:
            row = sess.copy()
            row["session_id"] = sid
            row["attendance_status"] = attendance[user_id].get("status")
            child_awareness_list.append(row)

    # ✅ Awareness sessions (Self / Health awareness) – awareness_sessions
    awareness_list = []
    aw_all = db.reference("awareness_sessions").get() or {}
    for sid, sess in aw_all.items():
        if not isinstance(sess, dict):
            continue
        attendance = sess.get("attendance", {})
        if isinstance(attendance, dict) and user_id in attendance:
            row = sess.copy()
            row["session_id"] = sid
            row["attendance_status"] = attendance[user_id].get("status")
            awareness_list.append(row)

    return render_template(
        "admin_user_overall_report.html",
        user=user,
        user_id=user_id,
        room=room_detail,
        assignments=user_assignments,
        counseling_classes=counseling_classes,
        manual_tests=manual_tests_list,
        final_results=final_results_list,
        legal_case=legal_case,
        training_apps=training_apps_summary,
        children_edu=children_edu_list,
        child_awareness_sessions=child_awareness_list,
        awareness_sessions=awareness_list,
    )



# ---------------- Admin: View Single User Documents ----------------
@app.route("/admin/user_documents/<user_id>")
def admin_user_documents(user_id):
    # ✅ Admin login check
    if "admin" not in session:
        flash("Please login as admin first.", "danger")
        return redirect(url_for("admin_login"))   # apna admin login route name

    # ✅ Fetch user from Firebase
    user_ref = db.reference("users").child(user_id)
    user = user_ref.get()

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("admin_user_reports"))  # ya admin_dashboard, jo tum use kar rahe ho

    # ✅ Collect documents from user record
    documents = []

    def add_doc(key, label, description):
        path = user.get(key)
        if not path:
            return
        lower = str(path).lower()
        if lower.endswith(".pdf"):
            ftype = "pdf"
        elif lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            ftype = "image"
        else:
            ftype = "other"
        documents.append({
            "key": key,
            "label": label,
            "description": description,
            "path": path,
            "file_type": ftype,
        })

    # ye keys tum signup me save kar rahe ho
    add_doc("profile_image_path", "Profile Image", "User profile photo")
    add_doc("legal_doc_path", "Legal Document", "Marriage certificate / legal documents")
    add_doc("cnic_front_path", "National ID (Front)", "Front side of national identity card")
    add_doc("cnic_back_path", "National ID (Back)", "Back side of national identity card")

    return render_template(
        "admin_user_documents.html",
        user=user,
        user_id=user_id,
        documents=documents
    )
@app.route("/medical_appointments")
def medical_appointments_view():
    # Sirf admin ko allow karna ho to:
    if "admin" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("admin_login"))

    # ?status=pending / approved / all
    status_filter = (request.args.get("status", "all") or "all").lower()

    appt_ref = db.reference("medical_appointments")
    appts_raw = appt_ref.get() or {}

    users_raw = db.reference("users").get() or {}

    appointments = []

    for appt_id, appt in appts_raw.items():
        if not isinstance(appt, dict):
            continue

        # Status filter
        appt_status = str(appt.get("status", "")).lower()
        if status_filter != "all" and appt_status != status_filter:
            continue

        user_id = appt.get("user_id")
        user = users_raw.get(user_id, {})

        row = appt.copy()
        row["id"] = appt_id
        row["status_norm"] = appt_status
        row["user"] = {
            "id": user_id,
            "name": user.get("name", appt.get("user_name")),
            "email": user.get("email", ""),
            "phone": user.get("contact_number", appt.get("user_phone")),
            "cnic": user.get("cnic", appt.get("user_cnic")),
        }
        appointments.append(row)

    # Latest first
    appointments.sort(key=lambda a: a.get("created_at", 0), reverse=True)

    return render_template(
        "medical_appointments.html",
        appointments=appointments,
        status_filter=status_filter,
    )
@app.route("/approve_appointment/<appointment_id>")
def approve_appointment(appointment_id):
    if "admin" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("admin_login"))

    ref = db.reference("medical_appointments").child(appointment_id)
    appt = ref.get()

    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("medical_appointments_view"))

    # status ko lowercase me rakhte hain
    ref.update({"status": "approved"})

    flash(f"Appointment approved for {appt.get('user_name', 'user')}", "success")
    return redirect(url_for("medical_appointments_view"))
@app.route("/medical_appointment/<appointment_id>")
def medical_appointment_detail(appointment_id):
    if "admin" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("admin_login"))

    appt_ref = db.reference("medical_appointments").child(appointment_id)
    appt = appt_ref.get()

    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("medical_appointments_view"))

    # User detail
    user = {}
    user_id = appt.get("user_id")
    if user_id:
        user = db.reference("users").child(user_id).get() or {}

    # Is user ke prescriptions bhi nikaal lein (image_base64 wale)
    pres_raw = db.reference("prescriptions").get() or {}
    user_prescriptions = []
    for pid, p in pres_raw.items():
        if not isinstance(p, dict):
            continue
        if p.get("user_id") == user_id:
            item = p.copy()
            item["id"] = pid
            user_prescriptions.append(item)

    # Latest first
    user_prescriptions.sort(key=lambda x: x.get("uploaded_at", 0), reverse=True)

    return render_template(
        "medical_appointment_detail.html",
        appointment=appt,
        user=user,
        prescriptions=user_prescriptions
    )

@app.route("/prescriptions")
def prescriptions_view():
    # Optional: sirf admin ko access do
    if "admin" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("admin_login"))

    pres_ref = db.reference("prescriptions")
    pres_raw = pres_ref.get() or {}

    users_raw = db.reference("users").get() or {}

    prescriptions = []

    for pres_id, pres in pres_raw.items():
        if not isinstance(pres, dict):
            continue

        user_id = pres.get("user_id")
        user = users_raw.get(user_id, {})

        row = pres.copy()
        row["id"] = pres_id
        row["user"] = {
            "id": user_id,
            "name": user.get("name", pres.get("user_name")),
            "email": user.get("email", ""),
            "phone": user.get("contact_number", ""),
            "cnic": user.get("cnic", pres.get("user_cnic")),
            "profile_image_path": user.get("profile_image_path"),
        }
        prescriptions.append(row)

    prescriptions.sort(key=lambda x: x.get("uploaded_at", 0), reverse=True)

    return render_template("prescriptions.html", prescriptions=prescriptions)
@app.route("/prescription_image/<prescription_id>")
def prescription_image(prescription_id):
    """
    prescriptions node me stored image_base64 ko decode karke
    actual image response me bhejta hai.
    """
    pres_ref = db.reference("prescriptions").child(prescription_id)
    record = pres_ref.get()

    if not record or not record.get("image_base64"):
        abort(404)

    try:
        image_bytes = base64.b64decode(record["image_base64"])
    except Exception:
        abort(500)

    return send_file(
        BytesIO(image_bytes),
        mimetype="image/jpeg",   # Agar png store karte ho to yahan change kar sakte ho
        as_attachment=False
    )
