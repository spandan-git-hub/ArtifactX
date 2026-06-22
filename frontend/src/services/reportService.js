import axios from 'axios';

const API_BASE = '/api';

/**
 * Report service for API calls
 */
export const reportService = {
  /**
   * Generate a PDF report
   */
  generateReport: async (caseId, options = {}) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/reports`, {
      report_type: options.reportType || 'full',
      include_evidence: options.includeEvidence !== false,
      include_timeline: options.includeTimeline !== false,
      include_deleted: options.includeDeleted !== false,
      include_correlations: options.includeCorrelations !== false,
    });
    return response.data;
  },

  /**
   * Get evidence summary
   */
  getEvidenceSummary: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/summary`);
    return response.data;
  },

  /**
   * Get timeline summary
   */
  getTimelineSummary: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/timeline`);
    return response.data;
  },

  /**
   * Get deleted messages summary
   */
  getDeletedSummary: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/deleted`);
    return response.data;
  },

  /**
   * Download a report
   */
  downloadReport: (caseId, filename) => {
    window.open(`${API_BASE}/reports/download/${caseId}/${filename}`, '_blank');
  },
};