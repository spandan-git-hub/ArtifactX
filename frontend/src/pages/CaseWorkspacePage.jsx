import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { caseService } from '../services/caseService';
import { Header } from '../components/layout';
import { Loader2, AlertCircle, ArrowLeft, ShieldCheck } from 'lucide-react';

const CaseWorkspacePage = ({ children }) => {
  const params = useParams();
  const caseId = params.id || params.caseId;

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

  const { case: caseData, hash_integrity_score } = workspace;

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
        {/* Sleek Minimal Header - Case Name & Integrity Status Only */}
        <div className="flex items-center justify-between pb-3 border-b border-forensic-800">
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
          </div>

          <span className="text-xs font-mono text-accent-emerald bg-accent-emerald/10 px-2.5 py-1 rounded border border-accent-emerald/20 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            {hash_integrity_score}% Integrity Verified
          </span>
        </div>

        {/* Child View */}
        <div>{children}</div>
      </div>
    </div>
  );
};

export default CaseWorkspacePage;
