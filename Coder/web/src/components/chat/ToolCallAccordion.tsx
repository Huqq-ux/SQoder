import type { ChatPart } from '@/types'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Wrench } from 'lucide-react'

export function ToolCallAccordion({ parts }: { parts: ChatPart[] }) {
  return (
    <Accordion className="mt-3">
      <AccordionItem value="tools" className="border-none">
        <AccordionTrigger className="text-xs text-slate-600 dark:text-slate-500 hover:text-slate-400 dark:hover:text-slate-400 py-1 no-underline">
          <span className="flex items-center gap-2">
            <Wrench className="h-3 w-3" />
            {parts.length} 次工具调用
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-2 pl-2 border-l-2 border-slate-300 dark:border-slate-700 mt-2">
            {parts.map((part, i) =>
              part.type === 'tool_call' ? (
                <div key={i} className="bg-slate-100 dark:bg-slate-900/80 rounded-lg px-3 py-2 text-xs">
                  <Badge variant="secondary" className="mr-2 text-[10px] bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-0">
                    调用
                  </Badge>
                  <code className="text-slate-700 dark:text-slate-400">{part.name}</code>
                  {part.args && (
                    <pre className="mt-1 text-[11px] text-slate-600 dark:text-slate-500 whitespace-pre-wrap">
                      {part.args}
                    </pre>
                  )}
                </div>
              ) : (
                <div key={i} className="bg-emerald-50 dark:bg-emerald-500/5 rounded-lg px-3 py-2 text-xs">
                  <Badge variant="secondary" className="mr-2 text-[10px] bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-0">
                    结果
                  </Badge>
                  <code className="text-slate-700 dark:text-slate-400">{part.name}</code>
                  <pre className="mt-1 text-[11px] text-slate-600 dark:text-slate-500 whitespace-pre-wrap max-h-24 overflow-y-auto">
                    {part.content}
                  </pre>
                </div>
              )
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
