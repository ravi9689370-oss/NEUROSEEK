'use client'

import { useEffect, useRef, useCallback } from 'react'
import { Loader2, Bot, Sparkles } from 'lucide-react'
import { Message } from './Message'
import { useChatStore } from '@/stores/chatStore'
import { clsx } from 'clsx'

interface ChatAreaProps {
  conversationId: string | null
}

export function ChatArea({ conversationId }: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { getMessages, setMessages } = useChatStore()
  
  const messages = conversationId ? getMessages(conversationId) : []

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleFeedback = useCallback((messageId: string, feedback: 'positive' | 'negative' | 'edited' | 'regenerated', editedContent?: string) => {
    // API call would go here
    console.log('Feedback:', messageId, feedback, editedContent)
  }, [])

  const handleRegenerate = useCallback((messageId: string) => {
    // API call would go here
    console.log('Regenerate:', messageId)
  }, [])

  if (!conversationId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-6">
          <Sparkles className="h-10 w-10 text-primary" />
        </div>
        <h1 className="text-3xl font-bold mb-2">Welcome to NeuroSeek AI</h1>
        <p className="text-muted-foreground max-w-md mb-8">
          Start a new conversation to chat with multiple AI models that continuously improve through your feedback.
        </p>
        <div className="flex flex-wrap gap-4 justify-center text-sm text-muted-foreground">
          <span className="flex items-center gap-2 px-3 py-1 bg-muted rounded-full">
            <Bot className="h-4 w-4" />
            Multi-model inference
          </span>
          <span className="flex items-center gap-2 px-3 py-1 bg-muted rounded-full">
            <Sparkles className="h-4 w-4" />
            Continuous learning
          </span>
          <span className="flex items-center gap-2 px-3 py-1 bg-muted rounded-full">
            <Loader2 className="h-4 w-4" />
            LoRA fine-tuning
          </span>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-6"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center text-muted-foreground">
          <p className="text-lg">No messages yet</p>
          <p className="text-sm mt-1">Start the conversation below</p>
        </div>
      ) : (
        messages.map((msg) => (
          <Message
            key={msg.id}
            message={msg}
            conversationId={conversationId}
            onFeedback={handleFeedback}
            onRegenerate={handleRegenerate}
          />
        ))
      )}
      
      <div ref={messagesEndRef} />
    </div>
  )
}