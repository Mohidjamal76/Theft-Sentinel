# Theft Sentinel - Frontend

AI-Powered Anti-Theft Surveillance System Frontend built with React + Vite + TailwindCSS

## 🚀 Features

- **Role-Based Access Control**: Admin, Security Incharge, and Guard roles with specific permissions
- **Real-time Dashboard**: Interactive charts and statistics
- **Camera Management**: CRUD operations for surveillance cameras
- **Alert System**: Real-time security alerts with acknowledgment
- **Incident Management**: Track and manage security incidents
- **Person Tracking**: Track individuals across multiple cameras
- **Feedback System**: Submit and manage user feedback
- **Personnel Management**: Manage security personnel
- **Responsive Design**: Mobile-first responsive UI
- **Modern UI/UX**: Clean, professional interface with custom color scheme

## 🎨 Color Scheme

- **Primary Dark**: `#1B3C53`
- **Secondary Blue**: `#234C6A`
- **Accent Blue-Gray**: `#456882`
- **Light Sand**: `#D2C1B6`

## 📦 Tech Stack

- **React 18**: UI library
- **Vite**: Build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Recoil**: State management
- **React Router DOM**: Client-side routing
- **Axios**: HTTP client
- **Recharts**: Data visualization
- **HeroIcons**: Icon library
- **React Hot Toast**: Toast notifications

## 🛠️ Installation

1. **Navigate to the project directory:**
   ```bash
   cd theft-sentinel-frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**
   
   Create a `.env` file in the root directory (it's already created):
   ```
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

4. **Run the development server:**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

## 📁 Project Structure

```
src/
├── api/                    # API service modules
│   ├── axios.js           # Axios configuration with interceptors
│   ├── auth.js            # Authentication APIs
│   ├── cameras.js         # Camera management APIs
│   ├── alerts.js          # Alert system APIs
│   ├── incidents.js       # Incident management APIs
│   ├── tracking.js        # Person tracking APIs
│   ├── surveillance.js    # Surveillance event APIs
│   ├── dashboard.js       # Dashboard statistics APIs
│   ├── mobile.js          # Mobile notification APIs
│   ├── feedback.js        # Feedback system APIs
│   └── personnel.js       # Personnel management APIs
│
├── store/                 # Recoil state management
│   ├── authStore.js       # Authentication state
│   └── uiStore.js         # UI state (sidebar, modals, etc.)
│
├── layouts/               # Layout components
│   ├── AdminLayout.jsx
│   ├── InchargeLayout.jsx
│   └── GuardLayout.jsx
│
├── components/            # Reusable components
│   ├── Navbar.jsx
│   ├── Sidebar.jsx
│   ├── Table.jsx
│   ├── CameraCard.jsx
│   ├── AlertCard.jsx
│   ├── IncidentCard.jsx
│   └── StatsCard.jsx
│
├── pages/                 # Page components
│   ├── auth/
│   │   ├── Login.jsx
│   │   └── Register.jsx
│   ├── dashboard/
│   │   ├── Overview.jsx
│   │   ├── AlertsStats.jsx
│   │   ├── IncidentsStats.jsx
│   │   ├── CamerasStats.jsx
│   │   └── RecentActivity.jsx
│   ├── cameras/
│   │   ├── List.jsx
│   │   ├── Create.jsx
│   │   └── Edit.jsx
│   ├── alerts/
│   │   ├── List.jsx
│   │   └── View.jsx
│   ├── incidents/
│   │   ├── List.jsx
│   │   ├── MyIncidents.jsx
│   │   ├── Unassigned.jsx
│   │   └── View.jsx
│   ├── tracking/
│   │   ├── Records.jsx
│   │   └── PersonPath.jsx
│   ├── feedback/
│   │   ├── List.jsx
│   │   ├── Create.jsx
│   │   └── MyFeedback.jsx
│   └── personnel/
│       ├── List.jsx
│       ├── Create.jsx
│       └── Edit.jsx
│
├── router/
│   └── AppRouter.jsx      # Route definitions with protected routes
│
├── App.jsx                # Main app component
├── main.jsx              # Entry point
└── index.css             # Global styles

```

## 🔐 User Roles & Permissions

### ADMIN
- Full system access
- User management
- Camera CRUD operations
- Personnel management
- Dashboard statistics
- Send notifications
- View all alerts and incidents

### SECURITY_INCHARGE
- View all alerts and incidents
- Assign incidents to guards
- Acknowledge alerts
- View camera status
- Access tracking data

### GUARD
- View assigned incidents only
- Update incident status
- Submit feedback
- View own feedback

## 🔑 Authentication

The app uses JWT-based authentication with automatic token refresh:

- **Access Token**: Stored in localStorage and sent with each request
- **Refresh Token**: Used to obtain new access tokens
- **Auto Logout**: Automatically logs out on authentication failure
- **Protected Routes**: Role-based route protection

## 🎯 Key Features

### Dashboard
- Overview with key metrics
- Interactive charts (Line, Bar, Pie)
- Alert and incident statistics
- Camera status monitoring
- Recent activity feed

### Camera Management
- Grid and table view
- Filter by status, zone
- Real-time status indicators
- CRUD operations (Admin only)

### Alert System
- Real-time alert notifications
- Severity-based color coding
- Acknowledge alerts
- AI detection frame viewing
- Filter by severity and status

### Incident Management
- Status tracking (pending, in_progress, resolved, escalated)
- Assignment to guards
- Status updates by guards
- Unassigned incidents view
- Priority-based organization

### Tracking
- Person path visualization
- Timeline view
- Filter by camera and date range
- Confidence scores

### Feedback System
- Submit feedback
- Category-based organization
- Status tracking
- Admin statistics view

## 🚀 Build for Production

```bash
npm run build
```

The production build will be available in the `dist/` directory.

## 📝 API Integration

All API calls are centralized in the `src/api/` directory. Each module exports functions that return Axios promises:

```javascript
// Example: Using the alerts API
import { listAlerts, acknowledgeAlert } from '../api/alerts';

// Fetch alerts
const response = await listAlerts({ page: 1, severity: 'high' });

// Acknowledge an alert
await acknowledgeAlert(alertId);
```

## 🎨 Styling

TailwindCSS is configured with custom theme colors. Use the predefined colors:

```jsx
<div className="bg-primary text-white">Primary Dark</div>
<div className="bg-secondary">Secondary Blue</div>
<div className="bg-accent">Accent Blue-Gray</div>
<div className="bg-sand">Light Sand</div>
```

## 🔧 Development Tips

1. **Hot Module Replacement**: Vite provides instant HMR for rapid development
2. **State Management**: Use Recoil hooks for accessing global state
3. **Toast Notifications**: Use `toast.success()`, `toast.error()`, etc.
4. **Protected Routes**: Wrap routes with `ProtectedRoute` component
5. **API Errors**: All API errors are automatically handled by Axios interceptors

## 📱 Responsive Design

The app is fully responsive with breakpoints:
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## 🐛 Debugging

- Check browser console for errors
- Verify API base URL in `.env`
- Ensure backend is running on `http://127.0.0.1:8000`
- Check localStorage for tokens (`access_token`, `refresh_token`)

## 📄 License

This project is part of the Theft Sentinel AI-Powered Surveillance System.

## 👥 Support

For issues or questions, please contact the development team.

---

**Built with ❤️ using React + Vite + TailwindCSS**
