import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useCases } from '../hooks/useCases';
import { Header } from '../components/layout';
import { caseService } from '../services/caseService';
import EvidenceUploader from '../components/evidence/EvidenceUploader';
import EvidenceInventory from '../components/evidence/EvidenceInventory';
import WhatsAppAnalysis from '../components/whatsapp/WhatsAppAnalysis';
import TelegramAnalysis from '../components/telegram/TelegramAnalysis';
import {
  ArrowLeft,
  Edit,
  Trash2,
  LayoutDashboard,
  Search,
  FileText,
  ClipboardList,
  Loader2,
  AlertCircle,
  Package,
  Database,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';

const CaseDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { deleteCase } = useCases();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [activeSection, setActiveSection] = useState('evidence');
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null);
  const [evidenceRefreshToken, setEvidenceRefreshToken] = useState(0);

  // Accidentally had a typo in "useParams()" - it's actually "useParams" which is correct

  useEffect(() => {
    const loadCase = async () => {
      try {
        setLoading(true);
        const data = await caseService.getCase(id);
        setCaseData(data);
        setError(null);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Failed to load case');
        setCaseData(null);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      loadCase();
    }
  }, [id]);

  const handleDelete = async () => {
    if (window.confirm(`Delete case "${caseData?.name}"? This cannot be undone.`)) {
      setDeleteLoading(true);
      try {
        await deleteCase(id);
        navigate('/cases');
      } catch (err) {
        alert('Failed to delete case');
        setDeleteLoading(false);
      }
    }
  };

  const toggleSection = (section) => {
    setActiveSection(activeSection === section ? null : section);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent-cyan" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen p-6">
        <div className="card border-accent-rose/30">
          <div className="flex items-center gap-3 text-accent-rose mb-4">
            <AlertCircle className="h-5 w-5" />
            <span className="font-semibold">Error Loading Case</span>
          </div>
          <p className="text-forensic-400 mb-4">{error}</p>
          <Link to="/cases" className="btn-secondary">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Cases
          </Link>
        </div>
      </div>
    );
  }

  if (!caseData) return null;

  return (
    <div className="min-h-screen">
      <Header
        breadcrumbs={[
          { label: 'ArtifactX', path: '/' },
          { label: 'Cases', path: '/cases' },
          { label: caseData.name },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Link
              to={`/cases/${id}/dashboard`}
              className="btn-ghost flex items-center gap-2"
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </Link>
            <Link
              to={`/cases/${id}/search`}
              className="btn-ghost flex items-center gap-2"
            >
              <Search className="h-4 w-4" />
              Search
            </Link>
            <Link
              to={`/cases/${id}/reports`}
              className="btn-ghost flex items-center gap-2"
            >
              <FileText className="h-4 w-4" />
              Reports
            </Link>
            <Link
              to={`/cases/${id}/logs`}
              className="btn-ghost flex items-center gap-2"
            >
              <ClipboardList className="h-4 w-4" />
              Logs
            </Link>
          </div>
        }
      />

      <div className="p-6 animate-in">
        {/* Case Header */}
        <div className="card mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-accent-cyan/20 flex items-center justify-center">
                <Database className="h-7 w-7 text-accent-cyan" />
              </div>
              <div>
                <h1 className="text-2xl font-bold mb-1">{caseData.name}</h1>
                <p className="text-forensic-400 mb-2">
                  {caseData.description || 'No description'}
                </p>
                <div className="flex items-center gap-3">
                  <span className={`badge ${
                    caseData.status === 'active' ? 'badge-emerald' :
                    caseData.status === 'archived' ? 'badge-amber' :
                    'badge-gray'
                  }`}>
                    {caseData.status || 'active'}
                  </span>
                  {caseData.investigator && (
                    <span className="text-sm text-forensic-500">
                      Investigator: {caseData.investigator}
                    </span>
                  )}
                  <span className="text-sm text-forensic-500">
                    ID: <span className="font-mono text-accent-cyan">{caseData.id}</span>
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link to={`/cases/${id}/edit`} className="btn-secondary flex items-center gap-2">
                <Edit className="h-4 w-4" />
                Edit
              </Link>
              <button
                onClick={handleDelete}
                disabled={deleteLoading}
                className="btn-danger flex items-center gap-2"
              >
                {deleteLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                Delete
              </button>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-forensic-700 flex items-center gap-6 text-sm text-forensic-500">
            <span>
              Created: {new Date(caseData.created_at).toLocaleString()}
            </span>
            <span>
              Updated: {new Date(caseData.updated_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Evidence Section */}
        <div className="card mb-6">
          <button
            onClick={() => toggleSection('evidence')}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
                <Package className="h-5 w-5 text-accent-emerald" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Evidence Management</h2>
                <p className="text-sm text-forensic-500">
                  Upload and manage evidence files
                </p>
              </div>
            </div>
            {activeSection === 'evidence' ? (
              <ChevronDown className="h-5 w-5 text-forensic-400" />
            ) : (
              <ChevronRight className="h-5 w-5 text-forensic-400" />
            )}
          </button>

          {activeSection === 'evidence' && (
            <div className="mt-6 pt-6 border-t border-forensic-700 space-y-6">
              <EvidenceUploader
                caseId={id}
                onUploadSuccess={(uploadedEvidence) => {
                  setSelectedEvidenceId(uploadedEvidence?.id ?? null);
                  setEvidenceRefreshToken((token) => token + 1);
                  setActiveSection('whatsapp');
                }}
              />
              <EvidenceInventory
                caseId={id}
                refreshToken={evidenceRefreshToken}
                selectedEvidenceId={selectedEvidenceId}
                onSelectEvidence={(evId) => setSelectedEvidenceId(evId)}
              />
            </div>
          )}
        </div>

        {/* Analysis Section - Only show if evidence is selected */}
        {selectedEvidenceId && (
          <>
            {/* WhatsApp Analysis */}
            <div className="card mb-6">
              <button
                onClick={() => toggleSection('whatsapp')}
                className="w-full flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
                    <svg className="h-5 w-5 text-accent-emerald" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413"/>
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold">WhatsApp Analysis</h2>
                    <p className="text-sm text-forensic-500">
                      Extract messages, contacts, groups, and media
                    </p>
                  </div>
                </div>
                {activeSection === 'whatsapp' ? (
                  <ChevronDown className="h-5 w-5 text-forensic-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-forensic-400" />
                )}
              </button>

              {activeSection === 'whatsapp' && (
                <div className="mt-6 pt-6 border-t border-forensic-700">
                  <WhatsAppAnalysis evidenceId={selectedEvidenceId} />
                </div>
              )}
            </div>

            {/* Telegram Analysis */}
            <div className="card mb-6">
              <button
                onClick={() => toggleSection('telegram')}
                className="w-full flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-accent-blue/20 flex items-center justify-center">
                    <svg className="h-5 w-5 text-accent-blue" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold">Telegram Analysis</h2>
                    <p className="text-sm text-forensic-500">
                      Extract messages, contacts, channels, and media
                    </p>
                  </div>
                </div>
                {activeSection === 'telegram' ? (
                  <ChevronDown className="h-5 w-5 text-forensic-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-forensic-400" />
                )}
              </button>

              {activeSection === 'telegram' && (
                <div className="mt-6 pt-6 border-t border-forensic-700">
                  <TelegramAnalysis evidenceId={selectedEvidenceId} />
                </div>
              )}
            </div>
          </>
        )}

        {/* Quick Navigation */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Link
              to={`/cases/${id}/dashboard`}
              className="flex flex-col items-center gap-2 p-4 rounded-lg bg-forensic-800 hover:bg-forensic-700 transition-colors"
            >
              <LayoutDashboard className="h-6 w-6 text-accent-cyan" />
              <span className="text-sm">Dashboard</span>
            </Link>
            <Link
              to={`/cases/${id}/search`}
              className="flex flex-col items-center gap-2 p-4 rounded-lg bg-forensic-800 hover:bg-forensic-700 transition-colors"
            >
              <Search className="h-6 w-6 text-accent-emerald" />
              <span className="text-sm">Search</span>
            </Link>
            <Link
              to={`/cases/${id}/reports`}
              className="flex flex-col items-center gap-2 p-4 rounded-lg bg-forensic-800 hover:bg-forensic-700 transition-colors"
            >
              <FileText className="h-6 w-6 text-accent-amber" />
              <span className="text-sm">Reports</span>
            </Link>
            <Link
              to={`/cases/${id}/logs`}
              className="flex flex-col items-center gap-2 p-4 rounded-lg bg-forensic-800 hover:bg-forensic-700 transition-colors"
            >
              <ClipboardList className="h-6 w-6 text-accent-violet" />
              <span className="text-sm">Logs</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CaseDetailPage;
