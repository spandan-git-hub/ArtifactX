import { useState, useCallback } from 'react';
import * as whatsappService from '../services/whatsappService';

export const useWhatsApp = () => {
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
      await whatsappService.analyzeEvidence(evidenceId);
      // After analysis, load the data
      await loadAllData(evidenceId);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to analyze WhatsApp evidence');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMessages = useCallback(async (evidenceId) => {
    try {
      const data = await whatsappService.getMessages(evidenceId);
      setMessages(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load WhatsApp messages');
      setMessages([]);
    }
  }, []);

  const loadContacts = useCallback(async (evidenceId) => {
    try {
      const data = await whatsappService.getContacts(evidenceId);
      setContacts(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load WhatsApp contacts');
      setContacts([]);
    }
  }, []);

  const loadGroups = useCallback(async (evidenceId) => {
    try {
      const data = await whatsappService.getGroups(evidenceId);
      setGroups(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load WhatsApp groups');
      setGroups([]);
    }
  }, []);

  const loadMedia = useCallback(async (evidenceId) => {
    try {
      const data = await whatsappService.getMedia(evidenceId);
      setMedia(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load WhatsApp media');
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