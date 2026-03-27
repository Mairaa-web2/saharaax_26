from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from firebase_admin import db
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid

super_admin_bp = Blueprint("super_admin", __name__, template_folder="templates")

SUPER_ADMIN_EMAIL = "supperadmin@gmail.com"
SUPER_ADMIN_PASSWORD = "super@1234"

SUPER_ADMIN_UPLOAD_FOLDER = os.path.join("static", "super_admin_uploads")
os.makedirs(SUPER_ADMIN_UPLOAD_FOLDER, exist_ok=True)


def is_super_admin():
    return session.get("super_admin_logged_in") is True


def require_super_admin():
    if not is_super_admin():
        flash("Please login as Super Admin first.", "danger")
        return False
    return True


def get_all_data():
    return db.reference("/").get() or {}


def normalize_dict(value):
    return value if isinstance(value, dict) else {}


def count_dict(node_name):
    data = normalize_dict(db.reference(node_name).get())
    return len(data)


@super_admin_bp.route("/supper_admin", methods=["GET", "POST"])
def supper_admin_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        if email == SUPER_ADMIN_EMAIL.lower() and password == SUPER_ADMIN_PASSWORD:
            session["super_admin_logged_in"] = True
            session["super_admin_email"] = SUPER_ADMIN_EMAIL
            flash("Super Admin login successful!", "success")
            return redirect(url_for("super_admin.supper_admin_dashboard"))

        flash("Invalid Super Admin credentials.", "danger")
        return redirect(url_for("super_admin.supper_admin_login"))

    return render_template("super_admin_login.html")


@super_admin_bp.route("/supper_admin/dashboard")
def supper_admin_dashboard():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    root = get_all_data()
    users = normalize_dict(root.get("users"))
    rooms = normalize_dict(root.get("rooms"))
    floors = normalize_dict(root.get("floors"))
    counselors = normalize_dict(root.get("conseling_signup"))
    awareness_counselors = normalize_dict(root.get("awareness_signup"))
    awareness_sessions = normalize_dict(root.get("awareness_sessions"))
    child_awareness_sessions = normalize_dict(root.get("child_awareness_sessions"))
    appointments = normalize_dict(root.get("medical_appointments"))
    prescriptions = normalize_dict(root.get("prescriptions"))
    donations = normalize_dict(root.get("donations"))
    volunteers = normalize_dict(root.get("volunteers"))
    subscribers = normalize_dict(root.get("subscribers"))
    admin_data = normalize_dict(root.get("admin"))

    approved = sum(1 for u in users.values() if str(u.get("status", "")).lower() == "approved")
    rejected = sum(1 for u in users.values() if str(u.get("status", "")).lower() == "rejected")
    unapproved = sum(1 for u in users.values() if str(u.get("status", "")).lower() == "unapproved")

    total_beds = sum(int(r.get("bed_count", 0) or 0) for r in rooms.values())
    total_available_beds = sum(int(r.get("available_beds", 0) or 0) for r in rooms.values())

    node_cards = [
        {"title": "Users", "count": len(users), "icon": "fa-users", "endpoint": "super_admin.view_users_data"},
        {"title": "Rooms", "count": len(rooms), "icon": "fa-bed", "endpoint": "super_admin.view_rooms_data"},
        {"title": "Floors", "count": len(floors), "icon": "fa-building", "endpoint": "super_admin.view_floors_data"},
        {"title": "Counselors", "count": len(counselors), "icon": "fa-user-doctor", "endpoint": "super_admin.view_counselors_data"},
        {"title": "Awareness Counselors", "count": len(awareness_counselors), "icon": "fa-person-chalkboard", "endpoint": "super_admin.view_awareness_counselors_data"},
        {"title": "Awareness Sessions", "count": len(awareness_sessions), "icon": "fa-chalkboard-user", "endpoint": "super_admin.view_awareness_sessions_data"},
        {"title": "Child Sessions", "count": len(child_awareness_sessions), "icon": "fa-children", "endpoint": "super_admin.view_child_awareness_sessions_data"},
        {"title": "Appointments", "count": len(appointments), "icon": "fa-hospital-user", "endpoint": "super_admin.view_medical_appointments_data"},
        {"title": "Prescriptions", "count": len(prescriptions), "icon": "fa-prescription-bottle-medical", "endpoint": "super_admin.view_prescriptions_data"},
        {"title": "Subscribers", "count": len(subscribers), "icon": "fa-envelope-open-text", "endpoint": "super_admin.view_subscribers_data"},
        {"title": "Volunteers", "count": len(volunteers), "icon": "fa-handshake-angle", "endpoint": "super_admin.view_volunteers_data"},
        {"title": "Donations", "count": len(donations), "icon": "fa-hand-holding-heart", "endpoint": "super_admin.view_donations_data"},
    ]

    return render_template(
        "super_admin_dashboard.html",
        admin_data=admin_data,
        node_cards=node_cards,
        approved=approved,
        rejected=rejected,
        unapproved=unapproved,
        total_users=len(users),
        total_rooms=len(rooms),
        total_floors=len(floors),
        total_beds=total_beds,
        total_available_beds=total_available_beds,
        total_counselors=len(counselors),
        total_awareness_counselors=len(awareness_counselors),
        total_appointments=len(appointments),
        total_prescriptions=len(prescriptions),
    )


