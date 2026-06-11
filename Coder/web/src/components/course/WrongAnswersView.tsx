import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { Plus } from 'lucide-react';

interface WrongAnswer {
  id: string;
  question: string;
  user_answer: string;
  correct_answer: string;
  knowledge_point?: string;
  created_at: string;
}

interface Props {
  slug: string;
}

export function WrongAnswersView({ slug }: Props) {
  const [items, setItems] = useState<WrongAnswer[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [question, setQuestion] = useState('');
  const [userAnswer, setUserAnswer] = useState('');
  const [correctAnswer, setCorrectAnswer] = useState('');

  useEffect(() => {
    api.get<{ wrong_answers: WrongAnswer[] }>(`/courses/${slug}/wrong-answers`)
      .then((d) => setItems(d.wrong_answers))
      .catch(() => setItems([]));
  }, [slug]);

  const handleAdd = async () => {
    if (!question.trim() || !userAnswer.trim() || !correctAnswer.trim()) return;
    await api.post(`/courses/${slug}/wrong-answers`, {
      course_id: slug,
      question: question.trim(),
      user_answer: userAnswer.trim(),
      correct_answer: correctAnswer.trim(),
    });
    setQuestion('');
    setUserAnswer('');
    setCorrectAnswer('');
    setShowAdd(false);
    const d = await api.get<{ wrong_answers: WrongAnswer[] }>(`/courses/${slug}/wrong-answers`);
    setItems(d.wrong_answers);
  };

  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex justify-end">
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-opacity hover:opacity-90 flex items-center gap-1"
          style={{ background: 'var(--brand)' }}
        >
          <Plus className="h-3.5 w-3.5" />
          添加错题
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl p-3 flex flex-col gap-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <input className="px-2.5 py-1.5 rounded-lg text-xs outline-none" style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }} placeholder="题目" value={question} onChange={(e) => setQuestion(e.target.value)} />
          <input className="px-2.5 py-1.5 rounded-lg text-xs outline-none" style={{ background: 'var(--card)', border: '1px solid rgba(239,68,68,.3)', color: 'var(--text)' }} placeholder="你的错误答案" value={userAnswer} onChange={(e) => setUserAnswer(e.target.value)} />
          <input className="px-2.5 py-1.5 rounded-lg text-xs outline-none" style={{ background: 'var(--card)', border: '1px solid rgba(34,197,94,.3)', color: 'var(--text)' }} placeholder="正确答案" value={correctAnswer} onChange={(e) => setCorrectAnswer(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowAdd(false)} className="px-3 py-1 rounded-md text-xs" style={{ color: 'var(--text-dim)' }}>取消</button>
            <button onClick={handleAdd} className="px-3 py-1 rounded-md text-xs text-white" style={{ background: 'var(--brand)' }}>保存</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto flex flex-col gap-2">
        {items.length === 0 && (
          <p className="text-center text-xs py-8" style={{ color: 'var(--text-dim)' }}>暂无错题，手动添加或答题时自动收录</p>
        )}
        {items.map((w) => (
          <div key={w.id} className="rounded-lg p-3" style={{ background: 'var(--surface)', border: '1px solid rgba(239,68,68,.2)', borderLeft: '3px solid var(--red)' }}>
            <div className="flex justify-between items-start mb-1.5">
              {w.knowledge_point && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-md" style={{ background: 'rgba(239,68,68,.1)', color: 'var(--red)' }}>{w.knowledge_point}</span>
              )}
              <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>{w.created_at?.slice(0, 10)}</span>
            </div>
            <p className="text-xs font-semibold" style={{ color: 'var(--text)' }}>Q: {w.question}</p>
            <p className="text-[11px] mt-1" style={{ color: 'var(--red)' }}>✗ 你的答案: {w.user_answer}</p>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--green)' }}>✓ 正确答案: {w.correct_answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
