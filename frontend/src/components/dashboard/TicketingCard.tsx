"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Clock } from "lucide-react"
import { formatDistanceToNow, isPast, parseISO, isBefore, addDays, isAfter } from "date-fns"

interface TicketingCardProps {
  memberData: any
}

// Helper function to determine priority badge color (matches burnout analysis colors exactly)
function getPriorityColor(priority: string | number): { backgroundColor: string; color: string } {
  if (typeof priority === "string") {
    // Jira priority - matches burnout analysis severity colors
    switch (priority.toLowerCase()) {
      case "highest":
        return { backgroundColor: "#EF4444", color: "white" } // Critical
      case "high":
        return { backgroundColor: "#F97316", color: "white" } // Poor
      case "medium":
        return { backgroundColor: "#F59E0B", color: "white" } // Fair
      case "low":
        return { backgroundColor: "#10B981", color: "white" } // Good
      case "lowest":
        return { backgroundColor: "#9CA3AF", color: "white" }
      default:
        return { backgroundColor: "#9CA3AF", color: "white" }
    }
  } else {
    // Linear priority (1=Urgent, 2=High, 3=Medium, 4=Low, 0=None) - matches burnout analysis severity colors
    switch (priority) {
      case 1:
        return { backgroundColor: "#EF4444", color: "white" } // Critical
      case 2:
        return { backgroundColor: "#F97316", color: "white" } // Poor
      case 3:
        return { backgroundColor: "#F59E0B", color: "white" } // Fair
      case 4:
        return { backgroundColor: "#10B981", color: "white" } // Good
      case 0:
        return { backgroundColor: "#9CA3AF", color: "white" }
      default:
        return { backgroundColor: "#9CA3AF", color: "white" }
    }
  }
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

// Format due date relative to today
function formatDueDate(dueDate: string | null): string {
  if (!dueDate) return "No due date"

  try {
    const date = parseISO(dueDate)
    if (isPast(date)) {
      return `Overdue by ${formatDistanceToNow(date)}`
    }
    return `Due in ${formatDistanceToNow(date)}`
  } catch {
    return "Invalid date"
  }
}

// Content component for Jira tickets (used in consolidated card)
function JiraTicketCardContent({ memberData }: TicketingCardProps) {
  if (!memberData?.jira_tickets || memberData.jira_tickets.length === 0) {
    return <p className="text-sm text-neutral-500 text-center py-4">No active Jira tickets</p>
  }

  const tickets = memberData.jira_tickets

  // Calculate metrics from raw data
  const totalTickets = tickets.length
  const highCriticalCount = tickets.filter((ticket: any) => isJiraHighCritical(ticket.priority)).length
  const dueIn7DaysCount = tickets.filter((ticket: any) => isDueIn7Days(ticket.duedate)).length
  const overdueCount = tickets.filter((ticket: any) => isOverdue(ticket.duedate)).length

  // Sort tickets by priority (high to low) then by due date, with None at the bottom
  const sortedTickets = [...tickets].sort((a, b) => {
    const priorityOrder: { [key: string]: number } = {
      highest: 1,
      high: 2,
      medium: 3,
      low: 4,
      lowest: 5,
    }
    const aPriority = a.priority?.toLowerCase() || ""
    const bPriority = b.priority?.toLowerCase() || ""

    const aOrder = priorityOrder[aPriority] !== undefined ? priorityOrder[aPriority] : 999
    const bOrder = priorityOrder[bPriority] !== undefined ? priorityOrder[bPriority] : 999

    if (aOrder !== bOrder) {
      return aOrder - bOrder
    }

    // If same priority, sort by due date (earlier first)
    if (a.duedate && b.duedate) {
      return new Date(a.duedate).getTime() - new Date(b.duedate).getTime()
    }
    return a.duedate ? -1 : 1
  })

  return (
    <div className="space-y-4 w-full overflow-hidden">
      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Total Tickets</p>
          <p className="text-lg font-semibold text-neutral-900">{totalTickets}</p>
        </div>
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">High/Critical</p>
          <p className="text-lg font-semibold text-red-600">{highCriticalCount}</p>
        </div>
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Due in 7 Days</p>
          <p className="text-lg font-semibold text-orange-600">{dueIn7DaysCount}</p>
        </div>
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Overdue</p>
          <p className="text-lg font-semibold text-red-600">{overdueCount}</p>
        </div>
      </div>

      <Separator />

      {/* Ticket List */}
      <div className="w-full overflow-hidden">
        <p className="text-xs font-semibold text-neutral-700 mb-3">Active Tickets ({sortedTickets.length})</p>
        <div className="space-y-2 max-h-64 overflow-y-auto w-full">
          {sortedTickets.map((ticket, index) => (
            <div key={index} className="flex items-center gap-2 p-2 bg-neutral-100 rounded-md hover:bg-neutral-200 transition overflow-hidden">
              <Badge
                className="text-xs flex-shrink-0"
                style={getPriorityColor(ticket.priority)}
              >
                {ticket.priority || "N/A"}
              </Badge>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-900 truncate line-clamp-1">
                  <span className="font-bold">{ticket.key}</span>
                  {ticket.summary || ticket.title ? ` - ${ticket.summary || ticket.title}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap flex-shrink-0">
                <Clock className="w-3 h-3" />
                <span>{formatDueDate(ticket.duedate)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Component to display Jira tickets
function JiraTicketCard({ memberData }: TicketingCardProps) {
  if (!memberData?.jira_tickets || memberData.jira_tickets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-blue-600">●</span> Jira Workload
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 text-center py-4">No active Jira tickets</p>
        </CardContent>
      </Card>
    )
  }

  const tickets = memberData.jira_tickets

  // Calculate metrics from raw data
  const totalTickets = tickets.length
  const highCriticalCount = tickets.filter((ticket: any) => isJiraHighCritical(ticket.priority)).length
  const dueIn7DaysCount = tickets.filter((ticket: any) => isDueIn7Days(ticket.duedate)).length
  const overdueCount = tickets.filter((ticket: any) => isOverdue(ticket.duedate)).length

  // Sort tickets by priority (high to low) then by due date, with None at the bottom
  const sortedTickets = [...tickets].sort((a, b) => {
    const priorityOrder: { [key: string]: number } = {
      highest: 1,
      high: 2,
      medium: 3,
      low: 4,
      lowest: 5,
    }
    const aPriority = a.priority?.toLowerCase() || ""
    const bPriority = b.priority?.toLowerCase() || ""

    const aOrder = priorityOrder[aPriority] !== undefined ? priorityOrder[aPriority] : 999
    const bOrder = priorityOrder[bPriority] !== undefined ? priorityOrder[bPriority] : 999

    if (aOrder !== bOrder) {
      return aOrder - bOrder
    }

    // If same priority, sort by due date (earlier first)
    if (a.duedate && b.duedate) {
      return new Date(a.duedate).getTime() - new Date(b.duedate).getTime()
    }
    return a.duedate ? -1 : 1
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-blue-600">●</span> Jira Workload
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Total Tickets</p>
            <p className="text-lg font-semibold text-neutral-900">{totalTickets}</p>
          </div>
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">High/Critical</p>
            <p className="text-lg font-semibold text-red-600">{highCriticalCount}</p>
          </div>
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Due in 7 Days</p>
            <p className="text-lg font-semibold text-orange-600">{dueIn7DaysCount}</p>
          </div>
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Overdue</p>
            <p className="text-lg font-semibold text-red-600">{overdueCount}</p>
          </div>
        </div>

        <Separator />

        {/* Ticket List */}
        <div>
          <p className="text-xs font-semibold text-neutral-700 mb-3">Active Tickets ({sortedTickets.length})</p>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {sortedTickets.map((ticket, index) => (
              <div key={index} className="flex items-center gap-2 p-2 bg-neutral-100 rounded-md hover:bg-neutral-200 transition">
                <Badge
                  className="text-xs flex-shrink-0"
                  style={getPriorityColor(ticket.priority)}
                >
                  {ticket.priority || "N/A"}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate">
                    <span className="font-bold">{ticket.key}</span>
                    {ticket.summary || ticket.title ? ` - ${ticket.summary || ticket.title}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  <span>{formatDueDate(ticket.duedate)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Content component for Linear issues (used in consolidated card)
function LinearIssueCardContent({ memberData }: TicketingCardProps) {
  if (!memberData?.linear_issues || memberData.linear_issues.length === 0) {
    return <p className="text-sm text-neutral-500 text-center py-4">No active Linear issues</p>
  }

  const issues = memberData.linear_issues

  // Calculate metrics from raw data
  const totalIssues = issues.length
  const urgentHighCount = issues.filter((issue: any) => isLinearUrgentHigh(issue.priority)).length
  const dueIn7DaysCount = issues.filter((issue: any) => isDueIn7Days(issue.dueDate)).length
  const overdueCount = issues.filter((issue: any) => isOverdue(issue.dueDate)).length

  // Sort issues by priority (urgent to low) then by due date, with None (0) at the bottom
  const sortedIssues = [...issues].sort((a, b) => {
    // Linear priority: 1=Urgent, 2=High, 3=Medium, 4=Low, 0=None
    const aPriority = a.priority ?? 0
    const bPriority = b.priority ?? 0

    // Put None (0) priority at the bottom by giving it highest sort order
    const aOrder = aPriority === 0 ? 999 : aPriority
    const bOrder = bPriority === 0 ? 999 : bPriority

    if (aOrder !== bOrder) {
      // Lower priority numbers are higher priority (1 is highest)
      return aOrder - bOrder
    }

    // If same priority, sort by due date
    if (a.dueDate && b.dueDate) {
      return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()
    }
    return a.dueDate ? -1 : 1
  })

  return (
    <div className="space-y-4 w-full overflow-hidden">
      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Total Issues</p>
          <p className="text-lg font-semibold text-neutral-900">{totalIssues}</p>
        </div>
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Urgent/High</p>
          <p className="text-lg font-semibold text-red-600">{urgentHighCount}</p>
        </div>
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Due in 7 Days</p>
          <p className="text-lg font-semibold text-orange-600">{dueIn7DaysCount}</p>
        </div>
        <div className="bg-neutral-100 p-3 rounded-md">
          <p className="text-xs text-neutral-700">Overdue</p>
          <p className="text-lg font-semibold text-red-600">{overdueCount}</p>
        </div>
      </div>

      <Separator />

      {/* Issue List */}
      <div>
        <p className="text-xs font-semibold text-neutral-700 mb-3">Active Issues ({sortedIssues.length})</p>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {sortedIssues.map((issue, index) => (
            <div key={index} className="flex items-center gap-2 p-2 bg-neutral-100 rounded-md hover:bg-neutral-200 transition">
              <Badge
                className="text-xs flex-shrink-0"
                style={getPriorityColor(issue.priority)}
              >
                {issue.priority === 1 ? "Urgent" : issue.priority === 2 ? "High" : issue.priority === 3 ? "Med" : issue.priority === 4 ? "Low" : "None"}
              </Badge>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-900 truncate">
                  <span className="font-bold">{issue.identifier}</span>
                  {issue.title ? ` - ${issue.title}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap flex-shrink-0">
                <Clock className="w-3 h-3" />
                <span>{formatDueDate(issue.dueDate)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Component to display Linear issues
function LinearIssueCard({ memberData }: TicketingCardProps) {
  if (!memberData?.linear_issues || memberData.linear_issues.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Linear Workload
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 text-center py-4">No active Linear issues</p>
        </CardContent>
      </Card>
    )
  }

  const issues = memberData.linear_issues

  // Calculate metrics from raw data
  const totalIssues = issues.length
  const urgentHighCount = issues.filter((issue: any) => isLinearUrgentHigh(issue.priority)).length
  const dueIn7DaysCount = issues.filter((issue: any) => isDueIn7Days(issue.dueDate)).length
  const overdueCount = issues.filter((issue: any) => isOverdue(issue.dueDate)).length

  // Sort issues by priority (urgent to low) then by due date, with None (0) at the bottom
  const sortedIssues = [...issues].sort((a, b) => {
    // Linear priority: 1=Urgent, 2=High, 3=Medium, 4=Low, 0=None
    const aPriority = a.priority ?? 0
    const bPriority = b.priority ?? 0

    // Put None (0) priority at the bottom by giving it highest sort order
    const aOrder = aPriority === 0 ? 999 : aPriority
    const bOrder = bPriority === 0 ? 999 : bPriority

    if (aOrder !== bOrder) {
      // Lower priority numbers are higher priority (1 is highest)
      return aOrder - bOrder
    }

    // If same priority, sort by due date
    if (a.dueDate && b.dueDate) {
      return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()
    }
    return a.dueDate ? -1 : 1
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Linear Workload
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Total Issues</p>
            <p className="text-lg font-semibold text-neutral-900">{totalIssues}</p>
          </div>
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Urgent/High</p>
            <p className="text-lg font-semibold text-red-600">{urgentHighCount}</p>
          </div>
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Due in 7 Days</p>
            <p className="text-lg font-semibold text-orange-600">{dueIn7DaysCount}</p>
          </div>
          <div className="bg-neutral-100 p-3 rounded-md">
            <p className="text-xs text-neutral-700">Overdue</p>
            <p className="text-lg font-semibold text-red-600">{overdueCount}</p>
          </div>
        </div>

        <Separator />

        {/* Issue List */}
        <div className="w-full overflow-hidden">
          <p className="text-xs font-semibold text-neutral-700 mb-3">Active Issues ({sortedIssues.length})</p>
          <div className="space-y-2 max-h-64 overflow-y-auto w-full">
            {sortedIssues.map((issue, index) => (
              <div key={index} className="flex items-center gap-2 p-2 bg-neutral-100 rounded-md hover:bg-neutral-200 transition overflow-hidden">
                <Badge
                  className="text-xs flex-shrink-0"
                  style={getPriorityColor(issue.priority)}
                >
                  {issue.priority === 1 ? "Urgent" : issue.priority === 2 ? "High" : issue.priority === 3 ? "Med" : issue.priority === 4 ? "Low" : "None"}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate line-clamp-1">
                    <span className="font-bold">{issue.identifier}</span>
                    {issue.title ? ` - ${issue.title}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  <span>{formatDueDate(issue.dueDate)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
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
