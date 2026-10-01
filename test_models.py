# test_models.py — ทดสอบคลาสใน models.py โดยไม่ต้องเปิดเว็บและไม่ต้องมีฐานข้อมูล
#
# วิธีรัน: python test_models.py
# สร้างอ็อบเจกต์ขึ้นมาเอง แล้วเรียกเมธอดตามลำดับการใช้งานจริง (สมัคร -> จอง -> รับของ -> คืน)

import sys
from datetime import datetime

from models import (Student, Admin, Equipment, BorrowRecord, is_booking_open,
                    STATUS_PENDING, STATUS_BORROWED, STATUS_OVERDUE,
                    STATUS_RETURNED, STATUS_DAMAGED, STATUS_CANCELED)

results = []    # เก็บผลของแต่ละข้อ (True = ผ่าน)


def check(title, actual, expected):
    """เทียบค่าที่ได้ (actual) กับค่าที่ควรได้ (expected)"""
    if actual == expected:
        print("  ผ่าน    ", title)
        results.append(True)
    else:
        print("  ไม่ผ่าน ", title, "| ได้", actual, "| ควรได้", expected)
        results.append(False)


def check_error(title, method, *args):
    """เรียกเมธอดที่ "ควร" ทำไม่ได้ตามกติกา ถ้า raise ValueError จริงถือว่าผ่าน
    (ส่งเมธอดเข้ามาโดยยังไม่เรียก แล้วให้ฟังก์ชันนี้เรียกแทนด้วย args ที่ให้มา)"""
    try:
        method(*args)
    except ValueError as error:
        print("  ผ่าน    ", title, "->", error)
        results.append(True)
        return
    print("  ไม่ผ่าน ", title, "(ควร raise ValueError แต่ไม่มี)")
    results.append(False)


def at(text):
    """สร้างเวลาจำลองจากข้อความ เช่น at('2026-09-28 10:00')"""
    return datetime.strptime(text, "%Y-%m-%d %H:%M")


print("\n[1] ช่วงเวลารับจอง is_booking_open()")
check("จันทร์ 09:00 จองได้", is_booking_open(at("2026-09-28 09:00")), True)
check("จันทร์ 15:30 จองได้", is_booking_open(at("2026-09-28 15:30")), True)
check("จันทร์ 08:59 จองไม่ได้", is_booking_open(at("2026-09-28 08:59")), False)
check("จันทร์ 15:31 จองไม่ได้", is_booking_open(at("2026-09-28 15:31")), False)
check("เสาร์ 10:00 จองไม่ได้", is_booking_open(at("2026-09-26 10:00")), False)

print("\n[2] สมัครสมาชิก Student.register() และ login()")
student = Student.register("6512345678901", "ธนกฤต", "อินทร์แก้ว", "Thanakrit@Example.com", "0812345678", "123456", "123456")
check("ได้อ็อบเจกต์ Student", type(student), Student)
check("เก็บรหัสผ่านเป็น hash ไม่ใช่ข้อความตรง ๆ", student.password == "123456", False)
check("login รหัสผ่านถูก", student.login("123456"), True)
check("login รหัสผ่านผิด", student.login("999999"), False)
check_error("รหัสนักศึกษา 12 หลัก", Student.register, "651234567890", "ก", "ข", "a@b.co", "0800000000", "123456", "123456")
check_error("รหัสนักศึกษามีตัวอักษร", Student.register, "65123456789ab", "ก", "ข", "a@b.co", "0800000000", "123456", "123456")
check_error("รหัสผ่านสั้นกว่า 6 ตัว", Student.register, "6512345678909", "ก", "ข", "a@b.co", "0800000000", "12345", "12345")
check_error("ยืนยันรหัสผ่านไม่ตรง", Student.register, "6512345678909", "ก", "ข", "a@b.co", "0800000000", "123456", "654321")
check_error("เบอร์โทร 9 หลัก", Student.register, "6512345678909", "ก", "ข", "a@b.co", "081234567", "123456", "123456")
check_error("เบอร์โทรไม่ขึ้นต้นด้วย 0", Student.register, "6512345678909", "ก", "ข", "a@b.co", "8123456789", "123456", "123456")
check("ชื่อย่อ short_name()", student.short_name(), "ธนกฤต อ.")
check("ชื่อเต็ม full_name()", student.full_name(), "ธนกฤต อินทร์แก้ว")
check("อีเมลเก็บเป็นตัวพิมพ์เล็ก", student.email, "thanakrit@example.com")
check_error("เว้นนามสกุลว่าง", Student.register, "6512345678909", "ก", "   ", "a@b.co", "0800000000", "123456", "123456")
check_error("เว้นชื่อว่าง", Student.register, "6512345678909", "", "ข", "a@b.co", "0800000000", "123456", "123456")
check_error("อีเมลไม่มี @", Student.register, "6512345678909", "ก", "ข", "abc.example.com", "0800000000", "123456", "123456")
check_error("อีเมลไม่มีจุดหลัง @", Student.register, "6512345678909", "ก", "ข", "abc@example", "0800000000", "123456", "123456")
check_error("อีเมลมีช่องว่าง", Student.register, "6512345678909", "ก", "ข", "ab c@example.com", "0800000000", "123456", "123456")
check("ชื่อย่อ นามสกุลขึ้นต้นด้วยสระหน้า", Student("1", "สมชาย", "ใจดี", "", "", "").short_name(), "สมชาย จ.")

