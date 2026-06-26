import axios from 'axios';

const API_BASE = '/api';

// Get comprehensive case statistics
export const getCaseStats = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/stats`);
  return response.data;
};

// Get correlation statistics
export const getCorrelationStats = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation-stats`);
  return response.data;
};

// Get timeline statistics
export const getTimelineStats = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/timeline-stats`);
  return response.data;
};

// Get comprehensive case overview for dashboard
export const getCaseOverview = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/overview`);
  return response.data;
};

// Default export
export default {
  getCaseStats,
  getCorrelationStats,
  getTimelineStats,
  getCaseOverview,
};