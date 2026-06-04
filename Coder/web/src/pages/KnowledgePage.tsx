import { useState, useCallback } from 'react'
import { api } from '../api/client'
import type { KnowledgeResult } from '../types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'

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
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [query])

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-6 text-slate-900 dark:text-slate-100">知识库</h2>

      <div className="flex gap-2 mb-6 border-b border-slate-200 dark:border-slate-800">
        {(['upload', 'search'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              tab === t
                ? 'text-blue-600 dark:text-blue-400 border-blue-400'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 border-transparent'
            }`}
          >
            {t === 'upload' ? '上传文档' : '检索测试'}
          </button>
        ))}
      </div>

      {tab === 'upload' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">上传文档到知识库</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex flex-col items-center gap-3 p-10 border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 rounded-xl cursor-pointer transition-colors">
              <Upload className="h-8 w-8 text-slate-400 dark:text-slate-600" />
              <span className="text-sm text-slate-500 dark:text-slate-400">拖拽或点击选择文件</span>
              <span className="text-xs text-slate-400 dark:text-slate-600">支持 .txt .md .pdf .docx</span>
              <input
                type="file"
                multiple
                accept=".txt,.md,.pdf,.docx"
                className="hidden"
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
              />
            </label>
            {files.length > 0 && (
              <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <FileText className="h-3.5 w-3.5" />
                已选择 {files.length} 个文件: {files.map((f) => f.name).join(', ')}
              </div>
            )}
            <Button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading}
              className="bg-blue-600 hover:bg-blue-500"
            >
              {uploading ? '导入中...' : '导入到知识库'}
            </Button>
            {uploadResults.length > 0 &&
              uploadResults.map((r, i) => (
                <div
                  key={i}
                  className={`text-xs px-3 py-2 rounded-lg ${
                    r.status === 'imported'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-red-500/10 text-red-400 border border-red-500/20'
                  }`}
                >
                  {r.filename}:{' '}
                  {r.status === 'imported' ? `${r.chunks} 个文档块已导入` : r.status}
                </div>
              ))}
          </CardContent>
        </Card>
      )}

      {tab === 'search' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">检索知识</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入检索关键词..."
                className="flex-1 text-sm"
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button
                onClick={handleSearch}
                disabled={!query.trim() || searching}
                className="bg-blue-600 hover:bg-blue-500"
              >
                {searching ? '检索中...' : '搜索'}
              </Button>
            </div>
            {searchResults.length > 0 && (
              <div className="space-y-3">
                {searchResults.map((r, i) => (
                  <Card key={i}>
                    <CardContent className="p-4 space-y-2">
                      <div className="flex gap-2 flex-wrap">
                        <Badge variant="secondary" className="text-[10px]">
                          来源: {r.metadata.filename}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          章节: {r.metadata.section || '-'}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          相关度: {r.metadata.relevance_score}
                        </Badge>
                      </div>
                      <pre className="text-xs text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
                        {r.content}
                      </pre>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
            {searchResults.length === 0 && !searching && query && (
              <EmptyState title="未找到相关结果" />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
