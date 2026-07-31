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
    <div className="animate-in space-y-6">
      {/* Search Bar */}
      <div>
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