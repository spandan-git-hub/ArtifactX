import axios from 'axios';

const API_BASE = '/api';

export const evidenceService = {
  // Upload evidence for a case
  uploadEvidence: async (caseId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE}/evidence/upload?case_id=${caseId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // List evidences for a case
  getEvidences: async (caseId) => {
    const response = await axios.get(`${API_BASE}/evidence?case_id=${caseId}`);
    return response.data;
  },

  // Get evidence by ID
  getEvidence: async (evidenceId) => {
    const response = await axios.get(`${API_BASE}/evidence/${evidenceId}`);
    return response.data;
  },

  // List files within an evidence
  getEvidenceFiles: async (evidenceId) => {
    const response = await axios.get(`${API_BASE}/evidence/${evidenceId}/files`);
    return response.data;
  },

  // Download a specific file from evidence
  downloadEvidenceFile: async (evidenceId, fileId) => {
    const response = await axios.get(`${API_BASE}/evidence/${evidenceId}/files/${fileId}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Delete evidence
  deleteEvidence: async (evidenceId) => {
    await axios.delete(`${API_BASE}/evidence/${evidenceId}`);
  },
};