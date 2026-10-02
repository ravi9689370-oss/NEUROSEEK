'use client'

import { useState, useRef, useEffect } from 'react'
import { Brain, Zap, ChevronDown, Check, X, Settings, Sparkles, Cpu, Database, Search } from 'lucide-react'
import { clsx } from 'clsx'

interface ModelSelectorProps {
  onOpenChange: (open: boolean) => void
  isOpen: boolean
}

const models = [
  { id: 'auto', name: 'Auto (Smart Routing)', description: 'Automatically selects best model', icon: Brain, badge: 'Recommended' },
  { id: 'ensemble', name: 'Ensemble', description: 'Multiple models + synthesis', icon: Sparkles, badge: 'Best Quality' },
  { id: 'llama3.1:8b', name: 'Llama 3.1 8B', description: 'General purpose, fast', icon: Cpu },
  { id: 'qwen2.5-coder:7b', name: 'Qwen 2.5 Coder 7B', description: 'Code generation expert', icon: Database },
  { id: 'nemotron3-ultra', name: 'Nemotron 3 Ultra', description: 'Complex reasoning', icon: Sparkles },
  { id: 'deepseek-r1:7b', name: 'DeepSeek R1 7B', description: 'Step-by-step reasoning', icon: Cpu },
  { id: 'phi3.5:3.8b', name: 'Phi 3.5 3.8B', description: 'Ultra fast, simple tasks', icon: Zap },
]

export function ModelSelector({ onOpenChange, isOpen }: ModelSelectorProps) {
  const [selectedModel, setSelectedModel] = useState('auto')
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          buttonRef.current && !buttonRef.current.contains(e.target as Node)) {
        onOpenChange(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onOpenChange])

  const filteredModels = models.filter(m =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleSelect = (modelId: string) => {
    setSelectedModel(modelId)
    onOpenChange(false)
  }

  const selected = models.find(m => m.id === selectedModel) || models[0]

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        ref={buttonRef}
        onClick={() => onOpenChange(!isOpen)}
        className={clsx(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors',
          isOpen ? 'bg-accent border-primary' : 'border-border hover:bg-accent'
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <selected.icon className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium truncate max-w-[150px]">{selected.name}</span>
        <ChevronDown className={clsx('h-4 w-4 text-muted-foreground transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-72 bg-popover border border-border rounded-xl shadow-lg overflow-hidden z-50 animate-slide-down">
          {/* Search */}
          <div className="p-2 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search models..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-muted border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                autoFocus
              />
            </div>
          </div>

          {/* Model list */}
          <div className="max-h-80 overflow-y-auto scrollbar-thin p-1">
            {filteredModels.map((model) => (
              <button
                key={model.id}
                onClick={() => handleSelect(model.id)}
                className={clsx(
                  'w-full flex items-center gap-3 p-2.5 rounded-lg transition-colors text-left',
                  selectedModel === model.id
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-accent text-foreground'
                )}
              >
                <model.icon className={clsx('h-5 w-5 flex-shrink-0', selectedModel === model.id ? 'text-primary' : 'text-muted-foreground')} />
                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{model.name}</span>
                    {model.badge && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-primary/10 text-primary rounded-full">
                        {model.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{model.description}</p>
                </div>
                {selectedModel === model.id && <Check className="h-4 w-4 text-primary flex-shrink-0" />}
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="border-t p-2 flex items-center gap-2">
            <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors">
              <Settings className="h-4 w-4" />
              Model Settings
            </button>
            <button
              onClick={() => { setSelectedModel('auto'); onOpenChange(false) }}
              className="p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground"
              title="Reset to auto"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}