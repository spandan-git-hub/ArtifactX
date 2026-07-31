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
    <div className="animate-in space-y-6">
      <LogsViewer caseId={caseId} />
    </div>
  );
};

export default LogsPage;