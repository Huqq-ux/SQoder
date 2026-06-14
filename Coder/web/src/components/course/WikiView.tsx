import { useState, useEffect, useCallback } from 'react';
import { BookOpen, Search, RefreshCw, AlertTriangle, FileText, ChevronRight } from 'lucide-react';
import {
  listWikiPages, getWikiPage, ingestWiki, lintWiki, searchWiki,
  type WikiPageSummary, type WikiPageDetail, type WikiLintResult,
} from '@/api/wiki';

interface Props {
  slug: string;
}

const LINK_RE = /\[\[([^\]]+)\]\]/g;

function renderMarkdownWithLinks(body: string): string {
  // Escape HTML
  let html = body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Convert [[links]] to clickable spans
  html = html.replace(LINK_RE, (_match: string, title: string) => {
    return `<span class="wiki-link" data-title="${title.replace(/"/g, '&quot;')}">${title}</span>`;
  });
  // Basic markdown: bold, italic, headings, code
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br/>');
  html = '<p>' + html + '</p>';
  return html;
}

export function WikiView({ slug }: Props) {
  const [pages, setPages] = useState<WikiPageSummary[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [pageDetail, setPageDetail] = useState<WikiPageDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [linting, setLinting] = useState(false);
  const [lintResult, setLintResult] = useState<WikiLintResult | null>(null);
  const [ingestResult, setIngestResult] = useState<{ pages_created: number; pages_updated: number; errors: string[] } | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPages = useCallback(async () => {
    try {
      const data = await listWikiPages(slug);
      setPages(data);
      setLoading(false);
    } catch {
      setPages([]);
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    fetchPages();
  }, [fetchPages]);

  useEffect(() => {
    if (!selectedPath) return;
    getWikiPage(slug, selectedPath)
      .then(setPageDetail)
      .catch(() => setPageDetail(null));
  }, [slug, selectedPath]);

  const handleSelectPage = (path: string) => {
    setSelectedPath(path);
    setLintResult(null);
    setIngestResult(null);
  };

  const handleIngest = async () => {
    setIngesting(true);
    setIngestResult(null);
    try {
      const result = await ingestWiki(slug);
      setIngestResult(result);
      await fetchPages();
      if (result.pages_created > 0 && !selectedPath) {
        // Auto-select first page
        const updated = await listWikiPages(slug);
        if (updated.length > 0) {
          setSelectedPath(updated[0].path);
        }
      }
    } catch (e: any) {
      setIngestResult({ pages_created: 0, pages_updated: 0, errors: [e.message || '构建失败'] });
    } finally {
      setIngesting(false);
    }
  };

  const handleLint = async () => {
    setLinting(true);
    setLintResult(null);
    try {
      const result = await lintWiki(slug);
      setLintResult(result);
    } catch {
      setLintResult({ broken_links: [], orphans: [], frontmatter_issues: [], total_pages: 0, health: 'error' });
    } finally {
      setLinting(false);
    }
  };

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) {
      await fetchPages();
      return;
    }
    try {
      const results = await searchWiki(slug, q);
      setPages(results.map(r => ({
        path: r.path,
        title: r.title,
        category: '',
        link_count: 0,
        backlink_count: 0,
        modified: '',
      })));
    } catch {
      // fallback to local filter
    }
  };

  const handleWikiLinkClick = (title: string) => {
    // Find page by title
    const target = pages.find(p => p.title === title || p.path.includes(title));
    if (target) {
      setSelectedPath(target.path);
    }
  };

  const filteredPages = searchQuery
    ? pages.filter(p => p.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : pages;

  const conceptPages = filteredPages.filter(p => p.category === 'concepts');
  const queryPages = filteredPages.filter(p => p.category === 'queries');

  const isEmpty = !loading && pages.length === 0;

  // Styles that match the project's CSS variable system
  const styles = {
    container: { display: 'flex', height: '100%', gap: 0 },
    sidebar: {
      width: 260, minWidth: 260, borderRight: '1px solid var(--border)',
      background: 'var(--surface)', display: 'flex', flexDirection: 'column' as const,
    },
    sidebarHeader: {
      padding: '12px 16px', borderBottom: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column' as const, gap: 8,
    },
    searchBox: {
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '6px 10px', borderRadius: 8,
      background: 'var(--bg)', border: '1px solid var(--border)',
    },
    searchInput: {
      flex: 1, border: 'none', background: 'transparent',
      outline: 'none', color: 'var(--text)', fontSize: 13,
    },
    actionButtons: {
      display: 'flex', gap: 6,
    },
    actionBtn: (disabled: boolean) => ({
      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      gap: 4, padding: '6px 8px', borderRadius: 6,
      border: '1px solid var(--border)', background: 'var(--bg)',
      color: 'var(--text)', fontSize: 12, cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
    }),
    pageList: { flex: 1, overflowY: 'auto' as const, padding: '8px 0' },
    pageItem: (active: boolean) => ({
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '8px 16px', cursor: 'pointer',
      background: active ? 'var(--brand)' : 'transparent',
      color: active ? '#fff' : 'var(--text)',
      fontSize: 13, borderLeft: active ? '3px solid var(--brand)' : '3px solid transparent',
    }),
    sectionLabel: {
      padding: '8px 16px 4px', fontSize: 11, fontWeight: 600,
      color: 'var(--text)', opacity: 0.5, textTransform: 'uppercase' as const,
    },
    content: {
      flex: 1, display: 'flex', flexDirection: 'column' as const, overflow: 'hidden',
    },
    contentHeader: {
      padding: '12px 20px', borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', gap: 8,
    },
    contentBody: {
      flex: 1, overflowY: 'auto' as const, padding: '20px 24px',
      color: 'var(--text)', lineHeight: 1.75, fontSize: 14,
    },
    emptyState: {
      flex: 1, display: 'flex', flexDirection: 'column' as const,
      alignItems: 'center', justifyContent: 'center',
      color: 'var(--text)', opacity: 0.6, gap: 16,
    },
    banner: (health: string) => ({
      margin: '0 0 16px 0', padding: '10px 14px', borderRadius: 8,
      background: health === 'good' ? 'rgba(34, 197, 94, 0.1)' :
                  health === 'warning' ? 'rgba(234, 179, 8, 0.1)' :
                  'rgba(239, 68, 68, 0.1)',
      border: `1px solid ${health === 'good' ? 'rgba(34, 197, 94, 0.3)' :
                         health === 'warning' ? 'rgba(234, 179, 8, 0.3)' :
                         'rgba(239, 68, 68, 0.3)'}`,
      fontSize: 13,
    }),
    backlinks: {
      marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border)',
      fontSize: 13, color: 'var(--text)', opacity: 0.7,
    },
    backlinkItem: {
      cursor: 'pointer', color: 'var(--brand)', marginRight: 12,
    },
  };

  return (
    <div style={styles.container}>
      {/* Left sidebar */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <div style={styles.searchBox}>
            <Search size={14} style={{ opacity: 0.4 }} />
            <input
              type="text"
              placeholder="搜索百科..."
              style={styles.searchInput}
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>
          <div style={styles.actionButtons}>
            <button
              style={styles.actionBtn(ingesting)}
              onClick={handleIngest}
              disabled={ingesting}
              title="从课件构建百科"
            >
              <RefreshCw size={13} style={ingesting ? { animation: 'spin 1s linear infinite' } : {}} />
              {ingesting ? '构建中' : '构建'}
            </button>
            <button
              style={styles.actionBtn(linting)}
              onClick={handleLint}
              disabled={linting}
              title="健康检查"
            >
              <AlertTriangle size={13} />
              {linting ? '检查中' : '检查'}
            </button>
          </div>
        </div>

        <div style={styles.pageList}>
          {conceptPages.length > 0 && (
            <>
              <div style={styles.sectionLabel}>概念 ({conceptPages.length})</div>
              {conceptPages.map(p => (
                <div
                  key={p.path}
                  style={styles.pageItem(selectedPath === p.path)}
                  onClick={() => handleSelectPage(p.path)}
                >
                  <FileText size={13} />
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.title}
                  </span>
                  {p.backlink_count > 0 && (
                    <span style={{ fontSize: 10, opacity: 0.6 }}>{p.backlink_count}</span>
                  )}
                </div>
              ))}
            </>
          )}
          {queryPages.length > 0 && (
            <>
              <div style={styles.sectionLabel}>查询归档 ({queryPages.length})</div>
              {queryPages.map(p => (
                <div
                  key={p.path}
                  style={styles.pageItem(selectedPath === p.path)}
                  onClick={() => handleSelectPage(p.path)}
                >
                  <FileText size={13} />
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.title}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Right content area */}
      <div style={styles.content}>
        {isEmpty ? (
          <div style={styles.emptyState}>
            <BookOpen size={48} style={{ opacity: 0.3 }} />
            <div style={{ fontSize: 16, fontWeight: 500 }}>百科尚未构建</div>
            <div style={{ fontSize: 13, textAlign: 'center', maxWidth: 320 }}>
              从已上传的课件中自动提取知识点，<br/>
              构建结构化的交叉引用知识百科。
            </div>
            <button
              onClick={handleIngest}
              disabled={ingesting}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 24px', borderRadius: 8,
                background: 'var(--brand)', color: '#fff',
                border: 'none', cursor: ingesting ? 'not-allowed' : 'pointer',
                fontSize: 14, fontWeight: 500,
                opacity: ingesting ? 0.6 : 1,
              }}
            >
              <RefreshCw size={16} style={ingesting ? { animation: 'spin 1s linear infinite' } : {}} />
              {ingesting ? '正在构建...' : '从课件构建百科'}
            </button>
          </div>
        ) : !selectedPath ? (
          <div style={styles.emptyState}>
            <BookOpen size={32} style={{ opacity: 0.3 }} />
            <div style={{ fontSize: 14 }}>选择一个页面开始阅读</div>
          </div>
        ) : pageDetail ? (
          <>
            <div style={styles.contentHeader}>
              <ChevronRight size={14} style={{ opacity: 0.4 }} />
              <span style={{ fontSize: 14, fontWeight: 500 }}>
                {pageDetail.frontmatter?.title || pageDetail.path}
              </span>
              {pageDetail.frontmatter?.source && (
                <span style={{ fontSize: 12, opacity: 0.5 }}>
                  · 来源: {pageDetail.frontmatter.source}
                </span>
              )}
            </div>
            <div style={styles.contentBody}>
              {ingestResult && (
                <div style={styles.banner(ingestResult.errors.length > 0 ? 'warning' : 'good')}>
                  {ingestResult.pages_created > 0 && `新建 ${ingestResult.pages_created} 个页面 `}
                  {ingestResult.pages_updated > 0 && `更新 ${ingestResult.pages_updated} 个页面`}
                  {ingestResult.errors.length > 0 && (
                    <span style={{ color: 'rgba(239,68,68,0.8)' }}>
                      {' · '}{ingestResult.errors.length} 个错误
                    </span>
                  )}
                </div>
              )}
              {lintResult && (
                <div style={styles.banner(lintResult.health)}>
                  {lintResult.health === 'good' ? '✓ 百科健康度良好' :
                   lintResult.health === 'warning' ? '⚠ 存在一些需要注意的问题' :
                   '✗ 需要修复的问题较多'}
                  {` · ${lintResult.total_pages} 个页面`}
                  {lintResult.broken_links.length > 0 && ` · ${lintResult.broken_links.length} 处断链`}
                  {lintResult.orphans.length > 0 && ` · ${lintResult.orphans.length} 个孤立页面`}
                </div>
              )}
              <div
                dangerouslySetInnerHTML={{
                  __html: renderMarkdownWithLinks(pageDetail.body),
                }}
                onClick={(e) => {
                  const target = e.target as HTMLElement;
                  if (target.classList.contains('wiki-link')) {
                    const title = target.getAttribute('data-title');
                    if (title) handleWikiLinkClick(title);
                  }
                }}
              />
              {pageDetail.backlinks && pageDetail.backlinks.length > 0 && (
                <div style={styles.backlinks}>
                  <strong>引用此页面的页面：</strong>
                  {pageDetail.backlinks.map(bl => (
                    <span
                      key={bl}
                      style={styles.backlinkItem}
                      onClick={() => setSelectedPath(bl)}
                    >
                      {bl}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={styles.emptyState}>
            <AlertTriangle size={32} style={{ opacity: 0.3 }} />
            <div style={{ fontSize: 14 }}>页面加载中...</div>
          </div>
        )}
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .wiki-link {
          color: var(--brand);
          cursor: pointer;
          text-decoration: underline;
          text-decoration-style: dotted;
          text-underline-offset: 3px;
        }
        .wiki-link:hover {
          color: var(--brand);
          opacity: 0.8;
        }
      `}</style>
    </div>
  );
}
