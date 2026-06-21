import { useState } from 'react';
import { useEvidence } from '../hooks/useEvidence';

const EvidenceUploader = ({ caseId }) => {
  const { uploadEvidence, loading, error } = useEvidence();
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0] || null);
    setUploadSuccess(false);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    try {
      await uploadEvidence(caseId, selectedFile);
      setUploadSuccess(true);
      // Optionally reset form
      setSelectedFile(null);
    } catch (err) {
      // error handled by hook
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-4">
      <h2 className="font-semibold mb-2">Upload Evidence</h2>
      <form onSubmit={handleUpload} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select file (ZIP or other)
          </label>
          <input
            type="file"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4
                       file:rounded file:border-0 file:bg-primary-50 file:text-primary-600
                       hover:file:bg-primary-100"
            onChange={handleFileChange}
            disabled={loading}
          />
          {selectedFile && (
            <p className="mt-1 text-xs text-gray-600">
              Selected: {selectedFile.name}
            </p>
          )}
        </div>
        <button
          type="submit"
          disabled={loading || !selectedFile}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Uploading...' : 'Upload Evidence'}
        </button>
      </form>
      {error && <p className="mt-2 text-red-600 text-sm">{error}</p>}
      {uploadSuccess && (
        <p className="mt-2 text-green-600 text-sm">
          Evidence uploaded successfully!
        </p>
      )}
    </div>
  );
};

export default EvidenceUploader;