import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';
import { parsingService } from '../services/parsingService';

export default function ParsingPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;
  const [searchParams, setSearchParams] = useSearchParams();

  // Inventory state
  const [fileList, setFileList] = useState([]);
  const [counts, setCounts] = useState({ databases: 0, documents: 0, media: 0, other: 0 });
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [fileSearch, setFileSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Currently inspected file
  const [selectedFile, setSelectedFile] = useState(null);
  const [inspectData, setInspectData] = useState(null);
  const [loadingInspect, setLoadingInspect] = useState(false);
  const [inspectError, setInspectError] = useState(null);

  // Database inspection parameters
  const [activeTable, setActiveTable] = useState(null);
  const [tableSearch, setTableSearch] = useState('');
  const [debouncedTableSearch, setDebouncedTableSearch] = useState('');
  const [pageLimit, setPageLimit] = useState(50);
  const [pageOffset, setPageOffset] = useState(0);

  // Selected row for drill-down modal/drawer
  const [inspectedRow, setInspectedRow] = useState(null);

  // Text / Raw inspection state
  const [viewMode, setViewMode] = useState('formatted'); // 'formatted' | 'raw' | 'hex'
  const [textSearch, setTextSearch] = useState('');
  const [copiedText, setCopiedText] = useState(null);

  // Media preview state
  const [mediaDimensions, setMediaDimensions] = useState(null);
  const [mediaZoom, setMediaZoom] = useState(1);

  const autoSelectedRef = useRef(false);

  // Reset auto-selected ref when caseId changes
  useEffect(() => {
    autoSelectedRef.current = false;
  }, [caseId]);

  // Debounce table search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedTableSearch(tableSearch);
      setPageOffset(0); // reset to page 1 on new search
    }, 350);
    return () => clearTimeout(handler);
  }, [tableSearch]);

  const formatFileSize = (bytes) => {
    if (!bytes || isNaN(bytes)) return '0 B';
    const num = Number(bytes);
    if (num < 1024) return `${num} B`;
    if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KiB`;
    if (num < 1024 * 1024 * 1024) return `${(num / (1024 * 1024)).toFixed(2)} MiB`;
    return `${(num / (1024 * 1024 * 1024)).toFixed(2)} GiB`;
  };

  const copyToClipboard = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedText(key);
    setTimeout(() => setCopiedText(null), 2200);
  };

  // 1. Fetch file inventory for active case
  const loadCaseFiles = useCallback(async () => {
    if (!caseId) {
      setFileList([]);
      setLoadingFiles(false);
      return;
    }
    setLoadingFiles(true);
    try {
      const data = await parsingService.getAccessibleFiles(caseId);
      const files = data?.files || [];
      setFileList(files);
      setCounts(data?.counts || { databases: 0, documents: 0, media: 0, other: 0 });

      // Auto-select once if not selected or if URL specifies target
      if (!autoSelectedRef.current && files.length > 0) {
        const qType = searchParams.get('type');
        const qId = searchParams.get('id');
        let target = null;
        if (qType && qId) {
          target = files.find(f => f.target_type === qType && String(f.target_id) === String(qId));
        }
        if (!target) {
          target = files.find(f => f.category === 'database') || files[0];
        }
        if (target) {
          autoSelectedRef.current = true;
          setSelectedFile(target);
        }
      }
    } catch (err) {
      console.error('Failed to load parsable files:', err);
    } finally {
      setLoadingFiles(false);
    }
  }, [caseId, searchParams]);

  useEffect(() => {
    loadCaseFiles();
  }, [loadCaseFiles]);

  // 2. Fetch file content / table data when selected file, activeTable, search, or pagination changes
  const fetchInspectedData = useCallback(async () => {
    if (!caseId || !selectedFile) {
      setInspectData(null);
      return;
    }
    setLoadingInspect(true);
    setInspectError(null);
    try {
      const data = await parsingService.inspectFile(caseId, {
        target_type: selectedFile.target_type,
        target_id: selectedFile.target_id,
        table_name: activeTable,
        search: debouncedTableSearch,
        limit: pageLimit,
        offset: pageOffset,
      });
      setInspectData(data);
      if (data.is_database && data.selected_table && !activeTable) {
        setActiveTable(data.selected_table);
      }
    } catch (err) {
      console.error('Failed to inspect file:', err);
      setInspectError(err.response?.data?.detail || err.message || 'Failed to inspect file.');
    } finally {
      setLoadingInspect(false);
    }
  }, [caseId, selectedFile, activeTable, debouncedTableSearch, pageLimit, pageOffset]);

  useEffect(() => {
    fetchInspectedData();
  }, [fetchInspectedData]);

  // Reset pagination and table selection when switching files
  const handleSelectFile = (file) => {
    setSelectedFile(file);
    setActiveTable(null);
    setTableSearch('');
    setDebouncedTableSearch('');
    setPageOffset(0);
    setInspectedRow(null);
    setViewMode('formatted');
    setMediaDimensions(null);
    setMediaZoom(1);
    setSearchParams({ type: file.target_type, id: file.target_id });
  };

  // Switch database table
  const handleSwitchTable = (tblName) => {
    setActiveTable(tblName);
    setTableSearch('');
    setDebouncedTableSearch('');
    setPageOffset(0);
    setInspectedRow(null);
  };

  // Filtered files in left list
  const filteredFiles = useMemo(() => {
    return fileList.filter(file => {
      if (selectedCategory !== 'all' && file.category !== selectedCategory) {
        return false;
      }
      if (fileSearch.trim()) {
        const q = fileSearch.toLowerCase().trim();
        const fn = (file.filename || '').toLowerCase();
        const rp = (file.relative_path || '').toLowerCase();
        const sc = (file.source_container || '').toLowerCase();
        return fn.includes(q) || rp.includes(q) || sc.includes(q);
      }
      return true;
    });
  }, [fileList, selectedCategory, fileSearch]);

  const getCategoryIcon = (category, fileType) => {
    if (category === 'database') return 'database';
    if (category === 'media') {
      if (fileType === 'audio') return 'audio_file';
      if (fileType === 'video') return 'video_file';
      return 'image';
    }
    if (category === 'document') {
      if (fileType === 'xml' || fileType === 'json') return 'code';
      if (fileType === 'key') return 'vpn_key';
      return 'description';
    }
    return 'terminal';
  };

  const getCategoryBadgeClass = (category) => {
    if (category === 'database') return 'bg-primary/15 text-primary border-primary/30';
    if (category === 'media') return 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30';
    if (category === 'document') return 'bg-tertiary/15 text-tertiary border-tertiary/30';
    return 'bg-surface-variant text-on-surface-variant border-outline-variant';
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background text-on-surface overflow-hidden">
      {/* ================= PAGE HEADER ================= */}
      <div className="px-6 py-3.5 border-b border-outline-variant bg-surface-container-low flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded bg-primary/10 text-primary border border-primary/20 flex items-center justify-center">
              <span className="material-symbols-outlined text-lg">table_view</span>
            </span>
            <h1 className="text-headline-sm font-semibold tracking-tight text-on-surface">
              Parsing &amp; Tabular Content Inspector
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-primary/10 text-primary border border-primary/30 uppercase tracking-wider">
              Phase 4 Core
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Examine underlying tabular columns and rows of accessible SQLite databases and structured exhibits identified across case evidence.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to={caseId ? `/cases/${caseId}/decryption` : '/cases'}
            className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
            title="Return to Decryption & Key Autofill Tab"
          >
            <span className="material-symbols-outlined text-sm">lock_open</span>
            <span>Decryption Tab</span>
          </Link>
          <button
            type="button"
            onClick={fetchInspectedData}
            disabled={loadingInspect}
            className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
            title="Refresh current view"
          >
            <span className={`material-symbols-outlined text-sm ${loadingInspect ? 'animate-spin' : ''}`}>
              refresh
            </span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ================= SPLIT VIEW: MASTER (Files List) & DETAIL (Inspector Grid) ================= */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden">
        {/* ================= LEFT MASTER PANEL: ACCESSIBLE FILES ================= */}
        <div className="w-80 md:w-96 border-r border-outline-variant bg-surface-container-low flex flex-col shrink-0">
          {/* Header & Filter Controls */}
          <div className="p-3.5 border-b border-outline-variant space-y-2.5 bg-surface-container/50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-on-surface flex items-center gap-1.5">
                <span className="material-symbols-outlined text-sm text-primary">folder_open</span>
                <span>Case Exhibits &amp; Files</span>
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-surface-variant text-on-surface-variant border border-outline-variant">
                {fileList.length} files
              </span>
            </div>

            {/* File Search Input */}
            <div className="relative">
              <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-outline text-xs">
                search
              </span>
              <input
                type="text"
                placeholder="Filter by name or container..."
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-8 pr-3 py-1.5 text-xs text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
              />
              {fileSearch && (
                <button
                  type="button"
                  onClick={() => setFileSearch('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Category Filter Chips */}
            <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar pb-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => setSelectedCategory('all')}
                className={`px-2 py-0.5 rounded font-medium whitespace-nowrap transition-colors ${
                  selectedCategory === 'all'
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                All ({fileList.length})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory('database')}
                className={`px-2 py-0.5 rounded font-medium whitespace-nowrap transition-colors flex items-center gap-1 ${
                  selectedCategory === 'database'
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-[13px]">database</span>
                <span>DBs ({counts.databases})</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory('document')}
                className={`px-2 py-0.5 rounded font-medium whitespace-nowrap transition-colors flex items-center gap-1 ${
                  selectedCategory === 'document'
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-[13px]">code</span>
                <span>Docs ({counts.documents})</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory('media')}
                className={`px-2 py-0.5 rounded font-medium whitespace-nowrap transition-colors flex items-center gap-1 ${
                  selectedCategory === 'media'
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-[13px]">image</span>
                <span>Media ({counts.media})</span>
              </button>
            </div>
          </div>

          {/* Files List Items */}
          <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-outline-variant/40">
            {loadingFiles && (
              <div className="p-8 text-center text-on-surface-variant">
                <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                <p className="text-xs">Loading accessible files...</p>
              </div>
            )}

            {!loadingFiles && filteredFiles.length === 0 && (
              <div className="p-8 text-center text-on-surface-variant">
                <span className="material-symbols-outlined text-2xl text-outline mb-1">filter_alt_off</span>
                <p className="text-xs font-semibold">No matching files found</p>
                <p className="text-[11px] text-outline mt-0.5">Try clearing filters or search terms.</p>
              </div>
            )}

            {!loadingFiles && filteredFiles.map((file) => {
              const isSelected = selectedFile?.id === file.id;
              const icon = getCategoryIcon(file.category, file.file_type);

              return (
                <div
                  key={file.id}
                  onClick={() => handleSelectFile(file)}
                  className={`p-3 text-left transition-all cursor-pointer select-none flex items-start gap-2.5 ${
                    isSelected
                      ? 'bg-primary/10 border-l-4 border-l-primary shadow-xs'
                      : 'hover:bg-surface-container-high/40'
                  }`}
                >
                  <span className={`p-1.5 rounded mt-0.5 shrink-0 flex items-center justify-center ${
                    isSelected ? 'bg-primary text-on-primary' : 'bg-surface-container-highest text-on-surface-variant'
                  }`}>
                    <span className="material-symbols-outlined text-[15px]">{icon}</span>
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className={`text-xs font-mono font-medium truncate ${isSelected ? 'text-primary' : 'text-on-surface'}`}>
                        {file.filename}
                      </span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-semibold uppercase border shrink-0 ${getCategoryBadgeClass(file.category)}`}>
                        {file.is_derived ? 'Decrypted DB' : file.category}
                      </span>
                    </div>

                    <div className="text-[11px] text-on-surface-variant/80 font-mono truncate mt-0.5" title={file.relative_path}>
                      {file.relative_path}
                    </div>

                    <div className="flex items-center justify-between mt-1.5 text-[10px] font-mono text-outline">
                      <span className="truncate max-w-[130px]" title={file.source_container}>
                        From: {file.source_container}
                      </span>
                      <span>{formatFileSize(file.size_bytes)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ================= RIGHT DETAIL PANEL: UNIVERSAL PARSER & TABULAR GRID ================= */}
        <div className="flex-1 flex flex-col min-w-0 bg-background overflow-hidden">
          {!selectedFile ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-on-surface-variant">
              <span className="material-symbols-outlined text-4xl text-outline mb-2">table_chart_view</span>
              <h3 className="font-semibold text-base text-on-surface">No File Selected</h3>
              <p className="text-xs text-outline max-w-sm mt-1">
                Select any accessible database or exhibit file from the left sidebar to inspect its underlying columns, records, or structured content.
              </p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
              {/* Selected File Overview Topbar */}
              <div className="px-5 py-3 border-b border-outline-variant bg-surface-container-low flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 shrink-0">
                <div className="flex items-center space-x-2.5 min-w-0">
                  <span className="p-1.5 rounded bg-primary/10 text-primary border border-primary/20 shrink-0">
                    <span className="material-symbols-outlined text-base">
                      {getCategoryIcon(selectedFile.category, selectedFile.file_type)}
                    </span>
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-bold font-mono text-on-surface truncate">
                        {selectedFile.filename}
                      </span>
                      {selectedFile.is_derived && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-tertiary/15 text-tertiary border border-tertiary/30 font-semibold">
                          DECRYPTED DERIVED
                        </span>
                      )}
                      <span className="text-xs text-outline font-mono">
                        ({formatFileSize(selectedFile.size_bytes)})
                      </span>
                    </div>
                    <div className="text-[11px] text-on-surface-variant font-mono truncate mt-0.5">
                      Provenance: <span className="text-on-surface">{selectedFile.source_container}</span> · Path: {selectedFile.relative_path}
                    </div>
                  </div>
                </div>

                {/* Topbar Actions: Copy Hash, Export CSV */}
                <div className="flex items-center gap-2 shrink-0">
                  {selectedFile.sha256 && (
                    <button
                      type="button"
                      onClick={() => copyToClipboard(selectedFile.sha256, 'sha')}
                      className="px-2.5 py-1 rounded bg-surface-container border border-outline-variant text-[11px] font-mono text-on-surface hover:text-primary flex items-center gap-1 transition-colors"
                      title="Copy full SHA-256 digest"
                    >
                      <span className="material-symbols-outlined text-xs">
                        {copiedText === 'sha' ? 'check' : 'content_copy'}
                      </span>
                      <span>SHA-256: {selectedFile.sha256.substring(0, 8)}...</span>
                    </button>
                  )}

                  {inspectData?.is_database && inspectData?.rows?.length > 0 && (
                    <button
                      type="button"
                      onClick={() => parsingService.exportTableCsv(inspectData.selected_table, inspectData.columns, inspectData.rows)}
                      className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1 text-primary border-primary/30 hover:bg-primary/10"
                      title="Export current table rows to CSV"
                    >
                      <span className="material-symbols-outlined text-sm">download</span>
                      <span>Export CSV</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Error Alert if inspection failed */}
              {inspectError && (
                <div className="p-4 m-4 bg-error/10 border border-error/30 rounded-lg text-xs font-mono text-error flex items-center gap-2 shrink-0">
                  <span className="material-symbols-outlined text-base">error</span>
                  <span>{inspectError}</span>
                </div>
              )}

              {/* Loading State */}
              {loadingInspect && (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-on-surface-variant">
                  <span className="material-symbols-outlined text-3xl animate-spin text-primary mb-2">sync</span>
                  <p className="text-xs font-mono">Parsing file structures &amp; executing memory query...</p>
                </div>
              )}

              {/* ================= CASE 1: SQLITE DATABASE TABULAR VIEWER ================= */}
              {!loadingInspect && inspectData?.is_database && (
                <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                  {/* Database Table Dropdown Selector Bar */}
                  <div className="px-5 py-2.5 border-b border-outline-variant bg-surface-container flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex items-center gap-2">
                        <label htmlFor="table-select" className="text-xs font-semibold uppercase tracking-wider text-outline flex items-center gap-1.5 shrink-0">
                          <span className="material-symbols-outlined text-sm text-primary">table_rows</span>
                          <span>Table:</span>
                        </label>

                        <div className="relative">
                          <select
                            id="table-select"
                            value={inspectData.selected_table || ''}
                            onChange={(e) => handleSwitchTable(e.target.value)}
                            className="bg-surface-container-high hover:bg-surface-container-highest border border-primary/40 focus:border-primary text-on-surface font-mono text-xs font-semibold rounded-lg pl-3 pr-8 py-1.5 focus:outline-none cursor-pointer transition-colors shadow-xs appearance-none max-w-xs sm:max-w-md truncate"
                          >
                            {inspectData.tables?.map((tbl) => (
                              <option key={tbl.name} value={tbl.name} className="bg-surface-container text-on-surface font-mono">
                                {tbl.name} ({tbl.row_count} rows)
                              </option>
                            ))}
                          </select>
                          <span className="material-symbols-outlined absolute right-2.5 top-1/2 -translate-y-1/2 text-outline text-xs pointer-events-none">
                            arrow_drop_down
                          </span>
                        </div>
                      </div>

                      {/* Active Table Details Badge */}
                      <div className="flex items-center gap-2 text-xs font-mono">
                        <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 font-bold">
                          {inspectData.selected_table}
                        </span>
                        <span className="text-[11px] text-on-surface-variant">
                          {inspectData.total_rows} records
                        </span>
                        <span className="text-outline">·</span>
                        <span className="text-[11px] text-outline">
                          {inspectData.tables?.length || 0} tables in database
                        </span>
                      </div>
                    </div>

                    {/* Table Navigation Shortcuts: Prev / Next Table buttons */}
                    {inspectData.tables && inspectData.tables.length > 1 && (
                      <div className="flex items-center space-x-1.5 shrink-0">
                        <button
                          type="button"
                          onClick={() => {
                            const curIdx = inspectData.tables.findIndex(t => t.name === inspectData.selected_table);
                            if (curIdx > 0) {
                              handleSwitchTable(inspectData.tables[curIdx - 1].name);
                            }
                          }}
                          disabled={inspectData.tables.findIndex(t => t.name === inspectData.selected_table) <= 0}
                          className="px-2 py-1 rounded bg-surface-container-high border border-outline-variant hover:bg-surface-container-highest disabled:opacity-40 disabled:cursor-not-allowed text-xs font-mono text-on-surface flex items-center gap-1 transition-colors"
                          title="Previous Table"
                        >
                          <span className="material-symbols-outlined text-xs">arrow_back</span>
                          <span className="hidden md:inline">Prev Table</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            const curIdx = inspectData.tables.findIndex(t => t.name === inspectData.selected_table);
                            if (curIdx >= 0 && curIdx < inspectData.tables.length - 1) {
                              handleSwitchTable(inspectData.tables[curIdx + 1].name);
                            }
                          }}
                          disabled={inspectData.tables.findIndex(t => t.name === inspectData.selected_table) >= inspectData.tables.length - 1}
                          className="px-2 py-1 rounded bg-surface-container-high border border-outline-variant hover:bg-surface-container-highest disabled:opacity-40 disabled:cursor-not-allowed text-xs font-mono text-on-surface flex items-center gap-1 transition-colors"
                          title="Next Table"
                        >
                          <span className="hidden md:inline">Next Table</span>
                          <span className="material-symbols-outlined text-xs">arrow_forward</span>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Table Control Bar: Columns Schema, Search & Pagination */}
                  <div className="px-5 py-2 border-b border-outline-variant/60 bg-surface-container-lowest/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 shrink-0">
                    {/* Search inside active table */}
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <div className="relative w-full sm:w-64">
                        <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-outline text-xs">
                          filter_list
                        </span>
                        <input
                          type="text"
                          placeholder={`Search all columns in ${inspectData.selected_table || 'table'}...`}
                          value={tableSearch}
                          onChange={(e) => setTableSearch(e.target.value)}
                          className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-8 pr-3 py-1 text-xs text-on-surface placeholder:text-outline focus:outline-none focus:border-primary font-mono"
                        />
                        {tableSearch && (
                          <button
                            type="button"
                            onClick={() => setTableSearch('')}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface text-xs"
                          >
                            ✕
                          </button>
                        )}
                      </div>

                      <div className="text-[11px] font-mono text-outline shrink-0">
                        {inspectData.filtered_rows !== undefined ? (
                          <span>
                            {inspectData.filtered_rows} / {inspectData.total_rows} rows
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {/* Pagination Controls */}
                    <div className="flex items-center space-x-2 shrink-0">
                      <div className="flex items-center space-x-1 text-xs text-on-surface-variant font-mono">
                        <span className="text-[11px]">Rows:</span>
                        <select
                          value={pageLimit}
                          onChange={(e) => {
                            setPageLimit(Number(e.target.value));
                            setPageOffset(0);
                          }}
                          className="bg-surface-container border border-outline-variant rounded px-2 py-0.5 text-xs text-on-surface focus:outline-none font-mono"
                        >
                          <option value={25}>25</option>
                          <option value={50}>50</option>
                          <option value={100}>100</option>
                          <option value={250}>250</option>
                        </select>
                      </div>

                      <div className="flex items-center space-x-1">
                        <button
                          type="button"
                          disabled={pageOffset <= 0}
                          onClick={() => setPageOffset(prev => Math.max(0, prev - pageLimit))}
                          className="p-1 rounded bg-surface-container border border-outline-variant hover:bg-surface-container-high disabled:opacity-40 disabled:cursor-not-allowed text-on-surface transition-colors"
                          title="Previous page"
                        >
                          <span className="material-symbols-outlined text-sm">chevron_left</span>
                        </button>

                        <span className="text-[11px] font-mono text-on-surface px-1.5">
                          {Math.floor(pageOffset / pageLimit) + 1} / {Math.max(1, Math.ceil((inspectData.filtered_rows || 1) / pageLimit))}
                        </span>

                        <button
                          type="button"
                          disabled={pageOffset + pageLimit >= (inspectData.filtered_rows || 0)}
                          onClick={() => setPageOffset(prev => prev + pageLimit)}
                          className="p-1 rounded bg-surface-container border border-outline-variant hover:bg-surface-container-high disabled:opacity-40 disabled:cursor-not-allowed text-on-surface transition-colors"
                          title="Next page"
                        >
                          <span className="material-symbols-outlined text-sm">chevron_right</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Schema Columns Strip */}
                  {inspectData.columns && inspectData.columns.length > 0 && (
                    <div className="px-5 py-1.5 bg-surface-container/30 border-b border-outline-variant/40 flex items-center gap-1.5 overflow-x-auto custom-scrollbar text-[10px] font-mono shrink-0">
                      <span className="text-outline uppercase tracking-wider font-semibold mr-1">Schema:</span>
                      {inspectData.columns.map((col) => (
                        <span
                          key={col.name}
                          className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant border border-outline-variant/60 flex items-center gap-1 shrink-0"
                          title={`Type: ${col.type} | NotNull: ${col.notnull} | PK: ${col.pk}`}
                        >
                          <span className="font-semibold text-on-surface">{col.name}</span>
                          <span className="text-primary text-[9px] uppercase">({col.type})</span>
                          {col.pk && <span className="text-amber-400 font-bold">PK</span>}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* The Tabular Content Grid */}
                  <div className="flex-1 overflow-auto custom-scrollbar">
                    {(!inspectData.rows || inspectData.rows.length === 0) ? (
                      <div className="p-12 text-center text-on-surface-variant font-mono text-xs">
                        <span className="material-symbols-outlined text-3xl text-outline mb-1">table_rows_narrow</span>
                        <p className="font-semibold text-on-surface">No records match the current criteria.</p>
                        <p className="text-[11px] text-outline mt-0.5">
                          The table "{inspectData.selected_table}" has 0 rows or your search query yielded no results.
                        </p>
                      </div>
                    ) : (
                      <table className="w-full text-left border-collapse text-xs font-mono">
                        <thead className="bg-surface-container-high sticky top-0 z-10 border-b border-outline-variant shadow-xs">
                          <tr>
                            <th className="py-2 px-3 text-[10px] uppercase tracking-wider text-outline border-r border-outline-variant/40 w-12 text-center">
                              #
                            </th>
                            {inspectData.columns?.map((col) => (
                              <th
                                key={col.name}
                                className="py-2 px-3 text-[11px] uppercase tracking-wider text-on-surface font-semibold border-r border-outline-variant/40 whitespace-nowrap"
                              >
                                <div className="flex items-center gap-1.5">
                                  <span>{col.name}</span>
                                  {col.pk && <span className="text-amber-400 text-[9px] font-bold">PK</span>}
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-outline-variant/40">
                          {inspectData.rows.map((row, rowIdx) => (
                            <tr
                              key={rowIdx}
                              onClick={() => setInspectedRow(row)}
                              className="hover:bg-primary/5 transition-colors cursor-pointer group"
                            >
                              <td className="py-2 px-3 text-[10px] text-outline text-center border-r border-outline-variant/40 select-none group-hover:text-primary">
                                {pageOffset + rowIdx + 1}
                              </td>
                              {inspectData.columns?.map((col) => {
                                const val = row[col.name];
                                const isNull = val === null || val === undefined;
                                const isBinary = typeof val === 'string' && val.startsWith('<') && val.endsWith('>');

                                return (
                                  <td
                                    key={col.name}
                                    className="py-2 px-3 text-on-surface border-r border-outline-variant/30 max-w-xs truncate"
                                    title={String(val ?? '')}
                                  >
                                    {isNull ? (
                                      <span className="text-outline/50 italic text-[10px]">NULL</span>
                                    ) : isBinary ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-outline-variant/20 text-outline border border-outline-variant/30 font-mono">
                                        {val}
                                      </span>
                                    ) : (
                                      <span className="truncate text-on-surface">{String(val)}</span>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              )}

              {/* ================= CASE 2: STRUCTURED TEXT / XML / JSON VIEWER ================= */}
              {!loadingInspect && !inspectData?.is_database && !inspectData?.is_media && inspectData?.content_text !== undefined && (
                <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                  {/* Toolbar for Text/Code viewer */}
                  <div className="px-5 py-2.5 border-b border-outline-variant bg-surface-container flex items-center justify-between gap-3 shrink-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-on-surface uppercase tracking-wider">
                        {inspectData.file_type} Viewer
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-variant text-on-surface-variant border border-outline-variant">
                        {inspectData.line_count} lines · {inspectData.encoding}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {inspectData.formatted_content && (
                        <div className="flex items-center rounded border border-outline-variant overflow-hidden text-xs">
                          <button
                            type="button"
                            onClick={() => setViewMode('formatted')}
                            className={`px-2.5 py-1 ${viewMode === 'formatted' ? 'bg-primary text-on-primary font-semibold' : 'bg-surface-container text-on-surface-variant'}`}
                          >
                            Prettified
                          </button>
                          <button
                            type="button"
                            onClick={() => setViewMode('raw')}
                            className={`px-2.5 py-1 ${viewMode === 'raw' ? 'bg-primary text-on-primary font-semibold' : 'bg-surface-container text-on-surface-variant'}`}
                          >
                            Raw
                          </button>
                        </div>
                      )}

                      <button
                        type="button"
                        onClick={() => copyToClipboard(inspectData.formatted_content || inspectData.content_text, 'code')}
                        className="px-2.5 py-1 rounded bg-surface-container border border-outline-variant text-xs text-on-surface hover:text-primary flex items-center gap-1"
                        title="Copy content to clipboard"
                      >
                        <span className="material-symbols-outlined text-xs">
                          {copiedText === 'code' ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedText === 'code' ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Code Editor / Preformatted Display */}
                  <div className="flex-1 overflow-auto custom-scrollbar p-4 bg-surface-container-lowest font-mono text-xs text-on-surface">
                    <pre className="whitespace-pre font-mono leading-relaxed select-text">
                      <code>{viewMode === 'formatted' ? (inspectData.formatted_content || inspectData.content_text) : inspectData.content_text}</code>
                    </pre>
                  </div>
                </div>
              )}

              {/* ================= CASE 3: MEDIA PREVIEW (Images / Audio / Video) ================= */}
              {!loadingInspect && inspectData?.is_media && (
                <div className="flex-1 flex flex-col min-h-0 bg-surface-container-lowest overflow-hidden">
                  {/* Media Controls Toolbar */}
                  <div className="px-5 py-2.5 border-b border-outline-variant bg-surface-container flex items-center justify-between gap-3 shrink-0">
                    <div className="flex items-center space-x-2">
                      <span className="p-1 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center justify-center">
                        <span className="material-symbols-outlined text-sm">
                          {inspectData.file_type === 'audio' ? 'audiotrack' : inspectData.file_type === 'video' ? 'videocam' : 'image'}
                        </span>
                      </span>
                      <span className="text-xs font-semibold text-on-surface uppercase tracking-wider">
                        {inspectData.file_type} Forensic Preview
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                        {inspectData.mime_type}
                      </span>
                      {mediaDimensions && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-variant text-on-surface-variant border border-outline-variant">
                          {mediaDimensions.width} × {mediaDimensions.height} px
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {inspectData.file_type === 'image' && (
                        <div className="flex items-center rounded border border-outline-variant overflow-hidden text-xs bg-surface-container">
                          <button
                            type="button"
                            onClick={() => setMediaZoom(prev => Math.max(0.25, prev - 0.25))}
                            className="px-2 py-1 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
                            title="Zoom out"
                          >
                            <span className="material-symbols-outlined text-xs">zoom_out</span>
                          </button>
                          <span className="px-2 py-1 text-[11px] font-mono text-on-surface select-none border-x border-outline-variant">
                            {Math.round(mediaZoom * 100)}%
                          </span>
                          <button
                            type="button"
                            onClick={() => setMediaZoom(prev => Math.min(3, prev + 0.25))}
                            className="px-2 py-1 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
                            title="Zoom in"
                          >
                            <span className="material-symbols-outlined text-xs">zoom_in</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setMediaZoom(1)}
                            className="px-2 py-1 text-[11px] text-outline hover:text-on-surface hover:bg-surface-container-high border-l border-outline-variant"
                            title="Reset zoom"
                          >
                            Fit
                          </button>
                        </div>
                      )}

                      {(inspectData.media_preview || inspectData.media_base64) && (
                        <a
                          href={inspectData.media_preview || inspectData.media_base64}
                          download={inspectData.filename}
                          className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10"
                          title="Download media file"
                        >
                          <span className="material-symbols-outlined text-sm">download</span>
                          <span>Download</span>
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Media Content Display */}
                  <div className="flex-1 flex flex-col items-center justify-center p-6 overflow-auto custom-scrollbar">
                    {inspectData.file_type === 'image' && (inspectData.media_preview || inspectData.media_base64) ? (
                      <div className="max-w-3xl max-h-[85%] p-3 rounded-lg border border-outline-variant bg-surface-container shadow-xl flex flex-col items-center">
                        <div
                          className="overflow-auto max-h-[550px] flex items-center justify-center rounded p-2"
                          style={{
                            backgroundImage: 'radial-gradient(#333 1px, transparent 1px)',
                            backgroundSize: '16px 16px',
                            backgroundColor: '#121212'
                          }}
                        >
                          <img
                            src={inspectData.media_preview || inspectData.media_base64}
                            alt={inspectData.filename}
                            onLoad={(e) => {
                              setMediaDimensions({
                                width: e.currentTarget.naturalWidth,
                                height: e.currentTarget.naturalHeight
                              });
                            }}
                            style={{
                              transform: `scale(${mediaZoom})`,
                              transformOrigin: 'center center',
                              transition: 'transform 0.15s ease-out'
                            }}
                            className="max-h-[500px] object-contain rounded select-none shadow-md"
                          />
                        </div>
                        <div className="mt-3 flex items-center justify-between w-full text-xs font-mono text-on-surface-variant border-t border-outline-variant/60 pt-2 px-1">
                          <span>{inspectData.filename}</span>
                          <span>{formatFileSize(inspectData.size_bytes)}</span>
                        </div>
                      </div>
                    ) : inspectData.file_type === 'audio' && (inspectData.media_preview || inspectData.media_base64) ? (
                      <div className="p-8 rounded-xl border border-cyan-500/30 bg-surface-container shadow-2xl flex flex-col items-center space-y-5 max-w-lg w-full">
                        <div className="w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                          <span className="material-symbols-outlined text-3xl">audiotrack</span>
                        </div>
                        <div className="text-center space-y-1 w-full">
                          <p className="font-mono text-sm font-bold text-on-surface truncate">{inspectData.filename}</p>
                          <p className="text-xs text-outline font-mono">
                            {inspectData.mime_type} · {formatFileSize(inspectData.size_bytes)}
                          </p>
                        </div>
                        <div className="w-full bg-surface-container-high/60 p-3 rounded-lg border border-outline-variant">
                          <audio
                            controls
                            src={inspectData.media_preview || inspectData.media_base64}
                            className="w-full"
                          />
                        </div>
                      </div>
                    ) : inspectData.file_type === 'video' && (inspectData.media_preview || inspectData.media_base64) ? (
                      <div className="max-w-2xl max-h-[85%] p-4 rounded-xl border border-outline-variant bg-surface-container shadow-xl flex flex-col items-center space-y-3">
                        <video
                          controls
                          src={inspectData.media_preview || inspectData.media_base64}
                          className="max-h-[480px] rounded-lg w-full"
                        />
                        <div className="flex items-center justify-between w-full text-xs font-mono text-on-surface-variant">
                          <span>{inspectData.filename}</span>
                          <span>{formatFileSize(inspectData.size_bytes)}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center text-on-surface-variant font-mono">
                        <span className="material-symbols-outlined text-4xl text-outline mb-2">perm_media</span>
                        <p className="text-sm font-semibold text-on-surface">{inspectData.filename}</p>
                        <p className="text-xs text-outline mt-1">Preview buffer not available for this media asset.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ================= CASE 4: CANONICAL BINARY HEX DUMP ================= */}
              {!loadingInspect && inspectData?.hex_dump && (
                <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                  <div className="px-5 py-2.5 border-b border-outline-variant bg-surface-container flex items-center justify-between shrink-0">
                    <span className="text-xs font-semibold uppercase tracking-wider text-on-surface flex items-center gap-1.5 font-mono">
                      <span className="material-symbols-outlined text-sm text-primary">binary</span>
                      <span>Binary Hex Dump Inspector (Offset | Hex | ASCII)</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(inspectData.hex_dump, 'hexdump')}
                      className="px-2.5 py-1 rounded bg-surface-container border border-outline-variant text-xs text-on-surface hover:text-primary flex items-center gap-1 font-mono"
                    >
                      <span className="material-symbols-outlined text-xs">
                        {copiedText === 'hexdump' ? 'check' : 'content_copy'}
                      </span>
                      <span>{copiedText === 'hexdump' ? 'Copied' : 'Copy Dump'}</span>
                    </button>
                  </div>

                  <div className="flex-1 overflow-auto custom-scrollbar p-4 bg-surface-container-lowest font-mono text-xs text-on-surface leading-snug">
                    <pre className="whitespace-pre font-mono select-text">
                      <code>{inspectData.hex_dump}</code>
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ================= DRILL-DOWN RECORD INSPECTOR MODAL ================= */}
      {inspectedRow && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface-container border border-outline-variant rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-5 py-3.5 border-b border-outline-variant bg-surface-container-high flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2">
                <span className="p-1 rounded bg-primary/10 text-primary border border-primary/20">
                  <span className="material-symbols-outlined text-sm">view_timeline</span>
                </span>
                <h3 className="font-headline-sm text-on-surface font-semibold text-sm">
                  Record Inspector: {inspectData?.selected_table}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectedRow(null)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded hover:bg-surface-variant transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Body: Field key-values */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-3 font-mono text-xs">
              {Object.entries(inspectedRow).map(([key, val]) => (
                <div key={key} className="p-2.5 bg-surface-container-lowest rounded-md border border-outline-variant/60 flex flex-col space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">{key}</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(String(val ?? ''), `row_${key}`)}
                      className="text-[10px] text-outline hover:text-on-surface flex items-center gap-0.5"
                    >
                      <span className="material-symbols-outlined text-[11px]">
                        {copiedText === `row_${key}` ? 'check' : 'content_copy'}
                      </span>
                      <span>{copiedText === `row_${key}` ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="text-on-surface break-all select-text font-mono text-xs whitespace-pre-wrap">
                    {val === null || val === undefined ? (
                      <span className="italic text-outline/60">NULL</span>
                    ) : (
                      String(val)
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 border-t border-outline-variant bg-surface-container-high flex items-center justify-end">
              <button
                type="button"
                onClick={() => setInspectedRow(null)}
                className="btn-secondary text-xs px-4 py-1.5"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
