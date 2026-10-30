# 🧠 EmoLearn v3 — Advanced Emotion-Based Learning Platform

## ⚡ Quick Start
```bash
./start.sh          # Linux/Mac
start.bat           # Windows

# Open in browser
http://localhost:5000            # User Panel
http://localhost:5000/admin-dashboard.html  # Admin Panel
```

## 🔐 Credentials
| Role  | Email           | Password |
|-------|-----------------|----------|
| Admin | admin@gmail.com | admin123 |
| Demo  | Register yourself | —      |

---

## 🆕 Advanced Features (v3)

### 🏆 Achievements & Badges
- 7 achievements (Common → Legendary)
- Auto-unlocked when conditions met (XP, streak, activities, emotions)
- Animated popup when earned + XP bonus
- Dedicated Achievements page with locked/unlocked state

### 📅 Daily Streak & Notifications
- Streak auto-updates on every emotion log
- Browser Push Notification support (with permission)
- Configurable daily reminder time in Settings
- Streak reminder on return visits

### 👥 Social / Leaderboard
- Top 20 learners ranked by XP
- Shows medals (🥇🥈🥉) and streak
- Highlighted "You" row
- Public/private profile toggle in Settings

### 📈 Mood Trend Prediction
- Analyzes last 14 days of emotion logs
- Predicts tomorrow's likely mood
- Shows improving / stable / declining trend
- Weekly activity bar chart
- Personalized improvement tips

### 🎯 Personalized Learning Path
- 3-step path: Warm-Up → Core Practice → Challenge
- Based on your dominant recent emotion
- Shows activities you haven't done yet
- XP progress to next level

### 🔔 Push Notifications
- Browser Notification API
- Daily reminder at configurable time
- Achievement unlock alerts
- Streak reminder on return

### 📤 Export Report
- **JSON export** — full data (emotions, activities, achievements, profile)
- **CSV export** — spreadsheet-friendly with 3 sections

### ⚙️ User Settings & Preferences
- Toggle notifications on/off
- Set daily reminder time
- Session duration preference (15–60 min)
- Show/hide mood prediction & learning path
- Public/private leaderboard toggle
- Avatar emoji picker (9 options)

### 🎵 App Deep Links (Music/Video Player)
After emotion → activity recommendation:
- **Music activities** → Spotify, YouTube Music, Apple Music, JioSaavn buttons
- **Video activities** → YouTube deep link
- **Meditation** → Headspace, Calm app links
- **Exercise** → YouTube Fitness
- All open native app or browser

---

## 🗄 Backend Structure
```
emolearn-backend/
├── app.py
├── database.py
├── models.py
└── routes/
    ├── auth.py       Register, Login, Profile
    ├── emotions.py   Save (+ streak update), History, Stats, Chart
    ├── activity.py   Recommendations, Choose, Complete (+ achievements check)
    ├── admin.py      Full CRUD + Manual Emotion
    ├── content.py    Public content listing
    └── advanced.py   ← NEW
        ├── /api/achievements          GET  — list with earned status
        ├── /api/achievements/check    POST — auto-unlock check
        ├── /api/settings              GET/PUT — user preferences
        ├── /api/mood/prediction       GET  — 14-day trend analysis
        ├── /api/learning-path         GET  — personalized 3-step path
        ├── /api/social/leaderboard    GET  — top 20 by XP
        ├── /api/social/profile/<id>   GET  — public profile
        ├── /api/export/json           GET  — full JSON download
        ├── /api/export/csv            GET  — CSV download
        ├── /api/activity/deep-link    POST — platform links for activity
        ├── /api/streak/update         POST — manual streak update
        └── /api/notifications/subscribe POST — store notif preference
```
