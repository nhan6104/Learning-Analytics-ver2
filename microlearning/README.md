# Microlearning Plugin - Student Drilldown Feature

## 📁 Folder Structure

```
microlearning/
├── assets/
│   ├── css/
│   │   └── student_detail.css          # Styles for student detail page
│   └── js/
│       ├── student_detail.js            # Core functions & cache
│       ├── student_detail_render.js     # Rendering functions
│       └── student_detail_main.js       # Main app logic
├── dashboard.php                        # Main dashboard page
├── student_detail.php                   # Student drilldown page
├── lib.php                              # Shared library functions
├── READY_TO_DEPLOY.md                   # Deployment guide
├── DEPLOYMENT_CHECKLIST.md              # Testing checklist
└── README.md                            # This file
```

## 🚀 Quick Deploy

```bash
# 1. Navigate to this folder
cd microlearning

# 2. Copy all files to server
scp dashboard.php student_detail.php lib.php root@192.168.1.220:/var/www/html/moodle/local/microlearning/
scp assets/css/student_detail.css root@192.168.1.220:/var/www/html/moodle/local/microlearning/assets/css/
scp assets/js/*.js root@192.168.1.220:/var/www/html/moodle/local/microlearning/assets/js/

# 3. Set permissions on server
ssh root@192.168.1.220
cd /var/www/html/moodle/local/microlearning/
chown www-data:www-data dashboard.php student_detail.php lib.php
chmod 644 dashboard.php student_detail.php lib.php
chown -R www-data:www-data assets/
```

## 📖 Documentation

- **READY_TO_DEPLOY.md** - Complete deployment instructions
- **DEPLOYMENT_CHECKLIST.md** - Testing and verification steps

## ✨ Features

- Student engagement analytics
- Risk assessment and predictions
- Time affinity analysis
- Activity transitions (Sankey diagram)
- Daily activity heatmap
- Deadline proximity tracking
- Class comparison metrics
- Progressive loading for better UX
- Session-based caching (5 minutes)

## 🎯 Server Location

**Server**: 192.168.1.220  
**Path**: /var/www/html/moodle/local/microlearning/  
**URL**: http://192.168.1.220/moodle/local/microlearning/dashboard.php
