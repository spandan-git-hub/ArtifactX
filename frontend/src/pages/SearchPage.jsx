import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { caseService } from '../services/caseService';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import { useGlobalSearch } from '../hooks/useSearch';

const SearchPage = () => {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { results, totalResults, loading: searchLoading, error: searchError, query, search, clear } = useGlobalSearch();

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

  const handleClear = () => {
    clear();
  };

  if (loading) {
    return <div className="p-6">Loading case...</div>;
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link to="/cases" className="hover:text-blue-600">Cases</Link>
          <span>/</span>
          <Link to={`/cases/${caseId}`} className="hover:text-blue-600">
            {caseData?.name || 'Case'}
          </Link>
          <span>/</span>
          <span>Search</span>
        </div>
        <h1 className="text-2xl font-bold">Search</h1>
        <p className="text-gray-600">
          Search messages, contacts, and media for case: {caseData?.name}
        </p>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <SearchBar
          onSearch={handleSearch}
          onClear={handleClear}
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