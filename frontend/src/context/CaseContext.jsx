import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { caseService } from '../services/caseService';

const CaseContext = createContext();

function normalizeCase(c) {
  if (!c) return null;
  const num = c.case_number || c.caseNumber || `ARX-2026-${String(c.id || '').padStart(3, '0')}`;
  return {
    ...c,
    id: c.id,
    caseNumber: num,
    title: c.name || c.title || 'Untitled Forensic Case',
    examiner: c.examiner_name || c.investigator || c.examiner || 'Unassigned',
    agency: c.agency || 'Special Cyber Forensics Division',
    status: c.status || 'Active',
    integrityState: c.integrity_state || c.integrityState || 'Pending Ingestion',
    evidenceCount: c.evidence_count ?? c.evidenceCount ?? 0,
    recordCount: c.record_count ?? c.recordCount ?? '0',
    lastPipeline: c.last_pipeline ?? c.lastPipeline ?? 'Not executed',
    updated: c.updated_at ? new Date(c.updated_at).toLocaleDateString() : (c.updated || 'Recently'),
    createdDate: c.created_at ? c.created_at.split('T')[0] : (c.createdDate || new Date().toISOString().split('T')[0]),
    headHash: c.head_hash || c.headHash || '',
    sha256Root: c.sha256_root || c.sha256Root || '',
    blockId: c.block_id || c.blockId || '',
    description: c.description || '',
    deviceTarget: c.device_target || c.deviceTarget || 'Mobile Device'
  };
}

export function CaseProvider({ children }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCaseId, setActiveCaseId] = useState(() => {
    return localStorage.getItem('arx_active_case_id') || null;
  });

  const fetchCases = useCallback(async () => {
    try {
      const data = await caseService.getCases();
      if (Array.isArray(data)) {
        const normalized = data.map(normalizeCase);
        setCases(normalized);
        if (normalized.length > 0) {
          setActiveCaseId(prev => {
            const exists = normalized.some(c => String(c.id) === String(prev) || c.caseNumber === prev);
            return exists ? prev : String(normalized[0].id);
          });
        } else {
          setActiveCaseId(null);
        }
      }
    } catch (err) {
      console.warn('Could not fetch cases from backend API:', err);
      // Fall back to saved local cases if any
      const saved = localStorage.getItem('arx_cases');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setCases(parsed.map(normalizeCase));
        } catch (e) {
          setCases([]);
        }
      } else {
        setCases([]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  useEffect(() => {
    if (cases.length > 0) {
      localStorage.setItem('arx_cases', JSON.stringify(cases));
    }
  }, [cases]);

  useEffect(() => {
    if (activeCaseId) {
      localStorage.setItem('arx_active_case_id', String(activeCaseId));
    } else {
      localStorage.removeItem('arx_active_case_id');
    }
  }, [activeCaseId]);

  const activeCase = cases.find(c => String(c.id) === String(activeCaseId) || c.caseNumber === activeCaseId) || cases[0] || null;

  const switchCase = (id) => {
    setActiveCaseId(String(id));
  };

  const addCase = async (newCaseData) => {
    try {
      const payload = {
        name: newCaseData.title || newCaseData.name || 'Untitled Case',
        description: newCaseData.description || '',
        investigator: newCaseData.examiner || newCaseData.investigator || '',
        agency: newCaseData.agency,
        case_number: newCaseData.caseNumber
      };
      const createdFromApi = await caseService.createCase(payload);
      const normalized = normalizeCase({ ...createdFromApi, ...newCaseData });
      setCases(prev => [normalized, ...prev]);
      setActiveCaseId(String(normalized.id));
      return normalized;
    } catch (err) {
      console.warn('Backend createCase error, creating locally:', err);
      const tempId = Date.now();
      const localCase = normalizeCase({
        id: tempId,
        ...newCaseData
      });
      setCases(prev => [localCase, ...prev]);
      setActiveCaseId(String(localCase.id));
      return localCase;
    }
  };

  const deleteCase = async (id) => {
    try {
      await caseService.deleteCase(id);
    } catch (err) {
      console.warn('Backend deleteCase error:', err);
    }

    setCases(prev => {
      const remaining = prev.filter(c => String(c.id) !== String(id));
      localStorage.setItem('arx_cases', JSON.stringify(remaining));
      return remaining;
    });

    setActiveCaseId(prev => {
      if (String(prev) === String(id)) {
        const remaining = cases.filter(c => String(c.id) !== String(id));
        return remaining.length > 0 ? String(remaining[0].id) : null;
      }
      return prev;
    });
  };

  return (
    <CaseContext.Provider value={{
      cases,
      activeCaseId,
      activeCase,
      loading,
      switchCase,
      addCase,
      deleteCase,
      setCases,
      refreshCases: fetchCases
    }}>
      {children}
    </CaseContext.Provider>
  );
}

export function useActiveCase() {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error('useActiveCase must be used within a CaseProvider');
  }
  return context;
}
