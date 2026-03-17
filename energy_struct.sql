-- MySQL dump 10.13  Distrib 8.0.39, for Win64 (x86_64)
--
-- Host: localhost    Database: energy_management
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `energy_consumption_new`
--

DROP TABLE IF EXISTS `energy_consumption_new`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `energy_consumption_new` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `building_id` varchar(100) NOT NULL COMMENT '建筑ID',
  `meter_id` varchar(100) NOT NULL COMMENT '设备ID',
  `timestamp` datetime NOT NULL COMMENT '时间戳',
  `hour` varchar(10) DEFAULT NULL COMMENT '小时 (如: 1:00:00)',
  `building_type` varchar(50) DEFAULT NULL COMMENT '建筑类型',
  `electricity` float DEFAULT NULL COMMENT '电力消耗 (kW)',
  `cooling_load` float DEFAULT NULL COMMENT '冷冻水冷量',
  `heating_load` float DEFAULT NULL COMMENT '供热能耗',
  `ambient_temp` float DEFAULT NULL COMMENT '气温 (℃)',
  `pressure` float DEFAULT NULL COMMENT '海平面气压 (hPa)',
  `is_anomaly` tinyint(1) DEFAULT '0' COMMENT '是否异常',
  `run_status` varchar(20) DEFAULT NULL COMMENT '运行状态: 正常/异常',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `meter_id` (`meter_id`),
  KEY `idx_building_time` (`building_id`,`timestamp`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_anomaly` (`is_anomaly`),
  KEY `idx_building_type` (`building_type`)
) ENGINE=InnoDB AUTO_INCREMENT=14951 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='能耗数据表（真实数据版）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-16 21:36:00
