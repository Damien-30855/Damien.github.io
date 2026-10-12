# models.py — คลาส 4 คลาสของระบบ: Student, Admin, Equipment, BorrowRecord
#
# ไฟล์นี้เก็บ "ข้อมูลของอ็อบเจกต์ + กติกาของระบบ" ทั้งหมด (ไม่มี SQL)
# - เมธอดที่เปลี่ยนค่า จะเปลี่ยนแค่ในอ็อบเจกต์ ยังไม่บันทึกลงฐานข้อมูล
#   (app.py เป็นคนเรียก db.save_...() ต่อ)
# - ถ้าทำไม่ได้ตามกติกา จะ raise ValueError("ข้อความภาษาไทย")

import math
import re
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

# ---------- ค่าคงที่: สถานะ 6 ค่า (เก็บในฐานข้อมูลเป็นภาษาไทยตามนี้) ----------
STATUS_PENDING  = "รอยืนยัน"
STATUS_BORROWED = "กำลังยืม"
STATUS_OVERDUE  = "เกินกำหนด"
STATUS_RETURNED = "คืนแล้ว"
STATUS_DAMAGED  = "คืน-ชำรุด"
STATUS_CANCELED = "ยกเลิก"

# ---------- ค่าคงที่: เวลา ----------
BOOK_OPEN  = "09:00"      # เปิดรับจอง
BOOK_CLOSE = "15:30"      # ปิดรับจอง
DEADLINE   = "16:00"      # ต้องคืนภายในเวลานี้ของวันที่ยืม
PICKUP_MINUTES = 30       # จองแล้วต้องมายืนยันรับภายใน 30 นาที
MIN_PASSWORD = 6          # รหัสผ่านอย่างน้อย 6 ตัว (ใช้ทั้งตอนสมัครและตอนแอดมินรีเซ็ต)


def is_booking_open(now):
    """อยู่ในช่วงรับจองหรือไม่: จันทร์-ศุกร์ 09:00-15:30 เท่านั้น"""
    # weekday(): จันทร์ = 0 ... ศุกร์ = 4, เสาร์ = 5, อาทิตย์ = 6
    if now.weekday() >= 5:
        return False
    # เทียบเป็นข้อความ "ชั่วโมง:นาที" ได้เลย เพราะเป็นเลข 2 หลักเสมอ เช่น "09:00" <= "10:15" <= "15:30"
    current = now.strftime("%H:%M")
    return BOOK_OPEN <= current <= BOOK_CLOSE


