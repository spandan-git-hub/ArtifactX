import axios from 'axios';

const API_BASE = '/api';

/**
 * Dashboard service for API calls
 */
export const dashboardService = {
  /**
   * Get comprehensive case statistics
   */
  getCaseStats: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/stats`);
    return response.data;
  },

  /**
   * Get correlation statistics for a case
   */
  getCorrelationStats: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation-stats`);
    return response.data;
  },

  /**
   * Get timeline statistics for a case
   */
  getTimelineStats: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/timeline-stats`);
    return response.data;
  },

  /**
   * Get comprehensive case overview for dashboard
   */
  getCaseOverview: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/overview`);
    return response.data;
  },
};