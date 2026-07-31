import { useState } from 'react';
import { useParams } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import EvidenceUploader from '../components/evidence/EvidenceUploader';
import EvidenceInventory from '../components/evidence/EvidenceInventory';

const EvidencePage = () => {
  const { caseId } = useParams();
  const [evidenceRefreshToken, setEvidenceRefreshToken] = useState(0);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null);

  const handleUploadSuccess = (uploadedEvidence) => {
    setSelectedEvidenceId(uploadedEvidence?.id ?? null);
    setEvidenceRefreshToken((token) => token + 1);
  };

  const handleDeleteSuccess = (deletedId) => {
    if (selectedEvidenceId === deletedId) {
      setSelectedEvidenceId(null);
    }
    setEvidenceRefreshToken((token) => token + 1);
  };

  return (
    <CaseWorkspacePage activeTab="overview">
      <div className="space-y-6 animate-in">
        {/* Upload Container */}
        <EvidenceUploader
          caseId={caseId}
          onUploadSuccess={handleUploadSuccess}
        />

        {/* Evidence Inventory & Artifact Inspector Container */}
        <EvidenceInventory
          caseId={caseId}
          refreshToken={evidenceRefreshToken}
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={(evId) => setSelectedEvidenceId(evId)}
          onDeleteSuccess={handleDeleteSuccess}
        />
      </div>
    </CaseWorkspacePage>
  );
};

export default EvidencePage;
