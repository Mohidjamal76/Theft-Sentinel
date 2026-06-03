# 🚀 Quick Start Guide - Theft Sentinel Frontend

## Prerequisites
- Node.js 16+ installed
- npm or yarn package manager
- Backend API running on `http://127.0.0.1:8000`

## Installation Steps

### 1. Navigate to Project Directory
```bash
cd theft-sentinel-frontend
```

### 2. Install Dependencies
```bash
npm install
```

This will install all required packages:
- React + React DOM
- Vite
- TailwindCSS
- Recoil (State Management)
- React Router DOM
- Axios
- Recharts
- HeroIcons
- React Hot Toast

### 3. Environment Configuration
The `.env` file is already configured with:
```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If your backend runs on a different URL, update this file.

### 4. Start Development Server
```bash
npm run dev
```

The application will start at: **http://localhost:3000**

## 🎯 Default Login Credentials

After registering or using backend-created users, you can login with:

**Admin User:**
- Username: `admin`
- Password: (as configured in backend)
- Role: ADMIN

**Security Incharge:**
- Username: `incharge`
- Password: (as configured in backend)
- Role: SECURITY_INCHARGE

**Guard:**
- Username: `guard`
- Password: (as configured in backend)
- Role: GUARD

## 📱 First Time Usage

1. **Register a new account** at `/register`
2. **Login** at `/login`
3. You'll be redirected to the **Dashboard**
4. Explore different sections based on your role

## 🔑 Role-Based Access

### ADMIN can access:
- ✅ Dashboard & Statistics
- ✅ Camera Management (CRUD)
- ✅ All Alerts & Incidents
- ✅ Personnel Management
- ✅ Tracking Data
- ✅ All Feedback

### SECURITY_INCHARGE can access:
- ✅ Dashboard Overview
- ✅ View All Alerts (Acknowledge)
- ✅ View All Incidents (Assign to Guards)
- ✅ Tracking Data
- ✅ Camera Status (View Only)

### GUARD can access:
- ✅ My Assigned Incidents
- ✅ Update Incident Status
- ✅ Submit Feedback
- ✅ View My Feedback

## 🎨 Key Features

### Dashboard
- Real-time statistics
- Interactive charts
- Quick action links
- System health monitoring

### Camera Management
- Add/Edit/Delete cameras
- View camera status
- Filter by zone and status
- Grid & Table views

### Alert System
- View active alerts
- Acknowledge alerts
- Filter by severity
- View AI detection frames

### Incident Management
- Create and track incidents
- Assign to guards
- Update status and resolution
- Priority-based organization

### Tracking
- View person tracking records
- Track person path across cameras
- Filter by date and camera

### Feedback
- Submit feedback
- Track feedback status
- Admin view all feedback

## 🛠️ Development Commands

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📊 Tech Stack Overview

- **React 18**: Modern UI library
- **Vite**: Fast build tool & dev server
- **TailwindCSS**: Utility-first CSS
- **Recoil**: Simple state management
- **React Router**: Client-side routing
- **Axios**: HTTP client with interceptors
- **Recharts**: Beautiful charts & graphs
- **HeroIcons**: Modern icon library

## 🎨 Color Palette

| Color | Hex Code | Usage |
|-------|----------|-------|
| Primary Dark | `#1B3C53` | Headers, primary buttons |
| Secondary Blue | `#234C6A` | Sidebar, secondary elements |
| Accent Blue-Gray | `#456882` | Hover states, accents |
| Light Sand | `#D2C1B6` | Backgrounds, highlights |

## 🔧 Common Issues & Solutions

### Issue: API Connection Failed
**Solution:** Ensure backend is running on `http://127.0.0.1:8000`

### Issue: Login Token Expired
**Solution:** The app auto-refreshes tokens. If it fails, logout and login again.

### Issue: Missing Pages/Routes
**Solution:** Clear browser cache and restart dev server.

### Issue: Styles Not Loading
**Solution:** Restart dev server. TailwindCSS will rebuild.

## 📁 Important Files

- `src/App.jsx` - Main application component
- `src/router/AppRouter.jsx` - All route definitions
- `src/api/axios.js` - Axios configuration with JWT interceptors
- `src/store/authStore.js` - Authentication state management
- `tailwind.config.js` - TailwindCSS theme customization

## 🚀 Production Deployment

1. Build the project:
```bash
npm run build
```

2. The `dist/` folder contains production-ready files

3. Deploy to:
   - Vercel
   - Netlify
   - AWS S3 + CloudFront
   - Any static hosting service

## 📞 Need Help?

- Check the main `README.md` for detailed documentation
- Review the code comments in each file
- Check browser console for error messages
- Ensure backend API is running and accessible

## ✅ Verification Checklist

Before starting development:
- [ ] Node.js 16+ installed
- [ ] Dependencies installed (`npm install`)
- [ ] Backend API running
- [ ] `.env` file configured
- [ ] Dev server started (`npm run dev`)
- [ ] Browser opened at `http://localhost:3000`
- [ ] Able to login/register

---

**🎉 You're all set! Happy coding!**

For more detailed information, refer to the main README.md file.

