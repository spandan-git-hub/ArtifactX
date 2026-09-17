import axios from 'axios';

const API_BASE = '/api';

export const decryptionService = {
  detectFormat: async (evidenceId, fileId = null) => {
    const params = fileId ? { file_id: fileId } : {};
    const res = await axios.post(`${API_BASE}/evidence/${evidenceId}/decryption/detect`, null, { params });
    return res.data;
  },

  runDecryption: async (evidenceId, payload) => {
    const res = await axios.post(`${API_BASE}/evidence/${evidenceId}/decryption/run`, payload);
    return res.data;
  },

  getOperations: async (evidenceId) => {
    const res = await axios.get(`${API_BASE}/evidence/${evidenceId}/decryption/operations`);
    return res.data;
  },

  getEvidenceDerivedArtifacts: async (evidenceId) => {
    const res = await axios.get(`${API_BASE}/evidence/${evidenceId}/derived-artifacts`);
    return res.data;
  },

  getCaseDerivedArtifacts: async (caseId) => {
    const res = await axios.get(`${API_BASE}/cases/${caseId}/derived-artifacts`);
    return res.data;
  },

  getStreamUrl: (caseId, artifactId) => {
    return `${API_BASE}/cases/${caseId}/derived-artifacts/${artifactId}/stream`;
  },
};
