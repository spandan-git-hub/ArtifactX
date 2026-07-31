import { useState, useCallback, useEffect } from 'react';
import timelineService from '../services/timelineService';

export const useTimeline = (caseId, initialFilters = {}) => {
  const [events, setEvents] = useState([]);
  const [histogram, setHistogram] = useState(null);
  const [loading, setLoading] = useState(true);
  const [histogramLoading, setHistogramLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({
    search: '',
    sourceApp: 'all', // 'all', 'whatsapp', 'telegram'
    eventType: 'all', // 'all', 'message', 'deleted_gap', 'evidence_ingest'
    startDate: '',
    endDate: '',
    interval: 'day',
    ...initialFilters,
  });

  const fetchTimeline = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.sourceApp && filters.sourceApp !== 'all') params.source_app = filters.sourceApp;
      if (filters.eventType && filters.eventType !== 'all') params.event_type = filters.eventType;
      if (filters.startDate) params.start_date = new Date(filters.startDate).toISOString();
      if (filters.endDate) params.end_date = new Date(filters.endDate).toISOString();

      const data = await timelineService.getTimeline(caseId, params);
      setEvents(data);
    } catch (err) {
      console.error('Error fetching timeline events:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch timeline');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [caseId, filters.search, filters.sourceApp, filters.eventType, filters.startDate, filters.endDate]);

  const fetchHistogram = useCallback(async () => {
    if (!caseId) return;
    setHistogramLoading(true);
    try {
      const params = { interval: filters.interval };
      if (filters.search) params.search = filters.search;
      if (filters.sourceApp && filters.sourceApp !== 'all') params.source_app = filters.sourceApp;
      if (filters.eventType && filters.eventType !== 'all') params.event_type = filters.eventType;
      if (filters.startDate) params.start_date = new Date(filters.startDate).toISOString();
      if (filters.endDate) params.end_date = new Date(filters.endDate).toISOString();

      const data = await timelineService.getHistogram(caseId, params);
      setHistogram(data);
    } catch (err) {
      console.error('Error fetching timeline histogram:', err);
      setHistogram(null);
    } finally {
      setHistogramLoading(false);
    }
  }, [caseId, filters.interval, filters.search, filters.sourceApp, filters.eventType, filters.startDate, filters.endDate]);

  const rebuildTimeline = useCallback(async () => {
    if (!caseId) return;
    setRebuilding(true);
    try {
      await timelineService.buildTimeline(caseId);
      await Promise.all([fetchTimeline(), fetchHistogram()]);
    } catch (err) {
      console.error('Error rebuilding timeline:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to rebuild timeline');
    } finally {
      setRebuilding(false);
    }
  }, [caseId, fetchTimeline, fetchHistogram]);

  const updateFilters = useCallback((newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      search: '',
      sourceApp: 'all',
      eventType: 'all',
      startDate: '',
      endDate: '',
      interval: 'day',
    });
  }, []);

  useEffect(() => {
    fetchTimeline();
    fetchHistogram();
  }, [fetchTimeline, fetchHistogram]);

  return {
    events,
    histogram,
    loading,
    histogramLoading,
    rebuilding,
    error,
    filters,
    updateFilters,
    resetFilters,
    rebuildTimeline,
    refresh: () => Promise.all([fetchTimeline(), fetchHistogram()]),
  };
};

export default useTimeline;
