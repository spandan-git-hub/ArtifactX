import { useState, useEffect } from 'react';
import { caseService } from '../services/caseService';

export const useCases = () => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCases = async () => {
    try {
      setLoading(true);
      const data = await caseService.getCases();
      setCases(data);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch cases');
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  const createCase = async (caseData) => {
    try {
      const newCase = await caseService.createCase(caseData);
      setCases(prev => [...prev, newCase]);
      return newCase;
    } catch (err) {
      throw err;
    }
  };

  const updateCase = async (id, caseData) => {
    try {
      const updatedCase = await caseService.updateCase(id, caseData);
      setCases(prev => prev.map(c => c.id === id ? updatedCase : c));
      return updatedCase;
    } catch (err) {
      throw err;
    }
  };

  const deleteCase = async (id) => {
    try {
      await caseService.deleteCase(id);
      setCases(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      throw err;
    }
  };

  // Load cases on mount
  useEffect(() => {
    loadCases();
  }, []);

  return { cases, loading, error, loadCases, createCase, updateCase, deleteCase };
};