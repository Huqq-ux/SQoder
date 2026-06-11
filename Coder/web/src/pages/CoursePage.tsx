import { useParams } from 'react-router-dom';
import { useState } from 'react';
import { ChatPage } from './ChatPage';

export function CoursePage() {
  const { slug } = useParams<{ slug: string }>();
  const [activeTab, setActiveTab] = useState<'qa' | 'notes' | 'graph' | 'wrong'>('qa');

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
            {slug}
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
        <div className="text-sm text-gray-500 dark:text-gray-400">
          知识点掌握度: --
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'qa' && <ChatPage courseId={slug} />}
        {activeTab === 'notes' && (
          <div className="p-8 text-gray-500 dark:text-gray-400">笔记功能即将上线</div>
        )}
        {activeTab === 'graph' && (
          <div className="p-8 text-gray-500 dark:text-gray-400">知识图谱即将上线</div>
        )}
        {activeTab === 'wrong' && (
          <div className="p-8 text-gray-500 dark:text-gray-400">错题本即将上线</div>
        )}
      </div>
    </div>
  );
}
