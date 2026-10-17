import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';
import { useActiveCase } from '../../context/CaseContext';

export function Layout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { cases, activeCaseId, activeCase, switchCase } = useActiveCase();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [caseMenuOpen, setCaseMenuOpen] = useState(false);
  const [examinerMenuOpen, setExaminerMenuOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  // Derive active section for breadcrumb
  const path = location.pathname;
  let sectionName = 'Overview';
  if (path === '/cases') sectionName = 'Cases';
  else if (path.includes('/new') || path.includes('/create')) sectionName = 'New Case';
  else if (path.includes('/evidence')) sectionName = 'Evidence';
  else if (path.includes('/decryption')) sectionName = 'Decryption';
  else if (path.includes('/pipeline')) sectionName = 'Pipeline';
  else if (path.includes('/messages') || path.includes('/chat')) sectionName = 'Messages';
  else if (path.includes('/timeline')) sectionName = 'Timeline';
  else if (path.includes('/recovery')) sectionName = 'Recovery';
  else if (path.includes('/correlations') || path.includes('/correlation')) sectionName = 'Correlations';
  else if (path.includes('/section63')) sectionName = 'Section 63';
  else if (path.includes('/integrity')) sectionName = 'Integrity & Audit';
  else if (path.includes('/metrics')) sectionName = 'Metrics';
  else if (path.includes('/limitations')) sectionName = 'Limitations';
  else if (path.includes('/reports')) sectionName = 'Reports';

  const caseId = activeCase?.id || '';

  const navTabs = [
    { name: 'Overview', icon: 'dashboard', path: caseId ? `/cases/${caseId}/overview` : '/cases', badge: activeCase ? 'LIVE' : undefined, badgeColor: 'bg-primary/20 text-primary' },
    { name: 'Evidence', icon: 'folder_open', path: caseId ? `/cases/${caseId}/evidence` : '/cases', count: activeCase?.evidenceCount },
    { name: 'Decryption', icon: 'key', path: caseId ? `/cases/${caseId}/decryption` : '/cases' },
    // Temporarily disabled tabs:
    // { name: 'Pipeline', icon: 'alt_route', path: caseId ? `/cases/${caseId}/pipeline` : '/cases' },
    // { name: 'Messages', icon: 'chat', path: caseId ? `/cases/${caseId}/messages` : '/cases', count: activeCase?.recordCount && activeCase.recordCount !== '0' ? activeCase.recordCount : undefined },
    { name: 'Timeline', icon: 'schedule', path: caseId ? `/cases/${caseId}/timeline` : '/cases' },
    { name: 'Recovery', icon: 'restore', path: caseId ? `/cases/${caseId}/recovery` : '/cases' },
    { name: 'Correlations', icon: 'hub', path: caseId ? `/cases/${caseId}/correlations` : '/cases' },
    { name: 'Reports', icon: 'description', path: caseId ? `/cases/${caseId}/reports` : '/cases' },
    // { name: 'Section 63', icon: 'gavel', path: caseId ? `/cases/${caseId}/section63` : '/cases' },
    // { name: 'Integrity & Audit', icon: 'verified_user', path: caseId ? `/cases/${caseId}/integrity` : '/cases' },
    // { name: 'Metrics', icon: 'analytics', path: caseId ? `/cases/${caseId}/metrics` : '/cases' },
    // { name: 'Limitations', icon: 'info', path: caseId ? `/cases/${caseId}/limitations` : '/cases' },
  ];

  const isTabActive = (tabPath) => {
    if (tabPath.includes('/overview') && (location.pathname === `/cases/${caseId}` || location.pathname === `/cases/${caseId}/overview`)) {
      return true;
    }
    return location.pathname.startsWith(tabPath);
  };

  return (
    <div className="min-h-screen h-screen flex flex-col font-body-md bg-background text-on-surface select-none overflow-hidden">
      {/* ================= TOP APP BAR ================= */}
      <header className="h-12 w-full border-b border-outline-variant bg-surface-container-low flex items-center justify-between px-space-lg shrink-0 z-30">
        {/* Brand Anchor & Breadcrumb */}
        <div className="flex items-center space-x-3">
          <Link to="/cases" className="flex items-center space-x-2 group">
            <div className="w-6 h-6 rounded flex items-center justify-center bg-primary/10 border border-primary/40 group-hover:border-primary transition-colors">
              <span className="material-symbols-outlined text-primary text-[15px]">terminal</span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="font-headline-sm text-headline-sm font-semibold tracking-tight text-on-surface group-hover:text-primary transition-colors">
                ArtifactX
              </span>
              <span className="text-[10px] font-mono tracking-wider bg-surface-variant text-on-surface-variant px-1.5 py-0.5 rounded border border-outline-variant uppercase">
                DFIR CORE
              </span>
            </div>
          </Link>

          <div className="h-4 w-[1px] bg-outline-variant" />

          <nav className="flex items-center space-x-1.5 text-body-sm font-body-sm">
            <Link to="/cases" className="text-on-surface-variant hover:text-on-surface transition-colors">
              Workstation
            </Link>
            <span className="text-outline">/</span>
            <span className="text-on-surface font-semibold">{sectionName}</span>
          </nav>
        </div>

        {/* Right Controls: Active Case, Airgap node, Theme Toggle, Profile */}
        <div className="flex items-center space-x-3">
          {/* Active Case Monospace Pill with switcher dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setCaseMenuOpen(!caseMenuOpen)}
              className="flex items-center bg-surface-container-highest/60 hover:bg-surface-container-highest border border-outline-variant rounded px-2.5 py-1 space-x-2 transition-colors cursor-pointer"
              title="Click to switch active case"
            >
              <span className="text-[10px] text-on-surface-variant font-mono uppercase tracking-wider">ACTIVE CONTEXT:</span>
              <span className="text-label-mono-sm font-label-mono-sm font-medium text-primary">
                {activeCase?.caseNumber || 'No Case Selected'}
              </span>
              <span className="material-symbols-outlined text-[14px] text-on-surface-variant">sync_alt</span>
            </button>

            {caseMenuOpen && (
              <div
                className="absolute right-0 mt-1 w-80 bg-surface-container border border-outline-variant rounded-lg shadow-xl py-1.5 z-50 text-left"
                onMouseLeave={() => setCaseMenuOpen(false)}
              >
                <div className="px-3 py-1.5 border-b border-outline-variant text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider flex items-center justify-between">
                  <span>Switch Investigation Context</span>
                  <Link to="/cases/new" onClick={() => setCaseMenuOpen(false)} className="text-primary hover:underline font-mono text-[10px]">
                    + New Case
                  </Link>
                </div>
                <div className="max-h-60 overflow-y-auto divide-y divide-outline-variant/40">
                  {cases.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => {
                        switchCase(c.id);
                        setCaseMenuOpen(false);
                        navigate(`/cases/${c.id}/overview`);
                      }}
                      className={`w-full text-left px-3 py-2 flex items-start justify-between hover:bg-surface-container-high transition-colors ${
                        c.id === caseId ? 'bg-primary/10 border-l-2 border-primary' : ''
                      }`}
                    >
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <span className="font-label-mono-sm font-medium text-on-surface">{c.caseNumber}</span>
                          <span className={`text-[9px] px-1 rounded font-mono ${
                            c.status === 'Active' ? 'bg-tertiary/20 text-tertiary' : 'bg-surface-variant text-on-surface-variant'
                          }`}>
                            {c.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-on-surface-variant truncate max-w-[210px]">{c.title}</p>
                      </div>
                      <span className="text-[10px] text-outline font-mono mt-0.5">{c.evidenceCount} artf</span>
                    </button>
                  ))}
                </div>
                <div className="p-2 border-t border-outline-variant bg-surface-container-low">
                  <Link
                    to="/cases"
                    onClick={() => setCaseMenuOpen(false)}
                    className="block text-center text-[11px] text-primary hover:underline font-medium"
                  >
                    View All Cases Directory →
                  </Link>
                </div>
              </div>
            )}
          </div>

          <div className="h-4 w-[1px] bg-outline-variant" />

          {/* Node Airgap Status Indicator */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2 py-0.5 rounded border border-outline-variant bg-surface-container-lowest text-on-surface-variant font-label-mono-sm text-label-mono-sm">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span>NODE: F-AIRGAP-09</span>
          </div>

          <div className="h-4 w-[1px] bg-outline-variant" />

          {/* Sun / Moon Theme Toggle */}
          <div className="flex items-center bg-surface-container-lowest border border-outline-variant rounded-lg p-0.5">
            <button
              onClick={() => theme !== 'light' && toggleTheme()}
              className={`p-1 rounded transition-colors ${
                theme === 'light'
                  ? 'bg-surface-container-highest text-primary border border-outline-variant shadow-xs'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
              title="Light Mode"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]">light_mode</span>
            </button>
            <button
              onClick={() => theme !== 'dark' && toggleTheme()}
              className={`p-1 rounded transition-colors ${
                theme === 'dark'
                  ? 'bg-surface-container-highest text-primary border border-outline-variant shadow-xs'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
              title="Dark Mode (Active)"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                dark_mode
              </span>
            </button>
          </div>

          <div className="h-4 w-[1px] bg-outline-variant" />

          {/* User Profile / Examiner Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setExaminerMenuOpen(!examinerMenuOpen)}
              className="flex items-center space-x-2 pl-1 cursor-pointer group hover:text-primary transition-colors"
            >
              <div className="w-6 h-6 rounded-full bg-surface-container-highest flex items-center justify-center text-primary border border-outline-variant">
                <span className="material-symbols-outlined text-[15px]">account_circle</span>
              </div>
              <span className="text-body-sm font-body-sm font-medium text-on-surface group-hover:text-primary transition-colors">
                A. Verma (Examiner)
              </span>
              <span className="material-symbols-outlined text-[14px] text-on-surface-variant">expand_more</span>
            </button>

            {examinerMenuOpen && (
              <div
                className="absolute right-0 mt-1.5 w-56 bg-surface-container border border-outline-variant rounded-lg shadow-xl py-1 z-50 text-left"
                onMouseLeave={() => setExaminerMenuOpen(false)}
              >
                <div className="px-3 py-2 border-b border-outline-variant">
                  <div className="text-body-sm font-semibold text-on-surface">Abhishek Verma</div>
                  <div className="text-[10px] text-on-surface-variant font-mono">Senior Forensic Analyst · ID #8942</div>
                  <div className="text-[10px] text-primary font-mono mt-0.5">Cert: BSA-SEC63-AUTH-091</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setExaminerMenuOpen(false);
                    setSettingsModalOpen(true);
                  }}
                  className="w-full text-left px-3 py-1.5 text-body-sm text-on-surface hover:bg-surface-container-high flex items-center space-x-2"
                >
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant">settings</span>
                  <span>Workstation Settings</span>
                </button>
                {/* Temporarily disabled Section 63 link in examiner menu:
                <Link
                  to={`/cases/${caseId}/section63`}
                  onClick={() => setExaminerMenuOpen(false)}
                  className="w-full text-left px-3 py-1.5 text-body-sm text-on-surface hover:bg-surface-container-high flex items-center space-x-2"
                >
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant">gavel</span>
                  <span>Section 63 Credential</span>
                </Link>
                */}
                <div className="border-t border-outline-variant my-1" />
                <Link
                  to="/login"
                  onClick={() => setExaminerMenuOpen(false)}
                  className="w-full text-left px-3 py-1.5 text-body-sm text-error hover:bg-surface-container-high flex items-center space-x-2"
                >
                  <span className="material-symbols-outlined text-[16px]">lock</span>
                  <span>Lock Workstation</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ================= PINNED AUDIT CHAIN VERIFICATION RIBBON ================= */}
      <div className="w-full bg-surface-container-low/70 border-b border-outline-variant px-space-lg py-1 flex items-center justify-between text-on-surface-variant font-label-mono-sm text-label-mono-sm shrink-0">
        <div className="flex items-center space-x-2 overflow-hidden text-ellipsis whitespace-nowrap">
          <span className="material-symbols-outlined text-[13px] text-primary">lock</span>
          <span className="text-tertiary flex items-center font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-tertiary mr-1 inline-block" />
            SECURE BOOT ENCLAVE: SHA-256 INTEGRITY VALIDATED
          </span>
          <span className="text-outline">|</span>
          <span>ROOT: <code className="text-on-surface">7a8f...39b1</code></span>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant">BLOCK: {activeCase?.blockId || '#40921-X9'}</span>
        </div>
        <div className="hidden md:flex items-center space-x-4">
          <span>TIME: UTC {new Date().toISOString().replace('T', ' ').substring(0, 19)}</span>
          <span className="text-outline">|</span>
          <span className="text-primary font-medium">ZERO EXTERNAL EGRESS ACTIVE</span>
        </div>
      </div>

      {/* ================= WORKSPACE BODY (SideNav + Content) ================= */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* ================= SIDEBAR NAVIGATION ================= */}
        <aside
          className={`flex flex-col justify-between h-full bg-surface-container-low border-r border-outline-variant transition-all duration-200 shrink-0 select-none ${
            sidebarCollapsed ? 'w-14 p-1.5' : 'w-[245px] p-space-sm'
          }`}
        >
          <div className="flex flex-col space-y-3 flex-1 overflow-hidden">
            {/* Sidebar Header / Cases Navigator Badge */}
            <div className={`px-2 pt-1 pb-2 border-b border-outline-variant ${sidebarCollapsed ? 'text-center' : ''}`}>
              {!sidebarCollapsed ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant font-semibold">
                      Cases Navigator
                    </span>
                    <button
                      type="button"
                      onClick={() => setSidebarCollapsed(true)}
                      className="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors"
                      title="Collapse sidebar"
                    >
                      <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                    </button>
                  </div>
                  <div className="text-[11px] text-outline font-mono mt-0.5 truncate">
                    Active: {caseId}
                  </div>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setSidebarCollapsed(false)}
                  className="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors"
                  title="Expand sidebar"
                >
                  <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                </button>
              )}
            </div>

            {/* Global Directory Links */}
            {!sidebarCollapsed && (
              <div className="px-2 py-0.5 flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-outline">
                <span>Investigation Directory</span>
                <Link to="/cases/new" className="text-primary hover:underline flex items-center" title="Create New Case">
                  <span className="material-symbols-outlined text-[13px]">add</span>
                </Link>
              </div>
            )}

            <div className="space-y-0.5">
              <Link
                to="/cases"
                className={`flex items-center space-x-2.5 px-space-sm py-1.5 transition-colors rounded ${
                  location.pathname === '/cases'
                    ? 'bg-surface-container-highest text-primary font-semibold border-l-2 border-primary rounded-none'
                    : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                }`}
                title="Cases Directory"
              >
                <span className="material-symbols-outlined text-[18px]">folder_special</span>
                {!sidebarCollapsed && (
                  <>
                    <span className="text-body-sm">Cases</span>
                    <span className="ml-auto text-[10px] font-mono bg-primary/10 border border-primary/30 text-primary px-1.5 py-0.2 rounded">
                      {cases.length}
                    </span>
                  </>
                )}
              </Link>
              <Link
                to="/cases/new"
                className={`flex items-center space-x-2.5 px-space-sm py-1.5 transition-colors rounded ${
                  location.pathname === '/cases/new' || location.pathname === '/cases/create'
                    ? 'bg-surface-container-highest text-primary font-semibold border-l-2 border-primary rounded-none'
                    : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                }`}
                title="New Case"
              >
                <span className="material-symbols-outlined text-[18px]">create_new_folder</span>
                {!sidebarCollapsed && <span className="text-body-sm">New Case</span>}
              </Link>
            </div>

            <div className="h-[1px] bg-outline-variant/60 my-1" />

            {/* 13 Blueprint Tabs for Active Case */}
            <div className="flex-1 overflow-y-auto custom-scrollbar pr-0.5 space-y-0.5">
              {!sidebarCollapsed && (
                <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-outline">
                  Case Modules: {caseId}
                </div>
              )}
              {navTabs.map((tab) => {
                const active = isTabActive(tab.path);
                return (
                  <Link
                    key={tab.name}
                    to={tab.path}
                    className={`flex items-center space-x-2.5 px-space-sm py-1.5 transition-colors ${
                      active
                        ? 'bg-surface-container-highest text-primary font-semibold border-l-2 border-primary rounded-none'
                        : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface rounded'
                    }`}
                    title={tab.name}
                  >
                    <span
                      className={`material-symbols-outlined text-[17px] ${active ? 'text-primary' : ''}`}
                      style={active ? { fontVariationSettings: "'FILL' 1" } : {}}
                    >
                      {tab.icon}
                    </span>
                    {!sidebarCollapsed && (
                      <>
                        <span className="text-label-ui font-label-ui flex-1 truncate">{tab.name}</span>
                        {tab.badge && (
                          <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border border-primary/30 ${tab.badgeColor || 'bg-primary/20 text-primary'}`}>
                            {tab.badge}
                          </span>
                        )}
                        {tab.count !== undefined && !tab.badge && (
                          <span className="text-label-mono-sm text-on-surface-variant text-[10px] font-mono">
                            {tab.count}
                          </span>
                        )}
                        {tab.dot && (
                          <span className={`w-1.5 h-1.5 rounded-full ${tab.dot}`} />
                        )}
                      </>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Sidebar Footers */}
          <div className="border-t border-outline-variant pt-2 space-y-0.5 text-body-sm font-body-sm shrink-0">
            {/* Temporarily disabled Audit Trail footer link:
            <Link
              to={`/cases/${caseId}/integrity`}
              className="flex items-center space-x-2.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface px-space-sm py-1.5 rounded transition-colors"
              title="Audit Trail"
            >
              <span className="material-symbols-outlined text-[17px]">shield</span>
              {!sidebarCollapsed && <span className="text-label-ui font-label-ui">Audit Trail</span>}
            </Link>
            */}
            <button
              type="button"
              onClick={() => setSettingsModalOpen(true)}
              className="w-full flex items-center space-x-2.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface px-space-sm py-1.5 rounded transition-colors text-left"
              title="Workstation Settings"
            >
              <span className="material-symbols-outlined text-[17px]">settings</span>
              {!sidebarCollapsed && <span className="text-label-ui font-label-ui">Settings</span>}
            </button>
            {!sidebarCollapsed && (
              <div className="mt-2 pt-2 border-t border-outline-variant/40 flex items-center justify-between text-label-mono-sm text-outline px-2 text-[10px]">
                <span>SEC-CH-ID: 0x48A</span>
                <span>v4.1.2</span>
              </div>
            )}
          </div>
        </aside>

        {/* ================= MAIN CONTENT CANVAS ================= */}
        <main className="flex-1 flex flex-col h-full min-h-0 overflow-hidden bg-background">
          {children}
        </main>
      </div>

      {/* Settings Modal */}
      {settingsModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container border border-outline-variant rounded-xl max-w-lg w-full p-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-outline-variant">
              <div className="flex items-center space-x-2">
                <span className="material-symbols-outlined text-primary text-[20px]">tune</span>
                <h3 className="text-headline-sm font-headline-sm text-on-surface">Workstation Configurations</h3>
              </div>
              <button
                type="button"
                onClick={() => setSettingsModalOpen(false)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
            <div className="py-4 space-y-4 text-body-sm text-on-surface">
              <div>
                <label className="text-label-ui text-on-surface-variant block mb-1">Active Forensic Node</label>
                <input
                  type="text"
                  readOnly
                  value="F-AIRGAP-09 (Air-gapped Cryptographic Workstation)"
                  className="w-full bg-surface-container-low border border-outline-variant rounded p-2 text-label-mono-sm text-on-surface"
                />
              </div>
              <div>
                <label className="text-label-ui text-on-surface-variant block mb-1">Active Cryptographic Standard</label>
                <div className="p-2 bg-surface-container-low border border-outline-variant rounded text-label-mono-sm text-primary flex items-center justify-between">
                  <span>SHA-256 + BLAKE3-256 Dual Verification</span>
                  <span className="text-[10px] bg-tertiary/20 text-tertiary px-1.5 py-0.5 rounded border border-tertiary/30">LOCKED</span>
                </div>
              </div>
              <div>
                <label className="text-label-ui text-on-surface-variant block mb-1">Theme Preference</label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => theme !== 'dark' && toggleTheme()}
                    className={`flex-1 py-2 px-3 rounded border text-center transition-colors ${
                      theme === 'dark' ? 'bg-primary/20 border-primary text-primary font-semibold' : 'border-outline-variant text-on-surface-variant'
                    }`}
                  >
                    Dark (Forensic Standard)
                  </button>
                  <button
                    type="button"
                    onClick={() => theme !== 'light' && toggleTheme()}
                    className={`flex-1 py-2 px-3 rounded border text-center transition-colors ${
                      theme === 'light' ? 'bg-primary/20 border-primary text-primary font-semibold' : 'border-outline-variant text-on-surface-variant'
                    }`}
                  >
                    Light Mode
                  </button>
                </div>
              </div>
            </div>
            <div className="pt-3 border-t border-outline-variant flex justify-end">
              <button
                type="button"
                onClick={() => setSettingsModalOpen(false)}
                className="btn-primary"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function Header({ breadcrumbs = [] }) {
  return (
    <header className="h-12 w-full border-b border-outline-variant bg-surface-container-low flex items-center justify-between px-space-lg shrink-0">
      <nav className="flex items-center space-x-2 text-body-sm font-body-sm">
        {breadcrumbs.map((b, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="text-outline">/</span>}
            {b.path ? (
              <Link to={b.path} className="text-on-surface-variant hover:text-on-surface transition-colors">
                {b.label}
              </Link>
            ) : (
              <span className="text-on-surface font-semibold">{b.label}</span>
            )}
          </React.Fragment>
        ))}
      </nav>
    </header>
  );
}