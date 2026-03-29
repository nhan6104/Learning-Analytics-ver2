import random
from datetime import datetime, timedelta
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("PGSQL_HOST"),
        port=os.getenv("PGSQL_PORT"),
        dbname="test",
        user=os.getenv("PGSQL_USER"),
        password=os.getenv("PGSQL_PASSWORD"),
        sslmode=os.getenv("PGSQL_SSL_MODE", "prefer"),
        sslrootcert=os.getenv("PGSQL_SSL_ROOT_CERT")
    )

def seed_data():
    print("🚀 Bắt đầu seed dữ liệu mock datamart...")
    try:
        conn = get_connection()
        conn.autocommit = True
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return

    schema_name = "datamart"
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

    # -------------------------------------------------------------------------
    # Schema definitions — khớp với loader đã fix
    # Fixes:
    #   - fact_daily_student_engagement: bỏ active_learning_index (loader không insert)
    #   - fact_student_engagement_depth: course_key VARCHAR (loader CAST AS VARCHAR)
    #   - fact_class_engagement_distribution: có excellent/good/warning/critical_student_count
    #   - fact_student_deadline_proximity: có hours_before_deadline và is_completed
    # -------------------------------------------------------------------------
    tables = {
        "dim_actor":
            "actor_id VARCHAR(255) PRIMARY KEY, "
            "actor_name VARCHAR(255)",

        "dim_course":
            "course_key VARCHAR(255) PRIMARY KEY, "
            "course_name VARCHAR(255), course_level VARCHAR(255), total_modules INT",

        "dim_resource":
            "resource_key VARCHAR(255) PRIMARY KEY, "
            "resource_name VARCHAR(255), resource_type VARCHAR(255), "
            "section_key VARCHAR(255), course_key VARCHAR(255)",

        "dim_section":
            "section_key VARCHAR(255) PRIMARY KEY, "
            "section_name VARCHAR(255), section_number INT, course_key VARCHAR(255)",

        "dim_time":
            "time_id VARCHAR(255) PRIMARY KEY, "
            "date INT, month INT, year INT, week INT, day_of_week VARCHAR(255), time_slot VARCHAR(255)",

        "fact_daily_student_engagement":
            "student_key VARCHAR(255), course_key INT, date_key VARCHAR(255), "
            "total_resource_access INT, total_quiz_attempt INT, "
            "total_active_minutes INT, engagement_score INT",

        "fact_risk_student_weekly":
            "student_key VARCHAR(255), course_key INT, week_of_year INT, year INT, "
            "engagement_score INT, progress_score INT, outcome_score INT, "
            "risk_score INT, dropout_probability_pct DECIMAL(5,2), risk_level VARCHAR(255)",

        "fact_class_engagement_distribution":
            "course_key VARCHAR(255), week_of_year INT, year INT, "
            "avg_engagement_score DECIMAL(5,2), p25_engagement INT, p50_engagement INT, p75_engagement INT, "
            "excellent_student_count INT, good_student_count INT, warning_student_count INT, critical_student_count INT, "
            "medium_engagement_count INT, low_engagement_count INT, "
            "active_student_count INT, passive_student_count INT",

        "fact_student_course_lifecycle":
            "student_key VARCHAR(255), course_key INT, "
            "milestone_25_date DATE, milestone_50_date DATE, milestone_75_date DATE, completion_date DATE, "
            "current_progress_pct INT, completed_module_count INT, dropout_date DATE, total_module_count INT, "
            "current_status VARCHAR(255), days_since_last_activity INT, last_activity_date DATE, "
            "CONSTRAINT PK_fact_student_course_lifecycle PRIMARY KEY (student_key, course_key)",

        "fact_activity_transitions":
            "course_key VARCHAR(255), from_resource_key VARCHAR(255), to_resource_key VARCHAR(255), "
            "transition_count INT, "
            "CONSTRAINT PK_fact_activity_transitions PRIMARY KEY (course_key, from_resource_key, to_resource_key)",

        "fact_student_time_affinity":
            "student_key VARCHAR(255), course_key VARCHAR(255), time_slot VARCHAR(50), "
            "efficiency_index DECIMAL(5,2), total_engagement_score INT, session_count INT, "
            "CONSTRAINT PK_fact_student_time_affinity PRIMARY KEY (student_key, course_key, time_slot)",

        "fact_student_deadline_proximity":
            "student_key VARCHAR(255), course_key VARCHAR(255), resource_key VARCHAR(255), "
            "deadline_date TIMESTAMP, first_attempt_date TIMESTAMP, hours_before_deadline DECIMAL(10,2), "
            "pressure_level VARCHAR(50), is_completed BOOLEAN, "
            "CONSTRAINT PK_fact_student_deadline_proximity PRIMARY KEY (student_key, course_key, resource_key)",

        "fact_student_engagement_depth":
            "student_key VARCHAR(255), course_key VARCHAR(255), resource_key VARCHAR(255), "
            "depth_ratio DECIMAL(5,2), engagement_type VARCHAR(50), "
            "CONSTRAINT PK_fact_student_engagement_depth PRIMARY KEY (student_key, course_key, resource_key)",

        "fact_behavior_outcome_correlation":
            "course_key VARCHAR(255), week_of_year INT, year INT, "
            "correlation_active_learning_score INT, correlation_cram_failure INT, "
            "avg_final_score DECIMAL(5,2), cram_student_count INT",
    }

    print("🏗️ Khởi tạo cấu trúc bảng...")
    for table_name, schema in tables.items():
        cursor.execute(f"DROP TABLE IF EXISTS {schema_name}.{table_name} CASCADE")
        cursor.execute(f"CREATE TABLE {schema_name}.{table_name} ({schema})")

    def insert_many(table, data):
        if not data:
            return
        keys = data[0].keys()
        cols = ", ".join(keys)
        query = f"INSERT INTO {schema_name}.{table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"
        vals = [[d[k] for k in keys] for d in data]
        execute_values(cursor, query, vals)
        print(f"  ✅ {table}: {len(data)} bản ghi")

    # -------------------------------------------------------------------------
    # 1. Dimensions
    # -------------------------------------------------------------------------
    ho  = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Đặng", "Bùi", "Đỗ"]
    dem = ["Văn", "Thị", "Minh", "Quang", "Anh", "Hữu", "Thanh", "Đức", "Ngọc", "Hoàng"]
    ten = ["An", "Bình", "Cường", "Dũng", "Em", "Giang", "Hùng", "Lan", "Nam", "Phúc",
           "Quân", "Sơn", "Trang", "Uyên", "Vinh"]

    actors = [
        {"actor_id": "2", "actor_name": "Admin User"},
        {"actor_id": "3", "actor_name": "Phát Hồ Tấn"},
        {"actor_id": "5", "actor_name": "Nguyễn Văn An"},
    ]
    student_profiles = {"2": "star", "3": "normal", "5": "procrastinator"}

    for i in range(6, 156):
        name = f"{random.choice(ho)} {random.choice(dem)} {random.choice(ten)}"
        actors.append({"actor_id": str(i), "actor_name": name})
        r = random.random()
        if   r < 0.12: student_profiles[str(i)] = "star"
        elif r < 0.22: student_profiles[str(i)] = "at-risk"
        elif r < 0.35: student_profiles[str(i)] = "procrastinator"
        elif r < 0.45: student_profiles[str(i)] = "ghost"
        elif r < 0.55: student_profiles[str(i)] = "reviewer"
        elif r < 0.65: student_profiles[str(i)] = "early-bird"
        elif r < 0.75: student_profiles[str(i)] = "night-owl"
        else:           student_profiles[str(i)] = "steady"

    insert_many("dim_actor", actors)

    courses = [
        {"course_key": "101", "course_name": "Python Cơ bản cho Phân tích Dữ liệu", "course_level": "Đại học", "total_modules": 10},
        {"course_key": "102", "course_name": "Cấu trúc dữ liệu & Giải thuật",        "course_level": "Đại học", "total_modules": 12},
        {"course_key": "103", "course_name": "Trí tuệ Nhân tạo nâng cao",            "course_level": "Cao học", "total_modules": 15},
    ]
    insert_many("dim_course", courses)

    sections = []
    resources = []
    for c in courses:
        # Mỗi khóa học có 3 sections
        sec_info = [
            {"num": 1, "name": "Chương 1: Nhập môn & Cài đặt"},
            {"num": 2, "name": "Chương 2: Kiến thức trọng tâm"},
            {"num": 3, "name": "Chương 3: Tổng kết & Đồ án"},
        ]
        for s in sec_info:
            s_id = f"{c['course_key']}S{s['num']}"
            sections.append({
                "section_key": s_id,
                "section_name": s['name'],
                "section_number": s['num'],
                "course_key": c["course_key"]
            })

        for i in range(1, c["total_modules"] + 1):
            r_id   = f"{c['course_key']}{i:02d}"
            r_type = "quiz" if i % 4 == 0 else ("assign" if i % 6 == 0 else "page")
            r_name = f"Module {i}: " + (
                "Bài kiểm tra" if r_type == "quiz" else
                "Bài tập lớn"  if r_type == "assign" else
                "Bài giảng Video/Text"
            )
            
            # Gán vào section dựa trên số thứ tự module
            if i <= 2: s_idx = 1
            elif i <= c["total_modules"] - 2: s_idx = 2
            else: s_idx = 3
            
            resources.append({
                "resource_key": r_id,
                "resource_name": r_name,
                "resource_type": r_type,
                "section_key": f"{c['course_key']}S{s_idx}",
                "course_key": c["course_key"],
            })
    
    insert_many("dim_section", sections)
    insert_many("dim_resource", resources)

    now        = datetime.now()
    start_date = now - timedelta(days=90)
    times = []
    for i in range(91):
        d = start_date + timedelta(days=i)
        for s in ["Morning", "Afternoon", "Evening", "Night"]:
            times.append({
                "time_id":     f"{s[0]}{d.strftime('%Y%m%d')}",
                "date":        d.day,
                "month":       d.month,
                "year":        d.year,
                "week":        d.isocalendar()[1],
                "day_of_week": d.strftime("%A"),
                "time_slot":   s,
            })
    insert_many("dim_time", times)

    # -------------------------------------------------------------------------
    # 2. Facts — per student per course
    # -------------------------------------------------------------------------
    last_8_weeks = []
    for i in range(8):
        dt = now - timedelta(weeks=i)
        last_8_weeks.append((dt.year, dt.isocalendar()[1]))

    daily      = []
    risk_weekly = []
    lifecycle  = []
    depth      = []
    proximity  = []
    affinity   = []

    for c in courses:
        res_in_course = [r for r in resources if r["course_key"] == c["course_key"]]
        total_modules = c["total_modules"]

        for a in actors:
            s_key  = a["actor_id"]
            p_type = student_profiles.get(s_key, "steady")

            enroll_days_ago = random.randint(40, 80)
            enroll_dt       = now - timedelta(days=enroll_days_ago)

            has_life_event = random.random() < 0.1
            event_day      = random.randint(20, 40)

            last_activity_dt = enroll_dt
            weekly_scores    = {}   # (year, week) -> [scores]

            # --- 2.1 Daily engagement (simulate 60 days) ---
            for day_i in range(60):
                d = now - timedelta(days=day_i)
                if d < enroll_dt:
                    continue

                persona = p_type
                if has_life_event and day_i < event_day:
                    persona = "at-risk" if p_type in ["star", "steady"] else "star"

                is_weekend = d.strftime("%A") in ["Saturday", "Sunday"]

                prob_map = {
                    "star": 0.85, "at-risk": 0.2, "ghost": 0.05,
                    "reviewer": 0.75, "steady": 0.55,
                    "early-bird": 0.6, "night-owl": 0.6,
                    "procrastinator": 0.7 if is_weekend else 0.1,
                }
                active_prob = prob_map.get(persona, 0.5)

                if random.random() >= active_prob:
                    continue

                slot_weights = {
                    "early-bird":    [4, 2, 1, 0],
                    "night-owl":     [0, 1, 3, 5],
                    "star":          [3, 4, 2, 1],
                    "procrastinator":[1, 1, 4, 6],
                }
                weights = slot_weights.get(persona, [1, 1, 1, 1])
                slot    = random.choices(["Morning", "Afternoon", "Evening", "Night"], weights=weights)[0]
                t_id    = f"{slot[0]}{d.strftime('%Y%m%d')}"

                base_acc = random.randint(30, 65) if persona in ["star", "reviewer"] else \
                           random.randint(2, 8)   if persona == "at-risk" else \
                           random.randint(5, 20)
                acc  = max(0, base_acc + random.randint(-4, 10))
                quiz = random.randint(1, 3) if persona in ["star", "procrastinator"] else \
                       (1 if random.random() < 0.3 else 0)

                # engagement_score: align với công thức loader thực tế
                # loader: LEAST(acc, 20% modules) * (50 / 20% modules) + LEAST(quiz,1)*50
                threshold = max(5, int(total_modules * 0.2))
                score = int(min(acc, threshold) * (50.0 / threshold) + min(quiz, 1) * 50)

                daily.append({
                    "student_key":          s_key,
                    "course_key":           int(c["course_key"]),
                    "date_key":             t_id,
                    "total_resource_access": acc,
                    "total_quiz_attempt":   quiz,
                    "total_active_minutes":  int(acc * random.uniform(1.5, 3.5)), # Simulate minutes based on access
                    "engagement_score":     score,
                })

                last_activity_dt = d
                w_key = (d.year, d.isocalendar()[1])
                weekly_scores.setdefault(w_key, []).append(score)

            # --- 2.2 Weekly risk ---
            for y, w in last_8_weeks:
                scores   = weekly_scores.get((y, w), [0])
                avg_eng  = sum(scores) / len(scores)

                # Align với loader: 3 ngưỡng cứng, nhưng thêm noise để phân tán
                if avg_eng < 20:
                    base_risk = 80
                elif avg_eng < 50:
                    base_risk = 50
                else:
                    base_risk = 10

                # Điều chỉnh theo profile
                if p_type in ["at-risk", "ghost"]:
                    base_risk = min(100, base_risk + 20)
                elif p_type == "star":
                    base_risk = max(0, base_risk - 20)

                risk = int(max(0, min(100, base_risk + random.randint(-8, 8))))

                risk_weekly.append({
                    "student_key":           s_key,
                    "course_key":            int(c["course_key"]),
                    "week_of_year":          w,
                    "year":                  y,
                    "engagement_score":      int(avg_eng),
                    "progress_score":        random.randint(80, 100) if p_type == "star" else random.randint(10, 70),
                    "outcome_score":         random.randint(75, 100) if p_type == "star" else random.randint(5, 80),
                    "risk_score":            risk,
                    "dropout_probability_pct": float(risk),
                    "risk_level":            "High" if risk > 70 else ("Medium" if risk > 40 else "Low"),
                })

            # --- 2.3 Lifecycle ---
            # progress phản ánh profile: ghost ít, star nhiều
            if p_type == "star":
                progress = random.randint(90, 100)
            elif p_type == "ghost":
                progress = random.randint(0, 20)
            elif p_type == "at-risk":
                progress = random.randint(10, 45)
            else:
                progress = random.randint(40, 95)

            days_inactive = (now.date() - last_activity_dt.date()).days
            if progress >= 100:
                status = "Completed"
            elif p_type == "ghost" or days_inactive > 30:
                status = "Dropout"
            else:
                status = "Active"

            lifecycle.append({
                "student_key":              s_key,
                "course_key":               int(c["course_key"]),
                "milestone_25_date":        (enroll_dt + timedelta(days=10)).date() if progress >= 25 else None,
                "milestone_50_date":        (enroll_dt + timedelta(days=25)).date() if progress >= 50 else None,
                "milestone_75_date":        (enroll_dt + timedelta(days=40)).date() if progress >= 75 else None,
                "completion_date":          (now - timedelta(days=2)).date() if progress >= 100 else None,
                "current_progress_pct":     int(progress),
                "completed_module_count":   int(progress * total_modules / 100),
                "dropout_date":             (now - timedelta(days=random.randint(5, 20))).date()
                                            if status == "Dropout" else None,
                "total_module_count":       total_modules,
                "current_status":           status,
                "days_since_last_activity": days_inactive,
                "last_activity_date":       last_activity_dt.date(),
            })

            # --- 2.4 Time affinity ---
            for slot in ["Morning", "Afternoon", "Evening", "Night"]:
                pref = 1.0
                if p_type == "early-bird" and slot == "Morning":   pref = 3.0
                if p_type == "night-owl"  and slot == "Night":     pref = 3.5
                if p_type == "star"       and slot in ["Morning", "Afternoon"]: pref = 2.0
                score_sum  = int(random.randint(400, 3000) * pref)
                sess_count = random.randint(10, 50)
                affinity.append({
                    "student_key":           s_key,
                    "course_key":            c["course_key"],
                    "time_slot":             slot,
                    "efficiency_index":      round(score_sum / max(sess_count, 1) / 10, 2),
                    "total_engagement_score": score_sum,
                    "session_count":         sess_count,
                })

            # --- 2.5 Engagement depth & deadline proximity ---
            # Xác suất reach giảm dần theo thứ tự module — mô phỏng drop-off tự nhiên
            for mod_i, r in enumerate(res_in_course):
                reach_prob = max(0.05, 1.0 - (mod_i / len(res_in_course)) * 0.75)
                if p_type == "star":
                    reach_prob = min(1.0, reach_prob + 0.2)
                elif p_type in ["ghost", "at-risk"]:
                    reach_prob = reach_prob * 0.3

                if random.random() > reach_prob:
                    continue

                if p_type == "reviewer":   depth_val = random.uniform(1.8, 4.0)
                elif p_type == "star":     depth_val = random.uniform(1.3, 2.8)
                elif p_type == "at-risk":  depth_val = random.uniform(0.1, 0.4)
                else:                      depth_val = random.uniform(0.5, 1.5)

                depth.append({
                    "student_key":   s_key,
                    "course_key":    c["course_key"],
                    "resource_key":  r["resource_key"],
                    "depth_ratio":   round(depth_val, 2),
                    "engagement_type": "Stuck" if depth_val > 1.5 else
                                       "Skimming"  if depth_val < 0.6 else "Deep Dive",
                })

                if r["resource_type"] in ["quiz", "assign"]:
                    # days_before_deadline: positif = nộp sớm, âm = nộp trễ
                    days_before = random.randint(1, 5) if p_type in ["star", "steady"] \
                                  else random.randint(-3, 2)
                    proximity.append({
                        "student_key":        s_key,
                        "course_key":         c["course_key"],
                        "resource_key":       r["resource_key"],
                        "deadline_date":      now + timedelta(days=2),
                        "first_attempt_date": now - timedelta(days=days_before),
                        "pressure_level":     "Safe"     if days_before >= 2 else
                                              "Warning"  if days_before >= 0 else "Critical",
                    })

    # -------------------------------------------------------------------------
    # 3. Aggregated facts
    # -------------------------------------------------------------------------
    transitions  = []
    distribution = []
    correlation  = []

    for c in courses:
        res_keys = [r["resource_key"] for r in resources if r["course_key"] == c["course_key"]]
        num_res  = len(res_keys)

        # Transitions: sequential + shortcuts + review loops
        for i in range(num_res - 1):
            bottleneck = 0.3 if i in [3, 7] else 1.0
            base_vol   = int(random.randint(80, 150) * (1.0 - i / num_res * 0.4) * bottleneck)
            transitions.append({
                "course_key":       c["course_key"],
                "from_resource_key": res_keys[i],
                "to_resource_key":   res_keys[i + 1],
                "transition_count":  max(5, base_vol),
            })
            if i + 2 < num_res and random.random() < 0.4:
                transitions.append({
                    "course_key":       c["course_key"],
                    "from_resource_key": res_keys[i],
                    "to_resource_key":   res_keys[i + 2],
                    "transition_count":  random.randint(10, 40),
                })
            if i > 0 and random.random() < 0.25:
                transitions.append({
                    "course_key":       c["course_key"],
                    "from_resource_key": res_keys[i + 1],
                    "to_resource_key":   res_keys[i],
                    "transition_count":  random.randint(5, 25),
                })

        # Distribution & correlation per week
        cram_base_count = sum(1 for t in student_profiles.values() if t == "procrastinator")
        
        # Sắp xếp tuần từ cũ đến mới để tạo trend
        sorted_weeks = sorted(last_8_weeks, key=lambda x: (x[0], x[1]))
        
        for idx, (y, w) in enumerate(sorted_weeks):
            # Số lượng cramming tăng dần theo thời gian (đạt đỉnh ở tuần cuối)
            week_cram_count = int(cram_base_count * (0.2 + 0.8 * (idx / max(len(sorted_weeks)-1, 1))))
            
            distribution.append({
                "course_key":              c["course_key"],
                "week_of_year":            w,
                "year":                    y,
                "avg_engagement_score":    round(random.uniform(40, 80), 2),
                "p25_engagement":          35,
                "p50_engagement":          58,
                "p75_engagement":          75,
                "medium_engagement_count": random.randint(20, 40),
                "low_engagement_count":    random.randint(10, 20),
                "active_student_count":    random.randint(30, 60),
                "passive_student_count":   random.randint(5, 15),
            })
            correlation.append({
                "course_key":                      c["course_key"],
                "week_of_year":                    w,
                "year":                            y,
                "correlation_active_learning_score": random.randint(75, 95),
                "correlation_cram_failure":          random.randint(60, 85),
                "avg_final_score":                   round(random.uniform(60, 90), 2),
                "cram_student_count":                week_cram_count,
            })

    # -------------------------------------------------------------------------
    # Final insert - Chuẩn bị dữ liệu với các cột đã fix
    # -------------------------------------------------------------------------
    
    # For distribution, add excellent/good/warning/critical columns
    distribution_final = []
    for d in distribution:
        d_final = d.copy()
        # Calculate thresholds (Excellent 80-100, Good 60-79, Warning 40-59, Critical <40)
        total_students = d['active_student_count'] + d['medium_engagement_count'] + d['low_engagement_count'] + d['passive_student_count']
        d_final['excellent_student_count'] = int(total_students * 0.15)  # ~15% excellent
        d_final['good_student_count'] = int(total_students * 0.35)       # ~35% good
        d_final['warning_student_count'] = int(total_students * 0.30)    # ~30% warning
        d_final['critical_student_count'] = int(total_students * 0.20)   # ~20% critical
        distribution_final.append(d_final)
    
    # For deadline_proximity, add hours_before_deadline and is_completed
    proximity_final = []
    for p in proximity:
        p_final = p.copy()
        # Calculate hours before deadline
        deadline = p['deadline_date']
        first_attempt = p['first_attempt_date']
        hours_diff = (deadline - first_attempt).total_seconds() / 3600
        p_final['hours_before_deadline'] = round(hours_diff, 2)
        p_final['is_completed'] = p['pressure_level'] != 'Critical'  # Assume non-critical are completed
        proximity_final.append(p_final)
    
    print("\n⏳ Đang nạp dữ liệu...")
    insert_many("fact_daily_student_engagement",      daily)
    insert_many("fact_risk_student_weekly",           risk_weekly)
    insert_many("fact_student_course_lifecycle",      lifecycle)
    insert_many("fact_student_time_affinity",         affinity)
    insert_many("fact_student_deadline_proximity",    proximity_final)
    insert_many("fact_student_engagement_depth",      depth)
    insert_many("fact_activity_transitions",          transitions)
    insert_many("fact_class_engagement_distribution", distribution_final)
    insert_many("fact_behavior_outcome_correlation",  correlation)

    print("\n✨ Seed hoàn tất.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed_data()
