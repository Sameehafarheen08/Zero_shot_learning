# Zero-Shot Image Classification & Object Detection

A full-stack web application combining **zero-shot image classification** using CLIP and **real-time object detection** using YOLOv8 for intelligent image analysis without model retraining.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.0-darkgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

### ✅ User Authentication
- User signup with email and password
- Secure login with JWT tokens
- Password hashing with bcrypt
- Session management with sessionStorage
- Admin role detection and redirect

### ✅ Image Classification
- Upload images (JPG, PNG, WebP)
- CLIP zero-shot classification
- Confidence percentage display (0-100%)
- Result storage with timestamps
- Image prediction history

### ✅ Image Comparison
- Upload and classify two images
- Side-by-side comparison
- Confidence visualization with progress bars
- Smart comparison logic (same/different class)
- Beautiful responsive UI

### ✅ Ask AI Module
- Ask questions about classified images
- Intelligent answer generation
- Multiple question pattern recognition
- ChatGPT integration ready
- Context-aware responses

### ✅ Feedback System
- User feedback submission
- Success message confirmation
- Admin feedback management
- Delete feedback entries
- Email tracking

### ✅ Admin Dashboard
- Dashboard with statistics
- User management (view, delete)
- Feedback management (view, delete)
- Prediction history with pagination
- Beautiful gradient UI

### ✅ User Profile
- User information display
- Prediction history
- Statistics and analytics
- Connected to backend API

---

## 🏗️ Architecture

### **Frontend** (Vanilla JavaScript + HTML/CSS)
```
frontend/
├── Authentication Pages
│   ├── signup.html          # User registration
│   ├── login.html           # User/Admin login
│   └── forgot-password.html # Password reset
├── User Pages
│   ├── index.html           # Home page
│   ├── upload.html          # Image classification
│   ├── result.html          # Prediction results
│   ├── compare.html         # Dual image comparison
│   ├── Ask.html             # Ask AI module
│   ├── feedback.html        # Feedback submission
│   └── profile.html         # User profile & history
├── Admin Pages
│   ├── admin_panel.html     # Admin dashboard
│   ├── admin_users.html     # User management
│   ├── admin_feedback.html  # Feedback management
│   └── admin_history.html   # Prediction history
├── Styling
│   ├── style.css            # Main stylesheet
│   └── admin.css            # Admin styling (900+ lines)
└── Assets
    └── sampleimage/         # Background images
```

### **Backend** (Flask + Python)
```
backend/
├── run.py                   # Server entry point
├── requirements.txt         # Python dependencies
├── label.txt               # 160+ classification labels
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── db.py               # MySQL connection
│   ├── clip_model.py       # CLIP classifier
│   └── utils.py            # Helper functions
└── routes/
    ├── auth_routes.py      # Signup, login, logout
    ├── prediction_routes.py # Image classification
    ├── user_routes.py      # Profile, feedback, ask AI
    └── admin_routes.py     # Admin functions
```

### **Database** (MySQL)
```
Database: zero_shot_classifier
├── users
│   ├── id (INT, PRIMARY KEY)
│   ├── email (VARCHAR, UNIQUE)
│   ├── password_hash (VARCHAR)
│   ├── created_at (TIMESTAMP)
│   └── updated_at (TIMESTAMP)
├── predictions
│   ├── id (INT, PRIMARY KEY)
│   ├── user_id (INT, FOREIGN KEY)
│   ├── image_path (VARCHAR)
│   ├── classification_result (VARCHAR)
│   ├── confidence (FLOAT)
│   └── timestamp (TIMESTAMP)
└── feedback
    ├── id (INT, PRIMARY KEY)
    ├── user_id (INT, FOREIGN KEY)
    ├── message (TEXT)
    └── timestamp (TIMESTAMP)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- MySQL 5.7 or higher
- pip (Python package manager)

### Installation

1. **Clone or Extract the Project**
   ```bash
   cd zero_shot_full_html_frontend
   ```

2. **Install Python Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Initialize Database**
   ```bash
   mysql -u root -p < database/schema.sql
   ```
   Enter your MySQL password when prompted.

4. **Configure Database Connection**
   
   Edit `backend/app/db.py` and update:
   ```python
   config = {
       'host': 'localhost',
       'user': 'root',
       'password': 'your_password',  # ← Change this
       'database': 'zero_shot_classifier',
   }
   ```

5. **Start the Backend Server**
   ```bash
   python run.py
   ```
   
   Expected output:
   ```
   * Running on http://127.0.0.1:5000
   * Debug mode: on
   ```

6. **Open the Frontend**
   
   Open in browser:
   ```
   file:///c:/Users/TOSHIBA/Documents/zero_shot_full_html_frontend/frontend/index.html
   ```
   
   Or serve with HTTP server:
   ```bash
   cd frontend
   python -m http.server 8000
   ```
   Then open: `http://localhost:8000`

