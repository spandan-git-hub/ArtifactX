import { describe, it, expect, vi } from 'vitest';
import axios from 'axios';
import { recoveryService } from './recoveryService';
vi.mock('axios', () => ({ default: { get: vi.fn() } }));
describe('complete recovery loading', () => {
  it('loads findings beyond the first API page', async () => {
    axios.get.mockResolvedValueOnce({ data: Array.from({ length: 1000 }, (_, id) => ({ id })) })
      .mockResolvedValueOnce({ data: [{ id: 1000 }] });
    const findings = await recoveryService.getRecoveryFindings(42);
    expect(findings).toHaveLength(1001);
    expect(axios.get.mock.calls[1][1].params.offset).toBe(1000);
  });
  it('surfaces a later page failure instead of returning partial counts', async () => {
    axios.get.mockResolvedValueOnce({ data: Array(1000).fill({}) }).mockRejectedValueOnce(new Error('offline'));
    await expect(recoveryService.getRecoveryFindings(42)).rejects.toThrow('offline');
  });
});
