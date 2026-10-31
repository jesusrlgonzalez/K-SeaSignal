-- Reference only: populated by src/i28/core.py
-- Do not interpret alerts as misconduct.
SELECT status, COUNT(*) AS n FROM ais_decisions GROUP BY status;
SELECT mmsi,status,COUNT(*) AS n FROM ais_decisions GROUP BY mmsi,status;
