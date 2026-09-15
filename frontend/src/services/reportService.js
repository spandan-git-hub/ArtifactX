import axios from 'axios';

const API_BASE = '/api';

/**
 * Generate a court-ready PDF report streamed directly into the browser
 * with zero files stored on the workspace disk.
 */
export const generateCourtReportStream = async (caseId, options = {}) => {
  const payload = {
    case_id: parseInt(caseId, 10),
    report_type: options.reportType || 'full',
    include_evidence: options.includeEvidence !== false,
    include_timeline: options.includeTimeline !== false,
    include_deleted: options.includeDeleted !== false,
    include_correlations: options.includeCorrelations !== false,
    include_custody_log: options.includeCustodyLog !== false,
    lead_analyst: options.leadAnalyst || 'Forensic Examiner',
    agency: options.agency || 'Digital Forensics Unit',
    case_notes: options.caseNotes || '',
    sworn_declaration: options.swornDeclaration !== false,
  };

  const response = await axios.post(`${API_BASE}/cases/${caseId}/reports`, payload, {
    responseType: 'blob',
  });

  // Extract filename from Content-Disposition header
  let filename = `ArtifactX_CourtReport_Case${caseId}.pdf`;
  const disposition = response.headers['content-disposition'];
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const reportId = response.headers['x-report-id'] || '';
  const sha256 = response.headers['x-report-hash'] || '';
  const totalPages = parseInt(response.headers['x-total-pages'] || '1', 10);

  // Trigger immediate browser download
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);

  return {
    reportId,
    filename,
    sha256,
    totalPages,
    status: 'completed',
  };
};

/**
 * Fetch past generated report history metadata from database
 */
export const getReportHistory = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/history`);
  return response.data;
};

/**
 * Download a past generated report by report ID via direct streaming
 */
export const downloadHistoricalReport = async (caseId, reportId, suggestedFilename) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/${reportId}/download`, {
    responseType: 'blob',
  });

  let filename = suggestedFilename || `ArtifactX_Report_${reportId}.pdf`;
  const disposition = response.headers['content-disposition'];
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = new Blob([response.data], { type: 'application/pdf' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);
};

// Summary endpoints
export const getEvidenceSummary = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/summary`);
  return response.data;
};

export const getTimelineSummary = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/timeline`);
  return response.data;
};

export const getDeletedSummary = async (caseId) => {
  const response = await axios.get(`${API_BASE}/cases/${caseId}/reports/deleted`);
  return response.data;
};

// Legacy compatibility
export const generateReport = generateCourtReportStream;
export const downloadReport = (caseId, filename) => {
  window.open(`${API_BASE}/reports/download/${caseId}/${filename}`, '_blank');
};

export default {
  generateCourtReportStream,
  generateReport,
  downloadReport,
  getReportHistory,
  downloadHistoricalReport,
  getEvidenceSummary,
  getTimelineSummary,
  getDeletedSummary,
};
