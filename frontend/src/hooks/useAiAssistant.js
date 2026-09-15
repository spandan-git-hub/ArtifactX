import { useState, useCallback } from 'react';
import assistantService from '../services/assistantService';

/**
 * Hook for managing forensic AI copilot queries and chat sentiment analysis.
 * @param {number|string} caseId
 */
export const useAiAssistant = (caseId) => {
  const [queryHistory, setQueryHistory] = useState([]);
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [queryError, setQueryError] = useState(null);

  const [sentimentData, setSentimentData] = useState(null);
  const [loadingSentiment, setLoadingSentiment] = useState(false);
  const [sentimentError, setSentimentError] = useState(null);

  /**
   * Submit natural language query to AI Copilot
   */
  const submitQuery = useCallback(
    async (queryText, jid = null) => {
      if (!caseId || !queryText?.trim()) return null;

      setLoadingQuery(true);
      setQueryError(null);

      const queryEntry = {
        id: `q_${Date.now()}`,
        timestamp: new Date().toISOString(),
        query: queryText.trim(),
        jid,
        response: null,
        loading: true,
        error: null,
      };

      setQueryHistory((prev) => [queryEntry, ...prev]);

      try {
        const result = await assistantService.queryAssistant(caseId, {
          query: queryText.trim(),
          jid: jid || undefined,
        });

        setQueryHistory((prev) =>
          prev.map((item) =>
            item.id === queryEntry.id
              ? { ...item, response: result, loading: false }
              : item
          )
        );
        return result;
      } catch (err) {
        const errMsg =
          err.response?.data?.detail || err.message || 'Failed to process AI copilot query';
        setQueryError(errMsg);
        setQueryHistory((prev) =>
          prev.map((item) =>
            item.id === queryEntry.id
              ? { ...item, error: errMsg, loading: false }
              : item
          )
        );
        return null;
      } finally {
        setLoadingQuery(false);
      }
    },
    [caseId]
  );

  /**
   * Fetch or refresh sentiment classification for a thread or case
   */
  const loadSentiment = useCallback(
    async (jid = null, messageIds = null) => {
      if (!caseId) return null;

      setLoadingSentiment(true);
      setSentimentError(null);

      try {
        const payload = {};
        if (jid) payload.jid = jid;
        if (messageIds && messageIds.length > 0) payload.message_ids = messageIds;

        const data = await assistantService.analyzeSentiment(caseId, payload);
        setSentimentData(data);
        return data;
      } catch (err) {
        const errMsg =
          err.response?.data?.detail ||
          err.message ||
          'Failed to execute chat sentiment analysis';
        setSentimentError(errMsg);
        return null;
      } finally {
        setLoadingSentiment(false);
      }
    },
    [caseId]
  );

  const clearHistory = useCallback(() => {
    setQueryHistory([]);
    setQueryError(null);
  }, []);

  return {
    queryHistory,
    loadingQuery,
    queryError,
    submitQuery,
    sentimentData,
    loadingSentiment,
    sentimentError,
    loadSentiment,
    clearHistory,
  };
};

export default useAiAssistant;
