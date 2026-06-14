import { useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ChatPage } from './ChatPage';
import { KnowledgeGraph } from '@/components/KnowledgeGraph';
import { NotesView } from '@/components/course/NotesView';
import { WrongAnswersView } from '@/components/course/WrongAnswersView';
import { WikiView } from '@/components/course/WikiView';
import { api } from '@/api/client';

interface ProgressData {
  total_points: number;
  tracked_points: number;
  mastered_points: number;
  overall_mastery: number;
}

export function CoursePage() {
  const { slug, tab } = useParams<{ slug: string; tab?: string }>();

  const [courseName, setCourseName] = useState('');
  const [progress, setProgress] = useState<ProgressData | null>(null);

  // Determine active tab from URL
  const activeTab: 'qa' | 'notes' | 'graph' | 'wrong' | 'wiki' = (() => {
    if (tab === 'notes') return 'notes';
    if (tab === 'graph') return 'graph';
    if (tab === 'wrong') return 'wrong';
    if (tab === 'wiki') return 'wiki';
    return 'qa';
  })();

  useEffect(() => {
    if (!slug) return;
    api.get<{ course: { name: string } }>(`/courses/${slug}`)
      .then((d) => setCourseName(d.course.name))
      .catch(() => setCourseName(slug));
    api.get<ProgressData>(`/courses/${slug}/progress`)
      .then(setProgress)
      .catch(() => setProgress(null));
  }, [slug]);

  if (!slug) {
    return <div className="p-8" style={{ color: 'var(--text-dim)' }}>请选择一个课程</div>;
  }

  const masteryPct = progress ? Math.round(progress.overall_mastery) : 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header
        className="flex items-center justify-between px-5 py-3 shrink-0 border-b"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)', transition: 'background 0.4s, border-color 0.4s' }}
      >
        <div>
          <h1 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>{courseName || slug}</h1>
          <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>
            共 {progress?.total_points ?? '--'} 个知识点 · {progress ? `${progress.mastered_points} 已掌握` : ''}
          </p>
        </div>
        {/* Progress bar */}
        <div className="flex items-center gap-2.5">
          <span className="text-xs" style={{ color: 'var(--text-dim)' }}>掌握度</span>
          <div className="w-28 h-1.5 rounded-full overflow-hidden relative progress-shimmer" style={{ background: 'var(--card)' }}>
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${masteryPct}%`,
                background: 'linear-gradient(90deg, var(--brand), var(--accent-glow))',
              }}
            />
          </div>
          <span className="text-sm font-bold" style={{
            background: 'var(--pct-gradient)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {progress ? `${masteryPct}%` : '--'}
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'qa' && <ChatPage courseId={slug} />}
        {activeTab === 'graph' && <KnowledgeGraph identifier={slug} />}
        {activeTab === 'notes' && <NotesView slug={slug} />}
        {activeTab === 'wrong' && <WrongAnswersView slug={slug} />}
        {activeTab === 'wiki' && <WikiView slug={slug} />}
      </div>
    </div>
  );
}
