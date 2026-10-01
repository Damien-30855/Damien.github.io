# app.py — หน้าเว็บทั้งหมดของระบบ (Flask)
#
# ทุกหน้าที่เปลี่ยนข้อมูลเขียนเป็น 4 ขั้นเหมือนกัน
#   1) โหลดอ็อบเจกต์จาก db   2) เรียกเมธอดของอ็อบเจกต์ (กติกาอยู่ในคลาส)
#   3) บันทึก + commit         4) redirect ไปหน้าที่เกี่ยวข้อง
# ถ้าเมธอด raise ValueError -> rollback แล้วแสดงข้อความเป็นแถบสีแดง

import secrets
from datetime import datetime

from flask import Flask, g, session, request, redirect, url_for, flash, render_template, abort
from markupsafe import Markup      # มากับ Flask: บอก Jinja ว่าข้อความนี้เป็น HTML ที่เราสร้างเอง

import config
from database import Database
from models import (Student,
                    STATUS_PENDING, STATUS_BORROWED, STATUS_OVERDUE,
                    STATUS_RETURNED, STATUS_DAMAGED, STATUS_CANCELED,
                    BOOK_OPEN, BOOK_CLOSE, DEADLINE, PICKUP_MINUTES)

app = Flask(__name__)
# ถ้า config.SECRET_KEY ว่าง ให้สุ่มกุญแจใหม่ทุกครั้งที่เปิดเว็บ (ไม่มีใครรู้ค่า จึงปลอม session เป็นแอดมินไม่ได้)
app.secret_key = config.SECRET_KEY or secrets.token_hex(32)

# ---------- บทบาทผู้ใช้ ----------
ROLE_GUEST = "guest"
ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"

# สิทธิ์เข้าแต่ละหน้า: ชื่อฟังก์ชันของหน้า -> บทบาทที่เข้าได้ (หน้าที่ไม่อยู่ในตารางนี้ ทุกคนเข้าได้)
PAGE_ROLES = {
    "login": [ROLE_GUEST],
    "signup": [ROLE_GUEST],
    "borrow": [ROLE_STUDENT],
    "history": [ROLE_STUDENT],
    "cancel_booking": [ROLE_STUDENT],
    "admin_pending": [ROLE_ADMIN],
    "admin_active": [ROLE_ADMIN],
    "admin_records": [ROLE_ADMIN],
    "admin_overdue": [ROLE_ADMIN],
    "admin_reports": [ROLE_ADMIN],
    "admin_members": [ROLE_ADMIN],
    "admin_member": [ROLE_ADMIN],
    "admin_confirm_pickup": [ROLE_ADMIN],
    "admin_confirm_return": [ROLE_ADMIN],
    "admin_cancel_record": [ROLE_ADMIN],
    "admin_update_quantity": [ROLE_ADMIN],
    "admin_reset_password": [ROLE_ADMIN],
}

THAI_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

# สถานะทั้ง 6 ค่า เรียงตามลำดับที่เกิด (ใช้เป็นตัวเลือกในแถบค้นหาของหน้ารายการทั้งหมด)
ALL_STATUSES = [STATUS_PENDING, STATUS_BORROWED, STATUS_OVERDUE,
                STATUS_RETURNED, STATUS_DAMAGED, STATUS_CANCELED]


# =====================================================================
# เวลาปัจจุบัน / ฐานข้อมูล / ผู้ใช้ที่ login อยู่
# =====================================================================

def now():
    """เวลาปัจจุบันของระบบ (มาจากที่นี่ที่เดียว)
    ถ้าตั้ง FAKE_NOW ใน config.py จะใช้เวลาจำลองแทนเวลาจริง"""
    if config.FAKE_NOW:
        return datetime.strptime(config.FAKE_NOW, "%Y-%m-%d %H:%M:%S")
    return datetime.now().replace(microsecond=0)


def get_db():
    """เปิดการเชื่อมต่อฐานข้อมูล 1 ครั้งต่อ 1 request (เก็บไว้ใน g)"""
    if "db" not in g:
        g.db = Database()
    return g.db


