import { create } from 'zustand';
import { api } from '../lib/api';
import { CopilotMessage, CopilotChatResponse } from '../types';

interface CopilotState {
  messages: CopilotMessage[];
  isLoading: boolean;
  error: string | null;

  sendMessage: (projectId: string, message: string) => Promise<void>;
  clearChat: () => void;
}

let _messageCounter = 0;

function createMessageId(): string {
  _messageCounter += 1;
  return `msg-${Date.now()}-${_messageCounter}`;
}

export const useCopilotStore = create<CopilotState>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,

  sendMessage: async (projectId: string, message: string) => {
    const userMessage: CopilotMessage = {
      id: createMessageId(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      const response = await api.post<CopilotChatResponse>(
        `/api/v1/projects/${projectId}/chat`,
        { message },
      );

      const assistantMessage: CopilotMessage = {
        id: createMessageId(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get copilot response';
      set({ isLoading: false, error: errorMessage });
    }
  },

  clearChat: () => {
    set({ messages: [], error: null });
  },
}));
