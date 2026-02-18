"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts"
import { Users, FileText, TrendingUp, Loader2 } from "lucide-react"

interface StatsSummary {
  total_users: number
  total_synced_users: number
  total_organizations: number
  total_analyses: number
  total_api_keys: number
  users_google: number
  users_github: number
  new_users_last_30_days: number
  new_users_last_7_days: number
  new_users_today: number
  logins_last_30_days: number
  logins_last_7_days: number
  logins_today: number
  analyses_last_30_days: number
  analyses_last_7_days: number
  analyses_today: number
}

interface TrendDataPoint {
  date: string
  count: number
}

interface UserItem {
  id: number
  email: string
  name: string | null
  organization_name: string | null
  created_at: string
  last_login: string | null
  role: string
  oauth_provider: string | null
}

interface IntegrationItem {
  id: number
  name: string
  platform: string
  user_email: string
  user_name: string | null
  organization_name: string | null
  is_active: boolean
  created_at: string
  last_used_at: string | null
}

interface RecentSignupItem {
  id: number
  email: string
  name: string | null
  organization_id: number | null
  created_at: string
}

interface RecentAnalysisItem {
  id: number
  user_email: string
  user_name: string | null
  integration_name: string | null
  status: string
  created_at: string
  completed_at: string | null
}

interface OrganizationBreakdownItem {
  id: number
  name: string
  domain: string | null
  created_at: string | null
  user_count: number
  analysis_count: number
  has_rootly: boolean
  has_pagerduty: boolean
}