print("\n[3] อุปกรณ์ Equipment")
football = Equipment(1, "ฟุตบอล", 0, 0)
check("เริ่มระบบจำนวน 0 -> ไม่พร้อมให้ยืม", football.is_available(), False)
check_error("ลดของตอนหมด", football.decrease_available)
check_error("เพิ่ม available เกิน total", football.increase_available)

print("\n[4] แอดมินปรับจำนวน Admin.update_quantity()")
admin = Admin(1, "สมชาย ใจดี", "admin1", "hash")
admin.update_quantity(football, 1)
admin.update_quantity(football, 1)
check("กด + 2 ครั้ง -> total 2, available 2", (football.total_quantity, football.available_quantity), (2, 2))
admin.update_quantity(football, -1)
check("กด - 1 ครั้ง -> total 1, available 1", (football.total_quantity, football.available_quantity), (1, 1))

print("\n[5] นักศึกษาจอง Student.book() (ตรวจ 4 ข้อ)")
check_error("จองนอกเวลา 15:31", student.book, football, [], at("2026-09-28 15:31"))
check_error("จองวันเสาร์", student.book, football, [], at("2026-09-26 10:00"))
record = student.book(football, [], at("2026-09-28 10:05"))
check("ได้ BorrowRecord ใหม่สถานะ รอยืนยัน", (type(record), record.status), (BorrowRecord, STATUS_PENDING))
check("บันทึกเวลาจอง / ยังไม่มีแอดมินยืนยัน", (record.booked_at, record.admin_id), (at("2026-09-28 10:05"), None))
check("จองแล้ว available เหลือ 0", football.available_quantity, 0)
check_error("กด - ตอน available = 0", admin.update_quantity, football, -1)
check("มีรายการ Active แล้ว -> ห้ามจองซ้อน", student.has_active_record([record]), True)
check_error("จองซ้อน", student.book, Equipment(2, "ฟุตซอล", 1, 1), [record], at("2026-09-28 10:06"))
other = Student.register("6512345678902", "พิมพ์ชนก", "ศรีสุข", "pimchanok@example.com", "0898765432", "123456", "123456")
check_error("คนอื่นจองของที่หมด", other.book, football, [], at("2026-09-28 10:06"))

check("รายการที่ค้างอยู่ active_record() คือรายการที่เพิ่งจอง", student.active_record([record]), record)
check("ไม่มีรายการค้าง active_record() เป็น None", other.active_record([record]), None)

print("\n[6] แอดมินยืนยันรับ (Association: Admin สั่ง BorrowRecord)")
check("มารับภายใน pickup_deadline() = จอง 10:05 + 30 นาที", record.pickup_deadline(), at("2026-09-28 10:35"))
check("เหลือเวลายืนยันตอน 10:17", record.minutes_left(at("2026-09-28 10:17")), 18)
check("10:35 ยังไม่หมดเวลา 30 นาที", record.is_expired(at("2026-09-28 10:35")), False)
check("10:36 หมดเวลา 30 นาทีแล้ว", record.is_expired(at("2026-09-28 10:36")), True)
check_error("ยืนยันรับหลังหมดเวลา", admin.confirm_pickup, record, at("2026-09-28 10:36"))
admin.confirm_pickup(record, at("2026-09-28 10:20"))
check("ยืนยันรับแล้ว -> กำลังยืม", record.status, STATUS_BORROWED)
check("บันทึกเวลายืมจริง", record.start_time, at("2026-09-28 10:20"))
check("บันทึกแอดมินผู้ยืนยัน", record.admin_id, admin.admin_id)
check("กำหนดคืน = 16:00 ของวันที่ยืม", record.due_time(), at("2026-09-28 16:00"))
check_error("ยืนยันรับซ้ำ", admin.confirm_pickup, record, at("2026-09-28 10:21"))

