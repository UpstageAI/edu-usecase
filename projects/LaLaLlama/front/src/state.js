import { useState } from 'react';

export function useGlobalState() {
  const [state, setState] = useState({
    currentBatchId: null,
    proposals: [],
    localUploads: {
      rfp: null,
      rubric: null,
      proposals: []
    },
    reports: {},
    chats: {},
    ui: {
      chatOpenFor: null
    }
  });

  const updateState = (updates) => {
    setState(prev => ({
      ...prev,
      ...updates
    }));
  };

  const updateLocalUploads = (uploads) => {
    setState(prev => ({
      ...prev,
      localUploads: {
        ...prev.localUploads,
        ...uploads
      }
    }));
  };

  const setReport = (proposalId, report) => {
    setState(prev => ({
      ...prev,
      reports: {
        ...prev.reports,
        [proposalId]: report
      }
    }));
  };

  const setProposals = (proposalsOrUpdater) => {
    setState(prev => {
      const nextProposals = typeof proposalsOrUpdater === 'function'
        ? proposalsOrUpdater(prev.proposals)
        : proposalsOrUpdater;
      return {
        ...prev,
        proposals: nextProposals
      };
    });
  };

  const addChatMessage = (proposalId, message) => {
    setState(prev => ({
      ...prev,
      chats: {
        ...prev.chats,
        [proposalId]: [...(prev.chats[proposalId] || []), message]
      }
    }));
  };

  const openChat = (proposalId) => {
    setState(prev => ({
      ...prev,
      ui: {
        ...prev.ui,
        chatOpenFor: proposalId
      }
    }));
  };

  const closeChat = () => {
    setState(prev => ({
      ...prev,
      ui: {
        ...prev.ui,
        chatOpenFor: null
      }
    }));
  };

  return {
    state,
    updateState,
    updateLocalUploads,
    setReport,
    setProposals,
    addChatMessage,
    openChat,
    closeChat
  };
}

