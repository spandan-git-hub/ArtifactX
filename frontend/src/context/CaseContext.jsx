import React, { createContext, useContext, useState, useEffect } from 'react';
import { caseService } from '../services/caseService';

const CaseContext = createContext();

const DEFAULT_CASES = [
  {
    id: 'ARX-2026-014',
    caseNumber: 'ARX-2026-014',
    title: 'Operation Iron Matrix (WhatsApp / Signal Extraction)',
    examiner: 'A. Verma',
    agency: 'Special Cyber Forensics Division, Directorate of Enforcement',
    status: 'Active',
    integrityState: 'All verified',
    evidenceCount: 7,
    recordCount: '1,482,904',
    lastPipeline: '14 mins ago',
    updated: 'Today 14:18',
    createdDate: '2026-03-28',
    headHash: '7f8a2c1b9d0e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8df2',
    sha256Root: 'c218f09d84e20791a82f3c7b6a19f048d21b780e1a674512e098df1245ba8912',
    blockId: '#40921-X9',
    description: 'Extraction and multi-app correlation of encrypted Android messaging databases and unallocated storage recovery for high-priority docket.',
    deviceTarget: 'Samsung Galaxy S23 Ultra (SM-S918B) / Android 14',
  },
  {
    id: 'ARX-2026-013',
    caseNumber: 'ARX-2026-013',
    title: 'Nexus FinTech Vault Breach & Exfiltration',
    examiner: 'A. Verma',
    agency: 'Financial Crimes Intelligence Unit',
    status: 'In Review',
    integrityState: 'All verified',
    evidenceCount: 4,
    recordCount: '842,100',
    lastPipeline: '1 day ago',
    updated: 'Yesterday 18:22',
    createdDate: '2026-03-15',
    headHash: '9a4fe88c1b3d2e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8d',
    sha256Root: '8f7e2a9b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c41d0ea',
    blockId: '#39842-A1',
    description: 'Cryptographic ledger analysis and transaction token recovery from extracted cache records.',
    deviceTarget: 'OnePlus 11 5G / Android 13',
  },
  {
    id: 'ARX-2026-012',
    caseNumber: 'ARX-2026-012',
    title: 'Cellular Handover & Physical Acquisition Audit',
    examiner: 'R. Sharma',
    agency: 'State Police Cyber Cell',
    status: 'Active',
    integrityState: 'Flagged Exception',
    evidenceCount: 5,
    recordCount: '395,200',
    lastPipeline: '3 hours ago',
    updated: 'Today 11:05',
    createdDate: '2026-03-10',
    headHash: '5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f',
    sha256Root: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
    blockId: '#39104-C8',
    description: 'Tower handover logs matched with SQLite cache frames and encrypted backup key analysis.',
    deviceTarget: 'Google Pixel 8 Pro / Android 14',
  },
  {
    id: 'ARX-2026-015',
    caseNumber: 'ARX-2026-015',
    title: 'Operation Skyfall Telegram Enclave (Unmounted Initial State)',
    examiner: 'A. Verma',
    agency: 'Central Forensic Science Laboratory (CFSL)',
    status: 'Draft',
    integrityState: 'Pending Ingestion',
    evidenceCount: 0,
    recordCount: '0',
    lastPipeline: 'Not executed',
    updated: 'Just now',
    createdDate: '2026-03-31',
    headHash: '0000000000000000000000000000000000000000000000000000000000000000',
    sha256Root: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    blockId: '#GENESIS',
    description: 'Fresh case container for testing empty state onboarding and raw partition ingestion workflow.',
    deviceTarget: 'Xiaomi 13 Pro / Android 14',
  }
];

export function CaseProvider({ children }) {
  const [cases, setCases] = useState(() => {
    const saved = localStorage.getItem('arx_cases');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) { /* ignore */ }
    }
    return DEFAULT_CASES;
  });

  const [activeCaseId, setActiveCaseId] = useState(() => {
    return localStorage.getItem('arx_active_case_id') || 'ARX-2026-014';
  });

  useEffect(() => {
    localStorage.setItem('arx_cases', JSON.stringify(cases));
  }, [cases]);

  useEffect(() => {
    localStorage.setItem('arx_active_case_id', activeCaseId);
  }, [activeCaseId]);

  const activeCase = cases.find(c => c.id === activeCaseId || c.caseNumber === activeCaseId) || cases[0];

  const switchCase = (id) => {
    setActiveCaseId(id);
  };

  const addCase = (newCaseData) => {
    const caseId = newCaseData.caseNumber || `ARX-2026-${String(cases.length + 10).padStart(3, '0')}`;
    const created = {
      id: caseId,
      caseNumber: caseId,
      title: newCaseData.title || 'Untitled Forensic Case',
      examiner: newCaseData.examiner || 'A. Verma (Examiner)',
      agency: newCaseData.agency || 'Special Cyber Forensics Division',
      status: 'Active',
      integrityState: 'All verified',
      evidenceCount: 0,
      recordCount: '0',
      lastPipeline: 'Pending',
      updated: 'Just now',
      createdDate: new Date().toISOString().split('T')[0],
      headHash: '7f8a2c1b9d0e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8df2',
      sha256Root: 'c218f09d84e20791a82f3c7b6a19f048d21b780e1a674512e098df1245ba8912',
      blockId: `#${Math.floor(40000 + Math.random() * 5000)}-X${Math.floor(Math.random() * 9)}`,
      description: newCaseData.description || 'Forensic case repository created for extraction and evidence verification.',
      deviceTarget: newCaseData.deviceTarget || 'Generic Android Mobile Device',
      ...newCaseData
    };

    setCases(prev => [created, ...prev]);
    setActiveCaseId(caseId);
    return created;
  };

  return (
    <CaseContext.Provider value={{
      cases,
      activeCaseId,
      activeCase,
      switchCase,
      addCase,
      setCases
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
