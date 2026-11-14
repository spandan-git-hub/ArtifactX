import axios from 'axios';
import { authService } from './authService';

const API_BASE = '/api';

export interface StageEventData {
  stage: string;
  status: string;
  timestamp: string;
  duration_ms?: number;
  counts?: Record<string, any>;
  output_hash?: string;
  errors?: string[];
  run_id?: string;
}

export const pipelineService = {
  runPipeline: async (caseId: string | number, payload?: any) => {
    const response = await axios.post(`${API_BASE}/cases/${caseId}/pipeline/run`, payload || {});
    return response.data;
  },

  getRuns: async (caseId: string | number) => {
    const response = await axios.get(`${API_BASE}/cases/${caseId}/pipeline/runs`);
    return response.data;
  },

  getRunDetails: async (runId: string) => {
    const response = await axios.get(`${API_BASE}/pipeline/runs/${runId}`);
    return response.data;
  },

  streamPipeline: async (
    caseId: string | number,
    onEvent: (event: StageEventData) => void,
    onError?: (err: any) => void,
    onComplete?: () => void
  ) => {
    const token = authService.getToken();
    const headers: Record<string, string> = {
      Accept: 'text/event-stream',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${API_BASE}/cases/${caseId}/pipeline/stream`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`Pipeline stream failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported on response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data:')) {
            const jsonStr = trimmed.slice(5).trim();
            if (jsonStr) {
              try {
                const parsed: StageEventData = JSON.parse(jsonStr);
                onEvent(parsed);
              } catch (parseErr) {
                console.warn('Failed to parse SSE payload:', jsonStr, parseErr);
              }
            }
          }
        }
      }

      onComplete?.();
    } catch (err) {
      console.error('Error in pipeline stream:', err);
      onError?.(err);
    }
  },
};

export default pipelineService;