@super_admin_bp.route("/supper_admin/admin-control", methods=["GET", "POST"])
def supper_admin_admin_control():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    admin_ref = db.reference("admin")
    admin_data = normalize_dict(admin_ref.get())

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        login_email = (request.form.get("login_email") or "").strip()
        password = (request.form.get("password") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        personal_email = (request.form.get("personal_email") or "").strip()
        designation = (request.form.get("designation") or "").strip()

        image_path = admin_data.get("image", "")

        image = request.files.get("image")
        if image and image.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
            save_path = os.path.join(SUPER_ADMIN_UPLOAD_FOLDER, filename)
            image.save(save_path)
            image_path = f"super_admin_uploads/{filename}"

        if not full_name or not login_email or not password:
            flash("Name, login email and password are required.", "danger")
            return redirect(url_for("super_admin.supper_admin_admin_control"))

        payload = {
            "name": full_name,
            "email": login_email,
            "password": password,
            "phone": phone,
            "personal_email": personal_email,
            "designation": designation or "Admin",
            "image": image_path,
            "updated_by": session.get("super_admin_email"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        admin_ref.set(payload)
        flash("Admin profile updated successfully.", "success")
        return redirect(url_for("super_admin.supper_admin_admin_control"))

    return render_template("super_admin_admin_control.html", admin_data=admin_data)


@super_admin_bp.route("/supper_admin/users")
def view_users_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    users = normalize_dict(db.reference("users").get())
    rows = []

    for uid, u in users.items():
        rows.append({
            "id": uid,
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "phone": u.get("contact_number", ""),
            "cnic": u.get("cnic", ""),
            "status": u.get("status", ""),
            "gender": u.get("gender", ""),
            "children": u.get("children", ""),
            "assigned_room": u.get("assigned_room", ""),
            "image": u.get("profile_image_path", "")
        })

    rows.sort(key=lambda x: (x["name"] or "").lower())
    return render_template("super_admin_data_table.html", title="Users Database", rows=rows, table_type="users")


@super_admin_bp.route("/supper_admin/rooms")
def view_rooms_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    rooms = normalize_dict(db.reference("rooms").get())
    rows = []

    for rid, r in rooms.items():
        rows.append({
            "id": rid,
            "floor": r.get("floor", ""),
            "room_number": r.get("room_number", ""),
            "bed_count": r.get("bed_count", 0),
            "available_beds": r.get("available_beds", 0),
            "images": len(r.get("images", []) or [])
        })

    rows.sort(key=lambda x: str(x["room_number"]))
    return render_template("super_admin_data_table.html", title="Rooms Database", rows=rows, table_type="rooms")


@super_admin_bp.route("/supper_admin/floors")
def view_floors_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    floors = normalize_dict(db.reference("floors").get())
    rows = []

    for fid, f in floors.items():
        if isinstance(f, dict):
            name = f.get("name") or f.get("number") or ""
        else:
            name = f
        rows.append({
            "id": fid,
            "name": name
        })

    rows.sort(key=lambda x: str(x["name"]).lower())
    return render_template("super_admin_data_table.html", title="Floors Database", rows=rows, table_type="floors")


@super_admin_bp.route("/supper_admin/counselors")
def view_counselors_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    counselors = normalize_dict(db.reference("conseling_signup").get())
    rows = []

    for cid, c in counselors.items():
        rows.append({
            "id": cid,
            "name": c.get("name", ""),
            "email": c.get("email", ""),
            "phone": c.get("phone", ""),
            "gender": c.get("gender", ""),
            "type": c.get("counseling", ""),
            "availability": c.get("availability", ""),
            "location": c.get("location", ""),
            "image": c.get("profile_image", "")
        })

    rows.sort(key=lambda x: (x["name"] or "").lower())
    return render_template("super_admin_data_table.html", title="Counselors Database", rows=rows, table_type="counselors")


@super_admin_bp.route("/supper_admin/awareness-counselors")
def view_awareness_counselors_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    counselors = normalize_dict(db.reference("awareness_signup").get())
    rows = []

    for cid, c in counselors.items():
        rows.append({
            "id": cid,
            "name": c.get("name", ""),
            "email": c.get("email", ""),
            "phone": c.get("phone", ""),
            "gender": c.get("gender", ""),
            "area": c.get("awareness_area", ""),
            "availability": c.get("availability", ""),
            "location": c.get("location", ""),
            "image": c.get("profile_image", "")
        })

    rows.sort(key=lambda x: (x["name"] or "").lower())
    return render_template("super_admin_data_table.html", title="Awareness Counselors Database", rows=rows, table_type="awareness_counselors")


@super_admin_bp.route("/supper_admin/awareness-sessions")
def view_awareness_sessions_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    sessions_data = normalize_dict(db.reference("awareness_sessions").get())
    rows = []

    for sid, s in sessions_data.items():
        attendance = s.get("attendance", {}) or {}
        present = sum(1 for _, a in attendance.items() if isinstance(a, dict) and a.get("status") == "Present")
        rows.append({
            "id": sid,
            "title": s.get("title", ""),
            "category": s.get("category", ""),
            "counselor_name": s.get("counselor_name", ""),
            "counselor_email": s.get("counselor_email", ""),
            "attendance_total": len(attendance),
            "present_count": present,
            "created_at": s.get("created_at", "")
        })

    rows.sort(key=lambda x: x["created_at"], reverse=True)
    return render_template("super_admin_data_table.html", title="Awareness Sessions", rows=rows, table_type="awareness_sessions")


@super_admin_bp.route("/supper_admin/child-awareness-sessions")
def view_child_awareness_sessions_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    sessions_data = normalize_dict(db.reference("child_awareness_sessions").get())
    rows = []

    for sid, s in sessions_data.items():
        attendance = s.get("attendance", {}) or {}
        present = sum(1 for _, a in attendance.items() if isinstance(a, dict) and a.get("status") == "Present")
        rows.append({
            "id": sid,
            "title": s.get("title", ""),
            "topic": s.get("topic", ""),
            "counselor_name": s.get("counselor_name", ""),
            "counselor_email": s.get("counselor_email", ""),
            "attendance_total": len(attendance),
            "present_count": present,
            "date": s.get("date", ""),
            "time": s.get("time", ""),
            "created_at": s.get("created_at", "")
        })

    rows.sort(key=lambda x: x["created_at"], reverse=True)
    return render_template("super_admin_data_table.html", title="Child Awareness Sessions", rows=rows, table_type="child_awareness_sessions")


@super_admin_bp.route("/supper_admin/medical-appointments")
def view_medical_appointments_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    appointments = normalize_dict(db.reference("medical_appointments").get())
    rows = []

    for aid, a in appointments.items():
        rows.append({
            "id": aid,
            "user_name": a.get("user_name", ""),
            "user_email": a.get("user_email", ""),
            "user_phone": a.get("user_phone", ""),
            "hospital": a.get("hospital_name", ""),
            "doctor": a.get("doctor_name", ""),
            "status": a.get("status", ""),
            "date": a.get("appointment_date", ""),
            "time": a.get("appointment_time", "")
        })

    rows.sort(key=lambda x: str(x["date"]), reverse=True)
    return render_template("super_admin_data_table.html", title="Medical Appointments", rows=rows, table_type="medical_appointments")


@super_admin_bp.route("/supper_admin/prescriptions")
def view_prescriptions_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    prescriptions = normalize_dict(db.reference("prescriptions").get())
    rows = []

    for pid, p in prescriptions.items():
        rows.append({
            "id": pid,
            "user_name": p.get("user_name", ""),
            "user_cnic": p.get("user_cnic", ""),
            "doctor_name": p.get("doctor_name", ""),
            "hospital_name": p.get("hospital_name", ""),
            "uploaded_at": p.get("uploaded_at", "")
        })

    rows.sort(key=lambda x: str(x["uploaded_at"]), reverse=True)
    return render_template("super_admin_data_table.html", title="Prescriptions", rows=rows, table_type="prescriptions")


@super_admin_bp.route("/supper_admin/subscribers")
def view_subscribers_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    subscribers = normalize_dict(db.reference("subscribers").get())
    rows = []

    for sid, s in subscribers.items():
        rows.append({
            "id": sid,
            "email": s.get("email", ""),
            "subscribed_at": s.get("subscribed_at", "")
        })

    rows.sort(key=lambda x: str(x["subscribed_at"]), reverse=True)
    return render_template("super_admin_data_table.html", title="Subscribers", rows=rows, table_type="subscribers")


@super_admin_bp.route("/supper_admin/volunteers")
def view_volunteers_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    volunteers = normalize_dict(db.reference("volunteers").get())
    rows = []

    for vid, v in volunteers.items():
        rows.append({
            "id": vid,
            "name": v.get("name", ""),
            "email": v.get("email", ""),
            "phone": v.get("phone", ""),
            "skills": v.get("skills", ""),
            "availability": v.get("availability", ""),
            "created_at": v.get("created_at", "")
        })

    rows.sort(key=lambda x: str(x["created_at"]), reverse=True)
    return render_template("super_admin_data_table.html", title="Volunteers", rows=rows, table_type="volunteers")


@super_admin_bp.route("/supper_admin/donations")
def view_donations_data():
    if not require_super_admin():
        return redirect(url_for("super_admin.supper_admin_login"))

    donations = normalize_dict(db.reference("donations").get())
    rows = []

    for did, d in donations.items():
        rows.append({
            "id": did,
            "name": d.get("name", ""),
            "email": d.get("email", ""),
            "phone": d.get("phone", ""),
            "amount": d.get("amount", ""),
            "message": d.get("message", ""),
            "created_at": d.get("created_at", "")
        })

    rows.sort(key=lambda x: str(x["created_at"]), reverse=True)
    return render_template("super_admin_data_table.html", title="Donations", rows=rows, table_type="donations")


@super_admin_bp.route("/supper_admin/logout")
def supper_admin_logout():
    session.pop("super_admin_logged_in", None)
    session.pop("super_admin_email", None)
    flash("Super Admin logged out successfully.", "info")
    return redirect(url_for("super_admin.supper_admin_login"))