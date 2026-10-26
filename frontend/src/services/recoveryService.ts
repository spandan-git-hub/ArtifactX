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
    const rawFindings: any[] = [];
    const limit = 1000;
    let offset = 0;
    while (true) {
      const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings`, {
        params: { ...params, limit, offset },
      });
      const page = response.data;
      if (Array.isArray(page)) {
        rawFindings.push(...page);
        if (page.length < limit) break;
        offset += page.length;
      } else if (page?.findings && Array.isArray(page.findings)) {
        rawFindings.push(...page.findings);
        break;
      } else {
        break;
      }
    }

    // Deduplicate findings by finding_id or composite identity
    const seen = new Set<string>();
    return rawFindings.filter((f: any) => {
      const key = f.finding_id || (f.id ? `id_${f.id}` : `${f.source_app}_${f.table_name}_${f.byte_offset}_${f.raw_payload_hash}`);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  },

  // Get specific carved finding detail
  getRecoveryFinding: async (caseId: any, findingId: any) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/recovery/findings/${findingId}`);
    return response.data;
  },
};

export default recoveryService;
