# Smart-education-tool
# 🎓 EduBoard – Smart Student & Teacher Dashboard

**EduBoard** is a full-stack web application designed to enhance the learning experience for both **students and teachers**. It provides tools for quiz management, performance tracking, analytics, and student data insights — all in one modern dashboard.

---

## 🚀 Overview

EduBoard is built using **Flask (Python)** for the backend and **HTML, CSS, JavaScript** for the frontend. It allows users to:

* Take quizzes and track performance
* Analyze marks with visual insights
* Manage student records
* Provide teacher-side quiz control
* Maintain leaderboards and analytics

The system supports **role-based access** for students and teachers.

---

## 🧩 Key Features

### 👨‍🎓 Student Features

* Attempt quizzes by subject and difficulty
* View performance analytics and scores
* Access leaderboard rankings
* Track academic progress over time
* Health & wellness dashboard

### 👩‍🏫 Teacher Features

* Create and manage quizzes
* Monitor student performance
* Access teacher dashboard with insights
* Manage student records and data

### 📊 Analytics & Tools

* Marks analyzer with charts
* Student data collection & prediction system
* Real-time scoring and percentage calculation
* Interactive dashboards

---

## 🏗️ Tech Stack

### Backend

* Python (Flask) 
* SQLite Database
* SQLAlchemy ORM
* Authentication (password hashing)

### Frontend

* HTML5, CSS3
* Responsive UI dashboards
* Chart.js (for analytics) 

---

## 📁 Project Structure

```id="y7dk28"
app.py                      # Main Flask backend
templates/
  ├── login.html
  ├── dashboard.html
  ├── analytics.html
  ├── leaderboard.html
  ├── health.html
  ├── marks_analyzer.html
  ├── quiz_select.html
  ├── quiz_management.html
  ├── teacher_dashboard.html
  ├── student_records.html
  ├── student_data_collection.html
```

---

## 🔐 Authentication System

* Secure login system with hashed passwords
* Role-based access:

  * **Student**
  * **Teacher**

---

## 🧠 Core Functionalities

* Quiz attempts stored with:

  * Score
  * Percentage
  * Time taken
* Question-level tracking
* Dynamic quiz generation
* Teacher-created quizzes available to students

---

## ▶️ How to Run

### 1. Install Dependencies

```bash id="x1f93l"
pip install flask flask_sqlalchemy werkzeug requests
```

### 2. Run the App

```bash id="k9z2lp"
python app.py
```

### 3. Open in Browser

```id="wq2sdf"
http://127.0.0.1:5000
```

---

## 🎯 Use Cases

* Schools & colleges for digital learning
* Practice platform for students
* Teacher performance tracking tool
* Academic analytics system

---

## 🚀 Future Improvements

* Add AI-based performance prediction
* Export reports (PDF/Excel)
* Mobile responsiveness improvements
* Real-time multiplayer quizzes

---

## 📄 License

This project is open-source and free to use.

---

## 🙌 Credits

Developed as an educational project to simplify student performance tracking and quiz management.

---
