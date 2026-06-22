import { useState, useCallback } from 'react';
import * as reportService from '../services/reportService';

/**
 * Hook for report generation
 */
export const useReports = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastReport, setLastReport] = useState(null);

  const generateReport = useCallback(async (caseId, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const result = await reportService.generateReport(caseId, options);
      setLastReport(result);
      return result;
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate report');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadReport = useCallback((caseId, filename) => {
    reportService.downloadReport(caseId, filename);
  }, []);

  return {
    loading,
    error,
    lastReport,
    generateReport,
    downloadReport,
  };
};

/**
 * Hook for report summaries
 */
export const useReportSummaries = (caseId) => {
  const [evidenceSummary, setEvidenceSummary] = useState(null);
  const [timelineSummary, setTimelineSummary] = useState(null);
  const [deletedSummary, setDeletedSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadSummaries = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [evidence, timeline, deleted] = await Promise.all([
        reportService.getEvidenceSummary(caseId),
        reportService.getTimelineSummary(caseId),
        reportService.getDeletedSummary(caseId),
      ]);

      setEvidenceSummary(evidence);
      setTimelineSummary(timeline);
      setDeletedSummary(deleted);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load summaries');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  return {
    evidenceSummary,
    timelineSummary,
    deletedSummary,
    loading,
    error,
    loadSummaries,
  };
};