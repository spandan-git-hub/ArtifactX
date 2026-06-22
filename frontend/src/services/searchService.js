import axios from 'axios';

const API_BASE = '/api';

/**
 * Search service for API calls
 */
export const searchService = {
  /**
   * Global search across messages, contacts, and media
   */
  globalSearch: async (caseId, query, app = 'all', limit = 20) => {
    const params = new URLSearchParams({
      case_id: caseId,
      query,
      app,
      limit,
    });
    const response = await axios.get(`${API_BASE}/search?${params.toString()}`);
    return response.data;
  },

  /**
   * Search messages with filters and pagination
   */
  searchMessages: async (caseId, options = {}) => {
    const params = new URLSearchParams({ case_id: caseId });

    if (options.query) params.append('query', options.query);
    if (options.dateFrom) params.append('date_from', options.dateFrom);
    if (options.dateTo) params.append('date_to', options.dateTo);
    if (options.app) params.append('app', options.app);
    params.append('page', options.page || 1);
    params.append('page_size', options.pageSize || 50);

    const response = await axios.get(`${API_BASE}/search/messages?${params.toString()}`);
    return response.data;
  },

  /**
   * Search contacts with filters and pagination
   */
  searchContacts: async (caseId, options = {}) => {
    const params = new URLSearchParams({ case_id: caseId });

    if (options.query) params.append('query', options.query);
    if (options.app) params.append('app', options.app);
    params.append('page', options.page || 1);
    params.append('page_size', options.pageSize || 50);

    const response = await axios.get(`${API_BASE}/search/contacts?${params.toString()}`);
    return response.data;
  },

  /**
   * Search media with filters and pagination
   */
  searchMedia: async (caseId, options = {}) => {
    const params = new URLSearchParams({ case_id: caseId });

    if (options.query) params.append('query', options.query);
    if (options.dateFrom) params.append('date_from', options.dateFrom);
    if (options.dateTo) params.append('date_to', options.dateTo);
    if (options.app) params.append('app', options.app);
    if (options.mediaType) params.append('media_type', options.mediaType);
    params.append('page', options.page || 1);
    params.append('page_size', options.pageSize || 50);

    const response = await axios.get(`${API_BASE}/search/media?${params.toString()}`);
    return response.data;
  },

  /**
   * Get search summary statistics for a case
   */
  getSummary: async (caseId) => {
    const params = new URLSearchParams({ case_id: caseId });
    const response = await axios.get(`${API_BASE}/search/summary?${params.toString()}`);
    return response.data;
  },
};