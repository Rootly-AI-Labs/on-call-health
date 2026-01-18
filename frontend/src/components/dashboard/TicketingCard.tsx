"use client"

import type { ReactElement } from "react"
import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Clock, ChevronDown, ChevronRight, AlertTriangle, AlertCircle, Ticket } from "lucide-react"
import { formatDistanceToNow, isPast, parseISO, isBefore, addDays, isAfter } from "date-fns"

interface TicketingCardProps {
  memberData: any
}

// Priority color mappings
const JIRA_PRIORITY_COLORS: Record<string, { backgroundColor: string; color: string }> = {
  highest: { backgroundColor: "#EF4444", color: "white" },
  high: { backgroundColor: "#F97316", color: "white" },
  medium: { backgroundColor: "#F59E0B", color: "white" },
  low: { backgroundColor: "#10B981", color: "white" },
  lowest: { backgroundColor: "#9CA3AF", color: "white" },
}

const LINEAR_PRIORITY_COLORS: Record<number, { backgroundColor: string; color: string }> = {
  1: { backgroundColor: "#EF4444", color: "white" },
  2: { backgroundColor: "#F97316", color: "white" },
  3: { backgroundColor: "#F59E0B", color: "white" },
  4: { backgroundColor: "#10B981", color: "white" },
  0: { backgroundColor: "#9CA3AF", color: "white" },
}

const DEFAULT_PRIORITY_COLOR = { backgroundColor: "#9CA3AF", color: "white" }

function getPriorityColor(priority: string | number): { backgroundColor: string; color: string } {
  if (typeof priority === "string") {
    return JIRA_PRIORITY_COLORS[priority.toLowerCase()] || DEFAULT_PRIORITY_COLOR
  }
  return LINEAR_PRIORITY_COLORS[priority] || DEFAULT_PRIORITY_COLOR
}

// Check if ticket is due within 7 days
function isDueIn7Days(dueDate: string | null): boolean {
  if (!dueDate) return false
  try {
    const date = parseISO(dueDate)
    const today = new Date()
    const sevenDaysFromNow = addDays(today, 7)
    return isAfter(date, today) && isBefore(date, sevenDaysFromNow)
  } catch {
    return false
  }
}

// Check if ticket is overdue
function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false
  try {
    const date = parseISO(dueDate)
    return isPast(date)
  } catch {
    return false
  }
}

// Check if Jira priority is high/critical
function isJiraHighCritical(priority: string | null): boolean {
  if (!priority) return false
  return ["highest", "high"].includes(priority.toLowerCase())
}

// Check if Linear priority is urgent/high
function isLinearUrgentHigh(priority: number | null): boolean {
  return priority === 1 || priority === 2
}

const LINEAR_PRIORITY_LABELS: Record<number, string> = {
  1: "Urgent",
  2: "High",
  3: "Med",
  4: "Low",
  0: "None",
}

function getLinearPriorityLabel(priority: number | null): string {
  return LINEAR_PRIORITY_LABELS[priority ?? 0] || "None"
}

const JIRA_PRIORITY_ORDER: Record<string, number> = {
  highest: 1,
  high: 2,
  medium: 3,
  low: 4,
  lowest: 5,
}

// Reusable attention metric box component
interface AttentionMetricBoxProps {
  count: number
  label: string
  activeColor: string
  Icon: typeof AlertTriangle
}

