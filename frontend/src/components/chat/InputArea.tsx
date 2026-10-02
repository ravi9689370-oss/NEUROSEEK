'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Mic, Paperclip, Smile, MoreHorizontal, X, Loader2, Zap, Brain } from 'lucide-react'
import { useChatStore } from '@/stores/chatStore'
import { clsx } from 'clsx'

interface InputAreaProps {
  conversationId: string | null
}

export function InputArea({ conversationId }: InputAreaProps) {
  const [text, setText] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [showAttachments, setShowAttachments] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { addMessage, currentConversationId } = useChatStore()
  const isLoading = conversationId ? useChatStore((s) => s.isLoading) : false

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim() || isLoading || !conversationId) return

    const userMessage = text.trim()
    setText('')
    textareaRef.current?.style.setProperty('height', 'auto')

    // Add user message immediately
    addMessage(conversationId, {
      conversationId,
      role: 'user',
      content: userMessage,
    })

    // Simulate streaming response (replace with actual API call)
    await simulateResponse(conversationId, userMessage)
  }, [text, isLoading, conversationId, addMessage])

  const simulateResponse = async (convId: string, userMsg: string) => {
    // This would be replaced with actual API call to backend
    const assistantMsgId = `msg-${Date.now()}`
    
    // Add placeholder assistant message
    const placeholderMsg = {
      id: assistantMsgId,
      conversationId: convId,
      role: 'assistant' as const,
      content: '',
      model: 'llama3.1:8b',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    
    // In real app, this would come from the streaming API
    // For now, simulate
    const responses = [
      "I understand your question. Let me provide a comprehensive answer.",
      "Based on the context you've provided, here's my analysis...",
      "There are several approaches we could take to solve this.",
      "Let me break this down step by step for clarity.",
    ]
    
    const fullResponse = responses[Math.floor(Math.random() * responses.length)]
    
    // In a real implementation, you'd stream from the API
    // This is just a placeholder
    console.log('Would stream response for:', userMsg)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const adjustHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const height = Math.min(textareaRef.current.scrollHeight, 200)
      textareaRef.current.style.height = `${height}px`
    }
  }

  useEffect(() => {
    adjustHeight()
  }, [text])

  if (!conversationId) return null

  return (
    <form onSubmit={handleSubmit} className="shrink-0 border-t bg-card/50 backdrop-blur-sm">
      <div className="mx-auto max-w-3xl px-4 py-3">
        <div className="relative">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={text}
                onChange={(e) => {
                  setText(e.target.value)
                  adjustHeight()
                }}
                onKeyDown={handleKeyDown}
                onCompositionStart={() => setIsComposing(true)}
                onCompositionEnd={() => setIsComposing(false)}
                placeholder="Message NeuroSeek... (Shift+Enter for new line)"
                disabled={isLoading}
                className={clsx(
                  'w-full min-h-[44px] max-h-[200px] px-4 py-3 pr-14',
                  'bg-background border border-border rounded-xl',
                  'text-base resize-none outline-none',
                  'focus:ring-2 focus:ring-primary focus:border-transparent',
                  'placeholder:text-muted-foreground/50',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
                style={{ height: 'auto' }}
                rows={1}
              />
              
              {/* Action buttons inside textarea */}
              <div className="absolute bottom-2 right-2 flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setShowAttachments(!showAttachments)}
                  className="p-2 rounded-lg hover:bg-accent transition-colors"
                  aria-label="Attach files"
                >
                  <Paperclip className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  className="p-2 rounded-lg hover:bg-accent transition-colors"
                  aria-label="Add emoji"
                >
                  <Smile className="h-5 w-5" />
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={!text.trim() || isLoading}
              className={clsx(
                'flex-shrink-0 p-2.5 rounded-xl transition-all',
                'flex items-center justify-center',
                text.trim() && !isLoading
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              )}
              aria-label={isLoading ? 'Generating...' : 'Send message'}
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>

          {/* Model indicator */}
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <Brain className="h-3.5 w-3.5" />
            <span>NeuroSeek will route to the best model</span>
            <Zap className="h-3.5 w-3.5 text-yellow-500" />
            <span className="px-2 py-0.5 bg-primary/10 text-primary rounded">Auto-routing</span>
          </div>
        </div>
      </div>
    </form>
  )
}