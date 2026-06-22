import { useState, useCallback } from 'react';
import * as logService from '../services/logService';

/**
 * Hook for fetching analysis logs
 */
export const useAnalysisLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);

    try {
      const data = await logService.getAnalysisLogs(params);
      setLogs(data);
      return data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch analysis logs';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    logs,
    loading,
    error,
    fetchLogs,
  };
};

/**
 * Hook for fetching error logs
 */
export const useErrorLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);

    try {
      const data = await logService.getErrorLogs(params);
      setLogs(data);
      return data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch error logs';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    logs,
    loading,
    error,
    fetchLogs,
  };
};

/**
 * Hook for fetching activity logs
 */
export const useActivityLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);

    try {
      const data = await logService.getActivityLogs(params);
      setLogs(data);
      return data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch activity logs';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    logs,
    loading,
    error,
    fetchLogs,
  };
};

/**
 * Hook for fetching log summary
 */
export const useLogSummary = (caseId) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSummary = useCallback(async () => {
    if (!caseId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await logService.getLogSummary(caseId);
      setSummary(data);
      return data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch log summary';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  return {
    summary,
    loading,
    error,
    fetchSummary,
  };
};