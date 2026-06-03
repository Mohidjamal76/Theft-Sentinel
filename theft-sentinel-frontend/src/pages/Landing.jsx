

import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { superAdminExists } from '../api/tenancy';
import { 
  CpuChipIcon, 
  VideoCameraIcon, 
  ChartBarIcon, 
  ShieldCheckIcon,
  BoltIcon,
  EyeIcon,
  BellAlertIcon,
  UserGroupIcon,
  AcademicCapIcon,
  BuildingOfficeIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

const Landing = () => {
  const navigate = useNavigate();
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstallPopup, setShowInstallPopup] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [showCreateSuperAdmin, setShowCreateSuperAdmin] = useState(false);

  useEffect(() => {
    // Check if app is already installed (standalone mode)
    const isStandaloneMode = window.matchMedia('(display-mode: standalone)').matches || 
                            window.navigator.standalone || 
                            document.referrer.includes('android-app://');
    setIsStandalone(isStandaloneMode);

    // Check if iOS
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    setIsIOS(iOS);

    // Check if already shown in this session
    const hasShownPopup = sessionStorage.getItem('installPopupShown');
    
    // Don't show if already installed or already shown
    if (isStandaloneMode || hasShownPopup) {
      return;
    }

    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      // Show popup after a short delay when app mounts
      setTimeout(() => {
        setShowInstallPopup(true);
        sessionStorage.setItem('installPopupShown', 'true');
      }, 100);
    };

    // Detect mobile device
    const mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    setIsMobile(mobile);

    // For mobile browsers (especially iOS), show popup even without beforeinstallprompt
    if (iOS && !hasShownPopup) {
      setTimeout(() => {
        setShowInstallPopup(true);
        sessionStorage.setItem('installPopupShown', 'true');
      }, 100);
    }

    // For Android Chrome, wait for beforeinstallprompt
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Fallback for Android mobile: show popup after 5 seconds if beforeinstallprompt hasn't fired
    let fallbackTimer;
    if (mobile && !iOS && !hasShownPopup) {
      fallbackTimer = setTimeout(() => {
        setShowInstallPopup(true);
        sessionStorage.setItem('installPopupShown', 'true');
      }, 100);
    }

    return () => {
      if (fallbackTimer) clearTimeout(fallbackTimer);
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await superAdminExists();
        setShowCreateSuperAdmin(!res.data?.exists);
      } catch {
        setShowCreateSuperAdmin(false);
      }
    };
    check();
  }, []);

  const handleInstall = async () => {
    if (deferredPrompt) {
      // Android Chrome - use native prompt
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setShowInstallPopup(false);
      }
      setDeferredPrompt(null);
    } else if (isIOS) {
      // iOS - instructions are shown in the popup
      setShowInstallPopup(false);
    } else {
      // Desktop - try to trigger install
      setShowInstallPopup(false);
    }
  };

  const handleClosePopup = () => {
    setShowInstallPopup(false);
  };

  return (
    <>
      {/* Custom Keyframes for Animations */}
      <style>{`
        @keyframes scan {
          0% { top: 0%; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
        .animate-scan-line {
          animation: scan 3s linear infinite;
        }
      `}</style>

      {/* Install App Popup Modal */}
      {showInstallPopup && (deferredPrompt || isIOS || isMobile) && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="glass-strong rounded-2xl p-6 sm:p-8 max-w-md w-full border border-white/10 shadow-2xl shadow-ai-blue/20 relative animate-slideUp">
            {/* Close Button */}
            <button
              onClick={handleClosePopup}
              className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>

            {/* Icon */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-ai-blue/20 rounded-full flex items-center justify-center">
                <ShieldCheckIcon className="h-8 w-8 text-ai-blue" />
              </div>
            </div>

            {/* Content */}
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-white mb-2">
                Install Theft Sentinel
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                Install our app for a better experience. Get quick access, offline support, and faster performance.
              </p>
            </div>

            {/* Buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleInstall}
                className="flex-1 px-6 py-3 bg-ai-blue text-dark-bg font-bold rounded-lg hover:bg-cyan-400 transition-all duration-300 shadow-[0_0_20px_rgba(0,212,255,0.3)] hover:shadow-[0_0_35px_rgba(0,212,255,0.6)] transform hover:scale-105"
              >
                Install Now
              </button>
              <button
                onClick={handleClosePopup}
                className="flex-1 px-6 py-3 glass border border-white/20 text-white font-semibold rounded-lg hover:bg-white/5 hover:border-ai-blue transition-all duration-300"
              >
                Maybe Later
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="min-h-screen bg-dark-bg text-dark-text-primary selection:bg-ai-blue selection:text-dark-bg overflow-x-hidden">
        
        {/* Navbar (Added for professional look) */}
        <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-2">
                <ShieldCheckIcon className="h-8 w-8 text-ai-blue" />
                <span className="font-bold text-xl tracking-tight">Theft<span className="text-ai-blue">Sentinel</span></span>
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="flex items-center gap-2 sm:gap-3">
                  {showCreateSuperAdmin && (
                    <button
                      onClick={() => navigate('/create-super-admin')}
                      className="hidden sm:inline-flex px-4 py-2 rounded-md glass border border-white/20 text-white hover:border-ai-blue transition-all duration-300 font-medium text-sm"
                    >
                      Create Super Admin
                    </button>
                  )}
                  <button
                    onClick={() => navigate('/register-branch')}
                    className="px-3 sm:px-4 py-2 rounded-md glass border border-ai-blue/40 text-ai-blue hover:bg-ai-blue hover:text-dark-bg transition-all duration-300 font-medium text-xs sm:text-sm"
                  >
                    Register Branch
                  </button>
                  <button 
                    onClick={() => navigate('/login')}
                    className="px-3 sm:px-4 py-2 rounded-md bg-ai-blue/10 text-ai-blue hover:bg-ai-blue hover:text-dark-bg transition-all duration-300 font-medium text-xs sm:text-sm"
                  >
                    Login
                  </button>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
          {/* Animated Background Particles */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {[...Array(30)].map((_, i) => (
              <div
                key={i}
                className="absolute w-1.5 h-1.5 bg-ai-blue rounded-full opacity-40 blur-[1px]"
                style={{
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                  animation: `particle ${10 + Math.random() * 15}s linear infinite`,
                  animationDelay: `${Math.random() * 5}s`,
                }}
              />
            ))}
            {/* Background Glows */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-ai-blue/20 rounded-full blur-[120px] animate-pulse-slow" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
          </div>

          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-b from-dark-bg via-dark-bg/90 to-dark-bg pointer-events-none" />

          {/* Content */}
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
            <div className="text-center">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-ai-blue/30 bg-dark-card/50 backdrop-blur-md mb-8 animate-fadeIn">
                <span className="w-2 h-2 rounded-full bg-ai-blue animate-pulse"></span>
                <span className="text-xs font-mono text-ai-blue font-semibold tracking-wide uppercase">Air University FYP 2025</span>
              </div>

              {/* Main Heading */}
              <div className="mb-10 animate-fadeIn" style={{ animationDelay: '0.1s' }}>
                <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight drop-shadow-2xl">
                  <span className="text-gradient-ai bg-clip-text text-transparent bg-gradient-to-r from-ai-blue to-cyan-400">Theft Sentinel</span>
                </h1>
                <p className="text-2xl md:text-3xl text-white font-light mb-4">
                  AI-Powered <span className="text-ai-blue font-medium">Intelligent Surveillance</span>
                </p>
                <p className="text-lg text-gray-400 max-w-3xl mx-auto leading-relaxed">
                  Automating retail security with advanced Computer Vision. Real-time threat detection, multi-camera tracking, and proactive loss prevention powered by Deep Learning.
                </p>
              </div>

              {/* AI Video Mock Container */}
              <div className="mt-12 mb-16 animate-slideUp" style={{ animationDelay: '0.3s' }}>
                <div className="relative max-w-5xl mx-auto group">
                  {/* Video Container with Glassmorphism */}
                  <div className="glass-strong rounded-2xl p-1.5 shadow-2xl border border-white/10 shadow-ai-blue/10">
                    <div className="relative aspect-video bg-gradient-to-br from-dark-card to-black rounded-xl overflow-hidden">
                      
                      {/* Simulated Scan Line */}
                      <div className="absolute inset-0 z-20 pointer-events-none opacity-20">
                        <div className="w-full h-1 bg-ai-blue shadow-[0_0_15px_rgba(0,212,255,0.8)] animate-scan-line"></div>
                      </div>

                      {/* Top UI Bar */}
                      <div className="absolute top-0 left-0 w-full h-10 bg-black/50 backdrop-blur-sm z-30 flex justify-between items-center px-4 border-b border-white/10">
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></div>
                          <span className="text-xs font-mono text-gray-300">LIVE FEED • CAM_01</span>
                        </div>
                        <div className="flex gap-4 text-[10px] font-mono text-ai-blue">
                          <span>FPS: 30</span>
                          <span>LATENCY: 12ms</span>
                          <span>STATUS: ACTIVE</span>
                        </div>
                      </div>

                      {/* Mock AI Detection Overlay */}
                      <div className="absolute inset-0 flex items-center justify-center z-10">
                        {/* Simulated bounding boxes */}
                        <div className="absolute top-1/3 left-1/4 w-36 h-56 border-2 border-ai-blue/60 rounded bg-ai-blue/5 backdrop-blur-[1px] shadow-[0_0_15px_rgba(0,212,255,0.2)] transition-all duration-500 group-hover:border-ai-blue">
                          <div className="absolute -top-7 left-0 bg-dark-bg/90 border border-ai-blue/50 px-2 py-0.5 rounded text-xs font-mono font-bold text-ai-blue flex items-center gap-1">
                            <CpuChipIcon className="w-3 h-3" /> PERSON 98%
                          </div>
                        </div>
                        <div className="absolute top-1/4 right-1/4 w-28 h-40 border-2 border-status-error/80 rounded bg-status-error/10 shadow-[0_0_20px_rgba(239,68,68,0.4)] animate-pulse">
                          <div className="absolute -top-7 left-0 bg-dark-bg/90 border border-status-error/50 px-2 py-0.5 rounded text-xs font-mono font-bold text-status-error flex items-center gap-1">
                            <BoltIcon className="w-3 h-3" /> ALERT
                          </div>
                          {/* Corner markers */}
                          <div className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-status-error"></div>
                          <div className="absolute -top-1 -right-1 w-2 h-2 border-t-2 border-r-2 border-status-error"></div>
                          <div className="absolute -bottom-1 -left-1 w-2 h-2 border-b-2 border-l-2 border-status-error"></div>
                          <div className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-status-error"></div>
                        </div>
                        
                        {/* Center AI Processing Indicator */}
                        <div className="relative z-0 opacity-20 group-hover:opacity-40 transition-opacity duration-700">
                          <div className="w-40 h-40 border border-ai-blue/30 rounded-full flex items-center justify-center relative">
                            <div className="absolute inset-0 border-t-2 border-ai-blue rounded-full animate-spin"></div>
                            <CpuChipIcon className="h-16 w-16 text-ai-blue" />
                          </div>
                        </div>
                      </div>

                      {/* Grid Pattern Overlay */}
                      <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
                        backgroundImage: 'radial-gradient(rgba(0, 217, 255, 0.5) 1px, transparent 1px)',
                        backgroundSize: '30px 30px',
                      }} />
                    </div>
                  </div>
                  
                  {/* Floating Stats Card */}
                  <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 glass px-8 py-3 rounded-full border border-white/10 flex items-center gap-6 shadow-2xl animate-fadeIn" style={{ animationDelay: '0.6s' }}>
                    <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                      <i className="fa-solid fa-shield-halved text-ai-blue"></i> SYSTEM ARMED
                    </div>
                    <div className="h-4 w-px bg-white/10"></div>
                    <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                      <i className="fa-solid fa-camera text-ai-blue"></i> CAMERAS: 12
                    </div>
                  </div>
                </div>
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-5 justify-center items-center animate-fadeIn pt-8" style={{ animationDelay: '0.5s' }}>
                <button
                  onClick={() => navigate('/login')}
                  className="group relative px-10 py-4 bg-ai-blue text-dark-bg font-bold rounded-lg overflow-hidden
                           hover:bg-cyan-400 transition-all duration-300 shadow-[0_0_20px_rgba(0,212,255,0.3)] hover:shadow-[0_0_35px_rgba(0,212,255,0.6)]
                           transform hover:-translate-y-1"
                >
                  <span className="relative z-10 flex items-center gap-2">
                    Sign In <ShieldCheckIcon className="w-4 h-4" />
                  </span>
                  <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                </button>
                
                <button
                  onClick={() => navigate('/login')}
                  className="group relative px-10 py-4 glass border border-white/20 text-white font-semibold rounded-lg
                           hover:bg-white/5 hover:border-ai-blue transition-all duration-300
                           transform hover:-translate-y-1"
                >
                  <span className="flex items-center gap-2">
                    <EyeIcon className="w-4 h-4" /> View Demo
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* Scroll Indicator */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-float z-20">
            <div className="w-6 h-10 border-2 border-white/20 rounded-full flex justify-center">
              <div className="w-1 h-3 bg-white rounded-full mt-2 animate-pulse" />
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="relative py-24 bg-dark-surface border-t border-white/5">
          {/* Decorative Elements */}
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] [mask-image:linear-gradient(to_bottom,white,transparent)]"></div>
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-20">
              <h2 className="text-4xl md:text-5xl font-bold mb-6">
                Enterprise-Grade <span className="text-gradient-ai">AI Surveillance</span>
              </h2>
              <p className="text-xl text-gray-400 max-w-3xl mx-auto">
                Leveraging YOLO and OSNet for comprehensive security monitoring and theft prevention in retail environments.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="glass rounded-2xl p-8 hover:border-ai-blue/50 transition-all duration-300 transform hover:-translate-y-2 group relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-ai-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10">
                  <div className="w-14 h-14 bg-ai-blue/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-glow-ai">
                    <BoltIcon className="h-7 w-7 text-ai-blue" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">Real-Time Detection</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">
                    Instant AI-powered threat detection using YOLO models with sub-second response times to catch theft as it happens.
                  </p>
                </div>
              </div>

              {/* Feature 2 */}
              <div className="glass rounded-2xl p-8 hover:border-ai-blue/50 transition-all duration-300 transform hover:-translate-y-2 group relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-ai-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10">
                  <div className="w-14 h-14 bg-ai-blue/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-glow-ai">
                    <ChartBarIcon className="h-7 w-7 text-ai-blue" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">Historical Analytics</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">
                    Comprehensive reporting and trend analysis for data-driven security decisions and performance auditing.
                  </p>
                </div>
              </div>

              {/* Feature 3 */}
              <div className="glass rounded-2xl p-8 hover:border-ai-blue/50 transition-all duration-300 transform hover:-translate-y-2 group relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-ai-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10">
                  <div className="w-14 h-14 bg-ai-blue/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-glow-ai">
                    <BellAlertIcon className="h-7 w-7 text-ai-blue" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">Automated Alerts</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">
                    Intelligent alert system with Twilio integration for SMS/Email notifications and instant security dispatch.
                  </p>
                </div>
              </div>

              {/* Feature 4 */}
              <div className="glass rounded-2xl p-8 hover:border-ai-blue/50 transition-all duration-300 transform hover:-translate-y-2 group relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-ai-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10">
                  <div className="w-14 h-14 bg-ai-blue/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-glow-ai">
                    <VideoCameraIcon className="h-7 w-7 text-ai-blue" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">Multi-Camera Tracking</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">
                    OSNet-powered Cross-Camera Handoff ensures seamless tracking of suspects across multiple store zones.
                  </p>
                </div>
              </div>

              {/* Feature 5 */}
              <div className="glass rounded-2xl p-8 hover:border-ai-blue/50 transition-all duration-300 transform hover:-translate-y-2 group relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-ai-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10">
                  <div className="w-14 h-14 bg-ai-blue/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-glow-ai">
                    <CpuChipIcon className="h-7 w-7 text-ai-blue" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">AI-Powered Analysis</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">
                    Deep learning models for behavior analysis and anomaly detection, reducing false positives over time.
                  </p>
                </div>
              </div>

              {/* Feature 6 */}
              <div className="glass rounded-2xl p-8 hover:border-ai-blue/50 transition-all duration-300 transform hover:-translate-y-2 group relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-ai-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative z-10">
                  <div className="w-14 h-14 bg-ai-blue/20 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-glow-ai">
                    <ShieldCheckIcon className="h-7 w-7 text-ai-blue" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">Secure & Reliable</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">
                    Enterprise-grade security with role-based access control (RBAC), audit logging, and encrypted communications.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Team Section (Added from Document) */}
        <section className="py-24 bg-dark-bg relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-ai-blue/5 rounded-full blur-[100px] pointer-events-none"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-16">
              <UserGroupIcon className="h-12 w-12 text-ai-blue mx-auto mb-4 opacity-80" />
              <h2 className="text-3xl md:text-4xl font-bold mb-4">The Development Team</h2>
              <p className="text-gray-400">Department of Computer Science, Air University Islamabad</p>
            </div>

            {/* Team Members Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-16">
              {/* Member 1 */}
              <div className="glass p-8 rounded-2xl text-center border-t-4 border-ai-blue hover:bg-white/5 transition-all duration-300">
                <div className="w-20 h-20 bg-gradient-to-br from-ai-blue to-blue-600 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold text-white shadow-lg shadow-ai-blue/20">
                  MJ
                </div>
                <h3 className="text-xl font-bold text-white mb-1">Mohid Jamal</h3>
                <p className="text-ai-blue font-mono text-sm mb-4">221363</p>
                
              </div>

              {/* Member 2 */}
              <div className="glass p-8 rounded-2xl text-center border-t-4 border-ai-blue hover:bg-white/5 transition-all duration-300">
                <div className="w-20 h-20 bg-gradient-to-br from-ai-blue to-blue-600 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold text-white shadow-lg shadow-ai-blue/20">
                  MAK
                </div>
                <h3 className="text-xl font-bold text-white mb-1">Muhammad Ali Khawaja</h3>
                <p className="text-ai-blue font-mono text-sm mb-4">221333</p>
                
              </div>

              {/* Member 3 */}
              <div className="glass p-8 rounded-2xl text-center border-t-4 border-ai-blue hover:bg-white/5 transition-all duration-300">
                <div className="w-20 h-20 bg-gradient-to-br from-ai-blue to-blue-600 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold text-white shadow-lg shadow-ai-blue/20">
                  MHM
                </div>
                <h3 className="text-xl font-bold text-white mb-1">Muhammad Hassaan Masood</h3>
                <p className="text-ai-blue font-mono text-sm mb-4">221321</p>
                
              </div>
            </div>
            
          </div>
        </section>

        {/* Final CTA Section */}
        <section className="relative py-24 bg-dark-surface border-t border-white/5">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Ready to <span className="text-gradient-ai">Secure Your Premises?</span>
            </h2>
            <p className="text-xl text-gray-400 mb-10">
              Experience the future of intelligent surveillance and theft prevention.
            </p>
            <button
              onClick={() => navigate('/register-branch')}
              className="group relative px-12 py-5 bg-ai-blue text-dark-bg font-bold text-lg rounded-full overflow-hidden
                       hover:bg-cyan-400 transition-all duration-300 shadow-[0_0_30px_rgba(0,212,255,0.4)]
                       transform hover:scale-105"
            >
              <span className="relative z-10 flex items-center gap-3">
                Get Started <i className="fa-solid fa-arrow-right group-hover:translate-x-1 transition-transform"></i>
              </span>
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            </button>
          </div>
        </section>

        {/* Footer (Added Proper Footer) */}
        <footer className="bg-black/80 backdrop-blur-md border-t border-white/10 pt-16 pb-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
              {/* Brand */}
              <div className="col-span-1 md:col-span-2">
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheckIcon className="h-8 w-8 text-ai-blue" />
                  <span className="font-bold text-2xl tracking-tight text-white">Theft<span className="text-ai-blue">Sentinel</span></span>
                </div>
                <p className="text-gray-400 max-w-sm leading-relaxed">
                  A web-based AI-powered anti-theft system designed to automate retail surveillance. 
                  Utilizing state-of-the-art computer vision to detect suspicious behavior and prevent loss.
                </p>
              </div>

              {/* Quick Links */}
              <div>
                <h4 className="text-white font-bold mb-4">Platform</h4>
                <ul className="space-y-2">
                  <li><a href="#" className="text-gray-400 hover:text-ai-blue transition-colors text-sm">Features</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-ai-blue transition-colors text-sm">Pricing</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-ai-blue transition-colors text-sm">Documentation</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-ai-blue transition-colors text-sm">Case Studies</a></li>
                </ul>
              </div>

              {/* University Info */}
              <div>
                <h4 className="text-white font-bold mb-4">Project Info</h4>
                <div className="flex items-start gap-3 mb-3 text-gray-400 text-sm">
                  <BuildingOfficeIcon className="h-5 w-5 mt-0.5 text-ai-blue" />
                  <div>
                    <p>Department of Computer Science</p>
                    <p>Air University Islamabad</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-gray-400 text-sm">
                  <AcademicCapIcon className="h-5 w-5 mt-0.5 text-ai-blue" />
                  <p>Final Year Project 2025</p>
                </div>
              </div>
            </div>

            <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
              <p className="text-gray-500 text-sm">
                © 2025 Theft Sentinel. All rights reserved.
              </p>
              <div className="flex gap-6">
                <a href="#" className="text-gray-500 hover:text-white transition-colors"><i className="fa-brands fa-github text-lg"></i></a>
                <a href="#" className="text-gray-500 hover:text-white transition-colors"><i className="fa-brands fa-linkedin text-lg"></i></a>
                <a href="#" className="text-gray-500 hover:text-white transition-colors"><i className="fa-solid fa-envelope text-lg"></i></a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
};

export default Landing;
