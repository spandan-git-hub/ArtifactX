import axios from 'axios';

const API_BASE = '/api';

// Upload evidence for a case
export const uploadEvidence = async (caseId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_BASE}/evidence/upload?case_id=${caseId}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// List evidences for a case
export const getEvidences = async (caseId) => {
  const response = await axios.get(`${API_BASE}/evidence?case_id=${caseId}`);
  return response.data;
};

// Get evidence by ID
export const getEvidence = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/evidence/${evidenceId}`);
  return response.data;
};

// List files within an evidence
export const getEvidenceFiles = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/evidence/${evidenceId}/files`);
  return response.data;
};

// Verify evidence cryptographic hashes (SHA-256, MD5, SHA-1)
export const verifyEvidenceHashes = async (evidenceId) => {
  const response = await axios.post(`${API_BASE}/evidence/${evidenceId}/verify-hashes`);
  return response.data;
};

// Download a specific file from evidence
export const downloadEvidenceFile = async (evidenceId, fileId) => {
  const response = await axios.get(`${API_BASE}/evidence/${evidenceId}/files/${fileId}`, {
    responseType: 'blob',
  });
  return response.data;
};

// Extract EXIF metadata for an evidence file or all images in evidence
export const getExifMetadata = async (evidenceId, fileId = null) => {
  const query = fileId ? `?file_id=${fileId}` : '';
  const response = await axios.get(`${API_BASE}/evidence/${evidenceId}/exif${query}`);
  return response.data;
};

// Inspect raw SQLite database tables, schemas, and rows
export const inspectSqliteDatabase = async (evidenceId, { fileId = null, tableName = null, limit = 50, offset = 0 } = {}) => {
  const params = new URLSearchParams();
  if (fileId) params.append('file_id', fileId);
  if (tableName) params.append('table_name', tableName);
  params.append('limit', limit);
  params.append('offset', offset);

  const response = await axios.get(`${API_BASE}/evidence/${evidenceId}/sqlite-inspect?${params.toString()}`);
  return response.data;
};

// Delete evidence
export const deleteEvidence = async (evidenceId) => {
  await axios.delete(`${API_BASE}/evidence/${evidenceId}`);
};

// Default export for backward compatibility
export default {
  uploadEvidence,
  getEvidences,
  getEvidence,
  getEvidenceFiles,
  verifyEvidenceHashes,
  downloadEvidenceFile,
  getExifMetadata,
  inspectSqliteDatabase,
  deleteEvidence,
};