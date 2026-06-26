import { useState } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import CaseListPage from './pages/CaseListPage';
import CaseDetailPage from './pages/CaseDetailPage';
import SearchPage from './pages/SearchPage';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage';
import LogsPage from './pages/LogsPage';
import CaseForm from './components/cases/CaseForm';
import { Layout } from './components/layout';
import { Shield } from 'lucide-react';

function HomeScreen() {
  return (
    <div className="min-h-screen bg-forensic-950 flex items-center justify-center">
      <div className="text-center animate-in">
        <div className="w-20 h-20 rounded-2xl bg-accent-cyan/20 flex items-center justify-center mx-auto mb-6 glow">
          <Shield className="h-10 w-10 text-accent-cyan" />
        </div>
        <h1 className="text-4xl font-mono font-bold text-gradient mb-3">ArtifactX</h1>
        <p className="text-forensic-400 text-lg mb-8 max-w-md mx-auto">
          Digital forensic analysis platform for extracting and analyzing evidence from mobile applications
        </p>
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="status-dot status-dot-active" />
          <span className="text-sm text-forensic-500 font-mono">System Online</span>
        </div>
        <Link to="/cases" className="btn-primary inline-flex items-center gap-2">
          Access Dashboard
        </Link>
      </div>
    </div>
  );
}

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <Layout sidebarCollapsed={sidebarCollapsed} onSidebarToggle={() => setSidebarCollapsed(!sidebarCollapsed)}>
      <Routes>
        <Route path="/" element={<HomeScreen />} />
        <Route path="/cases" element={<CaseListPage />} />
        <Route path="/cases/create" element={<CaseForm />} />
        <Route path="/cases/:id" element={<CaseDetailPage />} />
        <Route path="/cases/:id/edit" element={<CaseForm />} />
        <Route path="/cases/:caseId/search" element={<SearchPage />} />
        <Route path="/cases/:caseId/dashboard" element={<DashboardPage />} />
        <Route path="/cases/:caseId/reports" element={<ReportsPage />} />
        <Route path="/cases/:caseId/logs" element={<LogsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;