function IntegrationsTable({ integrations }: { integrations: IntegrationItem[] }) {
  const [sortBy, setSortBy] = useState<keyof IntegrationItem>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  if (!integrations || integrations.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Integrations</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500">No integrations found</p>
        </CardContent>
      </Card>
    )
  }

  const handleSort = (column: keyof IntegrationItem) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const sortedIntegrations = [...integrations].sort((a, b) => {
    const aVal = a[sortBy]
    const bVal = b[sortBy]
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1
    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  const SortIcon = ({ column }: { column: keyof IntegrationItem }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc' ? ' ↑' : ' ↓'
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Integrations ({integrations.length})</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('id')}>ID<SortIcon column="id" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('platform')}>Platform<SortIcon column="platform" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('name')}>Name<SortIcon column="name" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('user_email')}>User<SortIcon column="user_email" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('organization_name')}>Organization<SortIcon column="organization_name" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('is_active')}>Status<SortIcon column="is_active" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('created_at')}>Added<SortIcon column="created_at" /></th>
              </tr>
            </thead>
            <tbody>
              {sortedIntegrations.map((integration) => (
                <tr key={integration.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 text-sm text-gray-500">{integration.id}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      integration.platform === 'rootly' ? 'bg-purple-100 text-purple-800' :
                      integration.platform === 'pagerduty' ? 'bg-green-100 text-green-800' :
                      integration.platform === 'github' ? 'bg-gray-100 text-gray-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {integration.platform}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm font-medium">{integration.name}</td>
                  <td className="py-3 px-4 text-sm">{integration.user_email}</td>
                  <td className="py-3 px-4 text-sm">{integration.organization_name || "-"}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${integration.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {integration.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm">
                    {integration.created_at
                      ? new Date(integration.created_at).toLocaleDateString()
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  trend?: string
}) {
  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
            {subtitle && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
            )}
            {trend && (
              <p className="text-xs text-green-600 mt-1 flex items-center">
                <TrendingUp className="w-3 h-3 mr-1" />
                {trend}
              </p>
            )}
          </div>
          <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-full">
            <Icon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function TrendChart({
  title,
  data,
  color = "#3b82f6",
}: {
  title: string
  data: TrendDataPoint[]
  color?: string
}) {
  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => {
                  const date = new Date(value)
                  return `${date.getMonth() + 1}/${date.getDate()}`
                }}
              />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#8b5cf6"
                fillOpacity={1}
                fill={`url(#gradient-${title})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

function UsersTable({ users }: { users: UserItem[] }) {
  const [sortBy, setSortBy] = useState<keyof UserItem>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const handleSort = (column: keyof UserItem) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const sortedUsers = [...users].sort((a, b) => {
    const aVal = a[sortBy]
    const bVal = b[sortBy]
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1
    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  const SortIcon = ({ column }: { column: keyof UserItem }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc' ? ' ↑' : ' ↓'
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">All Users ({users.length})</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('id')}>ID< SortIcon column="id" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('name')}>Name< SortIcon column="name" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('email')}>Email< SortIcon column="email" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('organization_name')}>Organization< SortIcon column="organization_name" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('role')}>Role< SortIcon column="role" /></th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">OAuth</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('created_at')}>Signed Up< SortIcon column="created_at" /></th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.map((user) => (
                <tr key={user.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 text-sm text-gray-500">{user.id}</td>
                  <td className="py-3 px-4 font-medium">{user.name || "-"}</td>
                  <td className="py-3 px-4 text-sm">{user.email}</td>
                  <td className="py-3 px-4 text-sm">{user.organization_name || "-"}</td>
                  <td className="py-3 px-4 text-sm">{user.role || "user"}</td>
                  <td className="py-3 px-4 text-sm">
                    {user.oauth_provider ? (
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${user.oauth_provider === 'google' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {user.oauth_provider}
                      </span>
                    ) : "-"}
                  </td>
                  <td className="py-3 px-4 text-sm">
                    {user.created_at
                      ? new Date(user.created_at).toLocaleDateString()
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function RecentSignupsTable({ users }: { users: RecentSignupItem[] }) {
  if (!users || users.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Recent Signups</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500">No recent signups found</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Recent Signups</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">User</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">Email</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">Signed Up</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{user.name || "-"}</td>
                  <td className="py-3 px-4 text-sm">{user.email}</td>
                  <td className="py-3 px-4 text-sm">
                    {user.created_at
                      ? new Date(user.created_at).toLocaleString()
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function RecentAnalysesTable({ analyses }: { analyses: RecentAnalysisItem[] }) {
  if (!analyses || analyses.length === 0) {
    return (
      <Card className="bg-white dark:bg-gray-800">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Recent Analyses</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500">No recent analyses found</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Recent Analyses</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">ID</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">User</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">Integration</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">Run At</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((analysis) => (
                <tr key={analysis.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 text-sm text-gray-500">{analysis.id}</td>
                  <td className="py-3 px-4 text-sm">{analysis.user_email}</td>
                  <td className="py-3 px-4 text-sm">{analysis.integration_name || "-"}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${analysis.status === 'completed' ? 'bg-green-100 text-green-800' : analysis.status === 'failed' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>
                      {analysis.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm">
                    {analysis.created_at
                      ? new Date(analysis.created_at).toLocaleString()
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function OrganizationBreakdownTable({
  organizations,
  domainFilter,
  onDomainFilterChange,
  loading
}: {
  organizations: OrganizationBreakdownItem[]
  domainFilter: string
  onDomainFilterChange: (value: string) => void
  loading: boolean
}) {
  const [sortBy, setSortBy] = useState<keyof OrganizationBreakdownItem>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const handleSort = (column: keyof OrganizationBreakdownItem) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const sortedOrganizations = [...organizations].sort((a, b) => {
    const aVal = a[sortBy]
    const bVal = b[sortBy]
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1
    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  const SortIcon = ({ column }: { column: keyof OrganizationBreakdownItem }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc' ? ' ↑' : ' ↓'
  }

  return (
    <Card className="bg-white dark:bg-gray-800">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Organization Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center gap-2">
          <Input
            type="text"
            placeholder="Filter by domain (e.g., example.com)"
            value={domainFilter}
            onChange={(e) => onDomainFilterChange(e.target.value)}
            className="max-w-sm"
          />
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : !organizations || organizations.length === 0 ? (
          <p className="text-gray-500">No organizations found</p>
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('id')}>ID<SortIcon column="id" /></th>
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('name')}>Name<SortIcon column="name" /></th>
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('domain')}>Domain<SortIcon column="domain" /></th>
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('user_count')}>Users<SortIcon column="user_count" /></th>
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('analysis_count')}>Analyses<SortIcon column="analysis_count" /></th>
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500">Platform</th>
                  <th className="sticky top-0 bg-gray-50 text-left py-3 px-4 text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100" onClick={() => handleSort('created_at')}>Created<SortIcon column="created_at" /></th>
                </tr>
              </thead>
              <tbody>
                {sortedOrganizations.map((org) => (
                  <tr key={org.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm text-gray-500">{org.id}</td>
                    <td className="py-3 px-4 font-medium">{org.name || "-"}</td>
                    <td className="py-3 px-4 text-sm">{org.domain || "-"}</td>
                    <td className="py-3 px-4 text-sm">{org.user_count}</td>
                    <td className="py-3 px-4 text-sm">{org.analysis_count}</td>
                    <td className="py-3 px-4">
                      <div className="flex gap-1">
                        {org.has_rootly && (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                            Rootly
                          </span>
                        )}
                        {org.has_pagerduty && (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            PagerDuty
                          </span>
                        )}
                        {!org.has_rootly && !org.has_pagerduty && (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm">
                      {org.created_at
                        ? new Date(org.created_at).toLocaleDateString()
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<StatsSummary | null>(null)
  const [userTrends, setUserTrends] = useState<TrendDataPoint[]>([])
  const [syncedUserTrends, setSyncedUserTrends] = useState<TrendDataPoint[]>([])
  const [loginTrends, setLoginTrends] = useState<TrendDataPoint[]>([])
  const [analysisTrends, setAnalysisTrends] = useState<TrendDataPoint[]>([])
  const [users, setUsers] = useState<UserItem[]>([])
  const [recentAnalyses, setRecentAnalyses] = useState<RecentAnalysisItem[]>([])
  const [integrations, setIntegrations] = useState<IntegrationItem[]>([])
  const [platformCounts, setPlatformCounts] = useState<{[key: string]: number}>({})
  const [organizations, setOrganizations] = useState<OrganizationBreakdownItem[]>([])
  const [domainFilter, setDomainFilter] = useState("")
  const [orgLoading, setOrgLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)
  const [authenticated, setAuthenticated] = useState(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('admin_auth') === 'true'
    }
    return false
  })
  const [password, setPassword] = useState("")
  const [shake, setShake] = useState(false)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    setMounted(true)
  }, [])

  const handlePasswordSubmit = async () => {
    setError(null)

    return new Promise<void>((resolve) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${API_BASE}/api/admin/auth/login`, true)
      xhr.withCredentials = true
      xhr.setRequestHeader('Content-Type', 'application/json')

      xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          setAuthenticated(true)
          sessionStorage.setItem('admin_auth', 'true')
        } else {
          setError("Invalid password")
          setShake(true)
          setTimeout(() => setShake(false), 500)
        }
        resolve()
      }

      xhr.onerror = function() {
        setError("Invalid password")
        setShake(true)
        setTimeout(() => setShake(false), 500)
        resolve()
      }

      xhr.send(JSON.stringify({ password }))
    })
  }

  // No auth needed

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    const headers = {}

    try {
      console.log("Fetching admin data from:", API_BASE)
      console.log("With headers:", headers)

      // Use direct fetch to bypass any interceptor issues
      const makeRequest = async (url: string) => {
        console.log("Fetching:", url, headers)
        try {
          const res = await fetch(url, {
            headers,
            mode: 'cors',
            credentials: 'include'
          })
          console.log("Got response:", url, res.status)
          return res
        } catch (e) {
          console.error("Fetch error for", url, e)
          throw e
        }
      }

      const [statsRes, usersRes, recentAnalysesRes, integrationsRes, userTrendsRes, syncedUserTrendsRes, loginTrendsRes, analysisTrendsRes] =
        await Promise.allSettled([
          makeRequest(`${API_BASE}/api/admin/stats/summary`),
          makeRequest(`${API_BASE}/api/admin/stats/users?limit=500`),
          makeRequest(`${API_BASE}/api/admin/stats/recent-analyses?limit=50`),
          makeRequest(`${API_BASE}/api/admin/stats/integrations`),
          makeRequest(`${API_BASE}/api/admin/stats/trends/users?days=30`),
          makeRequest(`${API_BASE}/api/admin/stats/trends/synced-users?days=30`),
          makeRequest(`${API_BASE}/api/admin/stats/trends/logins?days=30`),
          makeRequest(`${API_BASE}/api/admin/stats/trends/analyses?days=30`),
        ])

      // Check for network errors
      const errors: string[] = []
      ;[statsRes, usersRes, recentAnalysesRes].forEach((res, i) => {
        if (res.status === 'rejected') {
          errors.push(`Request ${i} failed: ${res.reason}`)
        }
      })
      if (errors.length > 0) {
        console.error("Network errors:", errors)
        setError(`Network error: ${errors.join(', ')}`)
        setLoading(false)
        return
      }

      console.log("Admin API responses:", {
        stats: (statsRes as any).value?.status,
        users: (usersRes as any).value?.status,
        recentAnalyses: (recentAnalysesRes as any).value?.status,
        trendsUsers: (userTrendsRes as any).value?.status,
        trendsLogins: (loginTrendsRes as any).value?.status,
        trendsAnalyses: (analysisTrendsRes as any).value?.status,
        headers
      })

      const stats = (statsRes as any).value as Response
      const users = (usersRes as any).value as Response
      const recentAnalyses = (recentAnalysesRes as any).value as Response

      const statsData = await stats.json()
      const usersData = await users.json()
      const recentAnalysesData = await recentAnalyses.json()
      const integrationsData = await (integrationsRes as any).value.json()
      const userTrendsData = await (userTrendsRes as any).value.json()
      const syncedUserTrendsData = await (syncedUserTrendsRes as any).value.json()
      const loginTrendsData = await (loginTrendsRes as any).value.json()
      const analysisTrendsData = await (analysisTrendsRes as any).value.json()

      setStats(statsData)
      setUsers(usersData.users || [])
      setRecentAnalyses(recentAnalysesData.analyses || [])
      setIntegrations(integrationsData.integrations || [])
      setPlatformCounts(integrationsData.platform_counts || {})
      setUserTrends(userTrendsData.trends)
      setSyncedUserTrends(syncedUserTrendsData.trends)
      setLoginTrends(loginTrendsData.trends)
      setAnalysisTrends(analysisTrendsData.trends)

      // Fetch organizations separately (has its own endpoint)
      try {
        const orgRes = await makeRequest(`${API_BASE}/api/admin/stats/organizations?limit=100`)
        const orgData = await orgRes.json()
        setOrganizations(orgData.organizations || [])
      } catch (orgErr) {
        console.error("Failed to fetch organizations:", orgErr)
      }
    } catch (err) {
      setError(`Failed to load admin data: ${err}`)
      console.error("Admin fetch error:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Fetch organizations when domain filter changes
  useEffect(() => {
    const fetchOrganizations = async () => {
      setOrgLoading(true)
      try {
        const domainParam = domainFilter ? `&domain_filter=${encodeURIComponent(domainFilter)}` : ''
        const res = await fetch(`${API_BASE}/api/admin/stats/organizations?limit=100${domainParam}`, {
          mode: 'cors',
          credentials: 'include'
        })
        const data = await res.json()
        setOrganizations(data.organizations || [])
      } catch (err) {
        console.error("Failed to fetch organizations:", err)
      } finally {
        setOrgLoading(false)
      }
    }

    // Only fetch after initial load is complete
    if (!loading) {
      fetchOrganizations()
    }
  }, [domainFilter, loading])

  const handleDomainFilterChange = (value: string) => {
    setDomainFilter(value)
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-full mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          </div>
        </div>

        {!authenticated ? (
          <Card className="max-w-md mx-auto">
            <CardHeader>
              <CardTitle>Admin Password Required</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => { e.preventDefault(); handlePasswordSubmit(); }}>
                <Input
                  type="password"
                  placeholder="Enter admin password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`mb-4 ${shake ? 'animate-shake border-red-500' : ''}`}
                />
                <Button type="submit" className="w-full">
                  Access Admin
                </Button>
              </form>
              {error && <p className="text-red-500 mt-2">{error}</p>}
            </CardContent>
          </Card>
        ) : loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : stats ? (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
              <StatCard
                title="Logged-in Users"
                value={stats.total_users}
                subtitle={`Google: ${stats.users_google} | GitHub: ${stats.users_github}`}
                icon={Users}
                trend={`+${stats.new_users_today} today`}
              />
              <StatCard
                title="Synced Users"
                value={stats.total_synced_users}
                subtitle="Team members via integrations"
                icon={Users}
              />
              <StatCard
                title="Total Analyses"
                value={stats.total_analyses}
                subtitle={`+${stats.analyses_last_30_days} this month`}
                icon={FileText}
                trend={`+${stats.analyses_today} today`}
              />
              <StatCard
                title="Organizations"
                value={stats.total_organizations}
                subtitle="Total orgs"
                icon={Users}
              />
              <StatCard
                title="Integrations"
                value={Object.values(platformCounts).reduce((a, b) => a + b, 0)}
                subtitle={`Rootly: ${platformCounts.rootly || 0}, PagerDuty: ${platformCounts.pagerduty || 0}`}
                icon={Users}
              />
            </div>

            {/* Trend Charts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <TrendChart title="User Signups" data={userTrends} color="#3b82f6" />
              <TrendChart title="Synced Users" data={syncedUserTrends} color="#10b981" />
              <TrendChart title="Analyses Run" data={analysisTrends} color="#8b5cf6" />
            </div>

            {/* Tables */}
            <div className="grid grid-cols-1 gap-6">
              <UsersTable users={users} />
            </div>

            {/* Recent Analyses */}
            <div className="grid grid-cols-1 gap-6 mt-6">
              <RecentAnalysesTable analyses={recentAnalyses} />
            </div>

            {/* Organization Breakdown Table - full width */}
            <div className="mt-6">
              <OrganizationBreakdownTable
                organizations={organizations}
                domainFilter={domainFilter}
                onDomainFilterChange={handleDomainFilterChange}
                loading={orgLoading}
              />
            </div>

            {/* Integrations Table - full width */}
            <div className="mt-6">
              <IntegrationsTable integrations={integrations} />
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}
