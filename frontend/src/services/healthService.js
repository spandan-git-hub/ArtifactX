import axios from 'axios';

const API_BASE = '/api';

/**
 * Health check service for verifying backend connectivity
 */
export const healthService = {
  /**
   * Check if the backend is running and responsive.
   * @returns {Promise<Object>} - Health status object
   */
  check: async () => {
    try {
      const response = await axios.get(`${API_BASE}/health`, {
        timeout: 5000,
      });
      return response.data;
    } catch (error) {
      return {
        status: 'error',
        message: error.response?.data?.detail || 'Backend not responding',
        error: true,
      };
    }
  },

  /**
   * Check if demo mode is enabled.
   * @returns {Promise<boolean>}
   */
  isDemoMode: async () => {
    try {
      const health = await healthService.check();
      return health.demo_mode || false;
    } catch {
      return false;
    }
  },

  /**
   * Check if the system is healthy (status === 'ok').
   * @returns {Promise<boolean>}
   */
  isHealthy: async () => {
    const health = await healthService.check();
    return health.status === 'ok';
  },
};

export default healthService;