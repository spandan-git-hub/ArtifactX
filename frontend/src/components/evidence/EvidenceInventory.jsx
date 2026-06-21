import { useState, useEffect } from 'react';
import { useEvidence } from '../hooks/useEvidence';
import * as evidenceService from '../services/evidenceService';

const EvidenceInventory = ({ caseId }) => {
  const { evidences, loading, error, loadEvidences, deleteEvidence } = useEvidence();
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null);
  const [evidenceFiles, setEvidenceFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesError, setFilesError] = useState(null);

  useEffect(() => {
    if (caseId) {
      loadEvidences(caseId);
    }
  }, [caseId, loadEvidences]);

  const handleLoadFiles = async (evidenceId) => {
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

  const handleDeleteEvidence = async (evidenceId) => {
    if (window.confirm('Are you sure you want to delete this evidence?')) {
      try {
        await deleteEvidence(evidenceId);
        // Remove from list
        setEvidences((prev) => prev.filter((e) => e.id !== evidenceId));
        if (selectedEvidenceId === evidenceId) {
          setSelectedEvidenceId(null);
          setEvidenceFiles([]);
        }
      } catch (err) {
        // error handled by hook
      }
    }
  };

  if (loading) return <p className="text-center py-4">Loading evidences...</p>;
  if (error) return <p className="text-center text-red-600">{error}</p>;

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="font-semibold mb-2">Evidence List</h2>
      {evidences.length === 0 ? (
        <p className="text-gray-500">No evidence uploaded yet.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Filename
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    SHA-256
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {evidences.map((ev) => (
                  <tr key={ev.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {ev.original_filename}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {ev.evidence_type === 'zip' ? 'ZIP Package' : 'File'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {ev.sha256}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {(ev.upload_size || 0).toLocaleString()} bytes
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                      <button
                        onClick={() => handleLoadFiles(ev.id)}
                        className={`
                          btn text-xs font-semibold
                          ${selectedEvidenceId === ev.id ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-800'}
                          px-3 py-1 rounded hover:bg-gray-300
                        `}
                      >
                        {selectedEvidenceId === ev.id ? 'View Files' : 'View Files'}
                      </button>
                      <button
                        onClick={() => handleDeleteEvidence(ev.id)}
                        className="ml-2 text-xs font-semibold text-red-600 hover:text-red-800"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Files panel */}
          {selectedEvidenceId && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold mb-2">
                Files in Evidence:
                {evidences.find((e) => e.id === selectedEvidenceId)?.original_filename}
              </h3>
              {filesLoading ? (
                <p className="text-center py-4">Loading files...</p>
              ) : filesError ? (
                <p className="text-center text-red-600">{filesError}</p>
              ) : evidenceFiles.length === 0 ? (
                <p className="text-gray-500">No files in this evidence.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Relative Path
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Size
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          MIME Type
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {evidenceFiles.map((f) => (
                        <tr key={f.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {f.relative_path}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {f.size.toLocaleString()} bytes
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {f.mime_type || 'application/octet-stream'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                            <a
                              href="#"
                              onClick={(e) => {
                                e.preventDefault();
                                // Trigger download
                                evidenceService
                                  .downloadEvidenceFile(selectedEvidenceId, f.id)
                                  .then((blob) => {
                                    const url = window.URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = f.relative_path.split('/').pop() || 'file';
                                    a.click();
                                    window.URL.revokeObjectURL(url);
                                  })
                                  .catch(console.error);
                              }}
                              className="text-blue-600 hover:underline"
                            >
                              Download
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default EvidenceInventory;