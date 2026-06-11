import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { Search, Plus, ChevronDown, ChevronUp } from 'lucide-react';

interface Note {
  id: string;
  title: string;
  content: string;
  source?: string;
  created_at: string;
}

interface Props {
  slug: string;
}

export function NotesView({ slug }: Props) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.get<{ notes: Note[] }>(`/courses/${slug}/notes`)
      .then((d) => setNotes(d.notes))
      .catch(() => setNotes([]));
  }, [slug]);

  const handleCreate = async () => {
    if (!title.trim() || !content.trim()) return;
    await api.post(`/courses/${slug}/notes`, { course_id: slug, title: title.trim(), content: content.trim() });
    setTitle('');
    setContent('');
    setShowCreate(false);
    const d = await api.get<{ notes: Note[] }>(`/courses/${slug}/notes`);
    setNotes(d.notes);
  };

  const filtered = search
    ? notes.filter((n) => n.title.toLowerCase().includes(search.toLowerCase()) || n.content.toLowerCase().includes(search.toLowerCase()))
    : notes;

  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 flex-1 px-2.5 py-1.5 rounded-lg text-xs"
          style={{ background: 'var(--card)', color: 'var(--text-dim)' }}>
          <Search className="h-3 w-3 shrink-0" />
          <input
            className="bg-transparent border-none outline-none flex-1 text-xs"
            placeholder="搜索笔记..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ color: 'var(--text)' }}
          />
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90 flex items-center gap-1"
          style={{ background: 'var(--brand)' }}
        >
          <Plus className="h-3.5 w-3.5" />
          新建
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl p-3 flex flex-col gap-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <input
            className="px-2.5 py-1.5 rounded-lg text-xs outline-none"
            style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }}
            placeholder="笔记标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="px-2.5 py-1.5 rounded-lg text-xs outline-none resize-none"
            rows={3}
            style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }}
            placeholder="笔记内容..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-1 rounded-md text-xs" style={{ color: 'var(--text-dim)' }}>取消</button>
            <button onClick={handleCreate} className="px-3 py-1 rounded-md text-xs text-white" style={{ background: 'var(--brand)' }}>保存</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 && (
          <p className="text-center text-xs py-8" style={{ color: 'var(--text-dim)' }}>
            {notes.length === 0 ? '暂无笔记，在问答中可一键生成' : '无匹配结果'}
          </p>
        )}
        <div className="grid grid-cols-2 gap-2.5">
          {filtered.map((n) => {
            const isExpanded = expanded[n.id] || false;
            return (
              <div
                key={n.id}
                className="rounded-xl p-3.5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <h4 className="text-[13px] font-semibold" style={{ color: 'var(--text)' }}>{n.title}</h4>
                <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-dim)' }}>
                  {isExpanded ? n.content : n.content.slice(0, 100) + (n.content.length > 100 ? '...' : '')}
                </p>
                {n.content.length > 100 && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setExpanded((prev) => ({ ...prev, [n.id]: !prev })); }}
                    className="flex items-center gap-1 text-[11px] mt-1 transition-colors"
                    style={{ color: 'var(--accent-glow)' }}
                  >
                    {isExpanded ? <><ChevronUp className="h-3 w-3" />收起</> : <><ChevronDown className="h-3 w-3" />展开</>}
                  </button>
                )}
                <div className="flex justify-between items-center mt-2.5">
                  <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                    {n.created_at?.slice(0, 10)} · {n.source || '手动创建'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
