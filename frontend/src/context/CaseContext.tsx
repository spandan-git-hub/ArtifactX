import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { caseService } from '../services/caseService';

export interface CaseData {
  id: string | number;
  caseNumber: string;
  title: string;
  examiner: string;
  agency: string;
  status: string;
  integrityState: string;
  evidenceCount: number;
  recordCount: string | number;
  lastPipeline: string;
  updated: string;
  createdDate: string;
  headHash: string;
  sha256Root: string;
  blockId: string;
  description: string;
  deviceTarget: string;
  [key: string]: any;
}

export interface CaseContextType {
  cases: CaseData[];
  activeCaseId: string | null;
  activeCase: CaseData | null;
  loading: boolean;
  switchCase: (id: string | number) => void;
  addCase: (newCaseData: any) => Promise<CaseData>;
  deleteCase: (id: string | number) => Promise<void>;
  setCases: React.Dispatch<React.SetStateAction<CaseData[]>>;
  refreshCases: () => Promise<void>;
}

const CaseContext = createContext<CaseContextType>({} as CaseContextType);

function normalizeCase(c: any): CaseData | null {
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

export function CaseProvider({ children }: { children: ReactNode }) {
  const [cases, setCases] = useState<CaseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(() => {
    return localStorage.getItem('arx_active_case_id') || null;
  });

  const fetchCases = useCallback(async () => {
    try {
      const data = await caseService.getCases();
      if (Array.isArray(data)) {
        const normalized = data.map(normalizeCase).filter((c): c is CaseData => c !== null);
        setCases(normalized);
        if (normalized.length > 0) {
          setActiveCaseId(prev => {
            const exists = normalized.some(c => String(c.id) === String(prev) || c.caseNumber === prev);
            if (exists) return prev;
            const targetCase = normalized.find(c => String(c.id) === '124' || c.caseNumber === 'ARX-2026-004');
            return targetCase ? String(targetCase.id) : String(normalized[0].id);
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
          setCases(parsed.map(normalizeCase).filter((c: any): c is CaseData => c !== null));
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
    if (cases && cases.length > 0) {
      localStorage.setItem('arx_cases', JSON.stringify(cases));
    } else if (!loading) {
      localStorage.removeItem('arx_cases');
    }
  }, [cases, loading]);

  useEffect(() => {
    if (activeCaseId) {
      localStorage.setItem('arx_active_case_id', String(activeCaseId));
    } else {
      localStorage.removeItem('arx_active_case_id');
    }
  }, [activeCaseId]);

  const activeCase = cases.find(c => String(c.id) === String(activeCaseId) || c.caseNumber === activeCaseId) || cases[0] || null;

  const switchCase = (id: string | number) => {
    setActiveCaseId(String(id));
  };

  const addCase = async (newCaseData: any): Promise<CaseData> => {
    try {
      const payload = {
        name: newCaseData.title || newCaseData.name || 'Untitled Case',
        description: newCaseData.description || '',
        investigator: newCaseData.examiner || newCaseData.investigator || '',
        agency: newCaseData.agency,
        case_number: newCaseData.caseNumber
      };
      const createdFromApi = await caseService.createCase(payload);
      const normalized = normalizeCase({ ...createdFromApi, ...newCaseData })!;
      setCases(prev => [normalized, ...prev]);
      setActiveCaseId(String(normalized.id));
      return normalized;
    } catch (err) {
      console.warn('Backend createCase error, creating locally:', err);
      const tempId = Date.now();
      const localCase = normalizeCase({
        id: tempId,
        ...newCaseData
      })!;
      setCases(prev => [localCase, ...prev]);
      setActiveCaseId(String(localCase.id));
      return localCase;
    }
  };

  const deleteCase = async (id: string | number): Promise<void> => {
    const stringId = String(id);
    const prevCases = [...cases];
    const prevActiveId = activeCaseId;

    // 1. Optimistic update: immediately remove from local state and localStorage
    const remaining = prevCases.filter(c => String(c.id) !== stringId && c.caseNumber !== stringId);
    setCases(remaining);
    if (remaining.length > 0) {
      localStorage.setItem('arx_cases', JSON.stringify(remaining));
    } else {
      localStorage.removeItem('arx_cases');
    }

    if (String(activeCaseId) === stringId || (activeCase && activeCase.caseNumber === stringId)) {
      setActiveCaseId(remaining.length > 0 ? String(remaining[0].id) : null);
    }

    const targetCase = prevCases.find(c => String(c.id) === stringId || c.caseNumber === stringId);
    const backendId = targetCase?.id || id;

    // 2. Perform backend deletion
    try {
      await caseService.deleteCase(backendId);
    } catch (err: any) {
      // 404 means case is already gone from DB (or was created locally only) - treat as successful local deletion
      if (err.response?.status === 404) {
        console.warn(`Case ${id} was not in DB, cleaned up locally.`);
      } else {
        // Real server error: rollback optimistic state
        console.error('Backend deleteCase error:', err);
        setCases(prevCases);
        setActiveCaseId(prevActiveId);
        if (prevCases.length > 0) {
          localStorage.setItem('arx_cases', JSON.stringify(prevCases));
        }
        throw err;
      }
    }

    // 3. Ground-truth background sync with DB to guarantee complete synchronization
    try {
      const freshData = await caseService.getCases();
      if (Array.isArray(freshData)) {
        const freshNormalized = freshData.map(normalizeCase).filter((c): c is CaseData => c !== null);
        setCases(freshNormalized);
        if (freshNormalized.length > 0) {
          localStorage.setItem('arx_cases', JSON.stringify(freshNormalized));
        } else {
          localStorage.removeItem('arx_cases');
        }
      }
    } catch (syncErr) {
      console.warn('Post-delete DB sync warning:', syncErr);
    }
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

export function useActiveCase(): CaseContextType {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error('useActiveCase must be used within a CaseProvider');
  }
  return context;
}
