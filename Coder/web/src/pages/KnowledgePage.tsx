import { useState, useCallback } from 'react'
import { api } from '../api/client'
import type { KnowledgeResult } from '../types'

type Tab = 'upload' | 'search'

export function KnowledgePage() {
  const [tab, setTab] = useState<Tab>('upload')
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<{ filename: string; chunks: number; status: string }[]>([])
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<KnowledgeResult[]>([])

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return
    setUploading(true)
    try {
      const data = await api.uploadFiles<{ results: { filename: string; chunks: number; status: string }[] }>(
        '/knowledge/upload',
        files,
      )
      setUploadResults(data.results)
      setFiles([])
    } catch (e) {
      setUploadResults([{ filename: 'Error', chunks: 0, status: String(e) }])
    } finally {
      setUploading(false)
    }
  }, [files])

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const data = await api.post<{ results: KnowledgeResult[]; available: boolean }>(
        '/knowledge/search',
        { query: query.trim(), k: 5 },
      )
      setSearchResults(data.results)
    } catch (e) {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [query])

  return (
    <div>
      <div className="page-header">
        <h2>📚 知识库管理</h2>
      </div>

      <div className="tabs">
        <button
          className={`tab ${tab === 'upload' ? 'active' : ''}`}
          onClick={() => setTab('upload')}
        >
          上传文档
        </button>
        <button
          className={`tab ${tab === 'search' ? 'active' : ''}`}
          onClick={() => setTab('search')}
        >
          检索测试
        </button>
      </div>

      {tab === 'upload' && (
        <div className="card">
          <h3>上传文档到知识库</h3>
          <div className="form-group">
            <input
              type="file"
              multiple
              accept=".txt,.md,.pdf,.docx"
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
          </div>
          {files.length > 0 && (
            <div className="alert alert-info">
              已选择 {files.length} 个文件: {files.map((f) => f.name).join(', ')}
            </div>
          )}
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={files.length === 0 || uploading}
          >
            {uploading ? '导入中...' : '导入到知识库'}
          </button>

          {uploadResults.length > 0 && (
            <div style={{ marginTop: 16 }}>
              {uploadResults.map((r, i) => (
                <div
                  key={i}
                  className={`alert ${r.status === 'imported' ? 'alert-success' : 'alert-error'}`}
                >
                  {r.filename}: {r.status === 'imported' ? `${r.chunks} 个文档块已导入` : r.status}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'search' && (
        <div className="card">
          <h3>检索知识</h3>
          <div className="form-group">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入检索关键词..."
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={handleSearch}
            disabled={!query.trim() || searching}
          >
            {searching ? '检索中...' : '搜索'}
          </button>

          {searchResults.length > 0 && (
            <div style={{ marginTop: 16 }}>
              {searchResults.map((r, i) => (
                <div key={i} className="card">
                  <div className="tag">来源: {r.metadata.filename}</div>
                  <div className="tag">章节: {r.metadata.section || '-'}</div>
                  <div className="tag">相关度: {r.metadata.relevance_score}</div>
                  <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', fontSize: 13 }}>
                    {r.content}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {searchResults.length === 0 && !searching && query && (
            <div className="alert alert-warning">未找到相关结果</div>
          )}
        </div>
      )}
    </div>
  )
}
