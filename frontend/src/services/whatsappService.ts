import axios from 'axios';

const API_BASE = '/api';

// Analyze WhatsApp evidence
export const analyzeEvidence = async (evidenceId) => {
  const response = await axios.post(`${API_BASE}/whatsapp/evidence/${evidenceId}/analyze/whatsapp`);
  return response.data;
};

// Get WhatsApp messages
export const getMessages = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-messages`);
  return response.data;
};

// Get WhatsApp contacts
export const getContacts = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-contacts`);
  return response.data;
};

// Get WhatsApp groups
export const getGroups = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-groups`);
  return response.data;
};

// Get WhatsApp media references
export const getMedia = async (evidenceId) => {
  const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-media`);
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