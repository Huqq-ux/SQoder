import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import type { SkillMeta } from '../types'

interface SkillUploadResult {
  status: string
  name: string
  display_name: string
  description: string
  category: string
  version: string
  tags: string[]
  parameters: { name: string; type: string; required: boolean; description: string }[]
  code_ok: boolean
  code_msg: string
  has_code: boolean
}

type Tab = 'upload' | 'list' | 'detail'

export function SkillsPage() {
  const [tab, setTab] = useState<Tab>('list')
  const [skills, setSkills] = useState<SkillMeta[]>([])
  const [loading, setLoading] = useState(true)

  const [jsonInput, setJsonInput] = useState('')
  const [uploadMsg, setUploadMsg] = useState('')
  const [uploadErr, setUploadErr] = useState(false)

  const [mdFile, setMdFile] = useState<File | null>(null)
  const [mdUploading, setMdUploading] = useState(false)
  const [mdResult, setMdResult] = useState<SkillUploadResult | null>(null)
  const [mdError, setMdError] = useState('')
  const uploadFormRef = useRef<HTMLFormElement>(null)

  const loadSkills = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<{ skills: SkillMeta[] }>('/skills/')
      setSkills(data.skills)
    } catch {
      setSkills([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSkills()
  }, [loadSkills])

  const handleJsonUpload = async () => {
    try {
      const skillJson = JSON.parse(jsonInput)
      await api.post('/skills/upload', { skill_json: skillJson })
      setUploadMsg('上传成功')
      setUploadErr(false)
      setJsonInput('')
      loadSkills()
    } catch {
      setUploadMsg('JSON 格式错误')
      setUploadErr(true)
    }
  }

  const handleMdUpload = async () => {
    if (!mdFile) return
    setMdUploading(true)
    setMdResult(null)
    setMdError('')

    const formData = new FormData()
    formData.append('file', mdFile)

    try {
      const res = await fetch('/api/skills/upload-file', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) {
        setMdError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      } else {
        setMdResult(data as SkillUploadResult)
        setMdFile(null)
        if (uploadFormRef.current) uploadFormRef.current.reset()
        loadSkills()
      }
    } catch (e) {
      setMdError(String(e))
    } finally {
      setMdUploading(false)
    }
  }

  const handleToggle = async (name: string, enabled: boolean) => {
    await api.put(`/skills/${name}/toggle`, { enabled: !enabled })
    loadSkills()
  }

  const handleDelete = async (name: string) => {
    await api.del(`/skills/${name}`)
    loadSkills()
  }

  const handleViewDetail = async (name: string) => {
    const detail = await api.get<Record<string, unknown>>(`/skills/${name}`)
    alert(JSON.stringify(detail, null, 2))
  }

  return (
    <div>
      <div className="page-header">
        <h2>🔧 Skill 管理</h2>
      </div>

      <div className="tabs">
        {(['upload', 'list', 'detail'] as Tab[]).map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {{ upload: '上传 Skill', list: '已安装 Skills', detail: 'Skill 详情' }[t]}
          </button>
        ))}
      </div>

      {loading && <div className="empty-state"><p>加载中...</p></div>}

      {/* Tab: upload */}
      {!loading && tab === 'upload' && (
        <>
          <div className="card">
            <h3>📤 上传 Skill Markdown 文件</h3>
            <p className="tag" style={{ marginBottom: 12 }}>仅支持 `.md` 格式，文件名需包含 `skill` 关键词，大小不超过 5MB</p>
            <form ref={uploadFormRef}>
              <div className="form-group">
                <input
                  type="file"
                  accept=".md"
                  onChange={(e) => setMdFile(e.target.files?.[0] || null)}
                />
              </div>
            </form>
            {mdFile && (
              <div className="alert alert-info">
                已选择: {mdFile.name} ({(mdFile.size / 1024).toFixed(1)} KB)
              </div>
            )}
            <button
              className="btn btn-primary"
              onClick={handleMdUpload}
              disabled={!mdFile || mdUploading}
            >
              {mdUploading ? '解析中...' : '上传并解析'}
            </button>

            {mdError && (
              <div className="alert alert-error" style={{ marginTop: 12 }}>
                ❌ {mdError}
              </div>
            )}

            {mdResult && (
              <div style={{ marginTop: 20 }}>
                <div className="alert alert-success">
                  ✅ Skill "{mdResult.display_name}" {mdResult.status === 'updated' ? '已覆盖更新' : '已成功安装'}！
                </div>
                <div className="card">
                  <h3>📋 解析预览</h3>
                  <div className="grid-3" style={{ marginBottom: 12 }}>
                    <div className="metric">
                      <div className="metric-value" style={{ fontSize: 20 }}>{mdResult.name}</div>
                      <div className="metric-label">名称</div>
                    </div>
                    <div className="metric">
                      <div className="metric-value" style={{ fontSize: 20 }}>{mdResult.category}</div>
                      <div className="metric-label">分类</div>
                    </div>
                    <div className="metric">
                      <div className="metric-value" style={{ fontSize: 20 }}>{mdResult.version || '1.0.0'}</div>
                      <div className="metric-label">版本</div>
                    </div>
                  </div>
                  {mdResult.description && (
                    <p style={{ marginBottom: 8 }}><strong>描述</strong>: {mdResult.description}</p>
                  )}
                  {mdResult.tags && mdResult.tags.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <strong>标签</strong>: {mdResult.tags.map((t) => (
                        <span key={t} className="tag">{t}</span>
                      ))}
                    </div>
                  )}
                  {mdResult.parameters && mdResult.parameters.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <strong>参数定义</strong>:
                      <table style={{ width: '100%', marginTop: 8, fontSize: 13, borderCollapse: 'collapse' }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', padding: 4 }}>参数名</th>
                            <th style={{ textAlign: 'left', padding: 4 }}>类型</th>
                            <th style={{ textAlign: 'left', padding: 4 }}>必填</th>
                            <th style={{ textAlign: 'left', padding: 4 }}>说明</th>
                          </tr>
                        </thead>
                        <tbody>
                          {mdResult.parameters.map((p) => (
                            <tr key={p.name} style={{ borderTop: '1px solid var(--color-border)' }}>
                              <td style={{ padding: 4 }}>{p.name}</td>
                              <td style={{ padding: 4 }}>{p.type || 'str'}</td>
                              <td style={{ padding: 4 }}>{p.required ? '✅' : '❌'}</td>
                              <td style={{ padding: 4 }}>{p.description || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {mdResult.has_code && (
                    <div className={`alert ${mdResult.code_ok ? 'alert-success' : 'alert-warning'}`}>
                      {mdResult.code_ok ? '✅ 代码验证通过' : `⚠️ 代码验证未通过: ${mdResult.code_msg}`}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <hr className="divider" />

          <div className="card">
            <h3>或粘贴 Skill JSON</h3>
            <div className="form-group">
              <textarea
                rows={12}
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder={`{\n  "name": "my_skill",\n  "display_name": "My Skill",\n  "description": "...",\n  "category": "custom",\n  "code": "def run(**params):\\n    return params"\n}`}
                style={{ fontFamily: 'monospace', fontSize: 13 }}
              />
            </div>
            <button className="btn btn-primary" onClick={handleJsonUpload}>
              上传 JSON
            </button>
            {uploadMsg && (
              <div className={`alert ${uploadErr ? 'alert-error' : 'alert-success'}`} style={{ marginTop: 12 }}>
                {uploadMsg}
              </div>
            )}
          </div>
        </>
      )}

      {/* Tab: list */}
      {!loading && tab === 'list' && (
        <>
          {skills.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🔧</div>
              <p>暂无已安装的 Skill，请先上传</p>
            </div>
          ) : (
            <div>
              {skills.map((s) => (
                <div key={s.name} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3>
                        {s.display_name}{' '}
                        <code style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>({s.name})</code>
                      </h3>
                      <div style={{ marginTop: 4 }}>
                        <span className="tag">{s.category}</span>
                        {s.tags.map((t) => (
                          <span key={t} className="tag">{t}</span>
                        ))}
                        <span
                          className="tag"
                          style={
                            s.enabled
                              ? { background: '#dcfce7', color: '#166534' }
                              : { background: '#fee2e2', color: '#991b1b' }
                          }
                        >
                          {s.enabled ? '启用' : '禁用'}
                        </span>
                      </div>
                      <p style={{ marginTop: 6, fontSize: 13, color: 'var(--color-text-secondary)' }}>
                        {s.description}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-sm" onClick={() => handleViewDetail(s.name)}>
                        详情
                      </button>
                      <button className="btn btn-sm" onClick={() => handleToggle(s.name, s.enabled)}>
                        {s.enabled ? '禁用' : '启用'}
                      </button>
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.name)}>
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab: detail */}
      {!loading && tab === 'detail' && (
        <div className="card">
          <h3>🔍 Skill 详情查看</h3>
          {skills.length === 0 ? (
            <div className="empty-state"><p>暂无已安装的 Skill</p></div>
          ) : (
            <div className="form-group">
              <select
                value=""
                onChange={async (e) => {
                  const name = e.target.value
                  if (!name) return
                  const detail = await api.get<Record<string, unknown>>(`/skills/${name}`)
                  alert(JSON.stringify(detail, null, 2))
                }}
              >
                <option value="">-- 选择要查看的 Skill --</option>
                {skills.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.display_name} ({s.name})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
