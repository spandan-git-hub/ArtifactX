import { useParams } from 'react-router-dom';
import LogsViewer from '../components/logs/LogsViewer';

/**
 * Logs page component
 */
const LogsPage = () => {
  const { caseId: caseIdParam } = useParams();
  const caseId = caseIdParam ? parseInt(caseIdParam, 10) : undefined;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-gray-600 mt-1">
          View activity, analysis, and error logs for forensic tracking
        </p>
      </div>

      <LogsViewer caseId={caseId} />
    </div>
  );
};

export default LogsPage;