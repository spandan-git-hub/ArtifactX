import axios from 'axios';

const API_BASE = '/api';

/**
 * Log API service
 */
export const logService = {
  // Get analysis logs
  getAnalysisLogs: async (params = {}) => {
    const response = await axios.get(`${API_BASE}/logs/analysis`, { params });
    return response.data;
  },

  // Get error logs
  getErrorLogs: async (params = {}) => {
    const response = await axios.get(`${API_BASE}/logs/errors`, { params });
    return response.data;
  },

  // Get activity logs
  getActivityLogs: async (params = {}) => {
    const response = await axios.get(`${API_BASE}/logs/activity`, { params });
    return response.data;
  },

  // Get log summary for a case
  getLogSummary: async (caseId) => {
    const response = await axios.get(`${API_BASE}/logs/summary/${caseId}`);
    return response.data;
  },
};