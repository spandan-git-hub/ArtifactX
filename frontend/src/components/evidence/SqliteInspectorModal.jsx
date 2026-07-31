import { useState, useEffect } from 'react';
import {
  X,
  Database,
  Table as TableIcon,
  Code,
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  FileCode,
  Key,
} from 'lucide-react';
import { inspectSqliteDatabase } from '../../services/evidenceService';

const SqliteInspectorModal = ({ isOpen, onClose, evidenceId, fileId: initialFileId, fileName }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Inspector state
  const [selectedFileId, setSelectedFileId] = useState(initialFileId);
  const [activeTable, setActiveTable] = useState(null);
  const [tables, setTables] = useState([]);
  const [availableDbs, setAvailableDbs] = useState([]);
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [totalRows, setTotalRows] = useState(0);
  const [dbName, setDbName] = useState('');

  // Pagination & filter
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [filterQuery, setFilterQuery] = useState('');
  const [showDdl, setShowDdl] = useState(false);

  useEffect(() => {
    if (!isOpen || !evidenceId) return;

    setSelectedFileId(initialFileId);
    setActiveTable(null);
    setOffset(0);
    loadDatabase(initialFileId, null, 50, 0);
  }, [isOpen, evidenceId, initialFileId]);

  const loadDatabase = async (fId, tName, lim = limit, off = offset) => {
    try {
      setLoading(true);
      setError(null);

      const data = await inspectSqliteDatabase(evidenceId, {
        fileId: fId,
        tableName: tName,
        limit: lim,
        offset: off,
      });

      setDbName(data.database_name || fileName || 'Database Inspector');
      setAvailableDbs(data.available_databases || []);
      setTables(data.tables || []);
      setSelectedFileId(data.file_id);
      setActiveTable(data.selected_table);
      setColumns(data.columns || []);
      setRows(data.rows || []);
      setTotalRows(data.total_rows || 0);
    } catch (err) {
      console.error('Failed to inspect SQLite database:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to inspect SQLite database');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleTableChange = (tName) => {
    setActiveTable(tName);
    setOffset(0);
    loadDatabase(selectedFileId, tName, limit, 0);
  };

  const handleDbChange = (newFileId) => {
    setSelectedFileId(newFileId);
    setActiveTable(null);
    setOffset(0);
    loadDatabase(newFileId, null, limit, 0);
  };

  const handlePageChange = (newOffset) => {
    setOffset(newOffset);
    loadDatabase(selectedFileId, activeTable, limit, newOffset);
  };

  const selectedTableMeta = tables.find((t) => t.name === activeTable);
  const pageIndex = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(totalRows / limit) || 1;

  const filteredRows = rows.filter((r) => {
    if (!filterQuery.trim()) return true;
    return Object.values(r).some((val) =>
      String(val).toLowerCase().includes(filterQuery.toLowerCase())
    );
  });

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
      <div className="w-full max-w-6xl bg-forensic-900 border border-forensic-800 rounded-xl shadow-2xl h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-forensic-800 flex items-center justify-between bg-forensic-950">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent-violet/20 flex items-center justify-center border border-accent-violet/30">
              <Database className="w-5 h-5 text-accent-violet" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono font-bold text-forensic-100 text-lg">
                  {dbName}
                </h3>
                <span className="badge badge-violet text-xs">SQLite Inspector</span>
              </div>
              <p className="text-xs text-forensic-400 font-mono">
                {tables.length} Table(s) Extracted
              </p>
            </div>
          </div>

          {/* Database Selector Dropdown if multiple .db files exist */}
          <div className="flex items-center gap-3">
            {availableDbs.length > 1 && (
              <select
                value={selectedFileId || ''}
                onChange={(e) => handleDbChange(Number(e.target.value))}
                className="input py-1.5 px-3 text-xs bg-forensic-900 font-mono border-forensic-800"
              >
                {availableDbs.map((db) => (
                  <option key={db.id} value={db.id}>
                    {db.relative_path}
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-forensic-400 hover:text-forensic-100 hover:bg-forensic-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Grid */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Pane: Table Registry List */}
          <div className="w-64 border-r border-forensic-800 bg-forensic-950/60 flex flex-col">
            <div className="p-3 border-b border-forensic-800/80 text-xs font-semibold text-forensic-400 flex items-center justify-between">
              <span className="uppercase tracking-wider">Database Tables</span>
              <span className="font-mono text-accent-cyan">{tables.length}</span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {loading && tables.length === 0 ? (
                <div className="p-4 text-center">
                  <Loader2 className="w-5 h-5 animate-spin text-accent-cyan mx-auto mb-2" />
                  <span className="text-xs text-forensic-500 font-mono">Loading tables...</span>
                </div>
              ) : tables.length === 0 ? (
                <p className="p-3 text-xs text-forensic-500 text-center">No SQLite tables found.</p>
              ) : (
                tables.map((t) => {
                  const isSelected = activeTable === t.name;
                  return (
                    <button
                      key={t.name}
                      onClick={() => handleTableChange(t.name)}
                      className={`
                        w-full flex items-center justify-between p-2.5 rounded-lg text-xs font-mono transition-colors text-left
                        ${
                          isSelected
                            ? 'bg-accent-cyan/15 text-accent-cyan font-semibold border border-accent-cyan/30'
                            : 'text-forensic-300 hover:bg-forensic-800/60 hover:text-forensic-100'
                        }
                      `}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <TableIcon className="w-3.5 h-3.5 flex-shrink-0" />
                        <span className="truncate">{t.name}</span>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-forensic-800 text-forensic-400 font-mono">
                        {t.row_count}
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Pane: Table Data & Schema Viewer */}
          <div className="flex-1 flex flex-col bg-forensic-900/60 overflow-hidden">
            {error ? (
              <div className="p-8 flex items-center justify-center flex-1">
                <div className="card max-w-md border-accent-rose/30 bg-accent-rose/5 p-6 text-center">
                  <AlertCircle className="w-8 h-8 text-accent-rose mx-auto mb-2" />
                  <h4 className="text-accent-rose font-bold mb-1">SQLite Error</h4>
                  <p className="text-forensic-400 text-xs">{error}</p>
                </div>
              </div>
            ) : !activeTable ? (
              <div className="flex-1 flex items-center justify-center text-forensic-500 text-sm">
                Select a table from the sidebar to inspect records.
              </div>
            ) : (
              <>
                {/* Table Control Bar */}
                <div className="p-3 border-b border-forensic-800 bg-forensic-950/40 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <h4 className="text-sm font-mono font-bold text-forensic-100 flex items-center gap-2">
                      <TableIcon className="w-4 h-4 text-accent-cyan" />
                      <span>{activeTable}</span>
                    </h4>
                    <span className="text-xs text-forensic-400 font-mono">
                      {totalRows} Total Row(s)
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Search filter input */}
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-forensic-500" />
                      <input
                        type="text"
                        value={filterQuery}
                        onChange={(e) => setFilterQuery(e.target.value)}
                        placeholder="Search table rows..."
                        className="input pl-8 py-1 text-xs w-48 bg-forensic-900 border-forensic-800"
                      />
                    </div>

                    {/* DDL Schema Toggle */}
                    <button
                      onClick={() => setShowDdl(!showDdl)}
                      className={`btn-secondary py-1 px-3 text-xs inline-flex items-center gap-1.5 ${
                        showDdl ? 'border-accent-violet text-accent-violet bg-accent-violet/10' : ''
                      }`}
                    >
                      <Code className="w-3.5 h-3.5" />
                      <span>{showDdl ? 'Hide DDL' : 'Show DDL'}</span>
                    </button>
                  </div>
                </div>

                {/* Optional DDL Schema Display */}
                {showDdl && selectedTableMeta?.sql && (
                  <div className="p-4 bg-forensic-950 border-b border-forensic-800 animate-in fade-in">
                    <div className="flex items-center gap-2 text-xs font-semibold text-accent-violet mb-2">
                      <FileCode className="w-4 h-4" />
                      <span>SQL Schema DDL Definition</span>
                    </div>
                    <pre className="p-3 rounded bg-forensic-900 text-forensic-200 font-mono text-xs overflow-x-auto border border-forensic-800">
                      {selectedTableMeta.sql}
                    </pre>
                  </div>
                )}

                {/* Data Grid Container */}
                <div className="flex-1 overflow-auto p-4">
                  {loading ? (
                    <div className="flex items-center justify-center py-20">
                      <Loader2 className="w-7 h-7 animate-spin text-accent-cyan" />
                      <span className="ml-2 text-forensic-400 text-xs font-mono">Fetching rows...</span>
                    </div>
                  ) : filteredRows.length === 0 ? (
                    <div className="text-center py-16 text-forensic-500 text-sm">
                      No records found in table <code className="text-accent-cyan">{activeTable}</code>.
                    </div>
                  ) : (
                    <div className="table-container border border-forensic-800 rounded-lg">
                      <table className="data-table text-xs font-mono">
                        <thead className="bg-forensic-950 sticky top-0 border-b border-forensic-800">
                          <tr>
                            {columns.map((col) => (
                              <th key={col.name} className="py-2.5 px-3 text-forensic-300">
                                <div className="flex items-center gap-1.5">
                                  {col.pk && <Key className="w-3 h-3 text-accent-cyan" />}
                                  <span>{col.name}</span>
                                  <span className="text-[10px] text-forensic-500 font-normal">
                                    ({col.type})
                                  </span>
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-forensic-800/60 bg-forensic-900/40">
                          {filteredRows.map((row, idx) => (
                            <tr key={idx} className="hover:bg-forensic-800/50 transition-colors">
                              {columns.map((col) => {
                                const val = row[col.name];
                                const isNull = val === null || val === undefined;
                                return (
                                  <td key={col.name} className="py-2 px-3 whitespace-nowrap max-w-xs truncate">
                                    {isNull ? (
                                      <span className="text-forensic-600 italic">NULL</span>
                                    ) : typeof val === 'object' ? (
                                      JSON.stringify(val)
                                    ) : (
                                      String(val)
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Pagination Footer */}
                <div className="px-4 py-2.5 border-t border-forensic-800 bg-forensic-950 flex items-center justify-between text-xs text-forensic-400 font-mono">
                  <div className="flex items-center gap-2">
                    <span>Rows per page:</span>
                    <select
                      value={limit}
                      onChange={(e) => {
                        const newLimit = Number(e.target.value);
                        setLimit(newLimit);
                        setOffset(0);
                        loadDatabase(selectedFileId, activeTable, newLimit, 0);
                      }}
                      className="bg-forensic-900 border border-forensic-800 text-forensic-200 px-2 py-0.5 rounded"
                    >
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-4">
                    <span>
                      Page {pageIndex} of {totalPages} ({totalRows} rows)
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handlePageChange(Math.max(0, offset - limit))}
                        disabled={offset === 0}
                        className="btn-ghost p-1 disabled:opacity-40 disabled:hover:bg-transparent"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handlePageChange(offset + limit)}
                        disabled={offset + limit >= totalRows}
                        className="btn-ghost p-1 disabled:opacity-40 disabled:hover:bg-transparent"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SqliteInspectorModal;