print("\n[7] เกินกำหนด 16:00")
check("16:00 พอดี ยังไม่เกิน", record.is_overdue(at("2026-09-28 16:00")), False)
check("16:01 เกินกำหนด", record.is_overdue(at("2026-09-28 16:01")), True)
check_error("เปลี่ยนเป็นเกินกำหนดก่อน 16:00", record.mark_overdue, at("2026-09-28 15:00"))
record.mark_overdue(at("2026-09-28 16:01"))
check("สถานะเป็น เกินกำหนด", record.status, STATUS_OVERDUE)
check("มีรายการเกินกำหนดค้าง -> ยืมใหม่ไม่ได้", student.has_overdue_record([record]), True)
check("เกินกำหนดนับเป็นรายการที่ยังค้าง has_active_record()", student.has_active_record([record]), True)
check_error("จองวันถัดไปทั้งที่ยังค้างเกินกำหนด", student.book, Equipment(2, "ฟุตซอล", 1, 1), [record], at("2026-09-29 09:00"))

print("\n[8] ยืนยันคืน-ปกติ (คืนข้ามวันได้)")
admin.confirm_return(record, football, False, at("2026-09-29 09:10"))
check("สถานะเป็น คืนแล้ว", record.status, STATUS_RETURNED)
check("ของกลับเข้าสต็อก available 1", football.available_quantity, 1)
check("บันทึกเวลาคืนจริง", record.return_time, at("2026-09-29 09:10"))
check("คืนแล้วไม่ค้าง -> จองใหม่ได้", student.has_active_record([record]) or student.has_overdue_record([record]), False)
check_error("ยืนยันคืนซ้ำ", admin.confirm_return, record, football, False, at("2026-09-29 09:11"))
check_error("ยกเลิกรายการที่คืนแล้ว", admin.cancel_record, record, football)

print("\n[9] ยืนยันคืน-ชำรุด")
record2 = student.book(football, [record], at("2026-09-29 10:00"))
admin.confirm_pickup(record2, at("2026-09-29 10:05"))
check("กำลังถูกยืม 1 ชิ้น", football.borrowed_quantity(), 1)
admin.confirm_return(record2, football, True, at("2026-09-29 11:00"))
check("สถานะเป็น คืน-ชำรุด", record2.status, STATUS_DAMAGED)
check("total ลดเหลือ 0, available ไม่เพิ่ม (0)", (football.total_quantity, football.available_quantity), (0, 0))

print("\n[10] นักศึกษายกเลิกการจองเอง Student.cancel_booking()")
admin.update_quantity(football, 1)
record3 = student.book(football, [], at("2026-09-30 10:00"))
check_error("คนอื่นยกเลิกรายการของเรา", other.cancel_booking, record3, football)
student.cancel_booking(record3, football)
check("สถานะเป็น ยกเลิก", record3.status, STATUS_CANCELED)
check("ของกลับเข้าสต็อก available 1", football.available_quantity, 1)
check("ยกเลิกแล้วไม่มีปุ่มยกเลิกอีก", record3.can_cancel(), False)
check_error("ยกเลิกซ้ำ", student.cancel_booking, record3, football)

print("\n[11] แอดมินยกเลิกรายการ Admin.cancel_record()")
record4 = student.book(football, [], at("2026-09-30 11:00"))
admin.confirm_pickup(record4, at("2026-09-30 11:05"))
check_error("นักศึกษายกเลิกรายการที่กำลังยืมเอง", student.cancel_booking, record4, football)
admin.cancel_record(record4, football)
check("สถานะเป็น ยกเลิก", record4.status, STATUS_CANCELED)
check("ของกลับเข้าสต็อก available 1", football.available_quantity, 1)
check_error("ยกเลิกซ้ำ", admin.cancel_record, record4, football)

print("\n[12] แอดมินรีเซ็ตรหัสผ่าน Admin.reset_password()")
check_error("รหัสใหม่สั้นกว่า 6 ตัว", admin.reset_password, student, "12345", "12345")
check_error("รหัสใหม่สองช่องไม่ตรงกัน", admin.reset_password, student, "abcdef", "abcdeg")
check("รีเซ็ตไม่สำเร็จ รหัสเดิมยังใช้ได้", student.login("123456"), True)
admin.reset_password(student, "newpass1", "newpass1")
check("รีเซ็ตแล้ว login ด้วยรหัสใหม่ได้", student.login("newpass1"), True)
check("รีเซ็ตแล้ว รหัสเดิมใช้ไม่ได้", student.login("123456"), False)
check("รหัสใหม่เก็บเป็น hash", student.password == "newpass1", False)

print("\nสรุป: ผ่าน", results.count(True), "จาก", len(results), "ข้อ")
if False in results:
    sys.exit(1)
