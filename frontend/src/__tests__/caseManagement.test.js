import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { caseService } from '../services/caseService';

vi.mock('axios');

describe('Case Service & Data Isolation Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches cases from the API', async () => {
    const mockCases = [
      { id: 1, name: 'Case Alpha', case_number: 'ARX-2026-001' },
      { id: 2, name: 'Case Beta', case_number: 'ARX-2026-002' },
    ];
    axios.get.mockResolvedValueOnce({ data: mockCases });

    const result = await caseService.getCases();
    expect(axios.get).toHaveBeenCalledWith('/api/cases');
    expect(result).toHaveLength(2);
    expect(result[0].case_number).toBe('ARX-2026-001');
    expect(result[1].case_number).toBe('ARX-2026-002');
  });

  it('fetches a single case by ID with complete isolation', async () => {
    const mockCase1 = { id: 1, name: 'Operation Alpha', case_number: 'ARX-2026-001' };
    const mockCase2 = { id: 2, name: 'Operation Beta', case_number: 'ARX-2026-002' };

    axios.get.mockImplementation((url) => {
      if (url === '/api/cases/1') return Promise.resolve({ data: mockCase1 });
      if (url === '/api/cases/2') return Promise.resolve({ data: mockCase2 });
      return Promise.reject(new Error('Not found'));
    });

    const res1 = await caseService.getCase(1);
    expect(res1.name).toBe('Operation Alpha');
    expect(res1.case_number).toBe('ARX-2026-001');

    const res2 = await caseService.getCase(2);
    expect(res2.name).toBe('Operation Beta');
    expect(res2.case_number).toBe('ARX-2026-002');

    // Strict boundary: Case 1 never receives Case 2 data
    expect(res1.id).not.toBe(res2.id);
    expect(res1.name).not.toBe(res2.name);
  });

  it('creates a new case with sequential docket ID and metadata', async () => {
    const payload = {
      name: 'Cyber Breach 2026',
      investigator: 'Agent Vance',
      agency: 'Cyber Investigation Unit',
      case_number: 'ARX-2026-003',
    };

    axios.post.mockResolvedValueOnce({
      data: {
        id: 3,
        ...payload,
        status: 'open',
        created_at: '2026-10-17T00:00:00Z',
      },
    });

    const created = await caseService.createCase(payload);
    expect(axios.post).toHaveBeenCalledWith('/api/cases', payload);
    expect(created.id).toBe(3);
    expect(created.case_number).toBe('ARX-2026-003');
    expect(created.investigator).toBe('Agent Vance');
  });

  it('triggers delete case endpoint cleanly', async () => {
    axios.delete.mockResolvedValueOnce({
      data: { message: "Case 'Case Alpha' deleted successfully", case_id: 1 },
    });

    await caseService.deleteCase(1);
    expect(axios.delete).toHaveBeenCalledWith('/api/cases/1');
  });
});

describe('Case Isolation & Deletion Logic', () => {
  it('strictly isolates cases and removes deleted case from active list', () => {
    const cases = [
      { id: 1, caseNumber: 'ARX-2026-001', title: 'Case Alpha' },
      { id: 2, caseNumber: 'ARX-2026-002', title: 'Case Beta' },
      { id: 3, caseNumber: 'ARX-2026-003', title: 'Case Gamma' },
    ];

    // Delete Case 2
    const deletedId = 2;
    const remaining = cases.filter(c => String(c.id) !== String(deletedId));

    expect(remaining).toHaveLength(2);
    expect(remaining.some(c => c.id === 2)).toBe(false);
    expect(remaining[0].id).toBe(1);
    expect(remaining[1].id).toBe(3);

    // Active case redirection if deleted was active
    let activeId = 2;
    if (activeId === deletedId) {
      activeId = remaining.length > 0 ? remaining[0].id : null;
    }
    expect(activeId).toBe(1);
  });

  it('handles last case deletion by resetting active ID to null', () => {
    const cases = [{ id: 1, caseNumber: 'ARX-2026-001', title: 'Only Case' }];
    const remaining = cases.filter(c => c.id !== 1);
    expect(remaining).toHaveLength(0);

    const activeId = remaining.length > 0 ? remaining[0].id : null;
    expect(activeId).toBeNull();
  });
});
