import axios from 'axios';

const API_BASE = '/api';

// Analyze Telegram evidence
export const analyzeEvidence = async (evidenceId) => {
  const response = await axios.post(`${API_BASE}/telegram/evidence/${evidenceId}/analyze/telegram`);
  return response.data;
};

// Get Telegram messages
export const getMessages = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/telegram/evidence/${evidenceId}/tg-messages`);
  return response.data;
};

// Get Telegram contacts
export const getContacts = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/telegram/evidence/${evidenceId}/tg-contacts`);
  return response.data;
};

// Get Telegram groups/channels
export const getGroups = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/telegram/evidence/${evidenceId}/tg-groups`);
  return response.data;
};

// Get Telegram media references
export const getMedia = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/telegram/evidence/${evidenceId}/tg-media`);
  return response.data;
};

// Default export
export default {
  analyzeEvidence,
  getMessages,
  getContacts,
  getGroups,
  getMedia,
};