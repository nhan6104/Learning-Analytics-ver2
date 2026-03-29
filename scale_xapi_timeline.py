# -*- coding: utf-8 -*-
"""
scale_xapi_timeline.py  (v3 - Realistic Session Simulation)
============================================================
Doc sample_data.json (366 statements, tat ca cung ngay 21/03),
dua tren cau truc section trong .mbz de biet moi activity thuoc tuan nao,
sau do:
  1. Scale timestamps: moi topic -> dung tuan trong ky
  2. Them Login/Logout bao quanh moi phien hoc
  3. Tao 2 profile: Skimming (B - actor 5) va Steady (A - actor 4)

Output:
  skimming_scaled.json  - Hoc sinh B: don vao Toi Chu Nhat
  steady_scaled.json    - Hoc sinh A: rai deu T2/T4/T6 sang som
"""

import json
import uuid
import copy
import re
import xml.etree.ElementTree as ET
import os
from datetime import datetime, timedelta, timezone

# ===========================================================
# CAU HINH
# ===========================================================
INPUT_FILE    = r"C:\Users\tnpht\Desktop\Learning-Analytics-ver2\sample_data.json"
BACKUP_PATH   = r"C:\Users\tnpht\Downloads\backup-course-16-20260321-0527"
OUTPUT_SKIM   = r"C:\Users\tnpht\Desktop\Learning-Analytics-ver2\skimming_scaled.json"
OUTPUT_STEADY = r"C:\Users\tnpht\Desktop\Learning-Analytics-ver2\steady_scaled.json"

# Thu 2 dau tien cua hoc ky (tuan 1)
SEMESTER_START = datetime(2026, 3, 3, 0, 0, 0, tzinfo=timezone.utc)

MOODLE_BASE    = "http://171.246.190.1:82"

# Actor info tu bang mdl_user
SKIMMING_ACTOR = {"id": "5", "name": "Phat Ho Tan"}  # Hoc sinh B
STEADY_ACTOR   = {"id": "4", "name": "Thanh Nhan"}   # Hoc sinh A

# Verb IDs chuan xAPI (lay tu log thuc te)
VERB_LOGIN  = "https://xapi.edlm/profiles/edlm-lms/concepts/verbs/login"
VERB_LOGOUT = "https://xapi.edlm/profiles/edlm-lms/concepts/verbs/logout"


# ===========================================================
# BUOC 1: Doc week map tu .mbz
# ===========================================================
def build_week_map(backup_path):
    """
    Tra ve:
      week_map  = { "activity_id": week_number }
      week_info = { week_number: { "name": "...", "acts": [...] } }
    """
    week_map  = {}
    week_info = {}
    sections_path = os.path.join(backup_path, "sections")

    for section_dir in sorted(os.listdir(sections_path)):
        xml_file = os.path.join(sections_path, section_dir, "section.xml")
        if not os.path.exists(xml_file):
            continue
        tree = ET.parse(xml_file)
        root = tree.getroot()

        number_tag   = root.find("number")
        name_tag     = root.find("name")
        sequence_tag = root.find("sequence")

        if number_tag is None or sequence_tag is None or not sequence_tag.text:
            continue

        wn        = int(number_tag.text)
        wname     = name_tag.text if name_tag is not None else f"Topic {wn}"
        act_ids   = [a.strip() for a in sequence_tag.text.split(",") if a.strip()]

        week_info[wn] = {"name": wname, "acts": act_ids}
        for aid in act_ids:
            week_map[aid] = wn

    return week_map, week_info


# ===========================================================
# BUOC 2: Trich xuat activity ID tu xAPI object URL
# ===========================================================
def extract_act_id(statement):
    """
    Lay activity ID tu URL object hoac context parent.
    Vi du: .../view.php?id=418  ->  "418"
           .../section.php?id=126  ->  "126" (fallback)
    """
    obj_url = statement.get("object", {}).get("id", "")
    m = re.search(r"[?&](?:id|cmid)=(\d+)", obj_url)
    if m:
        return m.group(1)

    # Fallback: lay tu context parent dau tien
    try:
        parents = statement["context"]["contextActivities"]["parent"]
        for p in parents:
            pid = p.get("id", "")
            m2 = re.search(r"section\.php\?id=(\d+)", pid)
            if m2:
                return "section_" + m2.group(1)
    except (KeyError, TypeError):
        pass

    return None


