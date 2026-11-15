import streamlit as st
import pandas as pd
import re
import io
import pymysql
from datetime import date, timedelta

# ---- Backend: MySQL connection ----
DB = dict(host="localhost", user="root", password="YOUR_PASSWORD",
          database="space_tracker", cursorclass=pymysql.cursors.DictCursor)

def run(sql, params=None, write=False):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if write:
                conn.commit()
                return None
            return pd.DataFrame(cur.fetchall())
    finally:
        conn.close()

# ---- Frontend: blue and white space theme ----
st.set_page_config(page_title="Space Mission Tracker", page_icon="🛰️", layout="wide")
st.markdown("""<style>
.stApp{background:
 radial-gradient(1.5px 1.5px at 20px 30px,#fff,transparent),
 radial-gradient(1px 1px at 90px 80px,#cfe6ff,transparent),
 radial-gradient(1.5px 1.5px at 160px 20px,#fff,transparent),
 radial-gradient(1px 1px at 50px 140px,#9cc9ff,transparent),
 linear-gradient(180deg,#050F26 0%,#0A2150 60%,#0F3A7D 100%);
 background-size:200px 200px,200px 200px,200px 200px,200px 200px,100% 100%;
 background-attachment:fixed}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:rgba(5,15,38,.92);border-right:1px solid #1D4F9C}
.hero{position:relative;overflow:hidden;background:linear-gradient(120deg,#0E3C8A,#2E86F0 60%,#8CC8FF);
      padding:26px 30px;border-radius:18px;border:1px solid #6FB1FF;
      box-shadow:0 0 40px rgba(77,163,255,.35);margin-bottom:20px}
.hero:after{content:"";position:absolute;right:-60px;top:-60px;width:260px;height:260px;
      border:2px solid rgba(255,255,255,.35);border-radius:50%;
      box-shadow:0 0 0 30px rgba(255,255,255,.08),0 0 0 60px rgba(255,255,255,.05)}
.hero h1{color:#fff;margin:0;font-size:2rem}
.hero p{color:#DCEEFF;margin:6px 0 0}
[data-testid="stMetric"]{background:rgba(255,255,255,.96);border-radius:14px;
      padding:14px 18px;border-left:5px solid #4DA3FF}
[data-testid="stMetric"] *{color:#0B2545 !important}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{font-size:1.1rem;color:#9CC9FF}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.35rem}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:.45rem .7rem;border-radius:10px}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(77,163,255,.18)}
[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:1.15rem;font-weight:500}
</style>
<div class="hero"><h1>🛰️ Space Mission & Satellite Tracker</h1>
<p>Track satellites, launch vehicles and mission end dates</p></div>""", unsafe_allow_html=True)

try:
    run("SELECT 1")
except Exception as e:
    st.error(f"Cannot connect to MySQL. Check the password in app.py and run schema.sql first. ({e})")
    st.stop()