---

## 🧪 Testing

### Test Credentials

**Regular User**:
- Email: `testuser@example.com`
- Password: `Test@1234`

**Admin User**:
- Email: `admin123@gmail.com`
- Password: `admin123`

### Complete Flow Test

1. **Signup** → Enter email and password
2. **Login** → Use credentials to login
3. **Classify Image** → Upload image, see CLIP classification
4. **Compare Images** → Upload 2 images, see comparison
5. **Ask AI** → Ask question about classification
6. **Submit Feedback** → Submit feedback (see success message)
7. **View Profile** → See your predictions
8. **Admin Access** → Login as admin to view dashboard

See `QUICK_START.md` for detailed test cases.

---

## 🔌 API Endpoints

### Authentication
```
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
```

### Predictions
```
POST /api/predictions          # Upload & classify image
GET /api/predictions/{id}      # Get single prediction
GET /api/predictions           # List predictions (paginated)
DELETE /api/predictions/{id}   # Delete prediction
```

### User
```
GET /api/user/{id}                    # Get user profile
GET /api/user/{id}/predictions        # Get user's predictions
POST /api/feedback                    # Submit feedback
GET /api/feedbacks                    # Get all feedbacks (admin)
DELETE /api/feedbacks/{id}            # Delete feedback (admin)
POST /api/ask                         # Ask AI question
POST /api/forgot-password             # Password reset
```

### Admin
```
GET /api/admin/stats           # Get dashboard statistics
GET /api/admin/users           # List all users
DELETE /api/admin/users/{id}   # Delete user
GET /api/admin/history         # Get prediction history
GET /api/admin/feedbacks       # Get all feedbacks
```

See `FINAL_VERIFICATION.md` for detailed API documentation.

---

## 📊 Project Statistics

| Metric | Count |
|--------|-------|
| Frontend Pages | 13 |
| Backend Routes | 4 files |
| API Endpoints | 15+ |
| Database Tables | 3 |
| CSS Lines | 1000+ |
| Python Code Lines | 2000+ |
| Documentation | 1000+ lines |

---

## 🔐 Security Features

✅ **Authentication**
- bcrypt password hashing (10 salt rounds)
- JWT token generation and verification
- Session token stored in sessionStorage

✅ **Database**
- Parameterized queries (SQL injection prevention)
- Connection pooling
- Foreign key relationships
- CASCADE delete for referential integrity

✅ **API**
- CORS protection
- Authorization header validation
- Proper HTTP status codes
- Error handling without data leakage

✅ **Frontend**
- Form validation before submission
- Input sanitization
- Session checks before rendering

---

## 🎯 Key Implementation Details

### Image Classification Flow
1. User uploads image via `upload.html`
2. Backend receives image and user_id
3. CLIP model classifies image against 160+ labels
4. Confidence score calculated (0.0-1.0)
5. Result stored in MySQL predictions table
6. Response returned with label and confidence
7. Frontend displays result with confidence percentage

