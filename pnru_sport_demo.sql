-- pnru_sport_demo.sql : ฐานข้อมูล pnru_sport พร้อมข้อมูลตัวอย่าง (เหมือนรัน python init_db.py --demo)
-- วิธีใช้: เปิด http://localhost/phpmyadmin -> แท็บ Import -> เลือกไฟล์นี้ -> กด Import
-- (ไม่ต้องสร้างฐานข้อมูลก่อน ไฟล์นี้สร้าง pnru_sport ให้เอง และจะลบ pnru_sport เดิมถ้ามีอยู่)
-- บัญชี: แอดมิน admin1 / admin1234, admin2 / admin1234 | นักศึกษา 6512345678901-903 / 123456

DROP DATABASE IF EXISTS pnru_sport;
CREATE DATABASE pnru_sport CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pnru_sport;


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `admins` (
  `admin_id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

LOCK TABLES `admins` WRITE;
/*!40000 ALTER TABLE `admins` DISABLE KEYS */;
INSERT INTO `admins` VALUES (1,'admin1','scrypt:32768:8:1$hAVJm6inN6cotVQw$55ebd560facbe2cdbcba50217c926342b70dd3549ab1ef28605b2ebc137e95908f925ccb8a730e2d9d72a659ff9253c80aae278ad265608eae35993d43559cf3','สมชาย ใจดี'),(2,'admin2','scrypt:32768:8:1$uCWK2wo4Oe8k63v0$9c2343522237beb0f8570a14ce2dc76f9ed6d8a994b040e05d211d73a2fe4434966ad260139bdb1b0a003d54b1e2ed8ea3411cb3e90fd66b3306c0f88cce1e8e','อารีย์ สุขสม');
/*!40000 ALTER TABLE `admins` ENABLE KEYS */;
UNLOCK TABLES;
DROP TABLE IF EXISTS `borrow_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `borrow_records` (
  `record_id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` varchar(13) NOT NULL,
  `equipment_id` int(11) NOT NULL,
  `admin_id` int(11) DEFAULT NULL,
  `booked_at` datetime NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `return_time` datetime DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  PRIMARY KEY (`record_id`),
  KEY `student_id` (`student_id`),
  KEY `equipment_id` (`equipment_id`),
  KEY `admin_id` (`admin_id`),
  CONSTRAINT `borrow_records_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `borrow_records_ibfk_2` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`),
  CONSTRAINT `borrow_records_ibfk_3` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`admin_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

LOCK TABLES `borrow_records` WRITE;
/*!40000 ALTER TABLE `borrow_records` DISABLE KEYS */;
INSERT INTO `borrow_records` VALUES (1,'6512345678901',4,NULL,'2026-09-20 15:00:00',NULL,NULL,'ยกเลิก'),(2,'6512345678902',1,2,'2026-09-21 10:00:00','2026-09-21 10:05:00','2026-09-21 11:00:00','คืน-ชำรุด'),(3,'6512345678901',6,1,'2026-09-21 13:00:00','2026-09-21 13:10:00','2026-09-21 14:00:00','คืนแล้ว'),(4,'6512345678903',5,2,'2026-09-21 14:50:00','2026-09-21 15:00:00',NULL,'เกินกำหนด'),(5,'6512345678902',3,1,'2026-09-22 09:30:00','2026-09-22 09:40:00',NULL,'กำลังยืม'),(6,'6512345678901',1,NULL,'2026-09-22 10:05:00',NULL,NULL,'รอยืนยัน');
/*!40000 ALTER TABLE `borrow_records` ENABLE KEYS */;
UNLOCK TABLES;
DROP TABLE IF EXISTS `equipment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `equipment` (
  `equipment_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `total_quantity` int(11) NOT NULL DEFAULT 0,
  `available_quantity` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`equipment_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

LOCK TABLES `equipment` WRITE;
/*!40000 ALTER TABLE `equipment` DISABLE KEYS */;
INSERT INTO `equipment` VALUES (1,'ฟุตบอล',5,2),(2,'ฟุตซอล',4,4),(3,'บาสเกตบอล',4,3),(4,'วอลเลย์บอล',3,3),(5,'ตะกร้อ',3,0),(6,'ไม้แบดมินตัน',6,5),(7,'ไม้ปิงปอง',6,6),(8,'ชุดเปตอง',2,1);
/*!40000 ALTER TABLE `equipment` ENABLE KEYS */;
UNLOCK TABLES;
DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `students` (
  `student_id` varchar(13) NOT NULL,
  `first_name` varchar(50) NOT NULL,
  `last_name` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `phone` varchar(10) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES ('6512345678901','ธนกฤต','อินทร์แก้ว','thanakrit@example.com','0812345678','scrypt:32768:8:1$nCFjub1jsUzJxENT$0424462a5e8058bff7242fc30633a44062789e5122eba1b9d62de254e3bdaf2eb373d9d7dcf046ab03734f5507b2354331976178eb6d0ff29b759df3950e7329'),('6512345678902','พิมพ์ชนก','ศรีสุข','pimchanok@example.com','0898765432','scrypt:32768:8:1$8CoEbOr33Lm87d7e$c29652fe41eaf2ac7df146105ad58772a035e471a0f1a36b0dc766e9ea012aeb9cd4a82601d15126459a64914502ba69eb9ae7bc92f42eba0b7cda495d26b9ca'),('6512345678903','วีรภัทร','มั่นคง','weerapat@example.com','0861234567','scrypt:32768:8:1$Qp691mmVUAMtI5rD$c01b0461eaf7fc57afd8404ac3ac98f6ee401cd4698c79b5fd591eea230ec0d0934462f54d58da31c2fc5a52f0ecfc18f611403c3ad66cc096f3ddd3595e7635');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

