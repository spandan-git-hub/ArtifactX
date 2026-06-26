import { useState, useCallback } from 'react';
import * as telegramService from '../services/telegramService';

export const useTelegram = () => {
  const [messages, setMessages] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [groups, setGroups] = useState([]);
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeEvidence = useCallback(async (evidenceId) => {
    setLoading(true);
    setError(null);
    try {
      await telegramService.analyzeEvidence(evidenceId);
      await loadAllData(evidenceId);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to analyze Telegram evidence');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMessages = useCallback(async (evidenceId) => {
    try {
      const data = await telegramService.getMessages(evidenceId);
      setMessages(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load Telegram messages');
      setMessages([]);
    }
  }, []);

  const loadContacts = useCallback(async (evidenceId) => {
    try {
      const data = await telegramService.getContacts(evidenceId);
      setContacts(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load Telegram contacts');
      setContacts([]);
    }
  }, []);

  const loadGroups = useCallback(async (evidenceId) => {
    try {
      const data = await telegramService.getGroups(evidenceId);
      setGroups(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load Telegram groups');
      setGroups([]);
    }
  }, []);

  const loadMedia = useCallback(async (evidenceId) => {
    try {
      const data = await telegramService.getMedia(evidenceId);
      setMedia(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load Telegram media');
      setMedia([]);
    }
  }, []);

  const loadAllData = useCallback(async (evidenceId) => {
    await Promise.all([
      loadMessages(evidenceId),
      loadContacts(evidenceId),
      loadGroups(evidenceId),
      loadMedia(evidenceId)
    ]);
  }, []);

  return {
    messages,
    contacts,
    groups,
    media,
    loading,
    error,
    analyzeEvidence,
    loadMessages,
    loadContacts,
    loadGroups,
    loadMedia,
    loadAllData
  };
};