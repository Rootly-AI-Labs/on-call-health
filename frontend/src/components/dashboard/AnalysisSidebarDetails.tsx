import type { AnalysisResult } from "@/lib/types"

export function AnalysisSidebarDetails({ analysis }: { analysis: AnalysisResult }) {
  const date = new Date(analysis.created_at)
  const hasDate = !Number.isNaN(date.getTime())

  return (
    <div className="space-y-0.5 text-left text-xs leading-5 text-neutral-400 whitespace-normal">
      <p>Time range: {analysis.time_range || 30} days</p>
      {hasDate ? (
        <p title={`Created ${date.toLocaleString()}`}>
          Created <time dateTime={date.toISOString()}>{date.toLocaleDateString(undefined, {
            month: "short", day: "numeric", year: "numeric",
          })}</time>
        </p>
      ) : <p>Created date unknown</p>}
    </div>
  )
}
