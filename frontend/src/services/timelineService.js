import axios from 'axios';

const API_BASE = '/api';

export const timelineService = {
  // Get timeline events for a case with optional filter parameters
  getTimeline: async (caseId, params = {}) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/timeline`, { params });
    return response.data;
  },

  // Filter timeline events via POST payload
  filterTimeline: async (caseId, filterParams = {}) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/timeline/filter`, filterParams);
    return response.data;
  },

  // Get histogram time-density data for a case
  getHistogram: async (caseId, params = {}) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/timeline/histogram`, { params });
    return response.data;
  },

  // Rebuild timeline from evidence for a case
  buildTimeline: async (caseId) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/timeline/build`);
    return response.data;
  },
};

export default timelineService;
