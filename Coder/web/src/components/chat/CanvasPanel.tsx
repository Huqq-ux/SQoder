import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/stores/chatStore'

export function CanvasPanel() {
  const canvasOpen = useChatStore((s) => s.canvasOpen)
  const canvasContent = useChatStore((s) => s.canvasContent)
  const setCanvasOpen = useChatStore((s) => s.setCanvasOpen)

  return (
    <div
      className={`${
        canvasOpen ? 'w-96' : 'w-0'
      } border-l border-slate-800 bg-slate-950 shrink-0 overflow-hidden transition-all duration-200`}
    >
      <div className="w-96 p-4 h-full overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-300">画布</h3>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-500 hover:text-slate-300"
            onClick={() => setCanvasOpen(false)}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>

        {canvasContent ? (
          <div className="space-y-4">
            {canvasContent.type === 'code' && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-800">
                  <span className="text-xs text-slate-400">
                    {(canvasContent.data as any)?.filename || 'code'}
                  </span>
                </div>
                <pre className="p-3 text-[11px] leading-relaxed overflow-x-auto text-slate-400">
                  <code>{(canvasContent.data as any)?.content || ''}</code>
                </pre>
              </div>
            )}
            {canvasContent.type === 'tool' && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-medium text-slate-400 mb-2">
                  工具调用详情
                </h4>
                <div className="text-[11px] text-slate-500 space-y-1">
                  {Object.entries(canvasContent.data || {}).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span>{k}</span>
                      <span className="text-slate-400">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-slate-600 text-center mt-12">暂无内容</p>
        )}
      </div>
    </div>
  )
}
