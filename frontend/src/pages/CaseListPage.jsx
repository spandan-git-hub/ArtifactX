import React, { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';

export default function CaseListPage() {
  const navigate = useNavigate();
  const { cases, activeCaseId, switchCase, deleteCase, refreshCases } = useActiveCase();

  useEffect(() => {
    refreshCases?.();
  }, [refreshCases]);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [examinerFilter, setExaminerFilter] = useState('All');
  const [integrityFilter, setIntegrityFilter] = useState('All');
  const [caseToDelete, setCaseToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const examiners = useMemo(() => {
    return Array.from(new Set(cases.map((c) => c.examiner).filter(Boolean)));
  }, [cases]);

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const matchesSearch =
        c.caseNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.examiner.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus = statusFilter === 'All' || c.status === statusFilter;
      const matchesExaminer = examinerFilter === 'All' || c.examiner.includes(examinerFilter);
      const matchesIntegrity = integrityFilter === 'All' || c.integrityState === integrityFilter;

      return matchesSearch && matchesStatus && matchesExaminer && matchesIntegrity;
    });
  }, [cases, searchQuery, statusFilter, examinerFilter, integrityFilter]);

  const handleSelectCase = (caseId) => {
    switchCase(caseId);
    navigate(`/cases/${caseId}/overview`);
  };

  const handleConfirmDelete = async () => {
    if (!caseToDelete) return;
    const targetId = caseToDelete.id;
    setCaseToDelete(null);
    setIsDeleting(true);
    try {
      await deleteCase(targetId);
    } catch (err) {
      console.error('Failed to delete case:', err);
      alert('Failed to delete case: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg space-y-4">
      {/* ================= PAGE HEADER & QUICK METRICS ================= */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-2 border-b border-outline-variant">
        <div>
          <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface tracking-tight">
            Forensic Cases
          </h1>
          <p className="text-body-sm font-body-sm text-on-surface-variant mt-0.5">
            Authorized investigation repositories and artifact pipelines
          </p>
        </div>

        {/* Quick Metrics Bar */}
        <div className="flex items-center space-x-3 text-label-mono-sm">
          <div className="bg-surface-container border border-outline-variant rounded px-2.5 py-1 flex items-center space-x-2">
            <span className="text-outline uppercase text-[10px]">TOTAL CASES:</span>
            <span className="text-on-surface font-semibold">{cases.length}</span>
          </div>
          <div className="bg-surface-container border border-outline-variant rounded px-2.5 py-1 flex items-center space-x-2">
            <span className="text-outline uppercase text-[10px]">HASH AUDIT:</span>
            <span className="text-tertiary flex items-center gap-1 font-medium">
              <span className={`w-1.5 h-1.5 rounded-full ${cases.length > 0 ? 'bg-tertiary' : 'bg-outline'}`} /> {cases.length > 0 ? '100% VALID' : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* ================= ACTION & FILTER TOOLBAR ================= */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container p-2.5 rounded-lg border border-outline-variant">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[280px]">
          {/* Search Input */}
          <div className="relative flex-1 max-w-sm">
            <span className="material-symbols-outlined absolute left-2.5 top-2 text-outline text-[16px]">
              search
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search case #, title, examiner..."
              className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-8 pr-3 py-1.5 text-body-sm text-on-surface placeholder:text-outline focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          {/* Status Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant text-on-surface px-2.5 py-1.5 rounded text-body-sm focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">Status: All Statuses</option>
            <option value="Active">Active</option>
            <option value="In Review">In Review</option>
            <option value="Draft">Draft</option>
            <option value="Archived">Archived</option>
          </select>

          {/* Examiner Filter */}
          <select
            value={examinerFilter}
            onChange={(e) => setExaminerFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant text-on-surface px-2.5 py-1.5 rounded text-body-sm focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">Examiner: All Investigators</option>
            {examiners.map((ex) => (
              <option key={ex} value={ex}>
                {ex}
              </option>
            ))}
          </select>

          {/* Integrity Filter */}
          <select
            value={integrityFilter}
            onChange={(e) => setIntegrityFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant text-on-surface px-2.5 py-1.5 rounded text-body-sm focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">Integrity: All States</option>
            <option value="All verified">All verified</option>
            <option value="Flagged Exception">Flagged Exception</option>
            <option value="Pending Ingestion">Pending Ingestion</option>
          </select>
        </div>

        {/* Primary Action Button */}
        <div className="flex items-center space-x-2">
          <Link
            to="/cases/new"
            className="flex items-center space-x-1.5 bg-primary hover:opacity-90 text-on-primary font-medium text-body-sm px-3.5 py-1.5 rounded-lg shadow-sm transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span>+ New case</span>
          </Link>
        </div>
      </div>

      {/* ================= CASES DATA TABLE ================= */}
      <div className="bg-surface-container rounded-lg border border-outline-variant overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th className="py-2.5 px-3 w-[150px]">Case Number</th>
                <th className="py-2.5 px-3">Title & Target</th>
                <th className="py-2.5 px-3 w-[150px]">Examiner</th>
                <th className="py-2.5 px-3 w-[130px] text-right">Evidence Items</th>
                <th className="py-2.5 px-3 w-[160px]">Integrity State</th>
                <th className="py-2.5 px-3 w-[140px]">Last Pipeline</th>
                <th className="py-2.5 px-3 w-[120px]">Updated</th>
                <th className="py-2.5 px-3 w-[140px] text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 text-body-sm font-body-sm">
              {filteredCases.map((c) => {
                const isActive = c.id === activeCaseId;
                return (
                  <tr
                    key={c.id}
                    onClick={() => handleSelectCase(c.id)}
                    className={`hover:bg-surface-container-high/60 transition-colors cursor-pointer ${
                      isActive ? 'bg-primary/5 border-l-2 border-primary' : ''
                    }`}
                  >
                    <td className="py-3 px-3">
                      <div className="flex items-center space-x-1.5">
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            c.status === 'Active' ? 'bg-primary animate-pulse' : 'bg-outline'
                          }`}
                        />
                        <span className="font-label-mono-sm text-label-mono-sm font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded border border-primary/20">
                          {c.caseNumber}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      <div className="font-medium text-on-surface">{c.title}</div>
                      <div className="text-[11px] text-outline font-mono truncate max-w-md">
                        Target: {c.deviceTarget} · SHA-256: {c.headHash?.substring(0, 16)}...
                      </div>
                    </td>

                    <td className="py-3 px-3 text-on-surface">
                      <div className="flex items-center space-x-1.5">
                        <span className="material-symbols-outlined text-outline text-[16px]">account_circle</span>
                        <span>{c.examiner}</span>
                      </div>
                    </td>

                    <td className="py-3 px-3 text-right font-label-mono-sm">
                      <span className="text-on-surface font-semibold">{c.evidenceCount}</span>
                      <span className="text-outline text-[11px] block">{c.recordCount} rec</span>
                    </td>

                    <td className="py-3 px-3">
                      {c.integrityState === 'All verified' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-tertiary/10 text-tertiary border border-tertiary/30">
                          <span className="material-symbols-outlined text-[13px]">verified</span>
                          All verified
                        </span>
                      )}
                      {c.integrityState === 'Flagged Exception' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-error/10 text-error border border-error/30">
                          <span className="material-symbols-outlined text-[13px]">warning</span>
                          Flagged Exception
                        </span>
                      )}
                      {c.integrityState === 'Pending Ingestion' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-surface-container-high text-on-surface-variant border border-outline-variant">
                          <span className="material-symbols-outlined text-[13px]">hourglass_empty</span>
                          Pending
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3 text-on-surface-variant font-mono text-[11px]">
                      {c.lastPipeline}
                    </td>

                    <td className="py-3 px-3 text-on-surface-variant font-mono text-[11px]">
                      {c.updated}
                    </td>

                    <td className="py-3 px-3 text-center">
                      <div
                        className="flex items-center justify-center space-x-1.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => handleSelectCase(c.id)}
                          className="px-2.5 py-1 rounded bg-surface-container-high hover:bg-primary hover:text-on-primary text-primary border border-outline-variant text-[11px] font-medium transition-colors"
                          title="Open Case"
                        >
                          Open
                        </button>
                        <button
                          type="button"
                          onClick={() => setCaseToDelete(c)}
                          className="px-2 py-1 rounded bg-surface-container-high hover:bg-error/20 hover:text-error hover:border-error/40 text-on-surface-variant border border-outline-variant text-[11px] font-medium transition-colors flex items-center gap-1"
                          title={`Delete Case ${c.caseNumber}`}
                        >
                          <span className="material-symbols-outlined text-[14px]">delete</span>
                          <span>Delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredCases.length === 0 && (
          <div className="p-8 text-center text-on-surface-variant">
            <span className="material-symbols-outlined text-4xl text-outline mb-2">folder_off</span>
            <p className="text-body-md font-medium">No forensic cases match query filters.</p>
            <button
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('All');
                setExaminerFilter('All');
                setIntegrityFilter('All');
              }}
              className="mt-3 text-primary hover:underline text-sm font-medium"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* ================= CONFIRMATION MODAL ================= */}
      {caseToDelete && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        >
          <div className="bg-surface-container-high border border-outline-variant rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-start space-x-3">
              <div className="w-10 h-10 rounded-lg bg-error/15 border border-error/30 text-error flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[24px]">warning</span>
              </div>
              <div>
                <h3 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                  Delete Forensic Case?
                </h3>
                <p className="text-body-sm text-on-surface-variant mt-1">
                  Are you sure you want to permanently delete case{' '}
                  <span className="font-mono font-semibold text-primary">{caseToDelete.caseNumber}</span>
                  {caseToDelete.title ? ` (${caseToDelete.title})` : ''}?
                </p>
              </div>
            </div>

            <div className="bg-surface-container-lowest/70 border border-outline-variant/60 rounded-lg p-3 text-xs text-on-surface-variant space-y-1 font-mono">
              <div>• Case ID: {caseToDelete.id}</div>
              <div>• Total Evidence Exhibits: {caseToDelete.evidenceCount}</div>
              <div className="text-error mt-2 font-sans font-medium">
                Warning: All exhibits, physical extractions, timeline events, chats, and carved records will be permanently removed. This cannot be undone.
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setCaseToDelete(null)}
                className="px-4 py-2 rounded-lg bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-highest text-body-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={handleConfirmDelete}
                className="px-4 py-2 rounded-lg bg-error text-white hover:bg-error/90 text-body-sm font-medium transition-colors flex items-center space-x-1.5 shadow-sm"
              >
                {isDeleting ? (
                  <>
                    <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[18px]">delete_forever</span>
                    <span>Delete Case</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}