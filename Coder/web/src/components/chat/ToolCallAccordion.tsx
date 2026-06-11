import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Wrench } from 'lucide-react'

export function ToolCallAccordion({ name, args }: { name: string; args: string }) {
  return (
    <Accordion className="mt-1">
      <AccordionItem value="tools" className="border-none">
        <AccordionTrigger className="text-xs py-1 no-underline" style={{ color: 'var(--text-dim)' }}>
          <span className="flex items-center gap-2">
            <Wrench className="h-3 w-3" />
            <code>{name || '工具调用'}</code>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-2 pl-2 border-l-2 mt-2" style={{ borderColor: 'var(--border)' }}>
            <div className="rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--card)' }}>
              <Badge variant="secondary" className="mr-2 text-[10px] bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-0">
                参数
              </Badge>
              {args ? (
                <pre className="mt-1 text-[11px] whitespace-pre-wrap" style={{ color: 'var(--text-dim)' }}>
                  {args}
                </pre>
              ) : (
                <span style={{ color: 'var(--text-dim)' }}>无参数</span>
              )}
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
