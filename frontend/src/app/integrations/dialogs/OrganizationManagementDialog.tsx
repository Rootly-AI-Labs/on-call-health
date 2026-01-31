import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Users, Mail, Loader2, Search, ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"
import { UserInfo } from "../types"

const TEAM_MEMBERS_PER_PAGE = 10

interface OrganizationMember {
  id: number | string
  invitation_id?: number
  name: string
  email: string
  role: string
  status: 'active' | 'pending'
  is_current_user: boolean
  joined_at?: string
  invited_at?: string
  expires_at?: string
}

interface PendingInvitation {
  id: number
  email: string
  role: string
  invited_by: { name: string } | null
  created_at: string
  expires_at: string
  is_expired: boolean
}

interface OrganizationManagementDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  inviteEmail: string
  onInviteEmailChange: (email: string) => void
  inviteRole: string
  onInviteRoleChange: (role: string) => void
  isInviting: boolean
  onInvite: () => void
  loadingOrgData: boolean
  orgMembers: OrganizationMember[]
  pendingInvitations: PendingInvitation[]
  userInfo: UserInfo | null
  onRoleChange: (userId: number, newRole: string) => void
  onClose: () => void
  asInlineView?: boolean  // Flag to render as inline view instead of modal
  title?: string  // Custom title (defaults to "Organization Management")
  subtitle?: string  // Custom subtitle
}

