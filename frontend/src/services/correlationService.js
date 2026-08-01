import axios from 'axios';

const API_BASE = '/api';

export const correlationService = {
  // Trigger full correlation engine for a case
  triggerCorrelation: async (caseId) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/correlate`);
    return response.data;
  },

  // Get raw correlation edges
  getCorrelationEdges: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation`);
    return response.data;
  },

  // Get resolved cross-app entities (contacts mapped by E.164, handle, display name)
  getEntityResolutions: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/entities`);
    return response.data;
  },

  // Get cross-app message correlation matrix within a time window
  getMessageMatrix: async (caseId, windowSeconds = 300) => {
    const response = await axios.get(
      `${API_BASE}/cases/${caseId}/correlation/matrix?window_seconds=${windowSeconds}`
    );
    return response.data;
  },
};

export default correlationService;
