# init_db.py — สร้างฐานข้อมูล pnru_sport ใหม่ทั้งหมดจาก schema.sql
#
# วิธีใช้ (ต้องกด Start ที่ MySQL ใน XAMPP Control Panel ก่อน)
#   python init_db.py          -> ตาราง + อุปกรณ์ 8 ชนิด (จำนวน 0 ทุกชนิด) + แอดมิน 2 บัญชี
#   python init_db.py --demo   -> เหมือนข้างบน + ข้อมูลตัวอย่างชุดเดียวกับหน้าต้นแบบ (prototype)
#
# คำเตือน: ข้อมูลเดิมในฐานข้อมูล pnru_sport จะถูกลบทั้งหมด

import os
import sys
from datetime import datetime

from werkzeug.security import generate_password_hash

from database import Database
from models import (Student, Admin, Equipment, BorrowRecord,
                    STATUS_PENDING, STATUS_BORROWED, STATUS_OVERDUE,
                    STATUS_RETURNED, STATUS_DAMAGED, STATUS_CANCELED)

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# อุปกรณ์ 8 ชนิด: (ชื่อ, จำนวนทั้งหมดในโหมด --demo, จำนวนพร้อมใช้ในโหมด --demo)
# ถ้าไม่ใส่ --demo ทุกชนิดเริ่มที่ 0 ตามสเปก
EQUIPMENT_LIST = [
    ("ฟุตบอล", 5, 2),
    ("ฟุตซอล", 4, 4),
    ("บาสเกตบอล", 4, 3),
    ("วอลเลย์บอล", 3, 3),
    ("ตะกร้อ", 3, 0),
    ("ไม้แบดมินตัน", 6, 5),
    ("ไม้ปิงปอง", 6, 6),
    ("ชุดเปตอง", 2, 1),
]

# บัญชีแอดมินที่สร้างไว้ล่วงหน้า: (username, รหัสผ่านเริ่มต้น, ชื่อ-นามสกุล)
ADMIN_LIST = [
    ("admin1", "admin1234", "สมชาย ใจดี"),
    ("admin2", "admin1234", "อารีย์ สุขสม"),
]

# ---------- ข้อมูลตัวอย่าง (--demo) ชุดเดียวกับหน้าต้นแบบ (prototype) ----------
DEMO_PASSWORD = "123456"

# (รหัสนักศึกษา, ชื่อ, นามสกุล, อีเมล, เบอร์โทร) — อีเมลใช้โดเมน example.com ซึ่งเป็นโดเมนสำหรับตัวอย่าง
DEMO_STUDENTS = [
    ("6512345678901", "ธนกฤต", "อินทร์แก้ว", "thanakrit@example.com", "0812345678"),
    ("6512345678902", "พิมพ์ชนก", "ศรีสุข", "pimchanok@example.com", "0898765432"),
    ("6512345678903", "วีรภัทร", "มั่นคง", "weerapat@example.com", "0861234567"),
]

# (รหัสนักศึกษา, อุปกรณ์, แอดมินที่ยืนยัน, เวลาจอง, เวลายืมจริง, เวลาคืนจริง, สถานะ)
# เรียงจากเก่าไปใหม่ เพื่อให้ record_id เป็น 1-6 ตรงกับ prototype
DEMO_RECORDS = [
    ("6512345678901", "วอลเลย์บอล", None, "2026-09-20 15:00", None, None, STATUS_CANCELED),
    ("6512345678902", "ฟุตบอล", "admin2", "2026-09-21 10:00", "2026-09-21 10:05", "2026-09-21 11:00", STATUS_DAMAGED),
    ("6512345678901", "ไม้แบดมินตัน", "admin1", "2026-09-21 13:00", "2026-09-21 13:10", "2026-09-21 14:00", STATUS_RETURNED),
    ("6512345678903", "ตะกร้อ", "admin2", "2026-09-21 14:50", "2026-09-21 15:00", None, STATUS_OVERDUE),
    ("6512345678902", "บาสเกตบอล", "admin1", "2026-09-22 09:30", "2026-09-22 09:40", None, STATUS_BORROWED),
    ("6512345678901", "ฟุตบอล", None, "2026-09-22 10:05", None, None, STATUS_PENDING),
]


