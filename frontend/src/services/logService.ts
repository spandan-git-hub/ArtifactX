import axios from 'axios';

const API_BASE = '/api';

// Get analysis logs
export const getAnalysisLogs = async (params = {}) => {
  const response = await axios.get(`${API_BASE}/logs/analysis`, { params });
  return response.data;
};

// Get error logs
export const getErrorLogs = async (params = {}) => {
  const response = await axios.get(`${API_BASE}/logs/errors`, { params });
  return response.data;
};

// Get activity logs
export const getActivityLogs = async (params = {}) => {
  const response = await axios.get(`${API_BASE}/logs/activity`, { params });
  return response.data;
};

// Get log summary for a case
export const getLogSummary = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/logs/summary`);
  return response.data;
};

// Default export
export default {
  getAnalysisLogs,
  getErrorLogs,
  getActivityLogs,
  getLogSummary,
};