import { Link, useLocation } from 'react-router-dom';
import {
  FolderKanban,
  LayoutDashboard,
  Search,
  FileText,
  ClipboardList,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  Upload,
  Database,
} from 'lucide-react';

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();

  // Extract caseId from any case-specific route
  const caseIdMatch = location.pathname.match(/\/cases\/(\d+)/);
  const activeCaseId = caseIdMatch ? caseIdMatch[1] : null;

  const navItems = activeCaseId
    ? [
      { path: '/cases', icon: FolderKanban, label: 'All Cases' },
      { path: `/cases/${activeCaseId}/dashboard`, icon: LayoutDashboard, label: 'Dashboard' },
      { path: `/cases/${activeCaseId}/search`, icon: Search, label: 'Search' },
      { path: `/cases/${activeCaseId}/reports`, icon: FileText, label: 'Reports' },
      { path: `/cases/${activeCaseId}/logs`, icon: ClipboardList, label: 'Logs' },
    ]
    : [
      { path: '/cases', icon: FolderKanban, label: 'Cases' },
      { path: '#', icon: Search, label: 'Search', disabled: true },
      { path: '#', icon: FileText, label: 'Reports', disabled: true },
      { path: '#', icon: ClipboardList, label: 'Logs', disabled: true },
    ];

  const isActive = (path) => {
    if (path === '#') return false;
    return location.pathname === path || (path !== '/cases' && location.pathname.startsWith(path));
  };

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-forensic-900 border-r border-forensic-700
                  flex flex-col transition-all duration-300 z-50
                  ${collapsed ? 'w-16' : 'w-64'}`}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-forensic-700">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-cyan/20 flex items-center justify-center">
            <Shield className="h-5 w-5 text-accent-cyan" />
          </div>
          {!collapsed && (
            <span className="font-mono font-bold text-lg text-gradient">
              ArtifactX
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.label}
            to={item.disabled ? '#' : item.path}
            className={`
              nav-item
              ${isActive(item.path) && !item.disabled ? 'nav-item-active' : ''}
              ${item.disabled ? 'opacity-50 cursor-not-allowed hover:bg-transparent hover:text-forensic-400' : ''}
            `}
            onClick={(e) => item.disabled && e.preventDefault()}
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Status indicator */}
      <div className="p-4 border-t border-forensic-700">
        <div className={`flex items-center gap-2 ${collapsed ? 'justify-center' : ''}`}>
          <div className="status-dot status-dot-active" />
          {!collapsed && (
            <span className="text-xs text-forensic-500">System Online</span>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 bg-forensic-800 border border-forensic-600
                   rounded-full flex items-center justify-center text-forensic-400
                   hover:text-forensic-100 hover:bg-forensic-700 transition-colors"
      >
        {collapsed ? (
          <ChevronRight className="h-3 w-3" />
        ) : (
          <ChevronLeft className="h-3 w-3" />
        )}
      </button>
    </aside>
  );
};

const Header = ({ title, breadcrumbs = [], actions }) => {
  return (
    <header className="h-16 bg-forensic-900/80 backdrop-blur-sm border-b border-forensic-700
                        flex items-center justify-between px-6 sticky top-0 z-40">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm">
        {breadcrumbs.map((crumb, index) => (
          <div key={index} className="flex items-center gap-2">
            {index > 0 && <span className="text-forensic-600">/</span>}
            {crumb.path ? (
              <Link
                to={crumb.path}
                className="text-forensic-400 hover:text-accent-cyan transition-colors"
              >
                {crumb.label}
              </Link>
            ) : (
              <span className="text-forensic-100">{crumb.label}</span>
            )}
          </div>
        ))}
      </div>

      {/* Title (if no breadcrumbs) */}
      {!breadcrumbs.length && (
        <h1 className="text-lg font-semibold">{title}</h1>
      )}

      {/* Actions */}
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </header>
  );
};

const Layout = ({ children, sidebarCollapsed, onSidebarToggle }) => {
  return (
    <div className="min-h-screen bg-forensic-950">
      <Sidebar collapsed={sidebarCollapsed} onToggle={onSidebarToggle} />
      <main
        className={`transition-all duration-300 min-h-screen ${sidebarCollapsed ? 'ml-16' : 'ml-64'
          }`}
      >
        {children}
      </main>
    </div>
  );
};

export { Sidebar, Header, Layout };