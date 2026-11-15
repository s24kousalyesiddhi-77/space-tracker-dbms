# Space Mission & Satellite Tracking System

## Run it
1. Install MySQL 8 and MySQL Workbench.
2. In Workbench: File > Open SQL Script > `schema.sql` > run all (lightning icon).
3. Then open `queries.sql` and run each query one at a time (screenshots for your report).
4. Install Python 3.9+ then: `pip install -r requirements.txt`
5. Open `app.py` and set your MySQL password in the `DB` line.
6. Run: `streamlit run app.py` (opens in your browser).

## Files
- schema.sql: tables, sample data, view, triggers
- queries.sql: 9 queries incl. joins, subquery, trigger demo
- app.py: Streamlit frontend + MySQL backend
- er_diagram.mermaid: ER diagram (paste at mermaid.live to export PNG)

## Viva one-liner
A satellite is launched by a vehicle, owned by an agency, sits in an orbit and runs missions.
When a mission's end date passes, a trigger marks the satellite inactive.
