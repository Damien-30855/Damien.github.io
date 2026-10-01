# database.py — คลาส Database: เชื่อมต่อ MySQL (XAMPP) และแปลง "แถวในตาราง <-> อ็อบเจกต์"
#
# - SQL ทั้งหมดของระบบอยู่ในไฟล์นี้ ส่วนกติกาของระบบอยู่ใน models.py
# - เมธอด get_... คืนค่าเป็น "อ็อบเจกต์" เสมอ ไม่ส่ง dict ดิบออกไปให้ app.py
# - ใช้ placeholder %s ทุกครั้ง ไม่ต่อ string เป็น SQL (กัน SQL Injection)

import pymysql

import config
from models import Student, Admin, Equipment, BorrowRecord, STATUS_DAMAGED


class Database:
    """จัดการการเชื่อมต่อ MySQL (XAMPP) และการอ่าน/บันทึกข้อมูล"""

    def __init__(self, use_database=True):
        # use_database=False ใช้ใน init_db.py เท่านั้น เพราะตอนนั้นยังไม่มีฐานข้อมูล pnru_sport
        if use_database:
            database_name = config.DB_NAME
        else:
            database_name = None
        try:
            self.conn = pymysql.connect(host=config.DB_HOST, port=config.DB_PORT,
                                        user=config.DB_USER, password=config.DB_PASSWORD,
                                        database=database_name, charset="utf8mb4",
                                        cursorclass=pymysql.cursors.DictCursor,
                                        autocommit=False)
        except pymysql.err.OperationalError as error:
            if error.args[0] == 1049:       # 1049 = MySQL เปิดอยู่ แต่ยังไม่มีฐานข้อมูลนี้
                raise ConnectionError("ยังไม่มีฐานข้อมูล " + config.DB_NAME + " กรุณารัน python init_db.py ก่อน")
            raise ConnectionError("เชื่อมต่อฐานข้อมูลไม่ได้ กรุณาเปิด MySQL ใน XAMPP Control Panel")

    def close(self):
        self.conn.close()

    def commit(self):
        """ยืนยันการเปลี่ยนแปลงทั้งหมดตั้งแต่ commit ครั้งก่อน"""
        self.conn.commit()

    def rollback(self):
        """ยกเลิกการเปลี่ยนแปลงทั้งหมดที่ยังไม่ commit (ใช้ตอนเกิด error)"""
        self.conn.rollback()

    # ---------- เมธอดช่วยรัน SQL (เมธอดอื่นในคลาสเรียกใช้ 3 ตัวนี้) ----------

    def fetch_one(self, sql, params=None):
        """รัน SELECT แล้วคืนค่า 1 แถว (dict) หรือ None ถ้าไม่พบ"""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def fetch_all(self, sql, params=None):
        """รัน SELECT แล้วคืนค่าทุกแถว (list ของ dict)"""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute(self, sql, params=None):
        """รัน INSERT / UPDATE แล้วคืนค่า id ของแถวที่เพิ่งเพิ่ม (AUTO_INCREMENT)"""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid

    def run_sql_file(self, path):
        """อ่านไฟล์ .sql แล้วรันทีละคำสั่ง (คั่นด้วย ;) — ใช้ใน init_db.py เพื่อรัน schema.sql"""
        with open(path, encoding="utf-8") as file:
            text = file.read()
        for statement in text.split(";"):
            # ตัดบรรทัดที่เป็นคอมเมนต์ทั้งบรรทัด (ขึ้นต้นด้วย --) ออก
            lines = []
            for line in statement.splitlines():
                if not line.strip().startswith("--"):
                    lines.append(line)
            sql = "\n".join(lines).strip()
            if sql != "":
                self.execute(sql)
        self.commit()

    # ---------- students ----------

    def get_student(self, student_id):
        """-> Student หรือ None"""
        row = self.fetch_one("SELECT * FROM students WHERE student_id = %s", (student_id,))
        if row is None:
            return None
        return Student.from_row(row)

    def get_student_by_email(self, email):
        """-> Student หรือ None (ใช้เช็คอีเมลซ้ำตอนสมัคร)"""
        row = self.fetch_one("SELECT * FROM students WHERE email = %s", (email,))
        if row is None:
            return None
        return Student.from_row(row)

    def get_all_students(self, keyword=""):
        """ค้นหาจากรหัสนักศึกษา ชื่อ นามสกุล หรือชื่อเต็ม (keyword ว่าง = ทุกคน) -> [Student]"""
        pattern = "%" + keyword + "%"
        rows = self.fetch_all("SELECT * FROM students WHERE student_id LIKE %s "
                              "OR CONCAT(first_name, ' ', last_name) LIKE %s "
                              "ORDER BY student_id", (pattern, pattern))
        students = []
        for row in rows:
            students.append(Student.from_row(row))
        return students

    def add_student(self, student):
        self.execute("INSERT INTO students (student_id, first_name, last_name, email, phone, password) "
                     "VALUES (%s, %s, %s, %s, %s, %s)",
                     (student.student_id, student.first_name, student.last_name, student.email,
                      student.phone, student.password))

    def save_student_password(self, student):
        """บันทึกรหัสผ่าน (hash) ใหม่ของนักศึกษา (ใช้ตอนแอดมินรีเซ็ตรหัสผ่าน)"""
        self.execute("UPDATE students SET password = %s WHERE student_id = %s",
                     (student.password, student.student_id))

    # ---------- admins ----------

    def get_admin_by_username(self, username):
        """-> Admin หรือ None"""
        row = self.fetch_one("SELECT * FROM admins WHERE username = %s", (username,))
        if row is None:
            return None
        return Admin.from_row(row)

    def get_admin(self, admin_id):
        """-> Admin หรือ None"""
        row = self.fetch_one("SELECT * FROM admins WHERE admin_id = %s", (admin_id,))
        if row is None:
            return None
        return Admin.from_row(row)

    def get_all_admins(self):
        """-> [Admin]"""
        rows = self.fetch_all("SELECT * FROM admins ORDER BY admin_id")
        admins = []
        for row in rows:
            admins.append(Admin.from_row(row))
        return admins

    def add_admin(self, admin):
        """ใช้ใน init_db.py เท่านั้น (ระบบไม่มีหน้าสมัครแอดมิน) แล้วใส่ admin_id ใหม่กลับเข้าอ็อบเจกต์"""
        admin.admin_id = self.execute("INSERT INTO admins (username, password, name) VALUES (%s, %s, %s)",
                                      (admin.username, admin.password, admin.name))

    # ---------- equipment ----------

    def get_equipment(self, equipment_id):
        """-> Equipment หรือ None (ใช้ตอนจะเปลี่ยนจำนวนอุปกรณ์)
        FOR UPDATE = ล็อกแถวนี้ไว้จนกว่าจะ commit/rollback กันสองคนจองชิ้นสุดท้ายพร้อมกัน"""
        row = self.fetch_one("SELECT * FROM equipment WHERE equipment_id = %s FOR UPDATE", (equipment_id,))
        if row is None:
            return None
        return Equipment.from_row(row)

    def get_all_equipment(self):
        """-> [Equipment] เรียงตามลำดับที่เพิ่ม"""
        rows = self.fetch_all("SELECT * FROM equipment ORDER BY equipment_id")
        equipment_list = []
        for row in rows:
            equipment_list.append(Equipment.from_row(row))
        return equipment_list

    def add_equipment(self, equipment):
        """ใช้ใน init_db.py แล้วใส่ equipment_id ใหม่กลับเข้าอ็อบเจกต์"""
        equipment.equipment_id = self.execute(
            "INSERT INTO equipment (name, total_quantity, available_quantity) VALUES (%s, %s, %s)",
            (equipment.name, equipment.total_quantity, equipment.available_quantity))

    def save_equipment(self, equipment):
        """บันทึกจำนวนล่าสุดของอ็อบเจกต์ลงฐานข้อมูล"""
        self.execute("UPDATE equipment SET total_quantity = %s, available_quantity = %s "
                     "WHERE equipment_id = %s",
                     (equipment.total_quantity, equipment.available_quantity, equipment.equipment_id))

    # ---------- borrow_records ----------

    def get_record(self, record_id):
        """-> BorrowRecord หรือ None (ใช้ตอนจะเปลี่ยนสถานะรายการ)
        FOR UPDATE = ล็อกแถวนี้ไว้จนกว่าจะ commit/rollback กันกดปุ่มซ้ำพร้อมกัน
        (คำขอที่ 2 จะรอ แล้วได้ข้อมูลล่าสุด เช่น เห็นว่ารายการคืนไปแล้ว จึงไม่คืนสต็อกซ้ำ)"""
        row = self.fetch_one("SELECT * FROM borrow_records WHERE record_id = %s FOR UPDATE", (record_id,))
        if row is None:
            return None
        return BorrowRecord.from_row(row)

    def get_records(self, status=None, student_id=None, limit=None,
                    equipment_id=None, keyword=""):
        """ดึงรายการยืม ใหม่สุดขึ้นก่อน -> [BorrowRecord]
        กรองตามสถานะ / รหัสนักศึกษา / อุปกรณ์ / คำค้น / จำนวนแถวได้ (ไม่ใส่ = ไม่กรอง)
        - status รับได้ทั้งค่าเดียว เช่น "กำลังยืม" หรือ list เช่น ["กำลังยืม", "เกินกำหนด"]
        - keyword ค้นในชื่อ / นามสกุล / ชื่อเต็ม / รหัสนักศึกษา ของผู้ยืม"""
        # ป้องกัน SQL Injection: ค่าที่ผู้ใช้กรอกทุกตัวส่งผ่าน placeholder %s ใน params เท่านั้น
        # ไม่เอาค่ามาต่อเป็นข้อความ SQL เอง (PyMySQL จะใส่เครื่องหมายคำพูดและ escape ให้)
        sql = "SELECT * FROM borrow_records WHERE 1 = 1"     # 1 = 1 ใส่ไว้ให้ต่อ AND ข้างล่างได้เลย
        params = []
        if status is not None:
            if isinstance(status, list):
                # สร้างแค่ "%s, %s, ..." ตามจำนวนสถานะ (ตัวค่าจริงยังไปทาง params)
                sql += " AND status IN (" + ", ".join(["%s"] * len(status)) + ")"
                params.extend(status)
            else:
                sql += " AND status = %s"
                params.append(status)
        if student_id is not None:
            sql += " AND student_id = %s"
            params.append(student_id)
        if equipment_id is not None:
            sql += " AND equipment_id = %s"
            params.append(equipment_id)
        if keyword != "":
            # หาผู้ยืมจากตาราง students ด้วย subquery (ไม่ใช้ JOIN) แล้วกรองรายการของคนเหล่านั้น
            pattern = "%" + keyword + "%"
            sql += (" AND student_id IN (SELECT student_id FROM students"
                    " WHERE student_id LIKE %s OR first_name LIKE %s OR last_name LIKE %s"
                    " OR CONCAT(first_name, ' ', last_name) LIKE %s)")
            params.extend([pattern, pattern, pattern, pattern])
        sql += " ORDER BY record_id DESC"
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)

        rows = self.fetch_all(sql, params)
        records = []
        for row in rows:
            records.append(BorrowRecord.from_row(row))
        return records

    def add_record(self, record):
        """INSERT รายการใหม่ แล้วใส่ record_id ใหม่กลับเข้าอ็อบเจกต์"""
        record.record_id = self.execute(
            "INSERT INTO borrow_records "
            "(student_id, equipment_id, admin_id, booked_at, start_time, return_time, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (record.student_id, record.equipment_id, record.admin_id, record.booked_at,
             record.start_time, record.return_time, record.status))

    def save_record(self, record):
        """บันทึกค่าที่เปลี่ยนได้ของรายการ (ผู้ยืนยัน, เวลายืม, เวลาคืน, สถานะ)"""
        self.execute("UPDATE borrow_records SET admin_id = %s, start_time = %s, return_time = %s, status = %s "
                     "WHERE record_id = %s",
                     (record.admin_id, record.start_time, record.return_time, record.status, record.record_id))

    def count_records(self, status):
        """จำนวนรายการที่มีสถานะนี้ (การ์ดสรุปในหน้าแรก)"""
        row = self.fetch_one("SELECT COUNT(*) AS amount FROM borrow_records WHERE status = %s", (status,))
        return row["amount"]

    def count_damaged(self, equipment_id):
        """จำนวนครั้งที่คืน-ชำรุดของอุปกรณ์ชนิดนี้ (หน้าสรุปสถิติ)"""
        row = self.fetch_one("SELECT COUNT(*) AS amount FROM borrow_records "
                             "WHERE equipment_id = %s AND status = %s", (equipment_id, STATUS_DAMAGED))
        return row["amount"]
