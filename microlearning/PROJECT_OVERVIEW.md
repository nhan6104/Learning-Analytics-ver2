# Learning Analytics System - Project Overview

## 📋 Tổng quan dự án

Hệ thống Learning Analytics là một giải pháp phân tích học tập toàn diện được xây dựng trên nền tảng Moodle LMS. Hệ thống thu thập dữ liệu xAPI từ hoạt động học tập của sinh viên, xử lý qua pipeline ETL, và cung cấp dashboard trực quan cho cả giáo viên và sinh viên.

### Mục tiêu chính:
- **Phát hiện sớm sinh viên có nguy cơ bỏ học** thông qua các chỉ số rủi ro
- **Cung cấp insights về hành vi học tập** để giáo viên can thiệp kịp thời
- **Giúp sinh viên tự đánh giá** tiến độ và so sánh với lớp
- **Tối ưu hóa trải nghiệm học tập** dựa trên phân tích time affinity và engagement depth

---

## 🏗️ Kiến trúc hệ thống

### Data Pipeline (3 lớp)

```
┌─────────────────────────────────────────────────────────────────┐
│                        MOODLE LMS                                │
│                    (xAPI Statements)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAKE (Bronze)                            │
│  - Kafka: Real-time ingestion                                    │
│  - MinIO: Object storage for raw xAPI statements                 │
│  - ETL: datalake/etl.py                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DATA WAREHOUSE (Silver)                         │
│  - PostgreSQL: Normalized star schema                            │
│  - Fact Tables: fact_statement, fact_activity, fact_quiz, etc.   │
│  - Dim Tables: dim_actor, dim_context, dim_time, etc.            │
│  - ETL: datawarehouse/etl.py                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA MART (Gold)                              │
│  - PostgreSQL: Aggregated analytics tables                       │
│  - Fact Tables: fact_risk_student_weekly,                        │
│    fact_daily_student_engagement,                                │
│    fact_student_course_lifecycle,                                │
│    fact_student_time_affinity,                                   │
│    fact_student_engagement_depth,                                │
│    fact_student_deadline_proximity,                              │
│    fact_activity_transitions,                                    │
│    fact_class_engagement_distribution,                           │
│    fact_behavior_outcome_correlation                             │
│  - ETL: datamart/updateDatamart.py                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                              │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │  Teacher Dashboard   │    │  Student Drilldown Page      │  │
│  │  (dashboard.php)     │───>│  (student_detail.php)        │  │
│  │                      │    │                              │  │
│  │  - Class overview    │    │  - Individual analytics      │  │
│  │  - At-risk students  │    │  - Engagement trends         │  │
│  │  - Engagement dist.  │    │  - Time affinity             │  │
│  │  - Behavior patterns │    │  - Deadline proximity        │  │
│  └──────────────────────┘    │  - Activity transitions      │  │
│                               │  - Lifecycle milestones      │  │
│                               └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Cấu trúc thư mục

```
Learning-Analytics-ver2/
├── datalake/                    # Bronze layer - Raw data ingestion
│   ├── etl.py                   # Main ETL orchestrator
│   ├── extract.py               # Extract from Kafka/MinIO
│   ├── transform.py             # Basic cleaning
│   └── load.py                  # Load to Data Lake
│
├── datawarehouse/               # Silver layer - Normalized schema
│   ├── etl.py                   # Main ETL orchestrator
│   ├── extract.py               # Extract from Data Lake
│   ├── transform.py             # Transform to star schema
│   ├── load.py                  # Load to Data Warehouse
│   ├── models/                  # SQLAlchemy models
│   │   ├── dimActor.py
│   │   ├── dimContext.py
│   │   ├── dimTime.py
│   │   ├── factStatement.py
│   │   ├── factActivity.py
│   │   └── ...
│   └── transformers/            # Transformation logic
│       ├── transformDimActor.py
│       ├── transformFactStatement.py
│       └── ...
│
├── datamart/                    # Gold layer - Analytics tables
│   ├── updateDatamart.py        # Main ETL orchestrator
│   ├── load.py                  # Load aggregated data
│   ├── models/                  # SQLAlchemy models
│   │   ├── dimActor.py
│   │   ├── dimCourse.py
│   │   ├── factRiskStudentWeekly.py
│   │   ├── factDailyStudentEngagement.py
│   │   └── ...
│   ├── loader/                  # Loader logic for each fact table
│   │   ├── loadFactRiskStudentWeekly.py
│   │   ├── loadFactDailyStudentEngagement.py
│   │   └── ...
│   ├── datamart_schema.md       # Schema documentation
│   └── dashboard_queries.md     # Query examples
│
├── microlearning/               # Moodle plugin - Presentation layer
│   ├── assets/
│   │   ├── css/
│   │   │   └── student_detail.css
│   │   └── js/
│   │       ├── student_detail.js
│   │       ├── student_detail_render.js
│   │       └── student_detail_main.js
│   ├── dashboard.php            # Teacher dashboard
│   ├── student_detail.php       # Student drilldown page
│   ├── lib.php                  # Shared functions
│   ├── README.md
│   ├── READY_TO_DEPLOY.md
│   └── DEPLOYMENT_CHECKLIST.md
│
├── utils/                       # Shared utilities
│   ├── kafka_utils/             # Kafka connection
│   ├── minio_utils/             # MinIO connection
│   ├── pgsql_utils.py           # PostgreSQL connection
│   └── moodle_db_utils.py       # Moodle DB connection
│
├── .kiro/                       # Kiro AI workspace
│   └── specs/
│       └── student-drilldown/   # Student drilldown feature spec
│           ├── requirements.md
│           ├── design.md
│           └── tasks.md
│
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
└── PROJECT_OVERVIEW.md          # This file
```

---

## 🎯 Các tính năng chính

### 1. Teacher Dashboard (dashboard.php)

**Mục đích:** Cung cấp cái nhìn tổng quan về toàn bộ lớp học

**Tính năng:**
- **Overview Metrics**: Tổng số sinh viên, điểm tương tác TB, điểm rủi ro TB, số SV học dồn
- **Class Engagement Trend**: Biểu đồ xu hướng engagement của lớp qua 12 tuần
- **At-Risk Student List**: Danh sách sinh viên có nguy cơ bỏ học cao
- **Engagement Distribution**: Phân bố sinh viên theo mức độ tương tác (Active/Medium/Low/Passive)
- **Behavior Patterns**: Phân tích hành vi học dồn (cramming)
- **Activity Transitions**: Top transitions giữa các tài nguyên
- **Module Health Treemap**: Treemap hiển thị tình trạng từng module
- **Coverage Funnel**: Funnel chart theo dõi tỷ lệ tiếp cận tài liệu

**Công nghệ:**
- Backend: PHP + PostgreSQL
- Frontend: TailwindCSS + ApexCharts + D3.js + Google Charts
- AJAX: Fetch API cho real-time data loading

### 2. Student Drilldown Page (student_detail.php)

**Mục đích:** Phân tích chuyên sâu về từng sinh viên cá nhân

**Tính năng:**
- **Overview Metrics**: Engagement score, risk level, progress, last activity
- **Engagement Trend**: Biểu đồ xu hướng engagement cá nhân vs class average (12 tuần)
- **Time Affinity Analysis**: Phân tích khung giờ học hiệu quả nhất (Morning/Afternoon/Evening/Night)
- **Engagement Depth Table**: Bảng phân loại độ sâu học tập trên từng tài nguyên (Stuck/Skimming/Deep Dive)
- **Deadline Proximity**: Top 5 deadlines sắp tới với mức độ áp lực (Safe/Warning/Critical)
- **Activity Transitions (Sankey)**: Sankey diagram hiển thị luồng di chuyển giữa các tài nguyên
- **Lifecycle Milestones**: Timeline các mốc tiến độ (25%, 50%, 75%, 100%)
- **Daily Activity Heatmap**: Heatmap 90 ngày hoạt động hàng ngày
- **Class Comparison**: So sánh engagement, risk, progress với trung bình lớp
- **Insights & Recommendations**: Gợi ý can thiệp dựa trên phân tích

**Công nghệ:**
- Backend: PHP + PostgreSQL
- Frontend: TailwindCSS + ApexCharts + D3.js
- AJAX: Fetch API với session-based caching (5 phút)
- Progressive Loading: 4-phase loading strategy
- PDF Export: Browser print dialog

**Kiến trúc code (Option 3 - Assets folder):**
```
student_detail.php (830 lines)
├── PHP Backend (400 lines)
│   ├── Authentication & Authorization
│   ├── AJAX Data Handler (10 queries)
│   └── HTML Structure
└── External Assets
    ├── student_detail.css (50 lines)
    └── JavaScript (850 lines)
        ├── student_detail.js (250 lines)
        │   ├── Utility functions
        │   ├── Cache management
        │   └── Chart destruction
        ├── student_detail_render.js (400 lines)
        │   ├── Table rendering
        │   ├── Chart rendering
        │   ├── Sankey diagram
        │   └── Heatmap rendering
        └── student_detail_main.js (200 lines)
            ├── Progressive loading
            ├── Data fetching
            └── Event handlers
