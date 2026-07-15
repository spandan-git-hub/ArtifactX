import axios from 'axios';

const API_BASE = '/api';

export const demoService = {
  /**
   * Create a demo case with mock forensic data.
   * @param {Object} options - Configuration options
   * @param {string} options.case_name - Name for the demo case
   * @param {boolean} options.has_whatsapp - Include WhatsApp demo data
   * @param {boolean} options.has_telegram - Include Telegram demo data
   * @param {number} options.message_count - Number of demo messages
   * @param {number} options.contact_count - Number of demo contacts
   * @returns {Promise<Object>} - Created demo case stats
   */
  createDemoCase: async (options = {}) => {
    const defaults = {
      case_name: `Demo Case - ${new Date().toLocaleDateString()}`,
      has_whatsapp: true,
      has_telegram: false,
      message_count: 50,
      contact_count: 10,
    };
    const config = { ...defaults, ...options };
    const response = await axios.post(`${API_BASE}/demo/create-demo-case`, config);
    return response.data;
  },

  /**
   * Delete a demo case and all its data.
   * @param {number} caseId - The case ID to delete
   * @returns {Promise<Object>} - Deletion confirmation
   */
  deleteDemoCase: async (caseId) => {
    const response = await axios.delete(`${API_BASE}/demo/demo-case/${caseId}`);
    return response.data;
  },

  /**
   * Create a quick preview demo case with minimal data.
   * @returns {Promise<Object>} - Created demo case stats
   */
  createQuickDemo: async () => {
    return demoService.createDemoCase({
      case_name: `Quick Demo - ${new Date().toLocaleTimeString()}`,
      has_whatsapp: true,
      has_telegram: false,
      message_count: 25,
      contact_count: 5,
    });
  },

  /**
   * Create a full demo case with both WhatsApp and Telegram data.
   * @returns {Promise<Object>} - Created demo case stats
   */
  createFullDemo: async () => {
    return demoService.createDemoCase({
      case_name: `Full Demo - ${new Date().toLocaleDateString()}`,
      has_whatsapp: true,
      has_telegram: true,
      message_count: 100,
      contact_count: 20,
    });
  },
};

export default demoService;