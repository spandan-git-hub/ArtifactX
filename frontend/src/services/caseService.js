import axios from 'axios';

const API_BASE = '/api';

export const caseService = {
  // Get all cases
  getCases: async () => {
    const response = await axios.get(`${API_BASE}/cases`);
    return response.data;
  },

  // Get case by ID
  getCase: async (id) => {
    const response = await axios.get(`${API_BASE}/cases/${id}`);
    return response.data;
  },

  // Create new case
  createCase: async (caseData) => {
    const response = await axios.post(`${API_BASE}/cases`, caseData);
    return response.data;
  },

  // Update existing case
  updateCase: async (id, caseData) => {
    const response = await axios.put(`${API_BASE}/cases/${id}`, caseData);
    return response.data;
  },

  // Delete case
  deleteCase: async (id) => {
    await axios.delete(`${API_BASE}/cases/${id}`);
  },

  // Get case workspace summary
  getCaseWorkspace: async (id) => {
    const response = await axios.get(`${API_BASE}/cases/${id}/workspace`);
    return response.data;
  }
};