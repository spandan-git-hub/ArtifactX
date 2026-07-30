import { useState } from 'react';
import { useEvidence } from '../../hooks/useEvidence';
import { Upload, FileArchive, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

const EvidenceUploader = ({ caseId, onUploadSuccess }) => {
  const { uploadEvidence, loading, error } = useEvidence();
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0] || null;
    setSelectedFile(file);
    setUploadSuccess(false);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setUploadSuccess(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    try {
      const uploadedEvidence = await uploadEvidence(caseId, selectedFile);
      setUploadSuccess(true);
      setSelectedFile(null);
      onUploadSuccess?.(uploadedEvidence);
    } catch (err) {
      // error handled by hook
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
          <Upload className="h-5 w-5 text-accent-emerald" />
        </div>
        <div>
          <h3 className="font-semibold text-forensic-100">Upload Evidence</h3>
          <p className="text-sm text-forensic-500">ZIP packages, databases, or media files</p>
        </div>
      </div>

      <form onSubmit={handleUpload}>
        <div
          className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
            dragActive
              ? 'border-accent-cyan bg-accent-cyan/5'
              : 'border-forensic-700 hover:border-forensic-600'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <FileArchive className="h-12 w-12 text-forensic-500 mx-auto mb-4" />
          <p className="text-forensic-300 mb-1">
            Drag and drop evidence file here
          </p>
          <p className="text-sm text-forensic-500 mb-4">
            or click to browse files
          </p>
          <input
            type="file"
            className="file-input"
            onChange={handleFileChange}
            disabled={loading}
            accept=".zip,.db,.sqlite,.sqlite3,.vid"
          />
        </div>

        {selectedFile && (
          <div className="mt-4 p-4 bg-forensic-800/50 rounded-lg border border-forensic-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-cyan/20 flex items-center justify-center">
                  <FileArchive className="h-5 w-5 text-accent-cyan" />
                </div>
                <div>
                  <p className="text-forensic-100 font-medium truncate max-w-xs">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-forensic-500">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                className="text-forensic-500 hover:text-forensic-300"
              >
                &times;
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-center gap-2 text-accent-rose text-sm">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {uploadSuccess && (
          <div className="mt-4 flex items-center gap-2 text-accent-emerald text-sm">
            <CheckCircle className="h-4 w-4" />
            Evidence uploaded successfully! File is being processed.
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !selectedFile}
          className="btn-primary w-full mt-4"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Upload Evidence
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default EvidenceUploader;
