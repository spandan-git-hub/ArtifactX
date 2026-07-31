import { useState, useEffect } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { caseService } from '../services/caseService';
import { Header } from '../components/layout';
import ForensicWorkflowStepper from '../components/workspace/ForensicWorkflowStepper';
import {
  Database,
  LayoutDashboard,
  Search,
  FileText,
  ClipboardList,
  Loader2,
  AlertCircle,
  ArrowLeft,
  ShieldCheck,
} from 'lucide-react';

const CaseWorkspacePage = ({ children, activeTab }) => {
  const params = useParams();
  const caseId = params.id || params.caseId;
  const location = useLocation();

  const [workspace, setWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchWorkspace = async () => {
      if (!caseId) return;
      try {
        setLoading(true);
        const data = await caseService.getCaseWorkspace(caseId);
        setWorkspace(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load case workspace:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load case workspace');
      } finally {
        setLoading(false);
      }
    };

    fetchWorkspace();
  }, [caseId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-forensic-950">
        <Loader2 className="h-7 w-7 animate-spin text-accent-cyan" />
      </div>
    );
  }

  if (error || !workspace) {
    return (
      <div className="min-h-screen p-6 bg-forensic-950">
        <div className="card max-w-md mx-auto border-accent-rose/30">
          <div className="flex items-center gap-3 text-accent-rose mb-3">
            <AlertCircle className="h-5 w-5" />
            <span className="font-semibold">Error Loading Case</span>
          </div>
          <p className="text-forensic-400 text-sm mb-4">{error || 'Case workspace unavailable'}</p>
          <Link to="/cases" className="btn-secondary inline-flex items-center gap-2 text-xs">
            <ArrowLeft className="h-3.5 w-3.5" />
            Return to Cases
          </Link>
        </div>
      </div>
    );
  }

  const { case: caseData, hash_integrity_score, analysis_stage } = workspace;

  const tabs = [
    { id: 'overview', label: 'Evidence & Artifacts', path: `/cases/${caseId}/evidence`, icon: Database },
    { id: 'dashboard', label: 'Dashboard', path: `/cases/${caseId}/dashboard`, icon: LayoutDashboard },
    { id: 'search', label: 'Search', path: `/cases/${caseId}/search`, icon: Search },
    { id: 'reports', label: 'Reports', path: `/cases/${caseId}/reports`, icon: FileText },
    { id: 'logs', label: 'Audit Logs', path: `/cases/${caseId}/logs`, icon: ClipboardList },
  ];

  return (
    <div className="min-h-screen bg-forensic-950">
      <Header
        breadcrumbs={[
          { label: 'ArtifactX', path: '/' },
          { label: 'Cases', path: '/cases' },
          { label: caseData.name, path: `/cases/${caseId}` },
        ]}
      />

      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Sleek Minimal Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-forensic-800">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold font-mono text-forensic-50">{caseData.name}</h1>
            <span
              className={`badge text-xs ${
                caseData.status === 'active'
                  ? 'badge-emerald'
                  : caseData.status === 'archived'
                  ? 'badge-amber'
                  : 'badge-gray'
              }`}
            >
              {caseData.status || 'active'}
            </span>
            <span className="text-xs font-mono text-accent-emerald bg-accent-emerald/10 px-2 py-0.5 rounded border border-accent-emerald/20 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              {hash_integrity_score}% Integrity Verified
            </span>
          </div>

          {/* Compact Workflow Stepper Inline */}
          <ForensicWorkflowStepper
            currentStage={analysis_stage.stage_number}
            caseId={caseId}
            currentPath={location.pathname}
          />
        </div>

        {/* Clean Sub-Navigation Tabs */}
        <div className="flex items-center gap-1 border-b border-forensic-800 pb-px">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive =
              activeTab === tab.id ||
              (tab.id === 'overview' && location.pathname === `/cases/${caseId}`) ||
              location.pathname === tab.path;

            return (
              <Link
                key={tab.id}
                to={tab.path}
                className={`
                  flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px
                  ${
                    isActive
                      ? 'border-accent-cyan text-accent-cyan font-semibold'
                      : 'border-transparent text-forensic-400 hover:text-forensic-200'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Direct Child View */}
        <div>{children}</div>
      </div>
    </div>
  );
};

export default CaseWorkspacePage;
