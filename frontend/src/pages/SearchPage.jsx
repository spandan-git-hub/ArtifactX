import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { caseService } from '../services/caseService';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import { useGlobalSearch } from '../hooks/useSearch';
import { ArrowLeft, Search, Loader2 } from 'lucide-react';

const SearchPage = () => {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { results, loading: searchLoading, error: searchError, query, search, clear } = useGlobalSearch();

  useEffect(() => {
    const loadCase = async () => {
      try {
        setLoading(true);
        const data = await caseService.getCase(caseId);
        setCaseData(data);
      } catch (err) {
        console.error('Failed to load case:', err);
      } finally {
        setLoading(false);
      }
    };

    if (caseId) {
      loadCase();
    }
  }, [caseId]);

  const handleSearch = (searchQuery, app) => {
    search(parseInt(caseId), searchQuery, app);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent-cyan" />
      </div>
    );
  }

  return (
    <div className="p-6 animate-in max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-forensic-500 mb-3">
          <Link to="/cases" className="hover:text-accent-cyan flex items-center gap-1 transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Cases
          </Link>
          <span className="text-forensic-700">/</span>
          <Link to={`/cases/${caseId}`} className="hover:text-accent-cyan transition-colors">
            {caseData?.name || 'Case'}
          </Link>
          <span className="text-forensic-700">/</span>
          <span className="text-accent-cyan">Search</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-accent-cyan/20">
            <Search className="h-6 w-6 text-accent-cyan" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-forensic-50">Search Evidence</h1>
            <p className="text-forensic-500">
              Search messages, contacts, and media for case: <span className="text-forensic-300">{caseData?.name}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <SearchBar
          onSearch={handleSearch}
          onClear={clear}
          loading={searchLoading}
        />
      </div>

      {/* Results */}
      <SearchResults
        results={results}
        loading={searchLoading}
        error={searchError}
        query={query}
      />
    </div>
  );
};

export default SearchPage;