import { useParams } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import LogsViewer from '../components/logs/LogsViewer';

/**
 * Logs page component - forensic audit trail viewer
 */
const LogsPage = () => {
  const { caseId: caseIdParam } = useParams();
  const caseId = caseIdParam ? parseInt(caseIdParam, 10) : undefined;

  return (
    <CaseWorkspacePage>
      <div className="animate-in space-y-6">
        <LogsViewer caseId={caseId} />
      </div>
    </CaseWorkspacePage>
  );
};

export default LogsPage;