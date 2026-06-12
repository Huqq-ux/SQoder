import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { notify } from '@/lib/toast'
import { BookOpen, FileText, AlertTriangle } from 'lucide-react'

interface CourseItem {
  id: string
  slug: string
  name: string
  semester: string
  kp_total: number
  kp_mastered: number
}

export function HomePage() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<CourseItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newSemester, setNewSemester] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const fetchCourses = () => {
    api.get<{ courses: CourseItem[] }>('/courses/')
      .then((d) => setCourses(d.courses))
      .catch(() => setCourses([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCourses() }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const res = await api.post<{ id: string; slug: string }>('/courses/', {
        name: newName.trim(),
        semester: newSemester.trim(),
        description: newDesc.trim(),
      })
      setShowCreate(false)
      setNewName('')
      setNewSemester('')
      setNewDesc('')
      await fetchCourses()
      navigate(`/course/${res.slug}`)
    } catch (err: any) {
      notify.error(`创建失败: ${err?.message || '未知错误'}`)
    } finally {
      setCreating(false)
    }
  }

  const noteCount = 0   // placeholder until backend stats endpoint
  const wrongCount = 0   // placeholder

  const firstCourse = courses[0]?.slug

  const statCards = [
    { label: '学习课程', value: courses.length, color: '#0d9488', icon: BookOpen, href: firstCourse ? `/course/${firstCourse}` : null },
    { label: '知识笔记', value: noteCount, color: '#6366f1', icon: FileText, href: firstCourse ? `/course/${firstCourse}/notes` : null },
    { label: '待复习错题', value: wrongCount, color: '#d97706', icon: AlertTriangle, href: firstCourse ? `/course/${firstCourse}/wrong` : null },
  ]

  return (
    <div className="h-full overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
      <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--text)' }}>我的课程</h2>
      <p className="text-xs mb-6" style={{ color: 'var(--text-dim)' }}>开始学习，追踪你的知识掌握度</p>

      {/* 统计卡片 — 可点击快捷入口 */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {statCards.map(({ label, value, color, icon: Icon, href }) => (
          <div
            key={label}
            onClick={() => href && navigate(href)}
            className={`rounded-xl p-4 transition-all duration-200 hover:-translate-y-0.5 ${href ? 'cursor-pointer' : ''}`}
            style={{
              background: `linear-gradient(135deg, ${color}11, ${color}08)`,
              border: `1px solid ${color}26`,
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon className="h-3.5 w-3.5" style={{ color }} />
              <span className="text-[11px]" style={{ color: 'var(--text-dim)' }}>{label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color }}>{loading ? '--' : value}</p>
          </div>
        ))}
      </div>

      {/* 课程列表 */}
      <div className="flex flex-col gap-2">
        {courses.map((c) => {
          const pct = c.kp_total > 0 ? Math.round((c.kp_mastered / c.kp_total) * 100) : 0
          return (
            <div
              key={c.slug}
              onClick={() => navigate(`/course/${c.slug}`)}
              className="rounded-xl p-4 cursor-pointer flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              <div>
                <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{c.name}</h3>
                <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>
                  {c.semester || '未设置学期'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px]" style={{ color: 'var(--text-dim)' }}>
                  {c.kp_mastered}/{c.kp_total} 已掌握
                </span>
                <div className="w-20 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--card)' }}>
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${pct}%`,
                      background: pct > 50 ? 'linear-gradient(90deg, var(--brand), var(--accent-glow))' :
                                  pct > 0 ? 'var(--amber)' : 'var(--text-dim)',
                    }}
                  />
                </div>
                <span className="text-sm font-semibold" style={{ color: pct > 0 ? 'var(--accent-glow)' : 'var(--text-dim)' }}>
                  {pct}%
                </span>
              </div>
            </div>
          )
        })}

        {!loading && courses.length === 0 && (
          <div className="text-center py-12" style={{ color: 'var(--text-dim)' }}>
            <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">还没有课程</p>
            <p className="text-xs mt-1">点击按钮创建你的第一门课程</p>
          </div>
        )}
      </div>

      {/* 新建课程 */}
      <div className="max-w-md mx-auto mt-6">
        {showCreate ? (
          <div className="rounded-xl p-4 flex flex-col gap-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>新建课程</h3>
            <input
              className="px-3 py-2 rounded-lg text-sm outline-none border-2 focus:border-[var(--brand-border)] transition-colors"
              style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }}
              placeholder="课程名称（必填）"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <input
              className="px-3 py-2 rounded-lg text-sm outline-none border-2 focus:border-[var(--brand-border)] transition-colors"
              style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }}
              placeholder="学期（如 2026 春季）"
              value={newSemester}
              onChange={(e) => setNewSemester(e.target.value)}
            />
            <textarea
              className="px-3 py-2 rounded-lg text-sm outline-none resize-none border-2 focus:border-[var(--brand-border)] transition-colors" rows={2}
              style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }}
              placeholder="课程描述（可选）"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-1.5 rounded-lg text-sm" style={{ color: 'var(--text-dim)' }}>取消</button>
              <button onClick={handleCreate} disabled={creating || !newName.trim()} className="px-4 py-1.5 rounded-lg text-sm text-white" style={{ background: 'var(--brand)', opacity: creating || !newName.trim() ? 0.6 : 1 }}>
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowCreate(true)}
            className="w-full px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-all duration-200 hover:opacity-90"
            style={{ background: 'var(--brand)' }}
          >
            ＋ 新建课程
          </button>
        )}
      </div>
    </div>
  )
}
