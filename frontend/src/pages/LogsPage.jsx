import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ClipboardList } from 'lucide-react';
import LogsViewer from '../components/logs/LogsViewer';

/**
 * Logs page component - forensic audit trail viewer
 */
const LogsPage = () => {
  const { caseId: caseIdParam } = useParams();
  const caseId = caseIdParam ? parseInt(caseIdParam, 10) : undefined;

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-forensic-500 mb-3">
          <Link to="/cases" className="hover:text-accent-cyan flex items-center gap-1 transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Cases
          </Link>
          {caseId && (
            <>
              <span className="text-forensic-700">/</span>
              <Link to={`/cases/${caseId}`} className="hover:text-accent-cyan transition-colors">
                Case {caseId}
              </Link>
            </>
          )}
          <span className="text-forensic-700">/</span>
          <span className="text-accent-cyan">Audit Logs</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-accent-violet/20">
            <ClipboardList className="h-6 w-6 text-accent-violet" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-forensic-50">Audit Logs</h1>
            <p className="text-forensic-500">
              View activity, analysis, and error logs for forensic tracking
            </p>
          </div>
        </div>
      </div>

      <LogsViewer caseId={caseId} />
    </div>
  );
};

export default LogsPage;