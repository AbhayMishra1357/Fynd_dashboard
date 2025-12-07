# 🔥 AI-Powered Review & Sentiment Analysis Dashboard  
### Built with Flask, PostgreSQL, ML Sentiment Model & Render Deployment

Live Application Links  
- **User Dashboard:** https://fynd-dashboard-2.onrender.com/  
- **Admin Dashboard:** https://fynd-dashboard-2.onrender.com/admin  

---

## 📌 Overview

This project is a complete **AI-driven Review Management System** that allows users to submit a review and rating.  
The system processes reviews using a **trained ML Sentiment Analysis model**, generates AI-based responses, and stores the data in a PostgreSQL database hosted on **Render Cloud**.

The **Admin Dashboard** provides analytics such as:  
- Sentiment classification (Positive, Neutral, Negative)  
- Average rating  
- Review list with timestamps  
- Export all data to CSV  
- Auto-refreshing visualization panel  

This project is built using:
- **Flask** (Backend Application Framework)  
- **PostgreSQL (Render Cloud)**  
- **SQLAlchemy ORM**  
- **Flask-Migrate**  
- **Custom ML Sentiment Model (TF–IDF + Logistic Regression)**  
- **Bootstrap 5 Professional UI** (User & Admin Dashboards)  

---

## ✨ Features

### **User Dashboard**
- Submit rating (1–5 stars)  
- Submit text review  
- AI-powered dynamic response based on ML sentiment  
- Clean, modern UI  

### **Admin Dashboard**
- Authentication protected  
- View latest reviews  
- Sentiment classification (positive/negative/neutral)  
- Analytics & charts (Bar charts, sentiment distribution, rating trends)  
- Data export as CSV  
- Auto-refresh via AJAX  
- Professional UI theme  

### **Backend**
- Modular Flask application factory  
- SQLAlchemy models  
- PostgreSQL compatible  
- Robust environment variable configuration  
- Production-ready Gunicorn setup  

### **Machine Learning**
A lightweight text classification pipeline:

- Text Preprocessing  
- TF–IDF Vectorizer  
- Logistic Regression Sentiment Model  
- Custom AI reply generator based on sentiment category  

The model runs instantly (fast inference) and does NOT rely on external APIs.

---

## 🗄️ Project Structure

project-root/
│
├── app.py                       # Main Flask application factory
├── models.py                    # SQLAlchemy ORM models (Submission table)
├── sentiments.py                # ML sentiment analysis module (TF-IDF + Logistic Regression)
├── llm.py                       # Wrapper to generate reply based on ML sentiment output
├── create_tables.py             # One-time script to create tables on Render PostgreSQL
│
├── migrations/                  # Flask-Migrate directory (if using migrations)
│   ├── env.py
│   ├── alembic.ini
│   ├── script.py.mako
│   └── versions/                # Auto-generated migration files
│
├── templates/
│   ├── user.html                # User dashboard UI
│   └── admin.html               # Admin analytics + data export dashboard
│
├── static/
│   ├── css/
│   │   └── styles.css           # Custom dashboard styling (Bootstrap extended)
│   ├── js/
│   │   └── charts.js            # JS for admin charts & analytics
│   └── assets/                  # Any images/icons (optional)
│
├── requirements.txt             # Python dependencies for Render + local
├── Procfile                     # Gunicorn start command for Render deployment
├── README.md                    # Documentation
├── .env.example                 # Example environment variables (safe to commit)
└── .gitignore                   # Git ignore rules


## 🤖 Sentiment Model Details
The ML model is implemented in sentiments.py:
Uses scikit-learn TF–IDF Vectorizer Logistic Regression classifier Trained on sample review dataset Exports model + tokenizer using pickle
Predicts sentiment: "positive" , "neutral" , "negative"

## 📄 License

This is an open, educational project.
Feel free to fork, modify, and enhance.











