-- ฐานข้อมูลระบบยืม-คืนอุปกรณ์กีฬา PNRU Sport (MySQL/MariaDB ของ XAMPP)
-- ใช้ได้ 2 วิธี
--   1) python init_db.py            (แนะนำ: สร้างตาราง + อุปกรณ์ 8 ชนิด + บัญชีแอดมินให้ด้วย)
--   2) import ไฟล์นี้ผ่าน http://localhost/phpmyadmin   (ได้แค่ตารางเปล่า)
-- คำเตือน: ไฟล์นี้ลบฐานข้อมูล pnru_sport เดิมทิ้งก่อนสร้างใหม่

DROP DATABASE IF EXISTS pnru_sport;
CREATE DATABASE pnru_sport CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pnru_sport;

CREATE TABLE students (
  student_id  VARCHAR(13)  NOT NULL PRIMARY KEY,   -- รหัสนักศึกษา 13 หลัก
  first_name  VARCHAR(50)  NOT NULL,
  last_name   VARCHAR(50)  NOT NULL,
  email       VARCHAR(100) NOT NULL UNIQUE,          -- เก็บไว้ก่อน ยังไม่ใช้ส่งอีเมล
  phone       VARCHAR(10)  NOT NULL,
  password    VARCHAR(255) NOT NULL                -- hash
) ENGINE=InnoDB;

CREATE TABLE admins (
  admin_id    INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username    VARCHAR(50)  NOT NULL UNIQUE,
  password    VARCHAR(255) NOT NULL,               -- hash
  name        VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE equipment (
  equipment_id        INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name                VARCHAR(50)  NOT NULL UNIQUE,
  total_quantity      INT          NOT NULL DEFAULT 0,
  available_quantity  INT          NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE borrow_records (
  record_id     INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
  student_id    VARCHAR(13)  NOT NULL,
  equipment_id  INT          NOT NULL,
  admin_id      INT          NULL,                 -- ว่างจนกว่าแอดมินจะยืนยันรับ
  booked_at     DATETIME     NOT NULL,             -- เวลาที่กดจอง
  start_time    DATETIME     NULL,                 -- เวลายืมจริง
  return_time   DATETIME     NULL,                 -- เวลาคืนจริง
  status        VARCHAR(20)  NOT NULL,
  FOREIGN KEY (student_id)   REFERENCES students(student_id),
  FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id),
  FOREIGN KEY (admin_id)     REFERENCES admins(admin_id)
) ENGINE=InnoDB;
