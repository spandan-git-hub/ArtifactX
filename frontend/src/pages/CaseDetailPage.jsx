import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { caseService } from '../services/caseService';
import EvidenceUploader from '../components/evidence/EvidenceUploader';
import EvidenceInventory from '../components/evidence/EvidenceInventory';
import WhatsAppAnalysis from '../components/whatsapp/WhatsAppAnalysis';
import { Search, LayoutDashboard, FileText } from 'lucide-react';

const CaseDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  if (loading) return <div className="p-6">Loading case...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;
  if (!caseData) return <div className="p-6">Case not found.</div>;

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold">{caseData.name || 'Unnamed Case'}</h1>
          <p className="text-gray-600">{caseData.description || 'No description'}</p>
        </div>
        <div className="space-x-3">
          <Link to={`/cases/${caseData.id}/edit`} className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700">
            Edit
          </Link>
          <button
            onClick={() => {
              if (window.confirm('Are you sure you want to delete this case?')) {
                caseService.deleteCase(caseData.id).then(() => {
                  navigate('/cases');
                });
              }
            }}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="font-semibold mb-2">Case Information</h2>
          <p className="text-sm text-gray-500"><strong>ID:</strong> {caseData.id}</p>
          <p className="text-sm text-gray-500"><strong>Status:</strong> {caseData.status || 'active'}</p>
          <p className="text-sm text-gray-500"><strong>Investigator:</strong> {caseData.investigator || 'Not assigned'}</p>
          <p className="text-sm text-gray-500"><strong>Created:</strong> {new Date(caseData.created_at).toLocaleString()}</p>
          <p className="text-sm text-gray-500"><strong>Updated:</strong> {new Date(caseData.updated_at).toLocaleString()}</p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <EvidenceUploader caseId={caseData.id} />
          <EvidenceInventory caseId={caseData.id} />
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="font-semibold mb-2">WhatsApp Analysis</h2>
          <p className="text-sm text-gray-500">
            Analyze WhatsApp databases extracted from evidence to retrieve messages, contacts, groups, and media.
          </p>
          {/* We'll need to select evidence for analysis - for now, we'll show a placeholder */}
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <p className="text-gray-500">
              Select evidence from the inventory above to analyze WhatsApp data.
            </p>
          </div>
        </div>
      </div>

      <Link to="/cases" className="mt-6 inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
        Back to Cases List
      </Link>
      <Link
        to={`/cases/${caseData.id}/dashboard`}
        className="mt-6 ml-3 inline-block bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
      >
        <LayoutDashboard className="inline h-4 w-4 mr-1" />
        Dashboard
      </Link>
      <Link
        to={`/cases/${caseData.id}/search`}
        className="mt-6 ml-3 inline-block bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
      >
        <Search className="inline h-4 w-4 mr-1" />
        Search
      </Link>
      <Link
        to={`/cases/${caseData.id}/reports`}
        className="mt-6 ml-3 inline-block bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
      >
        <FileText className="inline h-4 w-4 mr-1" />
        Reports
      </Link>
    </div>
  );
};

export default CaseDetailPage;