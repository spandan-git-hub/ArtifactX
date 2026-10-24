import axios from 'axios';

const API_BASE = '/api';

export const recoveryService = {
  // Trigger physical SQLite carving run
  runRecovery: async (caseId: any, options: any = {}) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/recovery/run`, options);
    return response.data;
  },

  // List past recovery runs for a case
  getRecoveryRuns: async (caseId: any) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/runs`);
    return response.data;
  },

  // List physically carved findings
  getRecoveryFindings: async (caseId: any, params: any = {}): Promise<any[]> => {
    const findings: any[] = [];
    const limit = 1000;
    let offset = 0;
    while (true) {
      const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings`, {
        params: { ...params, limit, offset },
      });
      const page = response.data;
      if (Array.isArray(page)) {
        findings.push(...page);
        if (page.length < limit) return findings;
        offset += page.length;
      } else if (page?.findings && Array.isArray(page.findings)) {
        return page.findings;
      } else {
        return findings;
      }
    }
  },

  // Get specific carved finding detail
  getRecoveryFinding: async (caseId: any, findingId: any) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings/${findingId}`);
    return response.data;
  },
};

export default recoveryService;
