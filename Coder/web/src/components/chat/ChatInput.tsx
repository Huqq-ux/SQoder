import type { KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, Square } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onStop: () => void
  streaming: boolean
}

export function ChatInput({ value, onChange, onSend, onStop, streaming }: ChatInputProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="border-t border-slate-800 pt-4">
      <div className="flex gap-3 items-end">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
          disabled={streaming}
          rows={1}
          className="flex-1 bg-slate-900 border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 resize-none min-h-[44px] max-h-[120px] focus-visible:ring-blue-500/30"
        />
        {streaming ? (
          <Button
            onClick={onStop}
            variant="destructive"
            size="icon"
            className="shrink-0 rounded-xl h-11 w-11"
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            onClick={onSend}
            disabled={!value.trim()}
            size="icon"
            className="shrink-0 rounded-xl h-11 w-11 bg-blue-600 hover:bg-blue-500"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
