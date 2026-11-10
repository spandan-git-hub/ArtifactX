import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

export default function LoginPage() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      navigate('/cases');
    }, 400);
  };

  return (
    <div className="min-h-screen flex flex-col font-body-md select-none bg-background text-on-surface">
      {/* Top Bar */}
      <header className="h-12 w-full border-b border-outline-variant bg-surface-container-low flex items-center justify-between px-space-lg shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 rounded flex items-center justify-center bg-primary/10 border border-primary/40">
            <span className="material-symbols-outlined text-primary text-[15px]">terminal</span>
          </div>
          <span className="font-headline-sm text-headline-sm font-semibold tracking-tight text-on-surface">ArtifactX</span>
        </div>

        {/* Theme Switcher */}
        <div className="flex items-center bg-surface-container-lowest border border-outline-variant rounded-lg p-0.5">
          <button
            onClick={() => theme !== 'light' && toggleTheme()}
            className={`p-1 rounded transition-colors ${
              theme === 'light' ? 'bg-surface-container-highest text-primary border border-outline-variant' : 'text-on-surface-variant'
            }`}
            title="Light Mode"
            type="button"
          >
            <span className="material-symbols-outlined text-[15px]">light_mode</span>
          </button>
          <button
            onClick={() => theme !== 'dark' && toggleTheme()}
            className={`p-1 rounded transition-colors ${
              theme === 'dark' ? 'bg-surface-container-highest text-primary border border-outline-variant' : 'text-on-surface-variant'
            }`}
            title="Dark Mode"
            type="button"
          >
            <span className="material-symbols-outlined text-[15px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              dark_mode
            </span>
          </button>
        </div>
      </header>

      {/* Main Canvas Centered Layout */}
      <main className="flex-1 flex flex-col items-center justify-center p-space-lg relative overflow-hidden">
        {/* Subtle grid accent */}
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
            backgroundSize: '32px 32px'
          }}
        />

        {/* Login Centered Card (440px) */}
        <div className="w-full max-w-[440px] bg-surface-container border border-outline-variant rounded-lg relative z-10 flex flex-col shadow-2xl">
          {/* Card Header */}
          <div className="p-space-lg border-b border-outline-variant">
            <div className="flex items-center space-x-2 mb-2">
              <span className="material-symbols-outlined text-primary text-[18px]">security</span>
              <span className="font-headline-md text-headline-md font-semibold text-on-surface">ArtifactX</span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
              Digital Forensic Analysis Workstation for Android Artifacts
            </p>
          </div>

          {/* Card Body */}
          <div className="p-space-lg space-y-4">
            <form className="space-y-3.5" onSubmit={handleSubmit}>
              {/* Username / Examiner ID */}
              <div className="space-y-1">
                <label className="font-label-ui text-label-ui uppercase tracking-wider text-on-surface-variant block" htmlFor="examiner-id">
                  Username / Examiner ID
                </label>
                <div className="relative">
                  <input
                    id="examiner-id"
                    type="text"
                    placeholder="examiner@forensics.agency.gov"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    className="w-full h-8 px-2.5 bg-surface-container-lowest border border-outline-variant rounded text-on-surface font-label-mono-md text-label-mono-md focus:border-primary focus:outline-none placeholder:text-outline"
                  />
                  <span className="material-symbols-outlined absolute right-2.5 top-2 text-on-surface-variant text-[16px]">
                    badge
                  </span>
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-1">
                <label className="font-label-ui text-label-ui uppercase tracking-wider text-on-surface-variant block" htmlFor="password-input">
                  Password / Master Pin
                </label>
                <div className="relative">
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter workstation passphrase"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full h-8 px-2.5 pr-8 bg-surface-container-lowest border border-outline-variant rounded text-on-surface font-label-mono-md text-label-mono-md focus:border-primary focus:outline-none placeholder:text-outline"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-2 text-on-surface-variant hover:text-on-surface transition-colors"
                    title="Toggle Visibility"
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {showPassword ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              {/* Sign In Button */}
              <div className="pt-1">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full h-8 rounded-lg bg-primary hover:opacity-90 text-on-primary font-body-md text-body-md font-semibold flex items-center justify-center space-x-1.5 transition-all shadow-sm"
                >
                  <span>{loading ? 'Authenticating...' : 'Sign in to Workstation'}</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </form>
          </div>

          {/* Security note footer */}
          <div className="p-space-md border-t border-outline-variant bg-surface-container-lowest/60 rounded-b-lg">
            <div className="flex items-start space-x-2">
              <span className="material-symbols-outlined text-on-surface-variant text-[15px] mt-0.5 shrink-0">verified_user</span>
              <p className="font-body-sm text-body-sm text-on-surface-variant leading-tight">
                Restricted Access · Authorized forensic examiners and expert reviewers only
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
