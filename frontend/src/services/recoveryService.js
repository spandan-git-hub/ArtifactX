import axios from 'axios';

const API_BASE = '/api';

export const recoveryService = {
  // Trigger physical SQLite carving run
  runRecovery: async (caseId, options = {}) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/recovery/run`, options);
    return response.data;
  },

  // List past recovery runs for a case
  getRecoveryRuns: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/runs`);
    return response.data;
  },

  // List physically carved findings
  getRecoveryFindings: async (caseId, params = {}) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings`, { params });
    return response.data;
  },

  // Get specific carved finding detail
  getRecoveryFinding: async (caseId, findingId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings/${findingId}`);
    return response.data;
  },
};

export default recoveryService;
