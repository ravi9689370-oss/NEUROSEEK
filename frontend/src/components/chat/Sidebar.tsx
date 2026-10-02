'use client'

import { useState } from 'react'
import { X, Plus, MessageSquare, ChevronRight, Pin, Archive, MoreVertical, Search, Settings, Trash2, Edit2, Copy, Branching } from 'lucide-react'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import { Conversation } from '@/stores/chatStore'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  conversations: Conversation[]
  currentConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
}

export function Sidebar({ isOpen, onClose, conversations, currentConversationId, onSelectConversation, onNewChat }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const pinned = filteredConversations.filter((c) => c.isPinned)
  const others = filteredConversations.filter((c) => !c.isPinned)

  return (
    <>
      <aside
        className={clsx(
          'fixed lg:relative z-50 w-80 h-full bg-card border-r flex flex-col transition-transform duration-200 ease-in-out',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Conversations sidebar"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            <span className="font-semibold">Chats</span>
            {conversations.length > 0 && (
              <span className="px-2 py-0.5 text-xs bg-muted rounded-full">{conversations.length}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded hover:bg-accent transition-colors"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* New chat button */}
        <button
          onClick={onNewChat}
          className="m-3 p-3 w-full flex items-center gap-3 rounded-lg hover:bg-accent transition-colors text-left border border-border"
        >
          <Plus className="h-5 w-5 text-primary" />
          <span className="font-medium">New Chat</span>
        </button>

        {/* Search */}
        <div className="px-3 pb-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-muted border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto scrollbar-thin px-2">
          {pinned.length > 0 && (
            <div className="mb-4">
              <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                Pinned
              </h3>
              {pinned.map((conv) => (
                <ConversationItem
                  key={conv.id}
                  conversation={conv}
                  isActive={conv.id === currentConversationId}
                  onSelect={() => onSelectConversation(conv.id)}
                  onClose={onClose}
                  hovered={hoveredId === conv.id}
                  onHover={() => setHoveredId(conv.id)}
                  onLeave={() => setHoveredId(null)}
                />
              ))}
            </div>
          )}

          {others.length > 0 ? (
            others.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentConversationId}
                onSelect={() => onSelectConversation(conv.id)}
                onClose={onClose}
                hovered={hoveredId === conv.id}
                onHover={() => setHoveredId(conv.id)}
                onLeave={() => setHoveredId(null)}
              />
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground/50">
              <MessageSquare className="h-12 w-12 mb-3" />
              <p className="text-sm">No conversations yet</p>
              <p className="text-xs mt-1">Start a new chat to begin</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t shrink-0">
          <button className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors text-sm">
            <Settings className="h-4 w-4" />
            Settings
          </button>
        </div>
      </aside>
    </>
  )
}

function ConversationItem({ conversation, isActive, onSelect, onClose, hovered, onHover, onLeave }: {
  conversation: Conversation
  isActive: boolean
  onSelect: () => void
  onClose: () => void
  hovered: boolean
  onHover: () => void
  onLeave: () => void
}) {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <div
      className="relative"
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      <button
        onClick={onSelect}
        className={clsx(
          'w-full flex items-center gap-3 p-2.5 rounded-lg transition-colors text-left',
          isActive
            ? 'bg-primary/10 text-primary'
            : 'hover:bg-accent text-foreground'
        )}
      >
        <div className="flex-1 min-w-0 text-left">
          <p className={clsx('font-medium truncate', isActive ? 'font-semibold' : '')}>
            {conversation.title || 'Untitled'}
          </p>
          <p className="text-xs text-muted-foreground truncate">
            {formatDistanceToNow(new Date(conversation.updatedAt), { addSuffix: true })}
            {conversation.model && ` • ${conversation.model}`}
          </p>
        </div>
        {conversation.isPinned && <Pin className="h-4 w-4 text-muted-foreground flex-shrink-0" />}
      </button>

      {hovered && !showMenu && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 animate-fade-in">
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu(true) }}
            className="p-1.5 rounded hover:bg-accent transition-colors"
            aria-label="More options"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
        </div>
      )}

      {showMenu && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 z-20 bg-popover border border-border rounded-lg shadow-lg py-1 min-w-[160px] animate-slide-up">
            <button
              onClick={(e) => { e.stopPropagation(); conversation.isPinned ? undefined : undefined; setShowMenu(false) }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
            >
              <Pin className="h-4 w-4" />
              {conversation.isPinned ? 'Unpin' : 'Pin'}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setShowMenu(false) }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
            >
              <Branching className="h-4 w-4" />
              Branch from here
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setShowMenu(false) }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
            >
              <Copy className="h-4 w-4" />
              Duplicate
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setShowMenu(false) }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors text-destructive"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  )
}