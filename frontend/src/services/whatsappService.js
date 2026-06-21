import axios from 'axios';

const API_BASE = '/api';

export const whatsappService = {
  // Analyze WhatsApp evidence
  analyzeEvidence: async (evidenceId) => {
    const response = await axios.post(`${API_BASE}/whatsapp/evidence/${evidenceId}/analyze/whatsapp`);
    return response.data;
  },

  // Get WhatsApp messages
  getMessages: async (evidenceId) => {
    const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-messages`);
    return response.data;
  },

  // Get WhatsApp contacts
  getContacts: async (evidenceId) => {
    const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-contacts`);
    return response.data;
  },

  // Get WhatsApp groups
  getGroups: async (evidenceId) => {
    const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-groups`);
    return response.data;
  },

  // Get WhatsApp media references
  getMedia: async (evidenceId) => {
    const response = await axios.get(`${API_BASE}/whatsapp/evidence/${evidenceId}/wa-media`);
    return response.data;
  }
};