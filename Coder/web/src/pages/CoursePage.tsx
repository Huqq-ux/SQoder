import { useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ChatPage } from './ChatPage';
import { KnowledgeGraph } from '@/components/KnowledgeGraph';
import { api } from '@/api/client';

interface ProgressData {
  total_points: number;
  tracked_points: number;
  mastered_points: number;
  overall_mastery: number;
}

interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
}

export function CoursePage() {
  const { slug } = useParams<{ slug: string }>();
  const [activeTab, setActiveTab] = useState<'qa' | 'notes' | 'graph' | 'wrong'>('qa');
  const [courseName, setCourseName] = useState('');
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');

  useEffect(() => {
    if (!slug) return;
    api.get<{ course: { name: string } }>(`/courses/${slug}`).then((d) => setCourseName(d.course.name)).catch(() => {});
    api.get<ProgressData>(`/courses/${slug}/progress`).then(setProgress).catch(() => {});
    api.get<{ notes: Note[] }>(`/courses/${slug}/notes`).then((d) => setNotes(d.notes)).catch(() => {});
  }, [slug]);

  const handleCreateNote = async () => {
    if (!newNoteTitle.trim() || !newNoteContent.trim() || !slug) return;
    await api.post(`/courses/${slug}/notes`, {
      course_id: slug,
      title: newNoteTitle,
      content: newNoteContent,
    });
    setNewNoteTitle('');
    setNewNoteContent('');
    const d = await api.get<{ notes: Note[] }>(`/courses/${slug}/notes`);
    setNotes(d.notes);
  };

  if (!slug) {
    return <div className="p-8 text-gray-500 dark:text-gray-400">请选择一个课程</div>;
  }

  const tabs = [
    { key: 'qa' as const, label: '问答' },
    { key: 'notes' as const, label: '笔记' },
    { key: 'graph' as const, label: '图谱' },
    { key: 'wrong' as const, label: '错题' },
  ];

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 shrink-0">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {courseName || slug}
          </h2>
          <div className="flex items-center gap-1">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  activeTab === key
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            掌握度:
          </span>
          <div className="w-28 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${progress?.overall_mastery ?? 0}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">
            {progress ? `${progress.mastered_points}/${progress.total_points}` : '--'}
          </span>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'qa' && <ChatPage courseId={slug} />}
        {activeTab === 'graph' && <KnowledgeGraph identifier={slug} />}
        {activeTab === 'wrong' && (
          <div className="p-8 text-gray-500 dark:text-gray-400">错题本即将上线</div>
        )}
        {activeTab === 'notes' && (
          <div className="flex flex-col h-full p-4 gap-4">
            <div className="flex-1 overflow-auto space-y-3">
              {notes.length === 0 && (
                <p className="text-gray-500 text-sm">暂无笔记，在问答中可一键生成</p>
              )}
              {notes.map((n) => (
                <div key={n.id} className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{n.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 whitespace-pre-wrap">{n.content}</p>
                  <p className="text-xs text-gray-400 mt-2">{n.created_at?.slice(0, 10)}</p>
                </div>
              ))}
            </div>
            <div className="border-t border-gray-200 dark:border-gray-800 pt-3 shrink-0">
              <input
                className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 mb-2"
                placeholder="笔记标题"
                value={newNoteTitle}
                onChange={(e) => setNewNoteTitle(e.target.value)}
              />
              <textarea
                className="w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 mb-2"
                rows={3}
                placeholder="笔记内容"
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
              />
              <button
                onClick={handleCreateNote}
                className="px-4 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
              >
                保存笔记
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
