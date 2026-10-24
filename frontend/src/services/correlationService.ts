import axios from 'axios';

const API_BASE = '/api';

export const correlationService = {
  // Trigger baseline correlation
  triggerCorrelation: async (caseId) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/correlate`);
    return response.data;
  },

  // Trigger full R4 Deep Correlation Engine
  triggerDeepCorrelation: async (caseId, params = {}) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/correlation/deep/run`, params);
    return response.data;
  },

  // Get full stable JSON graph of nodes, edges, and provenance
  getCorrelationGraph: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/graph`);
    return response.data;
  },

  // Get detected platform handover candidates
  getPlatformHandovers: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/handover`);
    return response.data;
  },

  // Get perceptual media matches (pHash/dHash)
  getMediaCorrelations: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/media`);
    return response.data;
  },

  // Get extracted and shared deterministic artifacts
  getSharedArtifacts: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/artifacts`);
    return response.data;
  },

  // Get spatiotemporal rendezvous candidates
  getRendezvousEvents: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/rendezvous`);
    return response.data;
  },

  // Get resolved person clusters
  getResolvedPersons: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/persons`);
    return response.data;
  },

  // Get raw correlation edges (backwards compatible)
  getCorrelationEdges: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation`);
    return response.data;
  },

  // Get resolved cross-app entities (backwards compatible)
  getEntityResolutions: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/entities`);
    return response.data;
  },

  // Get cross-app message correlation matrix within a time window
  getMessageMatrix: async (caseId, windowSeconds = 300) => {
    const response = await axios.get(
      `${API_BASE}/cases/${caseId}/correlation/matrix?window_seconds=${windowSeconds}`
    );
    return response.data;
  },

  // Get accurate evidence platform status for a case
  getCorrelationStatus: async (caseId) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/correlation/status`);
    return response.data;
  },
};

export default correlationService;
