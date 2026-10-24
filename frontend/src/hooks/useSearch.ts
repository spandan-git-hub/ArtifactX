import { useState, useCallback } from 'react';
import * as searchService from '../services/searchService';

/**
 * Hook for global search functionality
 */
export const useGlobalSearch = () => {
  const [results, setResults] = useState({
    messages: [],
    contacts: [],
    media: [],
  });
  const [totalResults, setTotalResults] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');

  const search = useCallback(async (caseId, searchQuery, app = 'all') => {
    if (!searchQuery || searchQuery.trim().length === 0) {
      setResults({ messages: [], contacts: [], media: [] });
      setTotalResults(0);
      return;
    }

    setLoading(true);
    setError(null);
    setQuery(searchQuery);

    try {
      const data = await searchService.globalSearch(caseId, searchQuery, app);
      setResults({
        messages: data.messages || [],
        contacts: data.contacts || [],
        media: data.media || [],
      });
      setTotalResults(data.total_results || 0);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
      setResults({ messages: [], contacts: [], media: [] });
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults({ messages: [], contacts: [], media: [] });
    setTotalResults(0);
    setQuery('');
    setError(null);
  }, []);

  return {
    results,
    totalResults,
    query,
    loading,
    error,
    search,
    clear,
  };
};

/**
 * Hook for message search with pagination
 */
export const useMessageSearch = () => {
  const [messages, setMessages] = useState([]);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(async (caseId, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const data = await searchService.searchMessages(caseId, {
        query: options.query,
        dateFrom: options.dateFrom,
        dateTo: options.dateTo,
        app: options.app || 'all',
        page: options.page || 1,
        pageSize: options.pageSize || 50,
      });

      setMessages(data.results || []);
      setPagination({
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
        totalPages: data.total_pages,
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const setPage = useCallback((page) => {
    setPagination(prev => ({ ...prev, page }));
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    setPagination({ total: 0, page: 1, pageSize: 50, totalPages: 0 });
    setError(null);
  }, []);

  return {
    messages,
    pagination,
    loading,
    error,
    search,
    setPage,
    clear,
  };
};

/**
 * Hook for contact search with pagination
 */
export const useContactSearch = () => {
  const [contacts, setContacts] = useState([]);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(async (caseId, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const data = await searchService.searchContacts(caseId, {
        query: options.query,
        app: options.app || 'all',
        page: options.page || 1,
        pageSize: options.pageSize || 50,
      });

      setContacts(data.results || []);
      setPagination({
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
        totalPages: data.total_pages,
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
      setContacts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const setPage = useCallback((page) => {
    setPagination(prev => ({ ...prev, page }));
  }, []);

  const clear = useCallback(() => {
    setContacts([]);
    setPagination({ total: 0, page: 1, pageSize: 50, totalPages: 0 });
    setError(null);
  }, []);

  return {
    contacts,
    pagination,
    loading,
    error,
    search,
    setPage,
    clear,
  };
};

/**
 * Hook for media search with pagination
 */
export const useMediaSearch = () => {
  const [media, setMedia] = useState([]);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(async (caseId, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const data = await searchService.searchMedia(caseId, {
        query: options.query,
        dateFrom: options.dateFrom,
        dateTo: options.dateTo,
        app: options.app || 'all',
        mediaType: options.mediaType,
        page: options.page || 1,
        pageSize: options.pageSize || 50,
      });

      setMedia(data.results || []);
      setPagination({
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
        totalPages: data.total_pages,
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
      setMedia([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const setPage = useCallback((page) => {
    setPagination(prev => ({ ...prev, page }));
  }, []);

  const clear = useCallback(() => {
    setMedia([]);
    setPagination({ total: 0, page: 1, pageSize: 50, totalPages: 0 });
    setError(null);
  }, []);

  return {
    media,
    pagination,
    loading,
    error,
    search,
    setPage,
    clear,
  };
};

/**
 * Hook for search summary
 */
export const useSearchSummary = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadSummary = useCallback(async (caseId) => {
    setLoading(true);
    setError(null);

    try {
      const data = await searchService.getSummary(caseId);
      setSummary(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load summary');
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    summary,
    loading,
    error,
    loadSummary,
  };
};