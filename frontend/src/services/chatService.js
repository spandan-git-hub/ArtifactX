import axios from 'axios';

const API_BASE = '/api';

export const chatService = {
  // Get all chat threads for a case
  getChats: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/chats`);
    return response.data;
  },

  // Get message stream and deletion indicators for a specific chat JID / dialog_id
  getChatMessages: async (caseId, jid) => {
    const encodedJid = encodeURIComponent(jid);
    const response = await axios.get(`${API_BASE}/cases/${caseId}/chats/${encodedJid}/messages`);
    return response.data;
  },
};

export default chatService;