function AttentionMetricBox({ count, label, activeColor, Icon }: AttentionMetricBoxProps): ReactElement {
  const isActive = count > 0
  const colorMap: Record<string, { bg: string; border: string; text: string }> = {
    red: { bg: "bg-red-50", border: "border-red-200", text: "text-red-600" },
    amber: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-600" },
    orange: { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-600" },
  }
  const colors = colorMap[activeColor] || colorMap.red

  return (
    <div className={`flex-1 p-3 rounded-lg border ${
      isActive ? `${colors.bg} ${colors.border}` : "bg-neutral-50 border-neutral-200"
    }`}>
      <div className="flex items-center gap-2">
        {isActive && <Icon className={`w-4 h-4 ${colors.text}`} />}
        <span className={`text-2xl font-bold ${isActive ? colors.text : "text-neutral-400"}`}>
          {count}
        </span>
      </div>
      <p className={`text-xs mt-1 ${isActive ? `${colors.text} font-medium` : "text-neutral-500"}`}>
        {label}
      </p>
    </div>
  )
}

function formatDueDate(dueDate: string | null): string {
  if (!dueDate) return "No due date"
  try {
    const date = parseISO(dueDate)
    const prefix = isPast(date) ? "Overdue by" : "Due in"
    return `${prefix} ${formatDistanceToNow(date)}`
  } catch {
    return "Invalid date"
  }
}

// Safe date parsing that handles invalid dates
function safeDateCompare(dateA: string | null, dateB: string | null): number {
  if (!dateA && !dateB) return 0
  if (!dateA) return 1
  if (!dateB) return -1
  const aTime = new Date(dateA).getTime()
  const bTime = new Date(dateB).getTime()
  if (isNaN(aTime) && isNaN(bTime)) return 0
  if (isNaN(aTime)) return 1
  if (isNaN(bTime)) return -1
  return aTime - bTime
}

// Sort Jira tickets by priority then due date
function sortJiraTickets(tickets: any[]): any[] {
  return [...tickets].sort((a, b) => {
    const aPriority = a.priority?.toLowerCase() || ""
    const bPriority = b.priority?.toLowerCase() || ""
    const aOrder = JIRA_PRIORITY_ORDER[aPriority] ?? 999
    const bOrder = JIRA_PRIORITY_ORDER[bPriority] ?? 999

    if (aOrder !== bOrder) return aOrder - bOrder
    return safeDateCompare(a.duedate, b.duedate)
  })
}

// Sort Linear issues by priority then due date
function sortLinearIssues(issues: any[]): any[] {
  return [...issues].sort((a, b) => {
    const aPriority = a.priority ?? 0
    const bPriority = b.priority ?? 0
    const aOrder = aPriority === 0 ? 999 : aPriority
    const bOrder = bPriority === 0 ? 999 : bPriority

    if (aOrder !== bOrder) return aOrder - bOrder
    return safeDateCompare(a.dueDate, b.dueDate)
  })
}

// Unified ticket/issue content component
interface TicketListContentProps {
  items: any[]
  emptyMessage: string
  itemLabel: string
  highPriorityLabel: string
  isHighPriority: (item: any) => boolean
  getDueDate: (item: any) => string | null
  getItemKey: (item: any) => string
  getItemTitle: (item: any) => string
  getPriorityLabel: (item: any) => string
  sortItems: (items: any[]) => any[]
}

function TicketListContent({
  items,
  emptyMessage,
  itemLabel,
  highPriorityLabel,
  isHighPriority,
  getDueDate,
  getItemKey,
  getItemTitle,
  getPriorityLabel,
  sortItems,
}: TicketListContentProps): ReactElement {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!items || items.length === 0) {
    return <p className="text-sm text-neutral-500 text-center py-4">{emptyMessage}</p>
  }

  const totalCount = items.length
  const highPriorityCount = items.filter(isHighPriority).length
  const dueIn7DaysCount = items.filter((item) => isDueIn7Days(getDueDate(item))).length
  const overdueCount = items.filter((item) => isOverdue(getDueDate(item))).length
  const sortedItems = sortItems(items)

  return (
    <div className="space-y-4 w-full overflow-hidden">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-center gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-neutral-100">
              <Ticket className="w-5 h-5 text-neutral-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{totalCount}</p>
              <p className="text-xs text-neutral-500">Active {itemLabel}</p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <AttentionMetricBox count={overdueCount} label="Overdue" activeColor="red" Icon={AlertTriangle} />
          <AttentionMetricBox count={dueIn7DaysCount} label="Due in 7 Days" activeColor="amber" Icon={Clock} />
          <AttentionMetricBox count={highPriorityCount} label={highPriorityLabel} activeColor="orange" Icon={AlertCircle} />
        </div>
      </div>

      <Separator />

      <div className="w-full overflow-hidden">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-xs font-semibold text-neutral-700 hover:text-neutral-900 transition-colors"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          View All {itemLabel} ({sortedItems.length})
        </button>
        {isExpanded && (
          <div className="space-y-2 max-h-64 overflow-y-auto w-full mt-3">
            {sortedItems.map((item, index) => (
              <div key={getItemKey(item) || `item-${index}`} className="flex items-center gap-2 p-2 bg-neutral-50 rounded-md hover:bg-neutral-100 transition overflow-hidden border border-neutral-100">
                <Badge className="text-xs flex-shrink-0" style={getPriorityColor(item.priority)}>
                  {getPriorityLabel(item)}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate line-clamp-1">
                    <span className="font-bold">{getItemKey(item)}</span>
                    {getItemTitle(item) && ` - ${getItemTitle(item)}`}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  <span>{formatDueDate(getDueDate(item))}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Jira-specific content component
function JiraTicketCardContent({ memberData }: TicketingCardProps): ReactElement {
  return (
    <TicketListContent
      items={memberData?.jira_tickets}
      emptyMessage="No active Jira tickets"
      itemLabel="Tickets"
      highPriorityLabel="High Priority"
      isHighPriority={(ticket) => isJiraHighCritical(ticket.priority)}
      getDueDate={(ticket) => ticket.duedate}
      getItemKey={(ticket) => ticket.key}
      getItemTitle={(ticket) => ticket.summary || ticket.title || ""}
      getPriorityLabel={(ticket) => ticket.priority || "N/A"}
      sortItems={sortJiraTickets}
    />
  )
}

// Standalone Jira card component (used when only Jira is available)
function JiraTicketCard({ memberData }: TicketingCardProps): ReactElement {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-blue-600">*</span> Jira Workload
        </CardTitle>
      </CardHeader>
      <CardContent>
        <JiraTicketCardContent memberData={memberData} />
      </CardContent>
    </Card>
  )
}

// Linear-specific content component
function LinearIssueCardContent({ memberData }: TicketingCardProps): ReactElement {
  return (
    <TicketListContent
      items={memberData?.linear_issues}
      emptyMessage="No active Linear issues"
      itemLabel="Issues"
      highPriorityLabel="Urgent/High"
      isHighPriority={(issue) => isLinearUrgentHigh(issue.priority)}
      getDueDate={(issue) => issue.dueDate}
      getItemKey={(issue) => issue.identifier}
      getItemTitle={(issue) => issue.title || ""}
      getPriorityLabel={(issue) => getLinearPriorityLabel(issue.priority)}
      sortItems={sortLinearIssues}
    />
  )
}

// Standalone Linear card component (used when only Linear is available)
function LinearIssueCard({ memberData }: TicketingCardProps): ReactElement {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Linear Workload
        </CardTitle>
      </CardHeader>
      <CardContent>
        <LinearIssueCardContent memberData={memberData} />
      </CardContent>
    </Card>
  )
}

// Main TicketingCard component
export function TicketingCard({ memberData }: TicketingCardProps) {
  const [activeTab, setActiveTab] = useState<"jira" | "linear">("jira")

  // Check data availability
  const hasJira = memberData?.jira_account_id && memberData?.jira_tickets !== undefined
  const hasLinear = memberData?.linear_user_id && memberData?.linear_issues !== undefined

  // If neither Jira nor Linear data, don't render
  if (!hasJira && !hasLinear) {
    return null
  }

  // If both are available, show consolidated card with toggle in header
  if (hasJira && hasLinear) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {activeTab === "jira" ? "Jira Workload" : "Linear Workload"}
            </CardTitle>
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab("jira")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === "jira"
                    ? "bg-purple-600 text-white"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                }`}
              >
                Jira
              </button>
              <button
                onClick={() => setActiveTab("linear")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  activeTab === "linear"
                    ? "bg-purple-600 text-white"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                }`}
              >
                Linear
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="w-full overflow-hidden">
          {activeTab === "jira" ? (
            <JiraTicketCardContent memberData={memberData} />
          ) : (
            <LinearIssueCardContent memberData={memberData} />
          )}
        </CardContent>
      </Card>
    )
  }

  // If only Jira is available
  if (hasJira) {
    return <JiraTicketCard memberData={memberData} />
  }

  // If only Linear is available
  return <LinearIssueCard memberData={memberData} />
}