# ---- Plain English -> SQL (keyword rules, no AI key needed) ----
def nl_to_sql(q):
    t = q.lower()
    has = lambda *w: any(x in t for x in w)
    agencies = run("SELECT name FROM Agency")["name"].tolist()
    vehicles = run("SELECT name FROM LaunchVehicle")["name"].tolist()
    agency = next((a for a in agencies if re.search(rf"\b{re.escape(a.lower())}\b", t)), None)
    vehicle = next((v for v in vehicles if v.lower() in t), None)

    if has("end of life", "ending", "expire", "expiring", "running out", "retiring"):
        m = re.search(r"(\d+)\s*day", t)
        days = int(m.group(1)) if m else 90
        return ("SELECT s.name AS satellite, a.name AS agency, m.expected_end_date, "
                "DATEDIFF(m.expected_end_date, CURDATE()) AS days_remaining "
                "FROM Satellite s JOIN Agency a ON s.agency_id=a.agency_id "
                "JOIN Mission m ON s.satellite_id=m.satellite_id "
                "WHERE s.status='active' AND DATEDIFF(m.expected_end_date, CURDATE()) BETWEEN 0 AND %s "
                "ORDER BY days_remaining", (days,), f"Active satellites ending within {days} days")
    if has("most satellites"):
        return ("SELECT a.name AS agency, COUNT(*) AS total FROM Agency a "
                "JOIN Satellite s ON a.agency_id=s.agency_id GROUP BY a.name "
                "ORDER BY total DESC LIMIT 1", None, "Agency with the most satellites")
    if has("per agency", "each agency", "by agency", "agency wise", "agency-wise"):
        return ("SELECT a.name AS agency, COUNT(*) AS total FROM Agency a "
                "JOIN Satellite s ON a.agency_id=s.agency_id GROUP BY a.name ORDER BY total DESC",
                None, "Satellites per agency")
    if not vehicle and has("vehicle", "rocket"):
        return ("SELECT lv.name AS vehicle, COUNT(s.satellite_id) AS satellites "
                "FROM LaunchVehicle lv LEFT JOIN Satellite s ON lv.vehicle_id=s.vehicle_id "
                "GROUP BY lv.name ORDER BY satellites DESC", None, "Satellites per launch vehicle")
    if has("mission", "purpose"):
        sql = ("SELECT s.name AS satellite, m.purpose, m.start_date, m.expected_end_date, m.mission_status "
               "FROM Mission m JOIN Satellite s ON m.satellite_id=s.satellite_id "
               "JOIN Agency a ON s.agency_id=a.agency_id")
        if agency:
            return (sql + " WHERE a.name=%s", (agency,), f"Missions of {agency} satellites")
        return (sql, None, "All missions")

    cond, par, parts = [], [], []
    if agency:
        cond.append("a.name=%s"); par.append(agency); parts.append(f"agency {agency}")
    if vehicle:
        cond.append("lv.name=%s"); par.append(vehicle); parts.append(f"vehicle {vehicle}")
    om = re.search(r"\b(leo|meo|geo)\b", t)
    orbit = om.group(1).upper() if om else ("GEO" if "geostationary" in t else None)
    if orbit:
        cond.append("o.orbit_type=%s"); par.append(orbit); parts.append(f"orbit {orbit}")
    status = ("inactive" if has("inactive", "retired", "decommissioned") else
              "debris" if has("debris") else "active" if has("active") else None)
    if status:
        cond.append("s.status=%s"); par.append(status); parts.append(f"status {status}")
    rm = re.search(r"\b(?:from|between)\s+(\d{4})\s*(?:to|and|-)\s*(\d{4})", t)
    if rm:
        cond.append("YEAR(s.launch_date) BETWEEN %s AND %s")
        par += [int(rm.group(1)), int(rm.group(2))]
        parts.append(f"launch year {rm.group(1)} to {rm.group(2)}")
    ym = None if rm else re.search(r"\b(after|since|before|in)\s+(\d{4})", t)
    if ym:
        op = {"after": ">", "since": ">=", "before": "<", "in": "="}[ym.group(1)]
        cond.append(f"YEAR(s.launch_date){op}%s"); par.append(int(ym.group(2)))
        parts.append(f"launch year {op} {ym.group(2)}")
    if not cond and not has("satellite", "all", "list", "show", "every"):
        return None
    frm = ("FROM Satellite s JOIN Agency a ON s.agency_id=a.agency_id "
           "JOIN LaunchVehicle lv ON s.vehicle_id=lv.vehicle_id "
           "JOIN OrbitDetail o ON s.satellite_id=o.satellite_id")
    where = (" WHERE " + " AND ".join(cond)) if cond else ""
    why = "Filters: " + ", ".join(parts) if parts else "All satellites"
    if has("how many", "count", "number of", "total"):
        return ("SELECT COUNT(*) AS total_satellites " + frm + where, tuple(par) or None, why)
    return ("SELECT s.name AS satellite, a.name AS agency, lv.name AS vehicle, o.orbit_type, "
            "s.launch_date, s.status " + frm + where + " ORDER BY s.launch_date",
            tuple(par) or None, why)

# ---- Ask page helpers: read-only SQL check + saved history ----
BLOCKED = r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|replace|rename|call|set|load|outfile)\b"

def check_sql(text):
    s = text.strip().rstrip(";").strip()
    if not s:
        return None, "Type a query first."
    if ";" in s:
        return None, "Run one statement at a time."
    if not re.match(r"(?is)(select|show|describe|desc|with)\b", s):
        return None, "Only SELECT queries are allowed here."
    if re.search(BLOCKED, s, re.I):
        return None, "This page is read-only, so commands that change data are blocked."
    return s, None

def ensure_history():
    run("""CREATE TABLE IF NOT EXISTS QueryHistory (
             history_id INT PRIMARY KEY AUTO_INCREMENT,
             asked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
             mode VARCHAR(20), question TEXT, sql_text TEXT,
             row_count INT, result_json LONGTEXT)""", write=True)

def save_history(mode, question, sql_text, df):
    run("INSERT INTO QueryHistory (mode, question, sql_text, row_count, result_json) "
        "VALUES (%s,%s,%s,%s,%s)",
        (mode, question, sql_text, len(df),
         df.head(200).to_json(orient="split", date_format="iso", default_handler=str)), write=True)

page = st.sidebar.radio("Go to", ["Dashboard", "Satellite Registry", "End-of-Life Alerts",
                                  "Vehicle Utilization", "Ask", "Trigger Demo"])

if page == "Dashboard":
    sat = run("SELECT status, COUNT(*) AS n FROM Satellite GROUP BY status").set_index("status")["n"]
    eol = run("SELECT COUNT(*) AS n FROM end_of_life_dashboard")["n"][0]
    c = st.columns(4)
    c[0].metric("Total satellites", int(sat.sum()))
    c[1].metric("Active", int(sat.get("active", 0)))
    c[2].metric("Inactive / debris", int(sat.sum() - sat.get("active", 0)))
    c[3].metric("Ending in 90 days", int(eol))
    st.subheader("Orbit details")
    st.dataframe(run("""SELECT s.name AS satellite, o.altitude_km, o.orbit_type
                        FROM Satellite s JOIN OrbitDetail o ON s.satellite_id=o.satellite_id"""),
                 width="stretch", hide_index=True)