```

---

## 📊 Data Mart Schema

### Dimension Tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `dim_actor` | Sinh viên/giáo viên | actor_id, actor_name |
| `dim_course` | Khóa học | course_key, course_name, total_modules |
| `dim_resource` | Tài nguyên học tập | resource_key, resource_name, resource_type |
| `dim_section` | Phần/chương | section_key, section_name |
| `dim_time` | Thời gian | time_id, date, month, year, week, time_slot |

### Fact Tables

| Table | Description | Granularity | Key Metrics |
|-------|-------------|-------------|-------------|
| `fact_daily_student_engagement` | Engagement hàng ngày | Student × Course × Date | engagement_score, total_resource_access, total_quiz_attempt |
| `fact_risk_student_weekly` | Rủi ro hàng tuần | Student × Course × Week | risk_score, dropout_probability_pct, risk_level |
| `fact_student_course_lifecycle` | Vòng đời sinh viên | Student × Course | current_progress_pct, current_status, days_since_last_activity |
| `fact_student_time_affinity` | Khung giờ học hiệu quả | Student × Course × TimeSlot | efficiency_index, total_engagement_score |
| `fact_student_engagement_depth` | Độ sâu học tập | Student × Course × Resource | engagement_type (Stuck/Skimming/Deep Dive), depth_ratio |
| `fact_student_deadline_proximity` | Áp lực deadline | Student × Course × Resource | pressure_level, hours_before_deadline |
| `fact_activity_transitions` | Luồng di chuyển | Course × FromResource × ToResource | transition_count |
| `fact_class_engagement_distribution` | Phân bố engagement lớp | Course × Week | avg_engagement_score, active/medium/low_engagement_count |
| `fact_behavior_outcome_correlation` | Tương quan hành vi-kết quả | Course × Week | cram_student_count, avg_final_score |

---

## 🔧 Công nghệ sử dụng

### Backend
- **Language**: Python 3.x, PHP 7.4+
- **Database**: PostgreSQL 13+
- **ORM**: SQLAlchemy (Python)
- **Message Queue**: Apache Kafka
- **Object Storage**: MinIO
- **Web Server**: Apache 2.4

### Frontend
- **CSS Framework**: TailwindCSS 3.x
- **Charts**: ApexCharts 3.x, D3.js v7, Google Charts
- **JavaScript**: Vanilla JS (ES6+)
- **Icons**: Heroicons (SVG)

### Infrastructure
- **LMS**: Moodle 4.x
- **Containerization**: Docker (for Kafka, MinIO, PostgreSQL)
- **Version Control**: Git

---

## 🚀 Deployment

### Server Information
- **Server IP**: 192.168.1.220
- **Moodle Path**: /var/www/html/moodle/
- **Plugin Path**: /var/www/html/moodle/local/microlearning/
- **Dashboard URL**: http://192.168.1.220/moodle/local/microlearning/dashboard.php

### Deployment Steps

1. **Copy files to server**:
```bash
cd microlearning
scp dashboard.php student_detail.php lib.php root@192.168.1.220:/var/www/html/moodle/local/microlearning/
scp assets/css/student_detail.css root@192.168.1.220:/var/www/html/moodle/local/microlearning/assets/css/
scp assets/js/*.js root@192.168.1.220:/var/www/html/moodle/local/microlearning/assets/js/
```

2. **Set permissions**:
```bash
ssh root@192.168.1.220
cd /var/www/html/moodle/local/microlearning/
chown www-data:www-data dashboard.php student_detail.php lib.php
chmod 644 dashboard.php student_detail.php lib.php
chown -R www-data:www-data assets/
```

3. **Verify and test**:
- Check PHP syntax: `php -l dashboard.php`
- Open browser: http://192.168.1.220/moodle/local/microlearning/dashboard.php
- Test navigation to student detail page
- Check browser console for errors

**Chi tiết**: Xem `microlearning/READY_TO_DEPLOY.md` và `microlearning/DEPLOYMENT_CHECKLIST.md`

---

## 📝 Specs & Documentation

### Completed Specs
- **Student Drilldown Feature** (`.kiro/specs/student-drilldown/`)
  - Requirements: 11 requirements với 60+ acceptance criteria
  - Design: Architecture, components, data flow, UI/UX
  - Tasks: 48 tasks (100% completed)
  - Status: ✅ Deployed to production

### Documentation Files
- `datamart/datamart_schema.md` - Chi tiết schema của Data Mart
- `datamart/dashboard_queries.md` - Các query mẫu cho dashboard
- `microlearning/README.md` - Hướng dẫn plugin Moodle
- `microlearning/READY_TO_DEPLOY.md` - Hướng dẫn deployment
- `microlearning/DEPLOYMENT_CHECKLIST.md` - Checklist kiểm tra
- `PROJECT_OVERVIEW.md` - File này

---

## 🎓 Key Concepts

### Engagement Score (0-100)
Điểm tương tác được tính dựa trên:
- **Tương tác tài liệu** (max 50 điểm): Số lần truy cập tài nguyên
- **Hoàn thành bài tập/Quiz** (max 50 điểm): Số lần làm quiz/assignment

### Risk Score (10-80)
Điểm rủi ro dự báo khả năng bỏ học, tính dựa trên:
- Sự sụt giảm tần suất đăng nhập
- Tiến độ làm bài chậm
- Số ngày không hoạt động

### Risk Level
- **High**: dropout_probability > 50% (cần can thiệp ngay)
- **Medium**: dropout_probability 30-50% (cần theo dõi)
- **Low**: dropout_probability < 30% (ổn định)

### Engagement Depth
- **Stuck**: Sinh viên gặp khó khăn, tương tác nhiều nhưng không tiến bộ
- **Skimming**: Sinh viên học lướt, tương tác ít
- **Deep Dive**: Sinh viên học chuyên sâu, tương tác nhiều và hiệu quả

### Time Affinity
Khung giờ sinh viên học hiệu quả nhất:
- **Morning** (6:00-12:00)
- **Afternoon** (12:00-18:00)
- **Evening** (18:00-22:00)
- **Night** (22:00-6:00)

### Deadline Proximity
- **Safe**: > 48 giờ trước deadline
- **Warning**: 24-48 giờ trước deadline
- **Critical**: < 24 giờ trước deadline

---

## 🔄 ETL Pipeline

### Data Flow
1. **Ingestion**: xAPI statements từ Moodle → Kafka → MinIO (Bronze)
2. **Transformation**: Bronze → Data Warehouse (Silver) - Normalized star schema
3. **Aggregation**: Silver → Data Mart (Gold) - Analytics tables
4. **Presentation**: Gold → Dashboard (PHP + JavaScript)

### ETL Schedule
- **Real-time**: Kafka ingestion (continuous)
- **Hourly**: Data Warehouse ETL
- **Daily**: Data Mart ETL (fact_daily_student_engagement)
- **Weekly**: Risk calculation (fact_risk_student_weekly)

### Running ETL Manually
```bash
# Data Lake ETL
python -m datalake.etl

# Data Warehouse ETL
python -m datawarehouse.etl

# Data Mart ETL
python -m datamart.updateDatamart
```

---

## 🧪 Testing

### Unit Tests
- Python: pytest
- PHP: PHPUnit (if needed)

### Integration Tests
- Test ETL pipeline end-to-end
- Test dashboard data loading
- Test student drilldown navigation

### Manual Testing
- Follow `microlearning/DEPLOYMENT_CHECKLIST.md`
- Test all dashboard features
- Test student drilldown features
- Test on different browsers
- Test responsive design

---

## 📈 Future Enhancements

### Planned Features
- [ ] Student self-service dashboard
- [ ] Email notifications for at-risk students
- [ ] Predictive analytics with ML models
- [ ] Real-time alerts for teachers
- [ ] Mobile app
- [ ] Export reports to PDF/Excel
- [ ] Integration with other LMS platforms

### Technical Improvements
- [ ] Add caching layer (Redis)
- [ ] Optimize SQL queries
- [ ] Add API layer (REST/GraphQL)
- [ ] Implement CI/CD pipeline
- [ ] Add monitoring and logging (ELK stack)
- [ ] Add automated testing

---

## 👥 Team & Contacts

### Development Team
- **Data Engineer**: ETL pipeline, Data Warehouse, Data Mart
- **Backend Developer**: PHP, PostgreSQL, Moodle integration
- **Frontend Developer**: Dashboard UI, Charts, Visualizations
- **AI Assistant**: Kiro (Spec creation, Code generation, Documentation)

### Support
- **Documentation**: See `microlearning/README.md`
- **Deployment**: See `microlearning/READY_TO_DEPLOY.md`
- **Issues**: Check `.kiro/specs/student-drilldown/tasks.md`

---

## 📄 License

This project is part of a Learning Analytics research initiative.

---

**Last Updated**: 2026-03-29  
**Version**: 1.0.0  
**Status**: ✅ Production Ready
