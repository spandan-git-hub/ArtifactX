import { useState } from 'react';
import { Search, X, Filter, Loader2 } from 'lucide-react';

const SearchBar = ({
  onSearch,
  onClear,
  placeholder = 'Search messages, contacts, media...',
  loading = false,
}) => {
  const [query, setQuery] = useState('');
  const [appFilter, setAppFilter] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), appFilter);
    }
  };

  const handleClear = () => {
    setQuery('');
    setAppFilter('all');
    onClear();
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-forensic-500 h-5 w-5" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="w-full pl-12 pr-10 py-3 rounded-lg bg-forensic-800 border border-forensic-700
                       text-forensic-100 placeholder-forensic-500
                       focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20
                       transition-all duration-200"
            disabled={loading}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-forensic-500 hover:text-forensic-300 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`px-4 py-3 rounded-lg border transition-all duration-200 flex items-center gap-2 ${
            showFilters
              ? 'bg-accent-cyan/10 border-accent-cyan/50 text-accent-cyan'
              : 'bg-forensic-800 border-forensic-700 text-forensic-400 hover:text-forensic-200 hover:border-forensic-600'
          }`}
        >
          <Filter className="h-5 w-5" />
          <span className="hidden sm:inline">Filters</span>
        </button>

        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="btn-primary px-6 py-3"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="h-5 w-5" />
              Search
            </>
          )}
        </button>
      </form>

      {showFilters && (
        <div className="mt-4 pt-4 border-t border-forensic-700">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm font-medium text-forensic-400 mb-2">
                App Filter
              </label>
              <select
                value={appFilter}
                onChange={(e) => setAppFilter(e.target.value)}
                className="px-4 py-2 rounded-lg bg-forensic-800 border border-forensic-700 text-forensic-100
                           focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20"
              >
                <option value="all">All Apps</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="telegram">Telegram</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {query && (
        <div className="mt-3 flex items-center justify-between">
          <p className="text-sm text-forensic-500">
            Searching for: <span className="text-forensic-200 font-medium">"{query}"</span>
          </p>
          <button
            type="button"
            onClick={handleClear}
            className="text-sm text-accent-cyan hover:text-accent-cyan-light transition-colors"
          >
            Clear search
          </button>
        </div>
      )}
    </div>
  );
};

export default SearchBar;