# =====================================================================
class Student:
    """นักศึกษา 1 คน (ตาราง students)"""

    def __init__(self, student_id, first_name, last_name, email, phone, password):
        self.student_id = student_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email                # เก็บไว้ก่อน ยังไม่ใช้ส่งอีเมล
        self.phone = phone
        self.password = password          # เก็บเป็น hash เสมอ ไม่ใช่รหัสผ่านจริง

    @classmethod
    def from_row(cls, row):
        """Factory: สร้าง Student จากแถวในฐานข้อมูล (row เป็น dict)"""
        return cls(row["student_id"], row["first_name"], row["last_name"], row["email"],
                   row["phone"], row["password"])

    @classmethod
    def register(cls, student_id, first_name, last_name, email, phone, password, confirm_password):
        """ตรวจข้อมูลสมัครสมาชิก ถ้าผิด raise ValueError ถ้าถูก return Student ใหม่ที่ hash รหัสผ่านแล้ว
        (การเช็ครหัสนักศึกษาซ้ำ/อีเมลซ้ำทำใน app.py ผ่าน db.get_student() / db.get_student_by_email()
        เพราะต้องใช้ฐานข้อมูล)"""
        student_id = student_id.strip()
        first_name = first_name.strip()
        last_name = last_name.strip()
        email = email.strip().lower()                    # เก็บอีเมลเป็นตัวพิมพ์เล็กเสมอ
        phone = phone.strip()

        # กติกา: รหัสนักศึกษาเป็นตัวเลข 0-9 จำนวน 13 หลักพอดี
        if not re.fullmatch(r"[0-9]{13}", student_id):
            raise ValueError("รหัสนักศึกษาต้องเป็นตัวเลข 13 หลัก")
        # กติกา: ชื่อและนามสกุลห้ามว่าง (ยาวไม่เกิน 50 ตัว ให้พอดีกับคอลัมน์ VARCHAR(50))
        if first_name == "":
            raise ValueError("กรุณากรอกชื่อ")
        if last_name == "":
            raise ValueError("กรุณากรอกนามสกุล")
        if len(first_name) > 50 or len(last_name) > 50:
            raise ValueError("ชื่อและนามสกุลยาวได้ไม่เกิน 50 ตัวอักษร")
        # กติกา: อีเมลรูปแบบถูก (ตรวจแบบง่าย: มี @ มีจุดหลัง @ และไม่มีช่องว่าง)
        at = email.find("@")
        if " " in email or at < 1 or "." not in email[at + 1:] or len(email) > 100:
            raise ValueError("รูปแบบอีเมลไม่ถูกต้อง")
        # กติกา: เบอร์โทรเป็นตัวเลข 10 หลัก ขึ้นต้นด้วย 0
        if not re.fullmatch(r"0[0-9]{9}", phone):
            raise ValueError("เบอร์โทรต้องเป็นตัวเลข 10 หลัก ขึ้นต้นด้วย 0")
        # กติกา: รหัสผ่านอย่างน้อย 6 ตัว และช่องยืนยันต้องตรงกัน
        if len(password) < MIN_PASSWORD:
            raise ValueError("รหัสผ่านต้องมีอย่างน้อย " + str(MIN_PASSWORD) + " ตัวอักษร")
        if password != confirm_password:
            raise ValueError("รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน")

        # Encapsulation: hash รหัสผ่านก่อนเก็บลงอ็อบเจกต์ ไม่มีการเก็บรหัสผ่านจริง
        return cls(student_id, first_name, last_name, email, phone, generate_password_hash(password))

    def login(self, password):
        """รหัสผ่านถูกต้องหรือไม่ (เทียบกับ hash ที่เก็บไว้)"""
        return check_password_hash(self.password, password)

    def active_records(self, records):
        """รายการที่ยังค้างอยู่ทั้งหมดของตัวเอง ('รอยืนยัน' / 'กำลังยืม' / 'เกินกำหนด') -> [BorrowRecord]
        ใช้ทั้งกติกา 'ห้ามจองซ้อน' และหน้าตรวจสอบสถานะที่แสดงคำร้องค้างของตัวเอง"""
        active = []
        for record in records:
            if record.student_id == self.student_id and \
                    record.status in (STATUS_PENDING, STATUS_BORROWED, STATUS_OVERDUE):
                active.append(record)
        return active

    def has_active_record(self, records):
        """มีรายการ 'รอยืนยัน' / 'กำลังยืม' / 'เกินกำหนด' ของตัวเองอยู่หรือไม่ (กติกา: ห้ามจองซ้อน)"""
        return len(self.active_records(records)) > 0

    def active_record(self, records):
        """รายการที่ยังค้างอยู่ของตัวเอง ('รอยืนยัน' / 'กำลังยืม' / 'เกินกำหนด') หรือ None
        ใช้เลือกว่าหน้ายืมอุปกรณ์จะแสดงฟอร์มจอง หรือการ์ดของรายการนั้น"""
        active = self.active_records(records)
        if len(active) > 0:
            return active[0]
        return None

    def has_overdue_record(self, records):
        """มีรายการ 'เกินกำหนด' ของตัวเองค้างอยู่หรือไม่ (กติกา: ค้างเกินกำหนดยืมใหม่ไม่ได้)"""
        for record in records:
            if record.student_id == self.student_id and record.status == STATUS_OVERDUE:
                return True
        return False

    def check_can_book(self, records, now):
        """ตรวจเงื่อนไขการจองข้อ 1-3 ถ้าจองไม่ได้ raise ValueError พร้อมเหตุผล
        (หน้ายืมอุปกรณ์เรียกใช้ เพื่อบอกเหตุผลและปิดปุ่มจองตั้งแต่เปิดหน้า)"""
        # ข้อ 1: จองได้เฉพาะจันทร์-ศุกร์ 09:00-15:30
        if not is_booking_open(now):
            raise ValueError("ขณะนี้อยู่นอกเวลารับจอง (รับจองจันทร์-ศุกร์ " + BOOK_OPEN + "-" + BOOK_CLOSE + ")")
        # ข้อ 2: ต้องไม่มีรายการเกินกำหนดค้างอยู่
        if self.has_overdue_record(records):
            raise ValueError("คุณมีรายการเกินกำหนดที่ยังไม่คืน ต้องคืนอุปกรณ์ก่อนจึงจะยืมใหม่ได้")
        # ข้อ 3: ห้ามจองซ้อน
        if self.has_active_record(records):
            raise ValueError("คุณมีรายการที่รอยืนยันหรือกำลังยืมอยู่แล้ว (ยืมได้ครั้งละ 1 ชิ้น)")

    def book(self, equipment, records, now):
        """จองอุปกรณ์ 1 ชิ้น: ตรวจครบ 4 ข้อ -> ของออกจากสต็อก -> return BorrowRecord ใหม่สถานะ 'รอยืนยัน'"""
        self.check_can_book(records, now)          # ข้อ 1-3
        if not equipment.is_available():           # ข้อ 4: อุปกรณ์ต้องพร้อมให้ยืม
            raise ValueError(equipment.name + " ไม่พร้อมให้ยืมในขณะนี้")
        equipment.decrease_available()
        # Association: Student สร้าง (make) BorrowRecord ของตัวเอง
        return BorrowRecord(None, self.student_id, equipment.equipment_id, None,
                            now, None, None, STATUS_PENDING)

    def cancel_booking(self, record, equipment):
        """นักศึกษายกเลิกการจองเอง: เฉพาะรายการของตัวเองที่ยัง 'รอยืนยัน' -> 'ยกเลิก' + available +1"""
        if record.student_id != self.student_id:
            raise ValueError("ยกเลิกได้เฉพาะรายการของตัวเองเท่านั้น")
        if record.status != STATUS_PENDING:
            raise ValueError("ยกเลิกการจองได้เฉพาะรายการที่ 'รอยืนยัน' เท่านั้น")
        record.cancel()
        equipment.increase_available()

    def full_name(self):
        """ชื่อเต็ม เช่น 'ธนกฤต อินทร์แก้ว' (ใช้ทุกที่ที่แสดงชื่อเต็ม เช่น หน้าแอดมิน)"""
        return self.first_name + " " + self.last_name

    def short_name(self):
        """ชื่อแบบย่อนามสกุล เช่น 'ธนกฤต อินทร์แก้ว' -> 'ธนกฤต อ.' (Guest/นักศึกษาเห็นแบบนี้)"""
        first_letter = self.last_name[0]
        # ถ้าตัวแรกของนามสกุลเป็นสระหน้า (เ แ โ ใ ไ) ให้ใช้พยัญชนะตัวถัดไป เช่น 'ใจดี' -> 'จ.'
        if first_letter in "เแโใไ" and len(self.last_name) > 1:
            first_letter = self.last_name[1]
        return self.first_name + " " + first_letter + "."


