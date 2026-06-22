import { useState } from 'react';
import { Search, X, Filter } from 'lucide-react';

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
    <div className="bg-white rounded-lg shadow p-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`p-2 border rounded-lg ${showFilters ? 'bg-blue-50 border-blue-300 text-blue-600' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
        >
          <Filter className="h-5 w-5" />
        </button>

        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? (
            <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
          ) : (
            'Search'
          )}
        </button>
      </form>

      {showFilters && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                App Filter
              </label>
              <select
                value={appFilter}
                onChange={(e) => setAppFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
          <p className="text-sm text-gray-600">
            Searching for: <span className="font-medium">"{query}"</span>
          </p>
          <button
            type="button"
            onClick={handleClear}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Clear search
          </button>
        </div>
      )}
    </div>
  );
};

export default SearchBar;