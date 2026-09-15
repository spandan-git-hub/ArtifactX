import { useState } from 'react';
import { useParams } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import { useGlobalSearch } from '../hooks/useSearch';

const SearchPage = () => {
  const { caseId } = useParams();
  const { results, loading: searchLoading, error: searchError, query, search, clear } = useGlobalSearch();

  const handleSearch = (searchQuery, app) => {
    search(parseInt(caseId), searchQuery, app);
  };

  return (
    <CaseWorkspacePage>
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
    </CaseWorkspacePage>
  );
};

export default SearchPage;