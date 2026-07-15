import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCases } from '../hooks/useCases';
import { Header } from '../components/layout';
import {
  Plus,
  FolderKanban,
  Calendar,
  User,
  Trash2,
  Search,
  Loader2,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';

const CaseListPage = () => {
  const { cases, loading, error, deleteCase } = useCases();
  const [deleteLoading, setDeleteLoading] = useState(null);

  const handleDelete = async (caseItem) => {
    if (window.confirm(`Delete case "${caseItem.name}"? This cannot be undone.`)) {
      setDeleteLoading(caseItem.id);
      try {
        await deleteCase(caseItem.id);
      } catch (err) {
        alert('Failed to delete case');
      } finally {
        setDeleteLoading(null);
      }
    }
  };

  return (
    <div className="min-h-screen">
      <Header
        title="Case Management"
        breadcrumbs={[
          { label: 'ArtifactX', path: '/' },
          { label: 'Cases' },
        ]}
        actions={
          <Link to="/cases/create" className="btn-primary flex items-center gap-2">
            <Plus className="h-4 w-4" />
            New Case
          </Link>
        }
      />

      <div className="p-6 animate-in">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="stats-card">
            <div className="stats-card-icon text-accent-cyan">
              <FolderKanban className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{cases.length}</p>
              <p className="text-sm text-forensic-500">Total Cases</p>
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-card-icon text-accent-emerald">
              <User className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {cases.filter(c => c.status === 'active').length}
              </p>
              <p className="text-sm text-forensic-500">Active</p>
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-card-icon text-accent-amber">
              <Calendar className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {cases.filter(c => c.status === 'archived').length}
              </p>
              <p className="text-sm text-forensic-500">Archived</p>
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-card-icon text-accent-violet">
              <Calendar className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {cases.filter(c => c.status === 'closed').length}
              </p>
              <p className="text-sm text-forensic-500">Closed</p>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="card border-accent-rose/30 mb-6">
            <div className="flex items-center gap-3 text-accent-rose">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-accent-cyan" />
            <span className="ml-3 text-forensic-400">Loading cases...</span>
          </div>
        )}

        {/* Empty State */}
        {!loading && cases.length === 0 && (
          <div className="card text-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-forensic-800 flex items-center justify-center mx-auto mb-4">
              <FolderOpen className="h-8 w-8 text-forensic-500" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No cases yet</h3>
            <p className="text-forensic-500 mb-6 max-w-sm mx-auto">
              Create your first forensic case to start analyzing evidence
            </p>
            <Link to="/cases/create" className="btn-primary inline-flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Create First Case
            </Link>
          </div>
        )}

        {/* Cases Grid */}
        {!loading && cases.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cases.map((caseItem) => (
              <div
                key={caseItem.id}
                className="card card-hover group animate-in"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-accent-cyan/20 flex items-center justify-center">
                      <FolderKanban className="h-5 w-5 text-accent-cyan" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-forensic-100">
                        {caseItem.name || 'Unnamed Case'}
                      </h3>
                      <span className={`badge ${
                        caseItem.status === 'active' ? 'badge-emerald' :
                        caseItem.status === 'archived' ? 'badge-amber' :
                        'badge-gray'
                      }`}>
                        {caseItem.status || 'active'}
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-forensic-400 mb-4 line-clamp-2">
                  {caseItem.description || 'No description provided'}
                </p>

                <div className="flex items-center gap-4 text-xs text-forensic-500 mb-4">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {caseItem.created_at ? new Date(caseItem.created_at).toLocaleDateString() : 'N/A'}
                  </div>
                  {caseItem.investigator && (
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {caseItem.investigator}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 pt-4 border-t border-forensic-700">
                  <Link
                    to={`/cases/${caseItem.id}`}
                    className="btn-secondary flex-1 text-center text-sm"
                  >
                    View Details
                  </Link>
                  <Link
                    to={`/cases/${caseItem.id}/dashboard`}
                    className="btn-ghost p-2"
                    title="Dashboard"
                  >
                    <Search className="h-4 w-4" />
                  </Link>
                  <button
                    onClick={() => handleDelete(caseItem)}
                    disabled={deleteLoading === caseItem.id}
                    className="btn-ghost p-2 text-accent-rose hover:bg-accent-rose/10"
                    title="Delete"
                  >
                    {deleteLoading === caseItem.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CaseListPage;