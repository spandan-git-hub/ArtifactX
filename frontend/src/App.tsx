import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { CaseProvider } from './context/CaseContext';
import { Layout } from './components/layout';

import LoginPage from './pages/LoginPage';
import CaseListPage from './pages/CaseListPage';
import NewCasePage from './pages/NewCasePage';
import CaseOverviewPage from './pages/CaseOverviewPage';
import EvidenceListPage from './pages/EvidenceListPage';
import UploadEvidencePage from './pages/UploadEvidencePage';
import DecryptionPage from './pages/DecryptionPage';
import ParsingPage from './pages/ParsingPage';
import PipelinePage from './pages/PipelinePage';
import MessagesPage from './pages/MessagesPage';
import TimelinePage from './pages/TimelinePage';
import RecoveryPage from './pages/RecoveryPage';
import CorrelationPage from './pages/CorrelationPage';
import Section63Page from './pages/Section63Page';
import IntegrityAuditPage from './pages/IntegrityAuditPage';
import CaseMetricsPage from './pages/CaseMetricsPage';
import LimitationsPage from './pages/LimitationsPage';
import ReportsPage from './pages/ReportsPage';

export default function App() {
  return (
    <ThemeProvider>
      <CaseProvider>
        <Routes>
          {/* Standalone Login Page */}
          <Route path="/login" element={<LoginPage />} />

          {/* Root redirect to Cases */}
          <Route path="/" element={<Navigate to="/cases" replace />} />

          {/* Workstation Application Shell Routes */}
          <Route
            path="/*"
            element={
              <Layout>
                <Routes>
                  <Route path="/cases" element={<CaseListPage />} />
                  <Route path="/cases/new" element={<NewCasePage />} />
                  <Route path="/cases/create" element={<NewCasePage />} />

                  {/* Case Specific Modules */}
                  <Route path="/cases/:caseId" element={<CaseOverviewPage />} />
                  <Route path="/cases/:caseId/overview" element={<CaseOverviewPage />} />
                  <Route path="/cases/:caseId/evidence" element={<EvidenceListPage />} />
                  <Route path="/cases/:caseId/evidence/:evidenceId" element={<EvidenceListPage />} />
                  <Route path="/cases/:caseId/upload" element={<UploadEvidencePage />} />
                  <Route path="/cases/:caseId/decryption" element={<DecryptionPage />} />
                  <Route path="/cases/:caseId/parsing" element={<ParsingPage />} />
                  <Route path="/cases/:caseId/pipeline" element={<PipelinePage />} />
                  <Route path="/cases/:caseId/pipeline/history" element={<PipelinePage />} />
                  <Route path="/cases/:caseId/pipeline/quality" element={<PipelinePage />} />
                  <Route path="/cases/:caseId/messages" element={<MessagesPage />} />
                  <Route path="/cases/:caseId/chat" element={<MessagesPage />} />
                  <Route path="/cases/:caseId/timeline" element={<TimelinePage />} />
                  <Route path="/cases/:caseId/recovery" element={<RecoveryPage />} />
                  <Route path="/cases/:caseId/correlations" element={<CorrelationPage />} />
                  <Route path="/cases/:caseId/correlation" element={<CorrelationPage />} />
                  <Route path="/cases/:caseId/section63" element={<Section63Page />} />
                  <Route path="/cases/:caseId/integrity" element={<IntegrityAuditPage />} />
                  <Route path="/cases/:caseId/metrics" element={<CaseMetricsPage />} />
                  <Route path="/cases/:caseId/dashboard" element={<CaseMetricsPage />} />
                  <Route path="/cases/:caseId/limitations" element={<LimitationsPage />} />
                  <Route path="/cases/:caseId/reports" element={<ReportsPage />} />
                  <Route path="/cases/:caseId/logs" element={<PipelinePage />} />

                  {/* Catch-all redirect */}
                  <Route path="*" element={<Navigate to="/cases" replace />} />
                </Routes>
              </Layout>
            }
          />
        </Routes>
      </CaseProvider>
    </ThemeProvider>
  );
}