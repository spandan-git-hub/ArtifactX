import { useState, useCallback } from 'react';
import * as reportService from '../services/reportService';

/**
 * Hook for court-ready report generation and history tracking
 */
export const useReports = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastReport, setLastReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const loadHistory = useCallback(async (caseId) => {
    if (!caseId) return;
    setLoadingHistory(true);
    try {
      const data = await reportService.getReportHistory(caseId);
      setHistory(data.reports || []);
    } catch (err) {
      console.error('Failed to load report history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const generateReport = useCallback(async (caseId, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const result = await reportService.generateCourtReportStream(caseId, options);
      setLastReport(result);
      // Automatically refresh history after generating a report
      await loadHistory(caseId);
      return result;
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to generate court report';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [loadHistory]);

  const reDownloadReport = useCallback(async (caseId, reportId, filename) => {
    try {
      await reportService.downloadHistoricalReport(caseId, reportId, filename);
    } catch (err) {
      console.error('Failed to download historical report:', err);
      throw err;
    }
  }, []);

  return {
    loading,
    error,
    lastReport,
    history,
    loadingHistory,
    loadHistory,
    generateReport,
    reDownloadReport,
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
    if (!caseId) {
      setEvidenceSummary(null);
      setTimelineSummary(null);
      setDeletedSummary(null);
      return;
    }

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