### Admin Authorization
1. User logs in with email
2. Backend checks if email === "admin123@gmail.com"
3. If admin, sets `is_admin: true` in JWT token
4. Frontend checks `is_admin` flag
5. Admin redirected to `admin_panel.html`
6. Regular users redirected to `index.html`

### Ask AI Response Generation
1. User enters label and question
2. Backend receives both via `/api/ask`
3. Question analyzed by keyword matching
4. Intelligent response generated based on question type
5. Response returned with source attribution
6. Frontend displays response in modal

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :5000

# Kill process using port 5000 or change port in run.py
```

### MySQL Connection Error
```bash
# Check MySQL is running
# Verify credentials in backend/app/db.py
# Ensure database exists:
mysql -u root -p -e "SHOW DATABASES LIKE 'zero_shot%';"
```

### CLIP Model Download
- First run downloads ~350MB model (~2-5 minutes)
- Subsequent runs use cached model (fast)
- For GPU acceleration, change device in `app/clip_model.py`

### Module Not Found
```bash
# Reinstall dependencies
pip install -r backend/requirements.txt --upgrade
```

See `QUICK_START.md` for more troubleshooting tips.

---

## 📚 Documentation

- **QUICK_START.md** - Setup and testing guide
- **FINAL_VERIFICATION.md** - Complete verification checklist
- **IMPLEMENTATION_COMPLETE.md** - Detailed implementation summary
- **PROJECT_STRUCTURE.md** - File organization
- **SETUP_GUIDE.md** - Installation instructions

---

## 🌐 Technology Stack

**Frontend**:
- HTML5
- CSS3 (with gradients and animations)
- Vanilla JavaScript (ES6+)
- Fetch API

**Backend**:
- Python 3.8+
- Flask 2.3.0
- Flask-CORS
- MySQL Connector Python
- PyJWT (JSON Web Tokens)
- bcrypt (password hashing)

**AI/ML**:
- CLIP (Contrastive Language-Image Pre-training)
- PyTorch
- Pillow (image processing)

**Database**:
- MySQL 5.7 or 8.0

---

## 📝 Default Admin Credentials

**Email**: `admin123@gmail.com`
**Password**: `admin123`

⚠️ **Security Note**: Change these credentials in production!

---

## 🎓 Learn More About CLIP

CLIP is a neural network trained on a wide variety of (image, text) pairs from the internet using a contrastive loss. It can recognize objects in images by text descriptions without being trained on a specific classification dataset.

- [OpenAI CLIP GitHub](https://github.com/openai/CLIP)
- [CLIP Paper](https://arxiv.org/abs/2103.14030)

---

## 🤝 Contributing

This is a complete implementation. For improvements:
1. Test thoroughly
2. Document changes
3. Ensure backward compatibility
4. Update relevant documentation

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## 📞 Support

**Having Issues?**

1. Check `QUICK_START.md` troubleshooting section
2. Verify all dependencies installed: `pip list`
3. Check MySQL is running and configured
4. Review browser console (F12) for frontend errors
5. Review backend console for error messages

---

## ✨ Features Showcase

### 🖼️ Image Classification
Upload any image and CLIP instantly classifies it without retraining!

### 🔄 Image Comparison
Compare two images side-by-side to see similarities and differences.

### 🧠 Ask AI
Ask questions about your classifications and get intelligent answers.

### 📊 Admin Dashboard
Comprehensive admin panel to manage users, feedbacks, and predictions.

### 👤 User Profiles
Track your classification history with timestamps and confidence scores.

### 💬 Feedback System
Submit feedback and let admins review it.

---

## 🎉 Ready to Use!

**Installation**: ~5 minutes  
**Setup**: ~2 minutes  
**First classification**: ~10 seconds (after CLIP downloads model)

```bash
# Quick start commands:
pip install -r backend/requirements.txt
mysql -u root -p < database/schema.sql
python backend/run.py
# Open frontend/index.html in browser
```

**Enjoy zero-shot image classification! 🚀**

---

**Last Updated**: November 17, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
