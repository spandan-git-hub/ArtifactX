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
    const findings = [];
    const limit = 1000;
    let offset = 0;
    while (true) {
      const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings`, {
        params: { ...params, limit, offset },
      });
      const page = response.data;
      findings.push(...page);
      if (page.length < limit) return findings;
      offset += page.length;
    }
  },

  // Get specific carved finding detail
  getRecoveryFinding: async (caseId, findingId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings/${findingId}`);
    return response.data;
  },
};

export default recoveryService;
