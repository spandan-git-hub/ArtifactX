import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';

export default function NewCasePage() {
  const navigate = useNavigate();
  const { cases, addCase } = useActiveCase();

  const nextCaseNumber = `ARX-2026-${String(cases.length + 1).padStart(3, '0')}`;

  const [formData, setFormData] = useState({
    caseNumber: nextCaseNumber,
    title: '',
    agency: '',
    examiner: '',
    deviceTarget: '',
    description: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title) return;

    const created = await addCase({
      caseNumber: formData.caseNumber,
      title: formData.title,
      agency: formData.agency,
      examiner: formData.examiner,
      deviceTarget: formData.deviceTarget,
      description: formData.description,
      status: 'Active',
      integrityState: 'Pending Ingestion',
      evidenceCount: 0,
    });

    navigate(`/cases/${created.id}/overview`);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg">
      <div className="max-w-[960px] mx-auto w-full space-y-5 pb-12">
        {/* ================= HEADER ================= */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-outline-variant">
          <div>
            <div className="flex items-center space-x-2.5 mb-1">
              <h1 className="text-headline-lg font-headline-lg text-on-surface font-semibold">
                New Forensic Case
              </h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-label-mono-sm bg-primary/10 text-primary border border-primary/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                INITIATING: {formData.caseNumber}
              </span>
            </div>
            <p className="text-body-sm text-on-surface-variant">
              Create a new forensic case docket and evidence staging workspace.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Link
              to="/cases"
              className="px-3 py-1.5 rounded bg-surface-container border border-outline-variant text-on-surface text-label-ui hover:bg-surface-container-high transition-colors"
            >
              Cancel
            </Link>
          </div>
        </div>

        {/* ================= FORM BODY ================= */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Section 1: Identification & Jurisdiction */}
          <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-outline-variant pb-2">
              <div className="flex items-center space-x-2">
                <span className="material-symbols-outlined text-primary text-[18px]">gavel</span>
                <h2 className="text-headline-sm font-headline-sm text-on-surface">1. Docket Identification</h2>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Case Number */}
              <div className="md:col-span-2 space-y-1">
                <label className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant block">
                  Assigned Case Docket ID *
                </label>
                <input
                  type="text"
                  name="caseNumber"
                  value={formData.caseNumber}
                  onChange={handleChange}
                  required
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-label-mono-sm font-label-mono-sm text-primary font-medium focus:outline-none focus:border-primary"
                />
              </div>

              {/* Case Title */}
              <div className="md:col-span-2 space-y-1">
                <label className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant block">
                  Official Investigation Title / Docket Subject *
                </label>
                <input
                  type="text"
                  name="title"
                  placeholder="Investigation / Docket Title"
                  value={formData.title}
                  onChange={handleChange}
                  required
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                />
              </div>

              {/* Agency */}
              <div className="space-y-1">
                <label className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant block">
                  Investigating Agency / Law Enforcement Unit
                </label>
                <input
                  type="text"
                  name="agency"
                  value={formData.agency}
                  onChange={handleChange}
                  required
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              {/* Examiner */}
              <div className="space-y-1">
                <label className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant block">
                  Lead Forensic Examiner & Badge ID
                </label>
                <input
                  type="text"
                  name="examiner"
                  value={formData.examiner}
                  onChange={handleChange}
                  required
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Evidentiary Target & Incident Scope */}
          <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-outline-variant pb-2">
              <div className="flex items-center space-x-2">
                <span className="material-symbols-outlined text-primary text-[18px]">smartphone</span>
                <h2 className="text-headline-sm font-headline-sm text-on-surface">2. Target Hardware & Forensic Scope</h2>
              </div>
              <span className="text-[11px] font-label-mono-sm text-outline">Target Parameters</span>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <div className="space-y-1">
                <label className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant block">
                  Target Device Spec / Model / OS
                </label>
                <input
                  type="text"
                  name="deviceTarget"
                  value={formData.deviceTarget}
                  onChange={handleChange}
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div className="space-y-1">
                <label className="text-label-ui font-label-ui uppercase tracking-wider text-on-surface-variant block">
                  Technical Objectives / Investigative Summary
                </label>
                <textarea
                  name="description"
                  rows={3}
                  placeholder="Detail expected evidence containers, target WhatsApp/Telegram databases, known cryptographic key parameters, or specific recovery mandates..."
                  value={formData.description}
                  onChange={handleChange}
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-2 text-body-sm text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                />
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="flex items-center justify-between pt-2">
            <Link to="/cases" className="text-body-sm text-on-surface-variant hover:text-on-surface">
              ← Return to Cases Directory
            </Link>

            <button
              type="submit"
              className="flex items-center space-x-2 bg-primary hover:opacity-90 text-on-primary font-semibold px-5 py-2 rounded-lg shadow-md transition-all text-body-md"
            >
              <span className="material-symbols-outlined text-[18px]">folder_special</span>
              <span>Initialize Case Repository &amp; Staging</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
