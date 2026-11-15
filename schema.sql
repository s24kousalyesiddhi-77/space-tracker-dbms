-- Space Mission & Satellite Tracking System (MySQL 8)
DROP DATABASE IF EXISTS space_tracker;
CREATE DATABASE space_tracker;
USE space_tracker;

CREATE TABLE Agency (
  agency_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL UNIQUE,
  country VARCHAR(50) NOT NULL
);
CREATE TABLE LaunchVehicle (
  vehicle_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  agency_id INT NOT NULL,
  capacity_kg INT CHECK (capacity_kg > 0),
  FOREIGN KEY (agency_id) REFERENCES Agency(agency_id)
);
CREATE TABLE Satellite (
  satellite_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(60) NOT NULL,
  agency_id INT NOT NULL,
  vehicle_id INT NOT NULL,
  launch_date DATE NOT NULL,
  status ENUM('active','inactive','debris') NOT NULL DEFAULT 'active',
  FOREIGN KEY (agency_id) REFERENCES Agency(agency_id),
  FOREIGN KEY (vehicle_id) REFERENCES LaunchVehicle(vehicle_id)
);
CREATE TABLE OrbitDetail (
  orbit_id INT PRIMARY KEY AUTO_INCREMENT,
  satellite_id INT NOT NULL UNIQUE,
  altitude_km INT NOT NULL,
  orbit_type ENUM('LEO','MEO','GEO') NOT NULL,
  FOREIGN KEY (satellite_id) REFERENCES Satellite(satellite_id)
);
CREATE TABLE Mission (
  mission_id INT PRIMARY KEY AUTO_INCREMENT,
  satellite_id INT NOT NULL,
  purpose VARCHAR(100) NOT NULL,
  start_date DATE NOT NULL,
  expected_end_date DATE NOT NULL,
  mission_status ENUM('planned','ongoing','completed') NOT NULL DEFAULT 'ongoing',
  FOREIGN KEY (satellite_id) REFERENCES Satellite(satellite_id),
  CHECK (expected_end_date > start_date)
);

-- ---------- Sample data ----------
INSERT INTO Agency (name, country) VALUES
('ISRO','India'),('NASA','USA'),('ESA','Europe'),('JAXA','Japan'),('SpaceX','USA');

INSERT INTO LaunchVehicle (name, agency_id, capacity_kg) VALUES
('PSLV',1,3800),('GSLV Mk III',1,8000),('Falcon 9',5,22800),
('Ariane 5',3,21000),('H-IIA',4,10000),('Vega',3,1500);

INSERT INTO Satellite (name, agency_id, vehicle_id, launch_date, status) VALUES
('RISAT-2B',1,1,'2019-05-22','active'),
('Cartosat-3',1,1,'2019-11-27','active'),
('GSAT-30',1,4,'2020-01-17','active'),
('Oceansat-3',1,1,'2022-11-26','active'),
('Sentinel-2A',3,6,'2015-06-23','active'),
('Aeolus',3,6,'2018-08-22','inactive'),
('Sentinel-6',3,3,'2020-11-21','active'),
('SWOT',2,3,'2022-12-16','active'),
('GOSAT',4,5,'2009-01-23','active');

INSERT INTO OrbitDetail (satellite_id, altitude_km, orbit_type) VALUES
(1,556,'LEO'),(2,509,'LEO'),(3,35786,'GEO'),(4,742,'LEO'),(5,786,'LEO'),
(6,320,'LEO'),(7,1336,'LEO'),(8,890,'LEO'),(9,666,'LEO');

-- End dates are relative to today so the end-of-life demo always shows rows
INSERT INTO Mission (satellite_id, purpose, start_date, expected_end_date, mission_status) VALUES
(1,'Radar earth observation','2019-05-22',DATE_ADD(CURDATE(),INTERVAL 40 DAY),'ongoing'),
(2,'High-resolution mapping','2019-11-27',DATE_ADD(CURDATE(),INTERVAL 75 DAY),'ongoing'),
(3,'Communication (DTH, VSAT)','2020-01-17',DATE_ADD(CURDATE(),INTERVAL 1500 DAY),'ongoing'),
(4,'Ocean and weather study','2022-11-26',DATE_ADD(CURDATE(),INTERVAL 900 DAY),'ongoing'),
(5,'Land and vegetation imaging','2015-06-23',DATE_ADD(CURDATE(),INTERVAL 20 DAY),'ongoing'),
(6,'Global wind measurement','2018-08-22','2023-07-28','completed'),
(7,'Sea-level monitoring','2020-11-21',DATE_ADD(CURDATE(),INTERVAL 700 DAY),'ongoing'),
(8,'Surface water survey','2022-12-16',DATE_ADD(CURDATE(),INTERVAL 500 DAY),'ongoing'),
(9,'Greenhouse gas observation','2009-01-23',DATE_ADD(CURDATE(),INTERVAL 10 DAY),'ongoing');

-- ---------- View ----------
CREATE VIEW end_of_life_dashboard AS
SELECT s.satellite_id, s.name AS satellite, a.name AS agency, m.expected_end_date,
       DATEDIFF(m.expected_end_date, CURDATE()) AS days_remaining
FROM Satellite s
JOIN Agency a  ON s.agency_id = a.agency_id
JOIN Mission m ON s.satellite_id = m.satellite_id
WHERE s.status = 'active'
  AND DATEDIFF(m.expected_end_date, CURDATE()) BETWEEN 0 AND 90;

-- ---------- Triggers (satellite becomes inactive when mission end date is past) ----------
DELIMITER //
CREATE TRIGGER mission_update_check
AFTER UPDATE ON Mission
FOR EACH ROW
BEGIN
  IF NEW.expected_end_date < CURDATE() THEN
    UPDATE Satellite SET status = 'inactive' WHERE satellite_id = NEW.satellite_id;
  END IF;
END//

CREATE TRIGGER mission_insert_check
AFTER INSERT ON Mission
FOR EACH ROW
BEGIN
  IF NEW.expected_end_date < CURDATE() THEN
    UPDATE Satellite SET status = 'inactive' WHERE satellite_id = NEW.satellite_id;
  END IF;
END//
DELIMITER ;
