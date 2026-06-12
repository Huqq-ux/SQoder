import { useState, useCallback, useEffect, useRef } from 'react'
import { api } from '../api/client'
import { notify } from '../lib/toast'
import { Upload, FileText, FileSpreadsheet, FileImage, File, Trash2 } from 'lucide-react'

interface DocFile {
  id: string
  filename: string
  size: number
  chunks: number
  course_slug?: string
  course_name?: string
  status: 'indexed' | 'indexing'
}

interface CourseOption {
  id: string
  slug: string
  name: string
}

export function KnowledgePage() {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [docFiles, setDocFiles] = useState<DocFile[]>([])
  const [courses, setCourses] = useState<CourseOption[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState('')
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    api.get<{ courses: CourseOption[] }>('/courses/')
      .then((d) => { if (mountedRef.current) setCourses(d.courses) })
      .catch(() => { if (mountedRef.current) setCourses([]) })
  }, [])

  const fetchDocuments = useCallback(() => {
    const query = selectedCourseId ? `?course_id=${encodeURIComponent(selectedCourseId)}` : ''
    api.get<{ documents: DocFile[] }>(`/knowledge/documents${query}`)
      .then((d) => { if (mountedRef.current) setDocFiles(d.documents) })
      .catch(() => { if (mountedRef.current) setDocFiles([]) })
  }, [selectedCourseId])

  useEffect(() => { fetchDocuments() }, [fetchDocuments])

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return
    setUploading(true)
    try {
      const query = selectedCourseId ? `?course_id=${encodeURIComponent(selectedCourseId)}` : ''
      const data = await api.uploadFiles<{ results: { filename: string; chunks: number; status: string }[] }>(
        `/knowledge/upload${query}`, files,
      )
      // Toast is global, always show regardless of mounted state
      for (const r of data.results) {
        if (r.status === 'imported') {
          notify.success(`${r.filename}: ${r.chunks} 个文档块已导入`)
        } else {
          notify.error(`${r.filename}: ${r.status}`)
        }
      }
      if (!mountedRef.current) return
      setFiles([])
      fetchDocuments()
    } catch (e: any) {
      notify.error(`上传失败: ${e?.message || '未知错误'}`)
      if (mountedRef.current) setUploading(false)
    } finally {
      if (mountedRef.current) setUploading(false)
    }
  }, [files, selectedCourseId, fetchDocuments])

  const handleDelete = useCallback(async (fileId: string, filename: string) => {
    if (!confirm(`确定要删除「${filename}」吗？此操作不可撤销。`)) return
    try {
      await api.del(`/knowledge/documents/${fileId}`)
      if (!mountedRef.current) return
      notify.success(`已删除「${filename}」`)
      fetchDocuments()
    } catch (e: any) {
      if (mountedRef.current) notify.error(`删除失败: ${e?.message || '未知错误'}`)
    }
  }, [fetchDocuments])

  const fileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    if (ext === 'pdf') return <FileText className="h-4 w-4" style={{ color: '#ef4444' }} />
    if (ext === 'pptx') return <FileImage className="h-4 w-4" style={{ color: '#f59e0b' }} />
    if (ext === 'xlsx' || ext === 'csv') return <FileSpreadsheet className="h-4 w-4" style={{ color: '#22c55e' }} />
    return <File className="h-4 w-4" style={{ color: 'var(--accent-glow)' }} />
  }

  const formatSize = (bytes: number) => {
    if (!bytes || bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
      <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--text)' }}>知识库管理</h2>
      <p className="text-xs mb-4" style={{ color: 'var(--text-dim)' }}>上传教材和课件，构建课程知识库</p>

      {/* Course selector */}
      <div className="mb-4">
        <select
          value={selectedCourseId}
          onChange={(e) => setSelectedCourseId(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-sm border-2 transition-colors"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}
        >
          <option value="">全局知识库（所有课程共享）</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {selectedCourseId && (
          <span className="ml-3 text-xs" style={{ color: 'var(--accent-glow)' }}>
            当前课程的知识库，上传和检索均独立
          </span>
        )}
      </div>

      {/* Upload zone */}
      <div className="mb-6">
        <label
          className="flex flex-col items-center gap-2.5 py-8 rounded-xl border-2 border-dashed cursor-pointer transition-colors hover:opacity-80"
          style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}
        >
          <Upload className="h-8 w-8" style={{ color: 'var(--text-dim)' }} />
          <span className="text-sm" style={{ color: 'var(--text)' }}>拖拽文件上传，或点击选择</span>
          <span className="text-xs" style={{ color: 'var(--text-dim)' }}>
            支持 PDF / PPTX / DOCX / EPUB / XLSX / CSV / TXT / MD
          </span>
          <input
            type="file" multiple
            accept=".txt,.md,.pdf,.docx,.pptx,.xlsx,.csv,.epub"
            className="hidden"
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
        </label>
        {files.length > 0 && (
          <div className="flex items-center justify-between mt-3 px-3 py-2 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <span className="text-xs" style={{ color: 'var(--text-dim)' }}>
              已选择 {files.length} 个文件: {files.map((f) => f.name).join(', ')}
            </span>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-4 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90"
              style={{ background: 'var(--brand)' }}
            >
              {uploading ? '导入中...' : `导入到${selectedCourseId ? '课程' : '全局'}知识库`}
            </button>
          </div>
        )}
      </div>

      {/* File list */}
      <div className="flex flex-col gap-1.5">
        <h3 className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-dim)' }}>
          {selectedCourseId ? '课程文档' : '全部文档'}
        </h3>
        {docFiles.map((f) => (
          <div key={f.id} className="flex items-center justify-between px-3.5 py-2.5 rounded-xl" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2.5">
              {fileIcon(f.filename)}
              <div>
                <p className="text-xs font-medium" style={{ color: 'var(--text)' }}>{f.filename}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                  {formatSize(f.size)} · {f.chunks} 个文档块
                  {f.course_name ? ` · ${f.course_name}` : ''}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium" style={{
                background: f.status === 'indexed' ? 'rgba(34,197,94,.1)' : 'rgba(245,158,11,.1)',
                color: f.status === 'indexed' ? 'var(--green)' : 'var(--amber)',
              }}>
                {f.status === 'indexed' ? '已索引' : '解析中'}
              </span>
              <button
                onClick={() => handleDelete(f.id, f.filename)}
                className="p-1 rounded-md transition-colors opacity-40 hover:opacity-100 hover:bg-red-500/10"
                title="删除文档"
              >
                <Trash2 className="h-3.5 w-3.5" style={{ color: 'var(--red)' }} />
              </button>
            </div>
          </div>
        ))}
        {docFiles.length === 0 && (
          <div className="text-center py-12" style={{ color: 'var(--text-dim)' }}>
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">暂无文档</p>
            <p className="text-xs mt-1">上传你的第一份课件开始构建知识库</p>
          </div>
        )}
      </div>
    </div>
  )
}
