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
import { Shield, Loader2 } from 'lucide-react';
import { demoService } from './services/demoService';

function HomeScreen() {
  const [demoLoading, setDemoLoading] = useState(false);

  const handleCreateDemo = async () => {
    setDemoLoading(true);
    try {
      const stats = await demoService.createDemoCase();
      // Navigate to the new demo case
      window.location.href = `/cases/${stats.case_id}/dashboard`;
    } catch (err) {
      console.error('Failed to create demo case:', err);
      alert('Failed to create demo case. Please try again.');
      setDemoLoading(false);
    }
  };

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
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/cases" className="btn-primary inline-flex items-center gap-2">
            Access Dashboard
          </Link>
          <button
            onClick={handleCreateDemo}
            disabled={demoLoading}
            className="btn-secondary inline-flex items-center gap-2"
          >
            {demoLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating Demo...
              </>
            ) : (
              'Create Demo Case'
            )}
          </button>
        </div>
        <p className="text-xs text-forensic-600 mt-4">
          Demo mode creates sample WhatsApp data for testing
        </p>
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