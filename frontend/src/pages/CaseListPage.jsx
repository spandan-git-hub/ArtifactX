import { useCases } from '../hooks/useCases';
import { Link } from 'react-router-dom';

const CaseListPage = () => {
  const { cases, loading, error, deleteCase } = useCases();

  if (loading) return <div className="p-6">Loading cases...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Cases</h1>
      <Link to="/cases/create" className="mb-4 inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
        Create New Case
      </Link>

      {cases.length === 0 ? (
        <p className="text-gray-500">No cases found.</p>
      ) : (
        <div className="space-y-4">
          {cases.map(caseItem => (
            <div key={caseItem.id} className="border rounded-lg p-4 flex justify-between items-start bg-white shadow-sm">
              <div>
                <h2 className="font-semibold">{caseItem.name || 'Unnamed Case'}</h2>
                <p className="text-sm text-gray-600">{caseItem.description || ''}</p>
                <p className="text-xs text-gray-400">
                  Created: {new Date(caseItem.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="space-x-2">
                <Link to={`/cases/${caseItem.id}`} className="text-blue-600 hover:underline">View</Link>
                <Link to={`/cases/${caseItem.id}/edit`} className="text-yellow-600 hover:underline">Edit</Link>
                <button
                  onClick={() => {
                    if (window.confirm('Are you sure you want to delete this case?')) {
                      deleteCase(caseItem.id);
                    }
                  }}
                  className="text-red-600 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CaseListPage;