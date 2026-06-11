import { api } from './client'
import type { SkillMeta } from '../types'

export async function listSkills(): Promise<SkillMeta[]> {
  const data = await api.get<{ skills: SkillMeta[] }>('/skills/')
  return data.skills
}

export async function uploadSkillFile(file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/skills/upload-file', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '上传失败')
  }
  return res.json()
}

export async function toggleSkill(name: string, enabled: boolean): Promise<void> {
  await api.put(`/skills/${encodeURIComponent(name)}/toggle`, { enabled })
}

export async function deleteSkill(name: string): Promise<void> {
  await api.del(`/skills/${encodeURIComponent(name)}`)
}
