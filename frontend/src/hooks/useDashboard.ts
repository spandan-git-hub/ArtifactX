import { useState, useCallback } from 'react';
import * as dashboardService from '../services/dashboardService';

/**
 * Hook for case statistics
 */
export const useCaseStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadStats = useCallback(async (caseId) => {
    setLoading(true);
    setError(null);

    try {
      const data = await dashboardService.getCaseStats(caseId);
      setStats(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load stats');
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    stats,
    loading,
    error,
    loadStats,
  };
};

/**
 * Hook for case overview (all dashboard data)
 */
export const useCaseOverview = () => {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadOverview = useCallback(async (caseId) => {
    setLoading(true);
    setError(null);

    try {
      const data = await dashboardService.getCaseOverview(caseId);
      setOverview(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load overview');
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    overview,
    loading,
    error,
    loadOverview,
  };
};

/**
 * Hook for correlation statistics
 */
export const useCorrelationStats = () => {
  const [correlationStats, setCorrelationStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadCorrelationStats = useCallback(async (caseId) => {
    setLoading(true);
    setError(null);

    try {
      const data = await dashboardService.getCorrelationStats(caseId);
      setCorrelationStats(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load correlation stats');
      setCorrelationStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    correlationStats,
    loading,
    error,
    loadCorrelationStats,
  };
};

/**
 * Hook for timeline statistics
 */
export const useTimelineStats = () => {
  const [timelineStats, setTimelineStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadTimelineStats = useCallback(async (caseId) => {
    setLoading(true);
    setError(null);

    try {
      const data = await dashboardService.getTimelineStats(caseId);
      setTimelineStats(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load timeline stats');
      setTimelineStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    timelineStats,
    loading,
    error,
    loadTimelineStats,
  };
};