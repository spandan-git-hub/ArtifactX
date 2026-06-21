import { useState, useCallback } from 'react';
import * as evidenceService from '../services/evidenceService';

export const useEvidence = () => {
  const [evidences, setEvidences] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadEvidences = useCallback(async (caseId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await evidenceService.getEvidences(caseId);
      setEvidences(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load evidences');
      setEvidences([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadEvidence = useCallback(async (caseId, file) => {
    setLoading(true);
    setError(null);
    try {
      const newEvidence = await evidenceService.uploadEvidence(caseId, file);
      // Optionally refresh list
      return newEvidence;
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload evidence');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteEvidence = useCallback(async (evidenceId) => {
    setLoading(true);
    setError(null);
    try {
      await evidenceService.deleteEvidence(evidenceId);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete evidence');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    evidences,
    loading,
    error,
    loadEvidences,
    uploadEvidence,
    deleteEvidence,
  };
};