# ===========================================================
# BUOC 3: Tinh timestamp theo tuan + profile + thu tu
# ===========================================================
def week_monday(wn):
    """Tra ve Thu 2 dau tuan thu wn (wn=0 -> intro, wn=1 -> tuan 1)"""
    offset = max(wn - 1, 0)
    return SEMESTER_START + timedelta(weeks=offset)


def compute_ts(wn, session_idx, stmt_idx_in_session, profile):
    """
    profile='skimming':
      - Moi tuan co 1 phien duy nhat vao Toi Chu Nhat (CN = Thu 2 + 6 ngay)
      - Bat dau tu 21:30 UTC (= 04:30 SA mon Viet Nam hom sau, nhung hien thi la 21:30 CN)
      - Moi statement cach nhau 1-3 phut (doc nhanh)

    profile='steady':
      - Moi tuan co nhieu phien tren cac buoi T2/T4/T6
      - Bat dau tu 01:30 UTC (= 08:30 sang VN)
      - Moi statement cach nhau 5-10 phut (doc sau)
    """
    mon = week_monday(wn)

    if profile == "skimming":
        sunday_start = mon + timedelta(days=6, hours=21, minutes=30)
        # tat ca statements trong 1 phien, cach 2 phut
        return sunday_start + timedelta(minutes=stmt_idx_in_session * 2)
    else:
        # Chia phien ra cac ngay T2(0), T4(2), T6(4) trong tuan
        day_slots  = [0, 2, 4]
        day_offset = day_slots[session_idx % 3]
        # Bat dau 01:30 UTC = 08:30 VN
        session_start = mon + timedelta(days=day_offset, hours=1, minutes=30)
        # Moi statement cach 8 phut (doc ky 45p)
        return session_start + timedelta(minutes=stmt_idx_in_session * 8)


# ===========================================================
# BUOC 4: Tao Login/Logout event
# ===========================================================
def make_login_event(actor_info, ts, registration):
    return {
        "id": str(uuid.uuid4()),
        "actor": {
            "objectType": "Agent",
            "name": actor_info["name"],
            "account": {
                "name": actor_info["id"],
                "homePage": MOODLE_BASE
            }
        },
        "verb": {
            "id": VERB_LOGIN,
            "display": {"en": "Logged In"}
        },
        "object": {
            "id": MOODLE_BASE,
            "definition": {
                "name": {"en": "MDL_Moodle"},
                "type": "http://id.tincanapi.com/activitytype/lms"
            },
            "objectType": "Activity"
        },
        "context": {
            "extensions": {
                "http://lrs.learninglocker.net/define/extensions/info": {
                    "http://moodle.org": "4.4.11+ (Build: 20251121)",
                    "https://github.com/xAPI-vle/moodle-logstore_xapi": "",
                    "event_name": "\\core\\event\\user_loggedin",
                    "event_function": "\\src\\transformer\\events\\core\\user_loggedin"
                }
            },
            "registration": registration,
            "language": "en",
            "platform": "Moodle"
        },
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "stored":    ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "authority": {
            "objectType": "Agent",
            "account": {
                "homePage": "http://cloud.scorm.com",
                "name": "IV2M3KSGCL"
            }
        },
        "version": "1.0.0"
    }


def make_logout_event(actor_info, ts, registration):
    evt = make_login_event(actor_info, ts, registration)
    evt["id"]   = str(uuid.uuid4())
    evt["verb"] = {
        "id": VERB_LOGOUT,
        "display": {"en": "Logged Out"}
    }
    evt["context"]["extensions"][
        "http://lrs.learninglocker.net/define/extensions/info"
    ]["event_name"]     = "\\core\\event\\user_loggedout"
    evt["context"]["extensions"][
        "http://lrs.learninglocker.net/define/extensions/info"
    ]["event_function"] = "\\src\\transformer\\events\\core\\user_loggedout"
    return evt


