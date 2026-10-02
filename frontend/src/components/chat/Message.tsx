'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageCircle, Send, Loader2, Copy, ThumbsUp, ThumbsDown, Edit, RotateCcw, Flag, MoreHorizontal, Check, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { clsx } from 'clsx'
import { useChatStore } from '@/stores/chatStore'
import { useAuthStore } from '@/stores/authStore'
import { formatDistanceToNow } from 'date-fns'

const codeBlocks: Record<string, React.ReactNode> = {}

interface CodeNode {
  children?: Array<{ value?: string }>
}

interface MessageProps {
  message: {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    model?: string
    timestamp: string
    tokens?: number
    generationTimeMs?: number
    feedback?: 'positive' | 'negative' | 'edited' | 'regenerated'
    isStreaming?: boolean
  }
  conversationId: string
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative' | 'edited' | 'regenerated', editedContent?: string) => void
  onRegenerate?: (messageId: string) => void
}

export function Message({ message, conversationId, onFeedback, onRegenerate }: MessageProps) {
  const [showActions, setShowActions] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.content)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { updateMessage } = useChatStore()

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [isEditing])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
  }

  const handleEdit = () => {
    setIsEditing(true)
    setEditContent(message.content)
  }

  const handleSaveEdit = () => {
    updateMessage(conversationId, message.id, { content: editContent })
    onFeedback?.(message.id, 'edited', editContent)
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditContent(message.content)
    setIsEditing(false)
  }

  const renderMarkdown = () => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code: ({ node, children, className, ...props }) => {
          const language = (className || '').replace(/language-/, '') || 'text'
          const codeNode = node as CodeNode | undefined
          const code = codeNode?.children?.[0]?.value ? String(codeNode.children[0].value) : ''
          
          return (
            <SyntaxHighlighter
              language={language}
              style={oneDark}
              customStyle={{ margin: '0.5rem 0', borderRadius: '0.5rem' }}
              showLineNumbers={code.split('\n').length > 5}
              lineNumberStyle={{ color: '#6272a4' }}
            >
              {code}
            </SyntaxHighlighter>
          )
        },
        pre: ({ children, ...props }) => (
          <div className="relative group my-4 rounded-lg bg-muted p-1">
            {children}
          </div>
        ),
      }}
    >
      {message.content}
    </ReactMarkdown>
  )

  if (message.role === 'system') {
    return (
      <div className="flex justify-center my-4">
        <span className="px-3 py-1 text-xs text-muted-foreground bg-muted rounded-full">
          {message.content}
        </span>
      </div>
    )
  }

  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  return (
    <div
      className={clsx(
        'flex gap-3 max-w-3xl mx-auto w-full px-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
          <MessageCircle className="h-4 w-4 text-primary" />
        </div>
      )}

      <div
        className={clsx(
          'flex flex-col gap-2 max-w-full',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        <div
          className={clsx(
            'relative rounded-2xl px-4 py-2.5 max-w-full break-words',
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-md'
              : 'bg-muted text-muted-foreground rounded-bl-md'
          )}
        >
          {isEditing ? (
            <div className="flex flex-col gap-2 w-full min-w-[200px]">
              <textarea
                ref={textareaRef}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSaveEdit()
                  } else if (e.key === 'Escape') {
                    handleCancelEdit()
                  }
                }}
                className="min-h-[60px] max-h-[300px] p-2 bg-background border border-border rounded resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Edit message..."
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={handleSaveEdit}
                  className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
                >
                  Save
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="px-3 py-1 text-sm bg-muted text-muted-foreground rounded hover:bg-muted/80"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            renderMarkdown()
          )}
        </div>

        <div
          className={clsx(
            'flex items-center gap-2 text-xs text-muted-foreground opacity-0 transition-opacity',
            showActions || message.isStreaming ? 'opacity-100' : '',
            isUser ? 'justify-end' : 'justify-start'
          )}
        >
          {isAssistant && (
            <>
              <span className="flex items-center gap-1">
                {message.model && <span className="px-2 py-0.5 bg-muted rounded text-[10px]">{message.model}</span>}
                {message.tokens && <span>• {message.tokens} tokens</span>}
                {message.generationTimeMs && <span>• {message.generationTimeMs}ms</span>}
              </span>
              <div className="flex items-center gap-1 ml-auto">
                <button
                  onClick={() => handleCopy()}
                  className="p-1.5 rounded hover:bg-accent transition-colors"
                  title="Copy"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onFeedback?.(message.id, 'positive')}
                  className={clsx(
                    'p-1.5 rounded hover:bg-accent transition-colors',
                    message.feedback === 'positive' && 'text-green-500'
                  )}
                  title="Good response"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onFeedback?.(message.id, 'negative')}
                  className={clsx(
                    'p-1.5 rounded hover:bg-accent transition-colors',
                    message.feedback === 'negative' && 'text-red-500'
                  )}
                  title="Bad response"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={handleEdit}
                  className="p-1.5 rounded hover:bg-accent transition-colors"
                  title="Edit"
                >
                  <Edit className="h-3.5 w-3.5" />
                </button>
                {onRegenerate && (
                  <button
                    onClick={() => onRegenerate(message.id)}
                    className="p-1.5 rounded hover:bg-accent transition-colors"
                    title="Regenerate"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </>
          )}
          
          {isUser && (
            <div className="flex items-center gap-1 mr-auto">
              <button
                onClick={handleEdit}
                className="p-1.5 rounded hover:bg-accent transition-colors"
                title="Edit"
              >
                <Edit className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>

        <div className="text-xs text-muted-foreground/60">
          {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
          <span className="text-xs font-medium text-muted-foreground">You</span>
        </div>
      )}
    </div>
  )
}