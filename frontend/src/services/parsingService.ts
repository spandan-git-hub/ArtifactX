import axios from 'axios';

const API_BASE = '/api';

export const parsingService = {
  /**
   * Fetch all accessible files for a given case (standalone evidence items,
   * unencrypted archive members, and decrypted derived artifacts).
   */
  getAccessibleFiles: async (caseId) => {
    const res = await axios.get(`${API_BASE}/cases/${caseId}/parsing/files`);
    return res.data;
  },

  /**
   * Inspect a specific case file:
   * - SQLite database: returns tables list, columns, and paginated rows.
   * - Documents / Text / XML / JSON: returns formatted content and line count.
   * - Media: returns preview data URI.
   * - Binary: returns hex dump representation.
   */
  inspectFile: async (caseId, {
    target_type,
    target_id,
    table_name = null,
    search = null,
    sort_by = null,
    sort_order = 'asc',
    limit = 100,
    offset = 0,
  }) => {
    const params = {
      target_type,
      target_id,
      limit,
      offset,
    };
    if (table_name) params.table_name = table_name;
    if (search && search.trim()) params.search = search.trim();
    if (sort_by) {
      params.sort_by = sort_by;
      params.sort_order = sort_order || 'asc';
    }

    const res = await axios.get(`${API_BASE}/cases/${caseId}/parsing/inspect`, { params });
    return res.data;
  },

  /**
   * Helper to export table rows as CSV download directly in browser.
   */
  exportTableCsv: (tableName, columns, rows) => {
    if (!columns || columns.length === 0 || !rows || rows.length === 0) return;

    const headers = columns.map(c => typeof c === 'string' ? c : c.name);
    const escapeCsv = (val) => {
      if (val === null || val === undefined) return '';
      const str = String(val);
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const csvLines = [
      headers.map(escapeCsv).join(','),
      ...rows.map(row => headers.map(h => escapeCsv(row[h])).join(','))
    ];

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tableName || 'export'}_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};