# ===========================================================
# BUOC 5: Scale toan bo statements
# ===========================================================
def scale_statements(statements, week_map, week_info, profile, actor_info):
    """
    Nhom statements theo week -> theo session ->
    chen Login truoc, Logout sau, scale timestamp.
    """

    # --- 5a. Phan nhom theo tuan ---
    grouped = {}   # week_num -> [statements]
    for s in statements:
        aid = extract_act_id(s)
        wn  = week_map.get(aid, 0) if aid else 0
        grouped.setdefault(wn, []).append(s)

    result = []

    # --- 5b. Xu ly tung tuan ---
    for wn in sorted(grouped.keys()):
        week_stmts = grouped[wn]
        week_name  = week_info.get(wn, {}).get("name", f"Topic {wn}")

        if profile == "skimming":
            # --- Skimming: 1 phien duy nhat Chu Nhat ---
            sessions = [week_stmts]      # 1 phien = tat ca
        else:
            # --- Steady: chia thanh 3 phien T2/T4/T6 ---
            n = len(week_stmts)
            chunk = max(1, n // 3)
            sessions = [
                week_stmts[0:chunk],
                week_stmts[chunk:chunk*2],
                week_stmts[chunk*2:]
            ]
            sessions = [p for p in sessions if p]  # bo phan rong

        for sess_idx, session in enumerate(sessions):
            if not session:
                continue

            # TAO REGISTRATION MOI CHO MOI SESSION (Rat quan trong de ETL khong bi trung attempt_id)
            reg = str(uuid.uuid4())

            # === LOGIN ===
            login_ts = compute_ts(wn, sess_idx, -1, profile)  # 1 phut truoc stmt dau
            if profile == "skimming":
                # login ngay truoc luot dau
                login_ts = compute_ts(wn, sess_idx, 0, profile) - timedelta(minutes=1)
            else:
                login_ts = compute_ts(wn, sess_idx, 0, profile) - timedelta(minutes=2)
            result.append(make_login_event(actor_info, login_ts, reg))

            # === STATEMENTS cua phien ===
            for stmt_idx, s in enumerate(session):
                ns = copy.deepcopy(s)

                # 1. Doi actor
                ns["id"] = str(uuid.uuid4())
                ns["actor"]["account"]["name"] = actor_info["id"]
                ns["actor"]["name"]            = actor_info["name"]

                # 2. XOA BO attempt=XX khoi tat ca URL de ETL tu gen UUID moi (Tranh loi khoa ngoai)
                def scrub_url(url):
                    if not isinstance(url, str): return url
                    return re.sub(r'([?&])attempt=\d+(&?)', r'\1', url).replace("?&", "?").rstrip("?").rstrip("&")

                if "object" in ns and "id" in ns["object"]:
                    ns["object"]["id"] = scrub_url(ns["object"]["id"])

                if "context" in ns and "contextActivities" in ns["context"]:
                    ca = ns["context"]["contextActivities"]
                    for cat in ["parent", "grouping", "category", "other"]:
                        if cat in ca:
                            for act in ca[cat]:
                                if "id" in act:
                                    act["id"] = scrub_url(act["id"])

                # 3. Gan registration moi
                if "context" not in ns: ns["context"] = {}
                ns["context"]["registration"] = reg

                # 4. Scale timestamp
                new_ts = compute_ts(wn, sess_idx, stmt_idx, profile)
                ns["timestamp"] = new_ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                ns["stored"]    = new_ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")

                # Steady: them duration
                if profile == "steady":
                    if "result" not in ns:
                        ns["result"] = {}
                    ns["result"]["duration"] = "PT45M"

                result.append(ns)

            # === LOGOUT ===
            last_ts  = compute_ts(wn, sess_idx, len(session) - 1, profile)
            logout_ts = last_ts + timedelta(minutes=3)
            result.append(make_logout_event(actor_info, logout_ts, reg))

    # Sap xep theo thoi gian tang dan (giong log thuc te)
    result.sort(key=lambda s: s["timestamp"])

    # Loai bo duplicate Login/Logout (cung actor + verb + timestamp)
    seen = set()
    deduped = []
    for s in result:
        key = (s["actor"]["account"]["name"], s["verb"]["id"], s["timestamp"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    return deduped


# ===========================================================
# MAIN
# ===========================================================
def main():
    print("=" * 62)
    print("  xAPI Timeline Scaler v3 - CS240 (13 weeks + Login/Logout)")
    print("=" * 62)

    # 1. Doc file goc
    print(f"\n[1] Reading input: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        statements = json.load(f)
    print(f"    -> {len(statements)} statements loaded")

    # Thong ke verbs goc
    verb_counts = {}
    for s in statements:
        v = s["verb"]["display"]["en"]
        verb_counts[v] = verb_counts.get(v, 0) + 1
    for v, c in sorted(verb_counts.items(), key=lambda x: -x[1]):
        print(f"       {c:4d}x {v}")

    # 2. Xay dung week map
    print(f"\n[2] Building week map from .mbz...")
    week_map, week_info = build_week_map(BACKUP_PATH)
    print(f"    -> {len(week_map)} activities mapped across {len(week_info)} sections:")
    for wn in sorted(week_info.keys()):
        label = "Intro" if wn == 0 else f"Week {wn:2d}"
        print(f"       {label}: {week_info[wn]['name'][:55]}")

    # 3. Hoc sinh B (Skimming)
    print(f"\n[3] Scaling SKIMMING (actor={SKIMMING_ACTOR['id']} - {SKIMMING_ACTOR['name']})...")
    skim = scale_statements(statements, week_map, week_info, "skimming", SKIMMING_ACTOR)
    with open(OUTPUT_SKIM, "w", encoding="utf-8") as f:
        json.dump(skim, f, indent=2, ensure_ascii=False)
    login_count  = sum(1 for s in skim if "Logged In"  in s["verb"]["display"]["en"])
    logout_count = sum(1 for s in skim if "Logged Out" in s["verb"]["display"]["en"])
    print(f"    -> {len(skim)} total statements saved ({login_count} logins, {logout_count} logouts)")
    print(f"    Preview (first 4):")
    for s in skim[:4]:
        print(f"      [{s['timestamp']}] {s['verb']['display']['en']:12s} -> {s['object']['definition']['name'].get('en','?')[:35]}")

    # 4. Hoc sinh A (Steady)
    print(f"\n[4] Scaling STEADY (actor={STEADY_ACTOR['id']} - {STEADY_ACTOR['name']})...")
    steady = scale_statements(statements, week_map, week_info, "steady", STEADY_ACTOR)
    with open(OUTPUT_STEADY, "w", encoding="utf-8") as f:
        json.dump(steady, f, indent=2, ensure_ascii=False)
    login_count  = sum(1 for s in steady if "Logged In"  in s["verb"]["display"]["en"])
    logout_count = sum(1 for s in steady if "Logged Out" in s["verb"]["display"]["en"])
    print(f"    -> {len(steady)} total statements saved ({login_count} logins, {logout_count} logouts)")
    print(f"    Preview (first 4):")
    for s in steady[:4]:
        dur = s.get("result", {}).get("duration", "")
        print(f"      [{s['timestamp']}] {s['verb']['display']['en']:12s} -> {s['object']['definition']['name'].get('en','?')[:30]} {dur}")

    # 5. Tom tat timeline
    print(f"\n[5] Timeline summary:")
    print(f"    SKIMMING: {skim[0]['timestamp'][:10]}  ->  {skim[-1]['timestamp'][:10]}")
    print(f"    STEADY  : {steady[0]['timestamp'][:10]}  ->  {steady[-1]['timestamp'][:10]}")

    print("\n" + "=" * 62)
    print("  DONE!")
    print(f"  B (Skimming) -> {OUTPUT_SKIM}")
    print(f"  A (Steady)   -> {OUTPUT_STEADY}")
    print("=" * 62)


if __name__ == "__main__":
    main()