def to_datetime(text):
    """แปลงข้อความ '2026-09-22 10:05' เป็น datetime (ถ้าเป็น None ก็คืน None)"""
    if text is None:
        return None
    return datetime.strptime(text, "%Y-%m-%d %H:%M")


def create_equipment(db, demo):
    """เพิ่มอุปกรณ์ 8 ชนิด แล้วคืนค่าเป็น dict {ชื่ออุปกรณ์: Equipment}"""
    equipment_by_name = {}
    for name, demo_total, demo_available in EQUIPMENT_LIST:
        if demo:
            equipment = Equipment(None, name, demo_total, demo_available)
        else:
            equipment = Equipment(None, name, 0, 0)
        db.add_equipment(equipment)
        equipment_by_name[name] = equipment
    return equipment_by_name


def create_admins(db):
    """เพิ่มแอดมิน 2 บัญชี แล้วคืนค่าเป็น dict {username: Admin}"""
    admin_by_username = {}
    for username, password, name in ADMIN_LIST:
        admin = Admin(None, name, username, generate_password_hash(password))
        db.add_admin(admin)
        admin_by_username[username] = admin
    return admin_by_username


def create_demo_students(db):
    """เพิ่มนักศึกษาตัวอย่าง 3 คน โดยสมัครผ่าน Student.register() เหมือนสมัครจริงบนเว็บ"""
    for student_id, first_name, last_name, email, phone in DEMO_STUDENTS:
        student = Student.register(student_id, first_name, last_name, email, phone,
                                   DEMO_PASSWORD, DEMO_PASSWORD)
        db.add_student(student)


def create_demo_records(db, equipment_by_name, admin_by_username):
    """เพิ่มรายการยืมตัวอย่างครบทั้ง 6 สถานะ"""
    for student_id, equipment_name, admin_username, booked, start, returned, status in DEMO_RECORDS:
        admin_id = None
        if admin_username is not None:
            admin_id = admin_by_username[admin_username].admin_id
        record = BorrowRecord(None, student_id, equipment_by_name[equipment_name].equipment_id, admin_id,
                              to_datetime(booked), to_datetime(start), to_datetime(returned), status)
        db.add_record(record)


def main():
    demo = "--demo" in sys.argv

    try:
        db = Database(use_database=False)
    except ConnectionError as error:
        print(error)
        sys.exit(1)

    try:
        db.run_sql_file(SCHEMA_FILE)            # ลบฐานข้อมูลเดิม แล้วสร้างตารางใหม่
        equipment_by_name = create_equipment(db, demo)
        admin_by_username = create_admins(db)
        if demo:
            create_demo_students(db)
            create_demo_records(db, equipment_by_name, admin_by_username)
        db.commit()                             # บันทึกทั้งหมดพร้อมกันครั้งเดียว
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("สร้างฐานข้อมูล pnru_sport เรียบร้อยแล้ว")
    print("บัญชีแอดมิน:")
    for username, password, name in ADMIN_LIST:
        print("  " + username + " / " + password + "  (" + name + ")")
    if demo:
        print("เพิ่มข้อมูลตัวอย่างแล้ว: นักศึกษา " + str(len(DEMO_STUDENTS)) + " คน (รหัสผ่าน " + DEMO_PASSWORD + ")"
              + ", รายการยืม " + str(len(DEMO_RECORDS)) + " รายการ")
    else:
        print("อุปกรณ์ทุกชนิดเริ่มที่ 0 ชิ้น (ถ้าต้องการข้อมูลตัวอย่าง ให้รัน python init_db.py --demo)")


if __name__ == "__main__":
    main()