@app.teardown_appcontext
def close_db(error):
    """ปิดการเชื่อมต่อฐานข้อมูลเมื่อจบ request"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def load_current_user(db):
    """โหลดอ็อบเจกต์ผู้ใช้ที่ login อยู่ไว้ใน g.user (Student หรือ Admin หรือ None ถ้าเป็น Guest)"""
    g.user = None
    role = session.get("role")
    if role == ROLE_STUDENT:
        g.user = db.get_student(session.get("user_id"))
    elif role == ROLE_ADMIN:
        g.user = db.get_admin(session.get("user_id"))
    if role is not None and g.user is None:
        # บัญชีใน session ไม่มีในฐานข้อมูลแล้ว (เช่น เพิ่งสร้างฐานข้อมูลใหม่) -> ให้เป็น Guest
        session.pop("role", None)
        session.pop("user_id", None)


def current_role():
    if g.get("user") is None:
        return ROLE_GUEST
    return session.get("role")


def refresh_statuses(db):
    """อัปเดตสถานะอัตโนมัติ (เรียกทุกครั้งที่มีคนเปิดหน้าเว็บ)
    - 'รอยืนยัน' ที่เกิน 30 นาที -> 'ยกเลิก' + คืนสต็อก
    - 'กำลังยืม' ที่เลย 16:00 -> 'เกินกำหนด'
    ตัดสินด้วยเมธอดของอ็อบเจกต์ทั้งหมด
    ก่อนเปลี่ยน จะอ่านรายการนั้นใหม่แบบล็อกแถว (db.get_record) เผื่อมีคนเพิ่งเปลี่ยนไปพร้อมกัน
    เช่น แอดมินกดคืนพอดี -> จะได้ไม่เขียนทับสถานะ 'คืนแล้ว' และไม่คืนสต็อกซ้ำ"""
    current = now()
    for found in db.get_records(status=STATUS_PENDING):
        if found.is_expired(current):
            record = db.get_record(found.record_id)          # อ่านใหม่แบบล็อก
            if not record.is_expired(current):               # มีคนเปลี่ยนไปแล้ว (ยืนยันรับ/ยกเลิก)
                db.commit()
                continue
            equipment = db.get_equipment(record.equipment_id)
            try:
                record.cancel()
                equipment.increase_available()
                db.save_record(record)
                db.save_equipment(equipment)
                db.commit()
            except ValueError:
                db.rollback()
    for found in db.get_records(status=STATUS_BORROWED):
        if found.is_overdue(current):
            record = db.get_record(found.record_id)          # อ่านใหม่แบบล็อก
            if record.is_overdue(current):                   # ยังกำลังยืมอยู่จริง (ยังไม่มีใครกดคืน)
                record.mark_overdue(current)
                db.save_record(record)
            db.commit()
    db.commit()


def check_permission():
    """ตรวจว่าบทบาทปัจจุบันเข้าหน้านี้ได้ไหม ถ้าไม่ได้ return หน้าที่ต้อง redirect ไป"""
    allowed_roles = PAGE_ROLES.get(request.endpoint)
    if allowed_roles is None or current_role() in allowed_roles:
        return None
    if current_role() == ROLE_GUEST:
        flash("กรุณาเข้าสู่ระบบก่อนทำรายการ", "danger")
        return redirect(url_for("login"))
    flash("หน้านี้ไม่ได้อยู่ในสิทธิ์ของบัญชีนี้", "danger")
    return redirect(url_for("dashboard"))


@app.before_request
def before_each_request():
    """ทำก่อนเปิดทุกหน้า: โหลดผู้ใช้ -> อัปเดตสถานะอัตโนมัติ -> ตรวจสิทธิ์"""
    if request.endpoint == "static":
        return None
    db = get_db()
    load_current_user(db)
    refresh_statuses(db)
    return check_permission()


@app.context_processor
def template_values():
    """ค่าที่ทุก template ใช้ได้เลย โดยไม่ต้องส่งเองทุกหน้า"""
    current = now()
    return {
        "role": current_role(),
        "current_time": current,
        "thai_day": THAI_DAYS[current.weekday()],
        "fake_now": config.FAKE_NOW,
        "STATUS_PENDING": STATUS_PENDING,
        "STATUS_BORROWED": STATUS_BORROWED,
        "STATUS_OVERDUE": STATUS_OVERDUE,
        "STATUS_RETURNED": STATUS_RETURNED,
        "STATUS_DAMAGED": STATUS_DAMAGED,
        "STATUS_CANCELED": STATUS_CANCELED,
        "BOOK_OPEN": BOOK_OPEN,
        "BOOK_CLOSE": BOOK_CLOSE,
        "DEADLINE": DEADLINE,
        "PICKUP_MINUTES": PICKUP_MINUTES,
    }


THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
               "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


@app.template_filter("thai_datetime")
def thai_datetime(value, plain=False):
    """วันที่แบบไทย พ.ศ. เช่น 22 ก.ย. 2569 10:05 (ถ้าไม่มีค่าแสดง -)
    ปกติคืนเป็น <span class="dt"> เพื่อให้คอมแสดง 2 บรรทัด มือถือบรรทัดเดียว (CSS ใน style.css)
    plain=True คืนเป็นข้อความธรรมดา"""
    if value is None:
        return "-"
    date_text = str(value.day) + " " + THAI_MONTHS[value.month - 1] + " " + str(value.year + 543)
    time_text = value.strftime("%H:%M")
    if plain:
        return date_text + " " + time_text
    return Markup('<span class="dt"><span class="d">' + date_text + '</span> <span class="t">'
                  + time_text + '</span></span>')


@app.template_filter("thai_time")
def thai_time(value):
    """เวลาอย่างเดียว เช่น 10:35 น."""
    if value is None:
        return "-"
    return value.strftime("%H:%M") + " น."


def read_search_filters():
    """อ่านค่าจากแถบค้นหา (?q=...&equipment_id=...&status=...) ค่าที่ผิดรูปแบบถือว่าไม่ได้กรอง
    คืนค่า dict: q (ข้อความ), equipment_id (ตัวเลขหรือ None), status (สถานะหรือ None), active (มีการค้นหาไหม)"""
    q = request.args.get("q", "").strip()
    equipment_id = request.args.get("equipment_id", type=int)     # ไม่ใช่ตัวเลข -> None
    status = request.args.get("status", "")
    if status not in ALL_STATUSES:
        status = None
    active = q != "" or equipment_id is not None or status is not None
    return {"q": q, "equipment_id": equipment_id, "status": status, "active": active}


def load_lookups(db):
    """dict สำหรับหาอ็อบเจกต์ผู้ยืม / อุปกรณ์ / แอดมิน จาก id ที่อยู่ในรายการยืม"""
    students_by_id = {}
    for student in db.get_all_students():
        students_by_id[student.student_id] = student
    equipment_by_id = {}
    for equipment in db.get_all_equipment():
        equipment_by_id[equipment.equipment_id] = equipment
    admins_by_id = {}
    for admin in db.get_all_admins():
        admins_by_id[admin.admin_id] = admin
    return students_by_id, equipment_by_id, admins_by_id


@app.errorhandler(ConnectionError)
def database_error(error):
    return render_template("error.html", message=str(error)), 500


@app.errorhandler(500)
def server_error(error):
    """error ที่ไม่ได้คาดไว้ (ตอน DEBUG = False) แสดงหน้าภาษาไทยแทนหน้าโค้ดภาษาอังกฤษ"""
    return render_template("error.html", message="เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง"), 500


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", message="ไม่พบหน้าที่ต้องการ"), 404


# =====================================================================
# หน้าของทุกคน (Guest ก็เข้าได้)
# =====================================================================

@app.get("/")
def dashboard():
    db = get_db()
    equipment_list = db.get_all_equipment()
    total_equipment = 0
    for equipment in equipment_list:
        total_equipment += equipment.total_quantity
    borrowed_count = db.count_records(STATUS_BORROWED) + db.count_records(STATUS_OVERDUE)
    returned_count = db.count_records(STATUS_RETURNED) + db.count_records(STATUS_DAMAGED)
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    return render_template("dashboard.html",
                           total_equipment=total_equipment,
                           borrowed_count=borrowed_count,
                           returned_count=returned_count,
                           equipment_types=len(equipment_list),
                           records=db.get_records(limit=10),
                           students_by_id=students_by_id,
                           equipment_by_id=equipment_by_id)


@app.get("/equipment")
def equipment():
    db = get_db()
    return render_template("equipment.html", equipment_list=db.get_all_equipment())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # ถ้า username ตรงกับตาราง admins -> login เป็นแอดมิน ถ้าไม่ตรง -> หาในตาราง students
        admin = db.get_admin_by_username(username)
        if admin is not None:
            if admin.login(password):
                session.clear()
                session["role"] = ROLE_ADMIN
                session["user_id"] = admin.admin_id
                flash("เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ " + admin.name, "success")
                return redirect(url_for("admin_pending"))
        else:
            student = db.get_student(username)
            if student is not None and student.login(password):
                session.clear()
                session["role"] = ROLE_STUDENT
                session["user_id"] = student.student_id
                flash("เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ " + student.full_name(), "success")
                return redirect(url_for("borrow"))

        flash("รหัสนักศึกษา/ชื่อผู้ใช้ หรือรหัสผ่านไม่ถูกต้อง", "danger")
        return render_template("login.html", username=username)
    return render_template("login.html", username="")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        db = get_db()
        form = request.form
        try:
            student = Student.register(form.get("student_id", ""), form.get("first_name", ""),
                                       form.get("last_name", ""), form.get("email", ""),
                                       form.get("phone", ""),
                                       form.get("password", ""), form.get("confirm_password", ""))
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("signup.html", form=form)

        # รหัสนักศึกษาต้องไม่ซ้ำ (ต้องถามฐานข้อมูล จึงเช็คที่นี่)
        if db.get_student(student.student_id) is not None:
            flash("รหัสนักศึกษานี้สมัครสมาชิกแล้ว", "danger")
            return render_template("signup.html", form=form)
        # อีเมลต้องไม่ซ้ำกับคนอื่น (เช็คด้วยอีเมลตัวพิมพ์เล็กที่ register() จัดให้แล้ว)
        if db.get_student_by_email(student.email) is not None:
            flash("อีเมลนี้ถูกใช้สมัครแล้ว", "danger")
            return render_template("signup.html", form=form)

        db.add_student(student)
        db.commit()
        flash("สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ", "success")
        return redirect(url_for("login"))
    return render_template("signup.html", form=request.form)


@app.get("/logout")
def logout():
    session.clear()
    flash("ออกจากระบบเรียบร้อยแล้ว", "success")
    return redirect(url_for("dashboard"))


# =====================================================================
# หน้าของนักศึกษา
# =====================================================================

@app.route("/borrow", methods=["GET", "POST"])
def borrow():
    db = get_db()
    student = g.user

    if request.method == "POST":
        equipment = db.get_equipment(request.form.get("equipment_id", type=int))    # ล็อกแถวอุปกรณ์ก่อน
        if equipment is None:
            flash("กรุณาเลือกอุปกรณ์", "danger")
            return redirect(url_for("borrow"))
        records = db.get_records(student_id=student.student_id)
        try:
            record = student.book(equipment, records, now())    # ตรวจครบ 4 ข้อ อยู่ในเมธอด
            db.add_record(record)
            db.save_equipment(equipment)
            db.commit()
            # กลับมาหน้าเดิม หน้าจะแสดงการ์ด "จองสำเร็จ" (new=1 = เพิ่งจองเสร็จ)
            return redirect(url_for("borrow", new=1))
        except ValueError as error:
            db.rollback()
            flash(str(error), "danger")
            return redirect(url_for("borrow"))

    # เปิดหน้า: แสดงตามสถานะของนักศึกษา
    #   มีรายการค้าง ('รอยืนยัน' / 'กำลังยืม' / 'เกินกำหนด') -> แสดงการ์ดของรายการนั้น
    #   ไม่มีรายการค้าง -> แสดงฟอร์มจอง (ถ้าตอนนี้จองไม่ได้ ให้บอกเหตุผลและปิดปุ่มจองไว้)
    records = db.get_records(student_id=student.student_id)
    record = student.active_record(records)
    if record is not None:
        students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
        return render_template("borrow.html", record=record, equipment=equipment_by_id[record.equipment_id],
                               is_new=request.args.get("new") == "1")
    reason = None
    try:
        student.check_can_book(records, now())
    except ValueError as error:
        reason = str(error)
    return render_template("borrow.html", record=None, equipment_list=db.get_all_equipment(), reason=reason)


@app.get("/history")
def history():
    db = get_db()
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    return render_template("history.html",
                           records=db.get_records(student_id=g.user.student_id),
                           equipment_by_id=equipment_by_id)


@app.post("/history/<int:record_id>/cancel")
def cancel_booking(record_id):
    db = get_db()
    record = db.get_record(record_id)
    if record is None:
        abort(404)
    equipment = db.get_equipment(record.equipment_id)
    try:
        g.user.cancel_booking(record, equipment)
        db.save_record(record)
        db.save_equipment(equipment)
        db.commit()
        flash("ยกเลิกการจองสำเร็จ อุปกรณ์ถูกคืนกลับเข้าสต็อกแล้ว", "success")
    except ValueError as error:
        db.rollback()
        flash(str(error), "danger")
    # กลับไปหน้าที่กดมา (การ์ดในหน้ายืม หรือ หน้าประวัติ)
    if request.form.get("back") == "borrow":
        return redirect(url_for("borrow"))
    return redirect(url_for("history"))


# =====================================================================
# หน้าของแอดมิน
# =====================================================================

@app.get("/admin/pending")
def admin_pending():
    db = get_db()
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    search = read_search_filters()                          # หน้านี้ค้นได้แค่ชื่อ/รหัสนักศึกษา
    records = db.get_records(status=STATUS_PENDING, keyword=search["q"])
    return render_template("admin_pending.html",
                           records=records,
                           search=search,
                           students_by_id=students_by_id,
                           equipment_by_id=equipment_by_id)


@app.get("/admin/active")
def admin_active():
    db = get_db()
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    # แสดงเฉพาะ "กำลังยืม" (ทีมตกลง 1 ต.ค.: รายการเกินกำหนดไปยืนยันคืนที่หน้ารายการเกินกำหนดแทน)
    search = read_search_filters()                          # หน้านี้ค้นได้ ชื่อ/รหัส + อุปกรณ์
    records = db.get_records(status=STATUS_BORROWED, keyword=search["q"],
                             equipment_id=search["equipment_id"])
    return render_template("admin_active.html",
                           records=records,
                           search=search,
                           equipment_list=db.get_all_equipment(),
                           students_by_id=students_by_id,
                           equipment_by_id=equipment_by_id)


@app.get("/admin/records")
def admin_records():
    db = get_db()
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    search = read_search_filters()                          # หน้านี้ค้นได้ ชื่อ/รหัส + อุปกรณ์ + สถานะ
    records = db.get_records(status=search["status"], keyword=search["q"],
                             equipment_id=search["equipment_id"])
    return render_template("admin_records.html",
                           records=records,
                           search=search,
                           equipment_list=db.get_all_equipment(),
                           all_statuses=ALL_STATUSES,
                           students_by_id=students_by_id,
                           equipment_by_id=equipment_by_id,
                           admins_by_id=admins_by_id)


@app.get("/admin/overdue")
def admin_overdue():
    db = get_db()
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    search = read_search_filters()                          # หน้านี้ค้นได้ ชื่อ/รหัส + อุปกรณ์
    records = db.get_records(status=STATUS_OVERDUE, keyword=search["q"],
                             equipment_id=search["equipment_id"])
    return render_template("admin_overdue.html",
                           records=records,
                           search=search,
                           equipment_list=db.get_all_equipment(),
                           students_by_id=students_by_id,
                           equipment_by_id=equipment_by_id)


@app.get("/admin/reports")
def admin_reports():
    db = get_db()
    equipment_list = db.get_all_equipment()
    damaged_by_id = {}
    for equipment in equipment_list:
        damaged_by_id[equipment.equipment_id] = db.count_damaged(equipment.equipment_id)
    return render_template("admin_reports.html", equipment_list=equipment_list, damaged_by_id=damaged_by_id)


@app.get("/admin/members")
def admin_members():
    db = get_db()
    keyword = request.args.get("q", "").strip()
    return render_template("admin_members.html", students=db.get_all_students(keyword), keyword=keyword)


@app.get("/admin/members/<student_id>")
def admin_member(student_id):
    db = get_db()
    student = db.get_student(student_id)
    if student is None:
        abort(404)
    students_by_id, equipment_by_id, admins_by_id = load_lookups(db)
    return render_template("admin_member.html",
                           student=student,
                           records=db.get_records(student_id=student_id),
                           equipment_by_id=equipment_by_id)


@app.post("/admin/records/<int:record_id>/pickup")
def admin_confirm_pickup(record_id):
    db = get_db()
    record = db.get_record(record_id)
    if record is None:
        abort(404)
    try:
        g.user.confirm_pickup(record, now())
        db.save_record(record)
        db.commit()
        flash("ยืนยันรับอุปกรณ์สำเร็จ สถานะเปลี่ยนเป็น 'กำลังยืม' และบันทึกเวลายืมจริงแล้ว", "success")
    except ValueError as error:
        db.rollback()
        flash(str(error), "danger")
    return redirect(url_for("admin_pending"))


@app.post("/admin/records/<int:record_id>/return")
def admin_confirm_return(record_id):
    db = get_db()
    record = db.get_record(record_id)                       # 1) โหลดอ็อบเจกต์
    if record is None:
        abort(404)
    equipment = db.get_equipment(record.equipment_id)
    is_damaged = request.form.get("damaged") == "1"
    try:
        g.user.confirm_return(record, equipment, is_damaged, now())    # 2) เรียกเมธอด (กติกาอยู่ในคลาส)
        db.save_record(record)                                          # 3) บันทึก
        db.save_equipment(equipment)
        db.commit()
        if is_damaged:
            flash("บันทึกคืน-ชำรุดแล้ว อุปกรณ์ไม่กลับเข้าสต็อก", "success")
        else:
            flash("ยืนยันคืน-ปกติแล้ว อุปกรณ์กลับเข้าสต็อกแล้ว", "success")
    except ValueError as error:
        db.rollback()
        flash(str(error), "danger")
    # 4) กลับไปหน้าที่กดมา (หน้ากำลังยืม หรือ หน้าเกินกำหนด)
    if request.form.get("back") == "overdue":
        return redirect(url_for("admin_overdue"))
    return redirect(url_for("admin_active"))


@app.post("/admin/records/<int:record_id>/cancel")
def admin_cancel_record(record_id):
    db = get_db()
    record = db.get_record(record_id)
    if record is None:
        abort(404)
    equipment = db.get_equipment(record.equipment_id)
    try:
        g.user.cancel_record(record, equipment)
        db.save_record(record)
        db.save_equipment(equipment)
        db.commit()
        flash("ยกเลิกรายการแล้ว อุปกรณ์กลับเข้าสต็อก", "success")
    except ValueError as error:
        db.rollback()
        flash(str(error), "danger")
    return redirect(url_for("admin_records"))


@app.post("/admin/members/<student_id>/reset-password")
def admin_reset_password(student_id):
    db = get_db()
    student = db.get_student(student_id)                    # 1) โหลดอ็อบเจกต์
    if student is None:
        abort(404)
    try:
        g.user.reset_password(student, request.form.get("new_password", ""),
                              request.form.get("confirm_password", ""))    # 2) เรียกเมธอด (กติกาอยู่ในคลาส)
        db.save_student_password(student)                                # 3) บันทึก
        db.commit()
        flash("เปลี่ยนรหัสผ่านของ " + student.full_name()
              + " เรียบร้อยแล้ว แจ้งรหัสผ่านใหม่ให้นักศึกษาใช้เข้าสู่ระบบ", "success")
    except ValueError as error:
        db.rollback()
        flash(str(error), "danger")
    return redirect(url_for("admin_member", student_id=student_id))    # 4) redirect


@app.post("/admin/equipment/<int:equipment_id>/quantity")
def admin_update_quantity(equipment_id):
    db = get_db()
    equipment = db.get_equipment(equipment_id)
    if equipment is None:
        abort(404)
    step = request.form.get("step", type=int)
    try:
        g.user.update_quantity(equipment, step)
        db.save_equipment(equipment)
        db.commit()
        flash("อัปเดตจำนวน " + equipment.name + " เรียบร้อยแล้ว", "success")
    except ValueError as error:
        db.rollback()
        flash(str(error), "danger")
    return redirect(url_for("equipment"))


if __name__ == "__main__":
    # host="0.0.0.0" = ให้เครื่องอื่นใน Wi-Fi วงเดียวกัน (เช่น โทรศัพท์) เปิดเว็บได้ที่ http://<IP เครื่องนี้>:5000
    app.run(host="0.0.0.0", debug=config.DEBUG)       # DEBUG ตั้งใน config.py (พรีเซนต์ใช้ False)
