import axios from 'axios';

const API_BASE = '/api';

// Global search across messages, contacts, and media
export const globalSearch = async (caseId: any, query: any, app: string = 'all', limit: number | string = 20) => {
  const params = new URLSearchParams({ case_id: String(caseId), query: String(query), app, limit: String(limit) });
  const response = await axios.get(`${API_BASE}/search?${params.toString()}`);
  return response.data;
};

// Search messages with filters and pagination
export const searchMessages = async (caseId: any, options: any = {}) => {
  const params = new URLSearchParams({ case_id: String(caseId) });
  if (options.query) params.append('query', options.query);
  if (options.dateFrom) params.append('date_from', options.dateFrom);
  if (options.dateTo) params.append('date_to', options.dateTo);
  if (options.app) params.append('app', options.app);
  params.append('page', String(options.page || 1));
  params.append('page_size', String(options.pageSize || 50));
  const response = await axios.get(`${API_BASE}/search/messages?${params.toString()}`);
  return response.data;
};

// Search contacts with filters and pagination
export const searchContacts = async (caseId: any, options: any = {}) => {
  const params = new URLSearchParams({ case_id: String(caseId) });
  if (options.query) params.append('query', options.query);
  if (options.app) params.append('app', options.app);
  params.append('page', String(options.page || 1));
  params.append('page_size', String(options.pageSize || 50));
  const response = await axios.get(`${API_BASE}/search/contacts?${params.toString()}`);
  return response.data;
};

// Search media with filters and pagination
export const searchMedia = async (caseId: any, options: any = {}) => {
  const params = new URLSearchParams({ case_id: String(caseId) });
  if (options.query) params.append('query', options.query);
  if (options.dateFrom) params.append('date_from', options.dateFrom);
  if (options.dateTo) params.append('date_to', options.dateTo);
  if (options.app) params.append('app', options.app);
  if (options.mediaType) params.append('media_type', options.mediaType);
  params.append('page', String(options.page || 1));
  params.append('page_size', String(options.pageSize || 50));
  const response = await axios.get(`${API_BASE}/search/media?${params.toString()}`);
  return response.data;
};

// Get search summary statistics
export const getSummary = async (caseId: any) => {
  const params = new URLSearchParams({ case_id: String(caseId) });
  const response = await axios.get(`${API_BASE}/search/summary?${params.toString()}`);
  return response.data;
};

// Default export
export default {
  globalSearch,
  searchMessages,
  searchContacts,
  searchMedia,
  getSummary,
};