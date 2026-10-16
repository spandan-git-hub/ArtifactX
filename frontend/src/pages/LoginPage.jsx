import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

export default function LoginPage() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [username, setUsername] = useState('a.verma@forensics.agency.gov');
  const [password, setPassword] = useState('ForensicPin-2026!');
  const [showPassword, setShowPassword] = useState(false);
  const [showError, setShowError] = useState(false);
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
      {/* Top Minimalist Bar per Stitch Blueprint */}
      <header className="h-12 w-full border-b border-outline-variant bg-surface-container-low flex items-center justify-between px-space-lg shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 rounded flex items-center justify-center bg-primary/10 border border-primary/40">
            <span className="material-symbols-outlined text-primary text-[15px]">terminal</span>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="font-headline-sm text-headline-sm font-semibold tracking-tight text-on-surface">ArtifactX</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant border-l border-outline-variant pl-2">
              WS-STAGE-04
            </span>
          </div>
        </div>

        {/* Right Controls: Node status & Theme Switcher */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded border border-outline-variant bg-surface-container-lowest text-on-surface-variant font-label-mono-sm text-label-mono-sm">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary" />
            <span>NODE: F-AIRGAP-09</span>
          </div>

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
              title="Dark Mode (Active)"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                dark_mode
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Pinned Audit Chain Verification Ribbon */}
      <div className="w-full bg-surface-container-low/70 border-b border-outline-variant px-space-lg py-1 flex items-center justify-between text-on-surface-variant font-label-mono-sm text-label-mono-sm shrink-0">
        <div className="flex items-center space-x-2">
          <span className="material-symbols-outlined text-[13px] text-primary">lock</span>
          <span>SECURE BOOT ENCLAVE: SHA-256 INTEGRITY VALIDATED</span>
          <span className="text-outline">|</span>
          <span className="text-on-surface">ROOT: 7a8f...39b1</span>
        </div>
        <div className="hidden sm:flex items-center space-x-4">
          <span>TIME: UTC {new Date().toISOString().replace('T', ' ').substring(0, 19)}</span>
          <span className="text-outline">|</span>
          <span>ZERO EXTERNAL EGRESS ACTIVE</span>
        </div>
      </div>

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
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="material-symbols-outlined text-primary text-[18px]">security</span>
                <span className="font-headline-md text-headline-md font-semibold text-on-surface">ArtifactX</span>
              </div>
              <span className="font-label-mono-sm text-label-mono-sm px-1.5 py-0.5 rounded border border-outline-variant bg-surface-container-lowest text-on-surface-variant">
                v4.12.0
              </span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
              Digital Forensic Analysis Workstation for Android Artifacts
            </p>
          </div>

          {/* Card Body */}
          <div className="p-space-lg space-y-4">
            {showError && (
              <div className="rounded-lg p-space-sm border border-error bg-error/15 flex items-start justify-between space-x-2">
                <div className="flex items-start space-x-2">
                  <span className="material-symbols-outlined text-error text-[16px] mt-0.5 shrink-0">error</span>
                  <div className="space-y-0.5">
                    <span className="block font-label-ui text-label-ui font-semibold text-error tracking-wide">
                      AUTHENTICATION ERROR
                    </span>
                    <p className="font-body-sm text-body-sm text-error leading-tight">
                      Sign-in failed. Check your security token or hardware PIN and try again.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowError(false)}
                  className="shrink-0 px-2 py-1 rounded bg-error/20 hover:bg-error/30 border border-error text-error font-label-ui text-label-ui"
                >
                  Dismiss
                </button>
              </div>
            )}

            <form className="space-y-3.5" onSubmit={handleSubmit}>
              {/* Username / Examiner ID */}
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <label className="font-label-ui text-label-ui uppercase tracking-wider text-on-surface-variant" htmlFor="examiner-id">
                    Username / Examiner ID
                  </label>
                  <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">PKI Validated</span>
                </div>
                <div className="relative">
                  <input
                    id="examiner-id"
                    type="text"
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
                <div className="flex justify-between items-center">
                  <label className="font-label-ui text-label-ui uppercase tracking-wider text-on-surface-variant" htmlFor="password-input">
                    Password / Master Pin
                  </label>
                  <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">256-bit AES</span>
                </div>
                <div className="relative">
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full h-8 px-2.5 pr-8 bg-surface-container-lowest border border-outline-variant rounded text-on-surface font-label-mono-md text-label-mono-md focus:border-primary focus:outline-none"
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

              {/* Workstation Hardware Token Status */}
              <div className="p-2.5 rounded bg-surface-container-lowest border border-outline-variant space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-label-ui text-label-ui uppercase tracking-wider text-on-surface-variant">
                    Workstation Station / Session
                  </span>
                  <span className="inline-flex items-center space-x-1 font-label-mono-sm text-label-mono-sm text-primary">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                    <span>CRYPT-SYNC</span>
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-on-surface">
                  <span className="material-symbols-outlined text-primary text-[16px] shrink-0">key</span>
                  <span className="font-body-sm text-body-sm text-on-surface truncate">
                    Hardware Token / Security Key verified (YubiKey Slot 1)
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-outline-variant font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                  <span>SERIAL: YK-8921-X9</span>
                  <span>SLOT: FIDO2/PIV</span>
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

              <div className="flex justify-between items-center text-[11px] text-on-surface-variant pt-1">
                <button
                  type="button"
                  onClick={() => setShowError(true)}
                  className="hover:underline text-outline"
                >
                  Simulate Token Mismatch
                </button>
                <span className="font-mono text-outline">Enclave v4.12</span>
              </div>
            </form>
          </div>

          {/* Security note footer */}
          <div className="p-space-md border-t border-outline-variant bg-surface-container-lowest/60 rounded-b-lg">
            <div className="flex items-start space-x-2">
              <span className="material-symbols-outlined text-on-surface-variant text-[15px] mt-0.5 shrink-0">verified_user</span>
              <p className="font-body-sm text-body-sm text-on-surface-variant leading-tight">
                Restricted Access · Authorized forensic examiners and expert reviewers only · All sessions logged to tamper-evident audit ledger
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
