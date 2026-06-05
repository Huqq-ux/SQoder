import { useState, useCallback, useRef, useEffect } from 'react'
import { X, FileText, Loader2 } from 'lucide-react'
import { useDocxPreviewStore } from '../stores/docxPreviewStore'

const MIN_WIDTH = 320
const MAX_WIDTH = 900

export function DocxPreviewPanel() {
  const { filename, loading, html, error, close } = useDocxPreviewStore()
  const [width, setWidth] = useState(420)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startW = useRef(0)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    startX.current = e.clientX
    startW.current = width
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'ew-resize'
  }, [width])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const delta = startX.current - e.clientX
      const newW = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startW.current + delta))
      setWidth(newW)
    }
    const onMouseUp = () => {
      dragging.current = false
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  if (!filename) return null

  return (
    <div
      className="fixed right-0 top-0 h-full bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-xl z-50 flex flex-col"
      style={{ width }}
    >
      {/* 拖拽把手 */}
      <div
        className="absolute left-0 top-0 w-1.5 h-full cursor-ew-resize hover:bg-blue-400/30 active:bg-blue-500/40 transition-colors z-10"
        onMouseDown={onMouseDown}
      />

      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 shrink-0">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
          <FileText className="h-4 w-4 text-blue-500 shrink-0" />
          {filename}
        </div>
        <button
          onClick={close}
          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 shrink-0"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {loading && (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            加载中...
          </div>
        )}

        {error && (
          <div className="px-3 py-2 rounded bg-red-500/5 border border-red-500/20 text-red-600 text-sm">
            {error}
          </div>
        )}

        {html && (
          <div
            className="docx-content text-sm text-slate-700 dark:text-slate-300 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
      </div>
    </div>
  )
}

/** 从文本中提取 .docx 文件名 */
export function extractDocxFilename(text: string): string | null {
  const match = text.match(/([\w\-.]+\.docx)/i)
  return match ? match[1] : null
}