elif page == "Satellite Registry":
    agencies = ["All"] + run("SELECT name FROM Agency")["name"].tolist()
    pick = st.selectbox("Agency", agencies)
    sql = """SELECT s.satellite_id, s.name, a.name AS agency, lv.name AS vehicle,
                    s.launch_date, s.status
             FROM Satellite s JOIN Agency a ON s.agency_id=a.agency_id
             JOIN LaunchVehicle lv ON s.vehicle_id=lv.vehicle_id"""
    df = run(sql + (" WHERE a.name=%s" if pick != "All" else ""), (pick,) if pick != "All" else None)
    st.dataframe(df, width="stretch", hide_index=True)

elif page == "End-of-Life Alerts":
    st.subheader("Active satellites whose mission ends within 90 days")
    df = run("SELECT satellite, agency, expected_end_date, days_remaining "
             "FROM end_of_life_dashboard ORDER BY days_remaining")
    if df.empty:
        st.info("No satellites are close to end of life.")
    else:
        red = lambda r: ["background-color:#8B1E2D;color:#fff" if r["days_remaining"] < 30 else ""] * len(r)
        st.dataframe(df.style.apply(red, axis=1), width="stretch", hide_index=True)
        st.caption("Red rows have fewer than 30 days left.")

elif page == "Vehicle Utilization":
    df = run("""SELECT lv.name AS vehicle, COUNT(s.satellite_id) AS satellites
                FROM LaunchVehicle lv LEFT JOIN Satellite s ON lv.vehicle_id=s.vehicle_id
                GROUP BY lv.name ORDER BY satellites DESC""")
    st.bar_chart(df.set_index("vehicle"), color="#4DA3FF")
    st.dataframe(df, width="stretch", hide_index=True)

elif page == "Ask":
    ensure_history()
    st.subheader("Ask the database")
    mode = st.radio("How do you want to ask?", ["Plain English", "SQL Query"], horizontal=True)
    with st.form("ask_form"):
        if mode == "Plain English":
            text = st.text_input("Type your question", placeholder="satellites launched by ISRO after 2019")
        else:
            text = st.text_area("Type your SQL query (SELECT only)", height=120,
                                placeholder="SELECT name, launch_date FROM Satellite WHERE launch_date > '2020-01-01'")
        go = st.form_submit_button("Run")
    if mode == "Plain English":
        st.caption("Try: how many active satellites in LEO, which satellites end in 60 days, "
                   "missions of ESA, inactive satellites, satellites launched by Falcon 9")
    if go and text.strip():
        sql, params, why, err = None, None, None, None
        if mode == "Plain English":
            res = nl_to_sql(text)
            if res is None:
                err = ("I did not understand that. Use words like satellites, an agency (ISRO, NASA, ESA), "
                       "LEO or GEO, active or inactive, a year, missions or launch vehicle.")
            else:
                sql, params, why = res
        else:
            sql, err = check_sql(text)
        if err:
            st.warning(err)
        else:
            try:
                out = run(sql, params)
            except Exception as e:
                st.error(f"MySQL could not run this query: {e}")
            else:
                shown = sql + (f"\n-- values: {params}" if params else "")
                if why:
                    st.info(why)
                st.code(shown, language="sql")
                if out.empty:
                    st.info("No matching records.")
                else:
                    st.dataframe(out, width="stretch", hide_index=True)
                save_history(mode, text.strip(), shown, out)

    st.divider()
    st.subheader("History")
    h = run("SELECT history_id, asked_at, mode, question, sql_text, row_count, result_json "
            "FROM QueryHistory ORDER BY history_id DESC LIMIT 30")
    if h.empty:
        st.caption("Your questions and their answers will appear here.")
    else:
        if st.button("Clear history"):
            run("DELETE FROM QueryHistory", write=True)
            st.rerun()
        for r in h.itertuples():
            when = pd.to_datetime(r.asked_at).strftime("%d %b, %I:%M %p")
            with st.expander(f"{when} | {r.mode} | {r.question[:80]}"):
                st.code(r.sql_text, language="sql")
                st.caption(f"{r.row_count} row(s)")
                data = pd.read_json(io.StringIO(r.result_json), orient="split", convert_dates=False)
                if data.empty:
                    st.info("No matching records.")
                else:
                    st.dataframe(data, width="stretch", hide_index=True)

else:
    st.subheader("Change a mission end date and watch the trigger fire")
    m = run("""SELECT m.mission_id, s.name FROM Mission m
               JOIN Satellite s ON m.satellite_id=s.satellite_id""")
    name = st.selectbox("Mission (satellite)", m["name"])
    mid = int(m[m["name"] == name]["mission_id"].iloc[0])
    new = st.date_input("New expected end date", date.today() - timedelta(days=1))
    if st.button("Update mission"):
        run("UPDATE Mission SET expected_end_date=%s WHERE mission_id=%s", (new, mid), write=True)
        st.success("Mission updated. The trigger checked the date and updated the satellite status.")
    st.dataframe(run("SELECT name, status FROM Satellite WHERE name=%s", (name,)),
                 width="stretch", hide_index=True)
    st.caption("To reset the demo, re-run schema.sql.")