# =====================================================================
class Admin:
    """แอดมิน 1 คน (ตาราง admins) — รวมเจ้าหน้าที่ รุ่นพี่ และอาจารย์ บัญชีสร้างไว้ล่วงหน้า"""

    def __init__(self, admin_id, name, username, password):
        self.admin_id = admin_id
        self.name = name
        self.username = username
        self.password = password          # hash

    @classmethod
    def from_row(cls, row):
        """Factory: สร้าง Admin จากแถวในฐานข้อมูล"""
        return cls(row["admin_id"], row["name"], row["username"], row["password"])

    def login(self, password):
        """รหัสผ่านถูกต้องหรือไม่"""
        return check_password_hash(self.password, password)

    # ----- Association: Admin รับอ็อบเจกต์ BorrowRecord / Equipment มาแล้วสั่งงานต่อ -----

    def confirm_pickup(self, record, now):
        """ยืนยันรับอุปกรณ์: ใช้ได้เฉพาะ 'รอยืนยัน' ที่ยังไม่หมดเวลา 30 นาที
        -> 'กำลังยืม', start_time = now, admin_id = แอดมินคนนี้"""
        if record.status != STATUS_PENDING:
            raise ValueError("ยืนยันรับได้เฉพาะรายการที่ 'รอยืนยัน' เท่านั้น")
        if record.is_expired(now):
            raise ValueError("รายการนี้เกินเวลายืนยันรับ " + str(PICKUP_MINUTES) + " นาทีแล้ว")
        # Admin เป็น "ผู้ยืนยันรายการ" (confirm) จึงเปลี่ยนค่าเหล่านี้ของ record ได้
        record.status = STATUS_BORROWED
        record.start_time = now
        record.admin_id = self.admin_id

    def confirm_return(self, record, equipment, is_damaged, now):
        """ยืนยันคืน: ใช้ได้กับ 'กำลังยืม' / 'เกินกำหนด' (คืนข้ามวันได้) -> return_time = now
        ปกติ: 'คืนแล้ว' + available +1 | ชำรุด: 'คืน-ชำรุด' + total -1 (available ไม่เพิ่ม)"""
        if record.status not in (STATUS_BORROWED, STATUS_OVERDUE):
            raise ValueError("ยืนยันคืนได้เฉพาะรายการที่ 'กำลังยืม' หรือ 'เกินกำหนด' เท่านั้น")
        # Encapsulation: จำนวนอุปกรณ์เปลี่ยนผ่านเมธอดของ Equipment เท่านั้น
        if is_damaged:
            equipment.decrease_total()          # ของชำรุดไม่กลับเข้าสต็อก และตัดออกจากจำนวนรวม
            record.status = STATUS_DAMAGED
        else:
            equipment.increase_available()      # ของกลับเข้าสต็อก
            record.status = STATUS_RETURNED
        record.return_time = now

    def cancel_record(self, record, equipment):
        """ยกเลิกรายการที่บันทึกผิด (เฉพาะที่ยังไม่คืน) -> 'ยกเลิก' + available +1"""
        record.cancel()                     # ให้ BorrowRecord เปลี่ยนสถานะตัวเอง (ข้างในเช็คสถานะให้)
        equipment.increase_available()      # ให้ Equipment คืนสต็อกตัวเอง

    def update_quantity(self, equipment, step):
        """ปุ่ม - / + ในหน้ารายการอุปกรณ์ของแอดมิน
        step = +1: total +1, available +1
        step = -1: ต้องมีของพร้อมใช้เหลืออยู่ (available > 0) ถึงลดได้ทั้งคู่"""
        if step == 1:
            equipment.increase_total()
            equipment.increase_available()
        elif step == -1:
            if not equipment.is_available():
                raise ValueError("ลดจำนวนไม่ได้ เพราะอุปกรณ์ที่เหลือถูกยืมออกไปทั้งหมดแล้ว")
            equipment.decrease_available()
            equipment.decrease_total()
        else:
            raise ValueError("ปรับจำนวนได้ครั้งละ +1 หรือ -1 เท่านั้น")

    def reset_password(self, student, new_password, confirm_password):
        """นักศึกษาลืมรหัสผ่าน แล้วมาติดต่อที่ห้องกีฬา แอดมินตั้งรหัสผ่านใหม่ให้
        กติกาเดียวกับตอนสมัคร: อย่างน้อย 6 ตัว และทั้งสองช่องต้องตรงกัน"""
        if len(new_password) < MIN_PASSWORD:
            raise ValueError("รหัสผ่านต้องมีอย่างน้อย " + str(MIN_PASSWORD) + " ตัวอักษร")
        if new_password != confirm_password:
            raise ValueError("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
        # Association: Admin เปลี่ยนรหัสผ่านของอ็อบเจกต์ Student ที่ส่งเข้ามา (เก็บเป็น hash เสมอ)
        student.password = generate_password_hash(new_password)


# =====================================================================
class Equipment:
    """อุปกรณ์ 1 ชนิด (ตาราง equipment) — นับรวมจำนวนต่อชนิด ไม่แยกรายชิ้น"""

    def __init__(self, equipment_id, name, total_quantity, available_quantity):
        self.equipment_id = equipment_id
        self.name = name
        self.total_quantity = total_quantity            # จำนวนทั้งหมดที่มี
        self.available_quantity = available_quantity    # จำนวนที่พร้อมให้ยืมตอนนี้

    @classmethod
    def from_row(cls, row):
        """Factory: สร้าง Equipment จากแถวในฐานข้อมูล"""
        return cls(row["equipment_id"], row["name"], row["total_quantity"], row["available_quantity"])

    def is_available(self):
        """พร้อมให้ยืมหรือไม่ (เหลืออย่างน้อย 1 ชิ้น)"""
        return self.available_quantity > 0

    def borrowed_quantity(self):
        """จำนวนที่กำลังถูกยืม = ทั้งหมด - พร้อมใช้ (หน้าสรุปสถิติ)"""
        return self.total_quantity - self.available_quantity

    # Encapsulation: เมธอดด้านล่างป้องกันไม่ให้จำนวนผิดกติกา (ติดลบ หรือ available เกิน total)

    def decrease_available(self):
        """ของออกจากสต็อก 1 ชิ้น (ตอนจอง / ตอนแอดมินกด -)"""
        if not self.is_available():
            raise ValueError(self.name + " ไม่พร้อมให้ยืมในขณะนี้")
        self.available_quantity -= 1

    def increase_available(self):
        """ของกลับเข้าสต็อก 1 ชิ้น (ตอนคืนปกติ / ยกเลิก / แอดมินกด +)"""
        if self.available_quantity >= self.total_quantity:
            raise ValueError("จำนวนพร้อมใช้ของ " + self.name + " จะเกินจำนวนทั้งหมดไม่ได้")
        self.available_quantity += 1

    def increase_total(self):
        """เพิ่มจำนวนทั้งหมด 1 ชิ้น (ตอนแอดมินกด +)"""
        self.total_quantity += 1

    def decrease_total(self):
        """ลดจำนวนทั้งหมด 1 ชิ้น (ตอนคืน-ชำรุด / แอดมินกด -)"""
        # จำนวนทั้งหมดต้องไม่น้อยกว่าจำนวนที่พร้อมใช้
        if self.total_quantity - 1 < self.available_quantity:
            raise ValueError("ลดจำนวนทั้งหมดของ " + self.name + " ไม่ได้")
        self.total_quantity -= 1


# =====================================================================
class BorrowRecord:
    """รายการยืม 1 รายการ (ตาราง borrow_records)
    Association: Student 1 - * BorrowRecord (make), Equipment 1 - * BorrowRecord (borrow),
                 Admin 0..1 - * BorrowRecord (confirm) -> admin_id เป็น None จนกว่าแอดมินจะยืนยันรับ"""

    def __init__(self, record_id, student_id, equipment_id, admin_id,
                 booked_at, start_time, return_time, status):
        self.record_id = record_id
        self.student_id = student_id
        self.equipment_id = equipment_id
        self.admin_id = admin_id            # None = ยังไม่มีแอดมินยืนยันรับ
        self.booked_at = booked_at          # datetime ตอนกดจอง
        self.start_time = start_time        # datetime ตอนแอดมินยืนยันรับ (None = ยังไม่เริ่มยืม)
        self.return_time = return_time      # datetime ตอนแอดมินยืนยันคืน (None = ยังไม่คืน)
        self.status = status

    @classmethod
    def from_row(cls, row):
        """Factory: สร้าง BorrowRecord จากแถวในฐานข้อมูล (PyMySQL คืน DATETIME เป็น datetime ให้แล้ว)"""
        return cls(row["record_id"], row["student_id"], row["equipment_id"], row["admin_id"],
                   row["booked_at"], row["start_time"], row["return_time"], row["status"])

    # Abstraction: คนเรียกไม่ต้องรู้ว่าข้างในเทียบกับ 16:00 หรือ 30 นาที แค่เรียกชื่อเมธอด

    def due_time(self):
        """กำหนดคืน = 16:00 ของวันที่เริ่มยืมเสมอ (ไม่ได้เก็บในฐานข้อมูล)
        ถ้ายังไม่เริ่มยืม return None"""
        if self.start_time is None:
            return None
        deadline = datetime.strptime(DEADLINE, "%H:%M").time()
        return datetime.combine(self.start_time.date(), deadline)

    def is_overdue(self, now):
        """'กำลังยืม' และเลย 16:00 ของวันที่ยืมแล้ว (ตัดเป๊ะ ไม่มี grace period)"""
        if self.status != STATUS_BORROWED:
            return False
        return now > self.due_time()

    def pickup_deadline(self):
        """เวลาสุดท้ายที่ต้องมารับอุปกรณ์ = เวลาจอง + 30 นาที (ใช้แสดง 'มารับภายใน 10:35 น.')"""
        return self.booked_at + timedelta(minutes=PICKUP_MINUTES)

    def is_expired(self, now):
        """'รอยืนยัน' และเลย 30 นาทีนับจากเวลาจองแล้ว"""
        if self.status != STATUS_PENDING:
            return False
        return now > self.pickup_deadline()

    def minutes_left(self, now):
        """เหลือเวลาให้มายืนยันรับอีกกี่นาที (ปัดขึ้น ไม่ต่ำกว่า 0) ใช้แสดง 'เหลือเวลา X นาที'"""
        seconds = (self.pickup_deadline() - now).total_seconds()
        if seconds <= 0:
            return 0
        return math.ceil(seconds / 60)

    def can_cancel(self):
        """ยกเลิกได้หรือไม่: ได้เฉพาะรายการที่ยังไม่คืน (รอยืนยัน / กำลังยืม / เกินกำหนด)"""
        return self.status in (STATUS_PENDING, STATUS_BORROWED, STATUS_OVERDUE)

    def cancel(self):
        """เปลี่ยนเป็น 'ยกเลิก' (การคืนสต็อกให้ผู้เรียกทำผ่าน Equipment.increase_available())"""
        if not self.can_cancel():
            raise ValueError("ยกเลิกได้เฉพาะรายการที่ยังไม่คืนเท่านั้น")
        self.status = STATUS_CANCELED

    def mark_overdue(self, now):
        """เปลี่ยน 'กำลังยืม' เป็น 'เกินกำหนด' เมื่อเลย 16:00 แล้ว (ใช้ตอนอัปเดตสถานะอัตโนมัติ)"""
        if not self.is_overdue(now):
            raise ValueError("รายการนี้ยังไม่เกินกำหนด")
        self.status = STATUS_OVERDUE
