# 🔐 SecureID — Face Recognition Attendance & Entry System

> **Project | Django + OpenCV + face_recognition**
> Smart campus security system with AI-powered identity verification, entry/exit tracking, and automated reporting.

---

## 📸 Features at a Glance

| Feature | Description |
|---|---|
| **Face Recognition** | OpenCV + dlib — real-time webcam matching |
| **Entry / Exit Tracking** | Late entry & early exit detection |
| **Admin Dashboard** | Daily stats, weekly chart, department-wise analytics |
| **Student Management** | Register, edit, deactivate with full CRUD |
| **Attendance Logs** | Filter by date / student / department / status |
| **CSV Export** | One-click downloadable reports |
| **Manual Override** | Admin can add / correct entries manually |
| **Student Reports** | Monthly attendance % per student |
| **Demo Mode** | Works even without face_recognition installed |

---

## 🛠 Tech Stack

```
Backend       → Django 4.2
AI / CV       → face_recognition (dlib) + OpenCV
Database      → SQLite (swap to PostgreSQL for production)
Frontend      → Custom HTML/CSS + Bootstrap 5 + Chart.js
Reports       → Python csv module + pandas/openpyxl
```

---

## 🚀 Setup Instructions

### 1. Clone / Extract the Project

```bash
cd secureid/
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install Dependencies

> **Important:** `face_recognition` requires `cmake` and `dlib`. Install them first:

**Windows:**
```bash
pip install cmake
pip install dlib
pip install face-recognition
pip install -r requirements.txt
```

**Ubuntu / Debian:**
```bash
sudo apt-get install -y build-essential cmake libopenblas-dev liblapack-dev
pip install -r requirements.txt
```

**macOS:**
```bash
brew install cmake
pip install -r requirements.txt
```

### 4. Apply Database Migrations

```bash
python manage.py makemigrations attendance
python manage.py migrate
```

### 5. Load Demo Data (Recommended for Testing)

```bash
python manage.py seed_demo
```

This creates:
- Admin user (`admin` / `admin123`)
- 4 departments
- 10 sample students
- 30 days of attendance history

### 6. Run the Development Server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

---

## 🖥 URLs

| URL | Description |
|---|---|
| `/` | Attendance Terminal (public webcam page) |
| `/login/` | Admin login |
| `/dashboard/` | Admin dashboard with analytics |
| `/students/` | Student list |
| `/students/register/` | Register new student |
| `/students/<id>/face/` | Capture face encoding |
| `/attendance/` | Attendance logs with filters |
| `/attendance/manual/` | Manual attendance entry |
| `/attendance/export/` | CSV export |
| `/admin/` | Django admin panel |

---

## 🧠 How Face Recognition Works

```
1. Admin registers student → captures webcam frame
2. face_recognition encodes face → saves 128-float vector to DB
3. At terminal: webcam frame sent to Django (base64 AJAX)
4. Server loads all encodings → runs face_recognition.compare_faces()
5. Best match below tolerance (0.5) → Student identified
6. Attendance saved: status = present / late based on time threshold
```

### Tolerance Setting
In `settings.py`:
```python
FACE_RECOGNITION_TOLERANCE = 0.5   # 0.4 = strict, 0.6 = lenient
LATE_ENTRY_THRESHOLD_HOUR  = 9     # After 9:00 AM = LATE
```

---

## 📁 Project Structure

```
secureid/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3                    ← Auto-generated
│
├── secureid/                     ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── attendance/                   ← Main app
│   ├── models.py                 ← Student, AttendanceLog, Department
│   ├── views.py                  ← All views (dashboard, terminal, CRUD, export)
│   ├── urls.py                   ← URL routing
│   ├── face_utils.py             ← Face recognition core logic
│   ├── forms.py                  ← Django forms
│   ├── admin.py                  ← Django admin config
│   └── templates/attendance/
│       ├── base.html             ← Dark sidebar layout
│       ├── login.html
│       ├── dashboard.html        ← Stats + charts
│       ├── mark_attendance.html  ← Webcam terminal
│       ├── capture_face.html     ← Face registration
│       ├── register_student.html
│       ├── student_list.html
│       ├── attendance_logs.html
│       ├── manual_attendance.html
│       └── student_report.html
│
├── media/
│   └── student_photos/           ← Uploaded student photos
│
└── static/
    ├── css/
    └── js/
```

---

## 🔒 Production Checklist

- [ ] Change `SECRET_KEY` in `settings.py`
- [ ] Set `DEBUG = False`
- [ ] Configure PostgreSQL database
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Run `python manage.py collectstatic`
- [ ] Use HTTPS (face recognition requires camera permissions)
- [ ] Set up Gunicorn + Nginx


## 👨‍💻 Author
  Umer Asghar [umerchaudhary2004@gmail.com]