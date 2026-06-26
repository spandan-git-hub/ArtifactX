import axios from 'axios';

const API_BASE = '/api';

// Generate a PDF report
export const generateReport = async (caseId, options = {}) => {
  const response = await axios.post(`${API_BASE}/cases/${caseId}/reports`, {
    report_type: options.reportType || 'full',
    include_evidence: options.includeEvidence !== false,
    include_timeline: options.includeTimeline !== false,
    include_deleted: options.includeDeleted !== false,
    include_correlations: options.includeCorrelations !== false,
  });
  return response.data;
};

// Download a report
export const downloadReport = (caseId, filename) => {
  window.open(`${API_BASE}/reports/download/${caseId}/${filename}`, '_blank');
};

// Get evidence summary
export const getEvidenceSummary = async (caseId) => {
  const response = await axios.post(`${API_BASE}/cases/${caseId}/reports/summary`);
  return response.data;
};

// Get timeline summary
export const getTimelineSummary = async (caseId) => {
  const response = await axios.post(`${API_BASE}/cases/${caseId}/reports/timeline`);
  return response.data;
};

// Get deleted messages summary
export const getDeletedSummary = async (caseId) => {
  const response = await axios.post(`${API_BASE}/cases/${caseId}/reports/deleted`);
  return response.data;
};

// Default export
export default {
  generateReport,
  downloadReport,
  getEvidenceSummary,
  getTimelineSummary,
  getDeletedSummary,
};