import { useState, useEffect } from 'react';
import { useEvidence } from '../../hooks/useEvidence';
import * as evidenceService from '../../services/evidenceService';
import {
  FileArchive,
  Trash2,
  Loader2,
  Eye,
  Download,
  FolderOpen,
  FileText,
} from 'lucide-react';

const EvidenceInventory = ({ caseId, refreshToken = 0, selectedEvidenceId: propSelectedId, onSelectEvidence }) => {
  const { evidences, loading, error, loadEvidences, deleteEvidence } = useEvidence();
  const [internalSelectedId, setInternalSelectedId] = useState(null);
  const [evidenceFiles, setEvidenceFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesError, setFilesError] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(null);

  const selectedEvidenceId = propSelectedId !== undefined ? propSelectedId : internalSelectedId;
  const setSelectedEvidenceId = propSelectedId !== undefined ? onSelectEvidence : setInternalSelectedId;

  useEffect(() => {
    if (caseId) {
      loadEvidences(caseId);
    }
  }, [caseId, refreshToken, loadEvidences]);

  const handleLoadFiles = async (evidenceId) => {
    if (selectedEvidenceId === evidenceId) {
      setSelectedEvidenceId(null);
      setEvidenceFiles([]);
      return;
    }
    setSelectedEvidenceId(evidenceId);
    setFilesLoading(true);
    setFilesError(null);
    try {
      const files = await evidenceService.getEvidenceFiles(evidenceId);
      setEvidenceFiles(files);
    } catch (err) {
      setFilesError(
        err.response?.data?.detail || err.message || 'Failed to load evidence files'
      );
      setEvidenceFiles([]);
    } finally {
      setFilesLoading(false);
    }
  };

  const handleDeleteEvidence = async (evidenceId, e) => {
    e.stopPropagation();
    const evidence = evidences.find(ev => ev.id === evidenceId);
    if (window.confirm(`Delete evidence "${evidence?.original_filename}"? This cannot be undone.`)) {
      setDeleteLoading(evidenceId);
      try {
        await deleteEvidence(evidenceId);
      } catch (err) {
        // error handled by hook
      } finally {
        setDeleteLoading(null);
      }
    }
  };

  const handleDownloadFile = async (fileId, fileName) => {
    try {
      const blob = await evidenceService.downloadEvidenceFile(selectedEvidenceId, fileId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
        <span className="ml-2 text-forensic-400">Loading evidences...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
            <FolderOpen className="h-5 w-5 text-accent-emerald" />
          </div>
          <div>
            <h3 className="font-semibold text-forensic-100">Evidence Files</h3>
            <p className="text-sm text-forensic-500">{evidences.length} file(s) uploaded</p>
          </div>
        </div>
      </div>

      {evidences.length === 0 ? (
        <div className="text-center py-8">
          <FileText className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No evidence uploaded yet.</p>
          <p className="text-sm text-forensic-600 mt-1">Upload a ZIP or database file to get started.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>SHA-256</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {evidences.map((ev) => (
                <tr
                  key={ev.id}
                  className={selectedEvidenceId === ev.id ? 'bg-accent-cyan/5' : ''}
                >
                  <td>
                    <div className="flex items-center gap-2">
                      <FileArchive className="h-4 w-4 text-accent-cyan" />
                      <span className="text-forensic-100 font-medium truncate max-w-[200px]">
                        {ev.original_filename}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${
                      ev.evidence_type === 'zip' ? 'badge-cyan' :
                      ev.evidence_type === 'database' ? 'badge-violet' : 'badge-gray'
                    }`}>
                      {ev.evidence_type || 'file'}
                    </span>
                  </td>
                  <td className="text-forensic-400 font-mono text-sm">
                    {formatFileSize(ev.upload_size)}
                  </td>
                  <td>
                    <span className="hash-text text-xs">
                      {ev.sha256?.substring(0, 16)}...
                    </span>
                  </td>
                  <td>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleLoadFiles(ev.id)}
                        className={`btn-ghost p-1.5 ${
                          selectedEvidenceId === ev.id ? 'text-accent-cyan' : ''
                        }`}
                        title="View Files"
                      >
                        {filesLoading && selectedEvidenceId === ev.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                      <button
                        onClick={(e) => handleDeleteEvidence(ev.id, e)}
                        disabled={deleteLoading === ev.id}
                        className="btn-ghost p-1.5 text-accent-rose hover:bg-accent-rose/10"
                        title="Delete"
                      >
                        {deleteLoading === ev.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Files panel */}
      {selectedEvidenceId && (
        <div className="mt-6">
          <div className="flex items-center gap-2 mb-3">
            <FolderOpen className="h-4 w-4 text-accent-emerald" />
            <h4 className="font-semibold text-forensic-100">
              Extracted Files
            </h4>
            <span className="badge badge-emerald">{evidenceFiles.length}</span>
          </div>

          {filesLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-accent-cyan" />
              <span className="ml-2 text-forensic-400">Loading files...</span>
            </div>
          ) : filesError ? (
            <div className="alert alert-error">
              <span>{filesError}</span>
            </div>
          ) : evidenceFiles.length === 0 ? (
            <p className="text-forensic-500 text-sm">This evidence is a single file. Open the analysis section for extracted data.</p>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Path</th>
                    <th>Size</th>
                    <th>MIME Type</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {evidenceFiles.slice(0, 100).map((f) => (
                    <tr key={f.id}>
                      <td className="text-forensic-300 font-mono text-sm truncate max-w-[300px]">
                        {f.relative_path}
                      </td>
                      <td className="text-forensic-400 font-mono text-sm">
                        {formatFileSize(f.size)}
                      </td>
                      <td>
                        <span className="badge badge-gray">
                          {f.mime_type?.split('/')[1] || 'unknown'}
                        </span>
                      </td>
                      <td>
                        <button
                          onClick={() => handleDownloadFile(f.id, f.relative_path.split('/').pop())}
                          className="btn-ghost p-1.5"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {evidenceFiles.length > 100 && (
                <div className="p-3 text-center text-sm text-forensic-500 border-t border-forensic-700">
                  Showing 100 of {evidenceFiles.length} files
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EvidenceInventory;
