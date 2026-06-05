import { create } from 'zustand'
import mammoth from 'mammoth'

interface DocxPreviewState {
  filename: string | null
  loading: boolean
  html: string
  error: string
  open: (filename: string) => Promise<void>
  close: () => void
}

export const useDocxPreviewStore = create<DocxPreviewState>((set) => ({
  filename: null,
  loading: false,
  html: '',
  error: '',

  open: async (filename: string) => {
    set({ filename, loading: true, error: '', html: '' })
    try {
      // 获取原始 docx 字节
      const res = await fetch(`/api/knowledge/docx-raw?path=${encodeURIComponent(filename)}`)
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: '加载失败' }))
        throw new Error(detail.detail || '加载失败')
      }
      const arrayBuffer = await res.arrayBuffer()

      // mammoth 转换 docx → HTML
      const result = await mammoth.convertToHtml({ arrayBuffer })
      set({ html: result.value, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  close: () => set({ filename: null, html: '', error: '' }),
}))

/** 从文本中提取 .docx 文件名 */
export function extractDocxFilename(text: string): string | null {
  const match = text.match(/([\w\-.]+\.docx)/i)
  return match ? match[1] : null
}
