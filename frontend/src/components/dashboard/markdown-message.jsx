"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownMessage({ content }) {
  return (
    <div className="w-full min-w-0 max-w-full overflow-hidden break-words text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="my-2 block w-full max-w-full overflow-x-auto rounded-lg border border-border">
              <table className="w-full min-w-full table-auto border-collapse text-left text-xs">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-border px-3 py-2 font-semibold text-muted-foreground whitespace-nowrap">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-border px-3 py-2 text-foreground break-all max-w-[220px]">
              {children}
            </td>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-primary underline underline-offset-4 hover:text-primary/80 break-all"
            >
              {children}
            </a>
          ),
          p: ({ children }) => <p className="mb-2 last:mb-0 break-words">{children}</p>,
          ul: ({ children }) => <ul className="mb-2 list-disc pl-4 last:mb-0 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 list-decimal pl-4 last:mb-0 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="break-words">{children}</li>,
          code: ({ inline, children }) =>
            inline ? (
              <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs text-foreground break-all">
                {children}
              </code>
            ) : (
              <pre className="my-2 max-w-full overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs">
                <code>{children}</code>
              </pre>
            ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}