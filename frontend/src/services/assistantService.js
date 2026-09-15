import axios from 'axios';

const API_BASE = '/api';

export const assistantService = {
  /**
   * Submit an investigator natural language query over case messages and evidence.
   * @param {number|string} caseId
   * @param {{ query: string, jid?: string, limit?: number }} payload
   */
  queryAssistant: async (caseId, payload) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/assistant/query`, payload);
    return response.data;
  },

  /**
   * Execute chat sentiment classification, intention detection, and suspicion scoring.
   * @param {number|string} caseId
   * @param {{ jid?: string, message_ids?: string[] }} [payload]
   */
  analyzeSentiment: async (caseId, payload = {}) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/assistant/sentiment`, payload);
    return response.data;
  },
};

export default assistantService;