export function OrganizationManagementDialog({
  open,
  onOpenChange,
  inviteEmail,
  onInviteEmailChange,
  inviteRole,
  onInviteRoleChange,
  isInviting,
  onInvite,
  loadingOrgData,
  orgMembers,
  pendingInvitations,
  userInfo,
  onRoleChange,
  onClose,
  asInlineView = false,  // Default to modal view
  title = "Organization Management",  // Default title
  subtitle = "Invite new members and manage your organization"  // Default subtitle
}: OrganizationManagementDialogProps) {
  // Content component extracted for reuse
  // Local search state for filtering members
  const [searchQuery, setSearchQuery] = useState("")
  const [currentPage, setCurrentPage] = useState(1)

  // Filter members based on search query
  const filteredMembers = orgMembers.filter((member) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      member.name.toLowerCase().includes(query) ||
      member.email.toLowerCase().includes(query)
    )
  })

  // Pagination calculations
  const totalPages = Math.ceil(filteredMembers.length / TEAM_MEMBERS_PER_PAGE)
  const startIndex = (currentPage - 1) * TEAM_MEMBERS_PER_PAGE
  const paginatedMembers = filteredMembers.slice(startIndex, startIndex + TEAM_MEMBERS_PER_PAGE)

  const dialogContentBody = (
    <>
      {/* Role descriptions */}
      <div className={asInlineView ? "px-0 py-3 bg-purple-100 rounded-lg mb-6" : "mt-4 px-4 py-3 bg-purple-100 rounded-lg"}>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-baseline space-x-2">
              <span className="font-semibold text-neutral-900 min-w-[80px]">Admin</span>
              <span className="text-neutral-700">Full access: manage members, integrations, run analyses, send surveys, and configure settings</span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="font-semibold text-neutral-900 min-w-[80px]">Member</span>
              <span className="text-neutral-700">Can view team health data, run analyses, and send surveys</span>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Invite New Member Section - Only visible to admins */}
          {(userInfo?.role === 'admin') && (
            <div className="p-6 border rounded-lg bg-white">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Mail className="w-5 h-5 text-purple-600" />
                </div>
                <div className="flex-1 space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-neutral-900">Invite Team Member</h3>
                    <p className="text-sm text-neutral-500 mt-1">Send an invitation to join your organization</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="invite-email" className="block text-sm font-medium text-neutral-700 mb-1.5">
                        Email Address
                      </label>
                      <Input
                        id="invite-email"
                        type="email"
                        placeholder="colleague@company.com"
                        value={inviteEmail}
                        onChange={(e) => onInviteEmailChange(e.target.value)}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <label htmlFor="invite-role" className="block text-sm font-medium text-neutral-700 mb-1.5">
                        Role
                      </label>
                      <select
                        id="invite-role"
                        value={inviteRole}
                        onChange={(e) => onInviteRoleChange(e.target.value)}
                        className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      >
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                  </div>

                  <Button
                    onClick={onInvite}
                    disabled={isInviting || !inviteEmail.trim()}
                    className="w-full md:w-auto bg-purple-700 hover:bg-purple-800"
                  >
                    {isInviting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Sending Invitation...
                      </>
                    ) : (
                      <>
                        <Mail className="w-4 h-4 mr-2" />
                        Send Invitation
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Current Members & Pending Invitations */}
          {loadingOrgData ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-neutral-500" />
              <p className="text-neutral-500">Loading organization data...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Search Bar - above members table */}
              {orgMembers.length > 0 && (
                <div className="mb-4">
                  <div className="relative max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                    <Input
                      type="text"
                      placeholder="Search members..."
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value)
                        setCurrentPage(1)
                      }}
                      className="pl-9 w-full"
                    />
                  </div>
                </div>
              )}

              {/* Current Members */}
              {filteredMembers.length > 0 && (
                <div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-neutral-200 bg-neutral-50">
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Name</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Email</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Status</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Role</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedMembers.map((member, index) => (
                          <tr key={member.id} className={`border-b border-neutral-100 hover:bg-neutral-50 ${index === paginatedMembers.length - 1 ? 'border-b-0' : ''}`}>
                            <td className="py-4 px-6">
                              <div className="flex items-center gap-3">
                                <span className="font-medium text-neutral-900">
                                  {member.name}
                                  {member.is_current_user && (
                                    <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">You</span>
                                  )}
                                </span>
                              </div>
                            </td>
                            <td className="py-4 px-6">
                              <span className="text-sm text-neutral-600">{member.email}</span>
                            </td>
                            <td className="py-4 px-6">
                              {member.status === 'pending' ? (
                                <span className="inline-block px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">
                                  Pending
                                </span>
                              ) : (
                                <span className="inline-block px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                                  Active
                                </span>
                              )}
                            </td>
                            <td className="py-4 px-6">
                              {member.status === 'pending' ? (
                                <span className="text-xs text-neutral-500 capitalize">
                                  {member.role?.replace('_', ' ') || 'member'}
                                </span>
                              ) : member.is_current_user ? (
                                <span className="inline-block px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-800 capitalize">
                                  {member.role?.replace('_', ' ') || 'member'}
                                </span>
                              ) : (
                                <div className="relative group">
                                  <select
                                    value={member.role || 'member'}
                                    onChange={(e) => onRoleChange(member.id as number, e.target.value)}
                                    className="text-xs px-2 py-1 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white disabled:opacity-60 disabled:cursor-not-allowed"
                                    disabled={userInfo?.role !== 'admin'}
                                  >
                                    <option value="member">Member</option>
                                    <option value="admin">Admin</option>
                                  </select>
                                  {userInfo?.role !== 'admin' && (
                                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-neutral-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                      Only admins can change roles
                                    </div>
                                  )}
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Pagination Controls */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200">
                      <p className="text-sm text-neutral-600">
                        Showing {startIndex + 1}-{Math.min(startIndex + TEAM_MEMBERS_PER_PAGE, filteredMembers.length)} of {filteredMembers.length}
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                          disabled={currentPage === 1}
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-sm text-neutral-600 px-3">
                          Page {currentPage} of {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                          disabled={currentPage === totalPages}
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Pending Invitations */}
              {pendingInvitations.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3 flex items-center space-x-2">
                    <Mail className="w-5 h-5" />
                    <span>Pending Invitations ({pendingInvitations.length})</span>
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-neutral-200 bg-neutral-50">
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Email</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Role</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Invited By</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Sent</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Expires</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pendingInvitations.map((invitation, index) => (
                          <tr key={invitation.id} className={`border-b border-neutral-100 hover:bg-neutral-50 bg-yellow-50 ${index === pendingInvitations.length - 1 ? 'border-b-0' : ''}`}>
                            <td className="py-4 px-6">
                              <span className="text-sm font-medium text-neutral-900">{invitation.email}</span>
                            </td>
                            <td className="py-4 px-6">
                              <span className="inline-block px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 capitalize">
                                {invitation.role?.replace('_', ' ') || 'member'}
                              </span>
                            </td>
                            <td className="py-4 px-6">
                              <span className="text-sm text-neutral-600">{invitation.invited_by?.name || 'Unknown'}</span>
                            </td>
                            <td className="py-4 px-6">
                              <span className="text-xs text-neutral-500">{new Date(invitation.created_at).toLocaleDateString()}</span>
                            </td>
                            <td className="py-4 px-6">
                              <span className="text-xs text-neutral-500">
                                {invitation.is_expired ? (
                                  <span className="text-red-600">Expired</span>
                                ) : (
                                  new Date(invitation.expires_at).toLocaleDateString()
                                )}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Empty State - No results from search */}
              {filteredMembers.length === 0 && orgMembers.length > 0 && (
                <div className="text-center py-8 text-neutral-500">
                  <p>No members found matching your search</p>
                </div>
              )}

              {/* Empty State - No members at all */}
              {!loadingOrgData && orgMembers.length === 0 && pendingInvitations.length === 0 && (
                <div className="text-center py-8 text-neutral-500">
                  <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No organization members or pending invitations found</p>
                  <p className="text-sm mt-1">Start by inviting team members above</p>
                </div>
              )}
            </div>
          )}
        </div>

      {!asInlineView && (
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
        </DialogFooter>
      )}
    </>
  )

  // If inline view, render content without Dialog wrapper
  if (asInlineView) {
    return (
      <>
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold">
            {title}
          </h2>
          <p className="text-sm text-neutral-600 mt-1">
            {subtitle}
          </p>
        </div>

        {/* Content */}
        {dialogContentBody}
      </>
    )
  }

  // Original modal rendering
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Users className="w-5 h-5" />
            <span>{title}</span>
          </DialogTitle>
          <DialogDescription>
            {subtitle}
          </DialogDescription>
        </DialogHeader>

        {dialogContentBody}
      </DialogContent>
    </Dialog>
  )
}
