'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Mic, Paperclip, Settings, Menu, X, Plus, Search, Sparkles, Brain, Zap, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import { ChatArea } from '@/components/chat/ChatArea'
import { Sidebar } from '@/components/chat/Sidebar'
import { ModelSelector } from '@/components/chat/ModelSelector'
import { InputArea } from '@/components/chat/InputArea'
import { useChatStore } from '@/stores/chatStore'
import { useAuthStore } from '@/stores/authStore'

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [modelSelectorOpen, setModelSelectorOpen] = useState(false)
  const { conversations, currentConversationId, createConversation, setCurrentConversation } = useChatStore()
  const { user, isAuthenticated } = useAuthStore()

  const handleNewChat = useCallback(() => {
    const newConv = createConversation()
    setCurrentConversation(newConv.id)
    setSidebarOpen(false)
  }, [createConversation, setCurrentConversation])

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={setCurrentConversation}
        onNewChat={handleNewChat}
      />

      {/* Main chat area */}
      <div className="flex flex-1 flex-col min-w-0 lg:min-w-[calc(100%-280px)]">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b bg-card/50 px-4 py-3 shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-accent transition-colors"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              <span className="font-semibold text-lg">NeuroSeek</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ModelSelector onOpenChange={setModelSelectorOpen} isOpen={modelSelectorOpen} />
            
            {isAuthenticated && (
              <div className="flex items-center gap-2">
                <button className="p-2 rounded-lg hover:bg-accent transition-colors" aria-label="Settings">
                  <Settings className="h-5 w-5" />
                </button>
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <span className="text-xs font-medium text-primary">
                    {user?.email?.[0]?.toUpperCase() || 'U'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Chat area */}
        <ChatArea conversationId={currentConversationId} />

        {/* Input area */}
        <InputArea conversationId={currentConversationId} />
      </div>
    </div>
  )
}