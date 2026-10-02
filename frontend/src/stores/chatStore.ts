import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { v4 as uuidv4 } from 'uuid'

export interface Conversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
  model?: string
  isPinned?: boolean
}

export interface Message {
  id: string
  conversationId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  model?: string
  timestamp: string
  tokens?: number
  generationTimeMs?: number
  feedback?: 'positive' | 'negative' | 'edited' | 'regenerated'
  isStreaming?: boolean
}

interface ChatState {
  conversations: Conversation[]
  messages: Record<string, Message[]>
  currentConversationId: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  createConversation: (title?: string) => Conversation
  setCurrentConversation: (id: string) => void
  deleteConversation: (id: string) => void
  updateConversationTitle: (id: string, title: string) => void
  togglePinConversation: (id: string) => void
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => Message
  updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => void
  deleteMessage: (conversationId: string, messageId: string) => void
  setMessages: (conversationId: string, messages: Message[]) => void
  getMessages: (conversationId: string) => Message[]
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      messages: {},
      currentConversationId: null,
      isLoading: false,
      error: null,

      createConversation: (title = 'New Chat') => {
        const newConv: Conversation = {
          id: uuidv4(),
          title,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          messageCount: 0,
        }
        set((state) => ({
          conversations: [newConv, ...state.conversations],
          currentConversationId: newConv.id,
          messages: { ...state.messages, [newConv.id]: [] },
        }))
        return newConv
      },

      setCurrentConversation: (id: string) => {
        set({ currentConversationId: id })
      },

      deleteConversation: (id: string) => {
        set((state) => {
          const { [id]: _, ...remainingMessages } = state.messages
          return {
            conversations: state.conversations.filter((c) => c.id !== id),
            messages: remainingMessages,
            currentConversationId: state.currentConversationId === id ? null : state.currentConversationId,
          }
        })
      },

      updateConversationTitle: (id: string, title: string) => {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, title, updatedAt: new Date().toISOString() } : c
          ),
        }))
      },

      togglePinConversation: (id: string) => {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, isPinned: !c.isPinned, updatedAt: new Date().toISOString() } : c
          ),
        }))
      },

      addMessage: (conversationId: string, message) => {
        const newMessage: Message = {
          ...message,
          id: uuidv4(),
          timestamp: new Date().toISOString(),
        }
        set((state) => ({
          messages: {
            ...state.messages,
            [conversationId]: [...(state.messages[conversationId] || []), newMessage],
          },
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, messageCount: c.messageCount + 1, updatedAt: new Date().toISOString() }
              : c
          ),
        }))
        return newMessage
      },

      updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => {
        set((state) => ({
          messages: {
            ...state.messages,
            [conversationId]: (state.messages[conversationId] || []).map((m) =>
              m.id === messageId ? { ...m, ...updates } : m
            ),
          },
        }))
      },

      deleteMessage: (conversationId: string, messageId: string) => {
        set((state) => ({
          messages: {
            ...state.messages,
            [conversationId]: (state.messages[conversationId] || []).filter((m) => m.id !== messageId),
          },
        }))
      },

      setMessages: (conversationId: string, messages: Message[]) => {
        set((state) => ({
          messages: { ...state.messages, [conversationId]: messages },
        }))
      },

      getMessages: (conversationId: string) => {
        return get().messages[conversationId] || []
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      setError: (error: string | null) => {
        set({ error })
      },
    }),
    {
      name: 'neuroseek-chat',
      partialize: (state) => ({
        conversations: state.conversations,
        messages: state.messages,
        currentConversationId: state.currentConversationId,
      }),
    }
  )
)