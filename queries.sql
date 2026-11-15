USE space_tracker;

-- 1. Satellite registry (3-table JOIN)
SELECT s.satellite_id, s.name, a.name AS agency, lv.name AS vehicle, s.launch_date, s.status
FROM Satellite s JOIN Agency a ON s.agency_id = a.agency_id
JOIN LaunchVehicle lv ON s.vehicle_id = lv.vehicle_id;

-- 2. Orbit details
SELECT s.name, o.altitude_km, o.orbit_type
FROM Satellite s JOIN OrbitDetail o ON s.satellite_id = o.satellite_id;

-- 3. Vehicle utilization (LEFT JOIN keeps vehicles with 0 satellites)
SELECT lv.name AS vehicle, COUNT(s.satellite_id) AS satellites_launched
FROM LaunchVehicle lv LEFT JOIN Satellite s ON lv.vehicle_id = s.vehicle_id
GROUP BY lv.name ORDER BY satellites_launched DESC;

-- 4. End-of-life dashboard (uses the view)
SELECT * FROM end_of_life_dashboard ORDER BY days_remaining;

-- 5. Satellites per agency
SELECT a.name, COUNT(*) AS total FROM Agency a
JOIN Satellite s ON a.agency_id = s.agency_id GROUP BY a.name;

-- 6. Agency with the most satellites (subquery)
SELECT name FROM Agency WHERE agency_id =
 (SELECT agency_id FROM Satellite GROUP BY agency_id ORDER BY COUNT(*) DESC LIMIT 1);

-- 7. Active satellites in GEO
SELECT s.name FROM Satellite s JOIN OrbitDetail o ON s.satellite_id = o.satellite_id
WHERE o.orbit_type = 'GEO' AND s.status = 'active';

-- 8. Satellites launched after 2019
SELECT name, launch_date FROM Satellite WHERE launch_date > '2019-12-31';

-- 9. TRIGGER DEMO: before -> update -> after
SELECT name, status FROM Satellite WHERE satellite_id = 192;
UPDATE Mission SET expected_end_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY) WHERE mission_id = 192;
SELECT name, status FROM Satellite WHERE satellite_id = 192;   -- now 'inactive'
