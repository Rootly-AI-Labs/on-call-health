import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Users, Mail, Loader2, Check, X, Building2, AlertCircle, Trash2 } from "lucide-react"
import { UserInfo } from "../types"
import { useState } from "react"
import { toast } from "sonner"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface OrganizationMember {
  id: number | string
  invitation_id?: number
  name: string
  email: string
  role: string
  is_super_admin?: boolean
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

interface ReceivedInvitation {
  id: number
  organization_id: number
  organization_name: string
  email: string
  role: string
  status: string
  created_at: string
  expires_at: string
  invited_by: { name: string } | null
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
  receivedInvitations: ReceivedInvitation[]
  userInfo: UserInfo | null
  onRoleChange: (userId: number, newRole: string) => void
  onRefreshOrgData: () => Promise<void>
  onClose: () => void
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
  receivedInvitations,
  userInfo,
  onRoleChange,
  onRefreshOrgData,
  onClose
}: OrganizationManagementDialogProps) {
  const [processingInvitationId, setProcessingInvitationId] = useState<number | null>(null)
  const [confirmingInvitationId, setConfirmingInvitationId] = useState<number | null>(null)
  const [removingUserId, setRemovingUserId] = useState<number | null>(null)
  const [confirmRemoveUserId, setConfirmRemoveUserId] = useState<number | null>(null)
  const [transferringSuperAdmin, setTransferringSuperAdmin] = useState<number | null>(null)
  const [confirmTransferSuperAdmin, setConfirmTransferSuperAdmin] = useState<number | null>(null)

  const handleAcceptInvitation = async (invitationId: number, skipWarning = false) => {
    // Check if user is already in an org and show warning first
    if (!skipWarning && userInfo?.organization_id) {
      setConfirmingInvitationId(invitationId)
      return
    }

    setProcessingInvitationId(invitationId)
    setConfirmingInvitationId(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_BASE}/api/invitations/accept/${invitationId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to accept invitation')
      }

      const data = await response.json()

      if (data.success) {
        toast.success(data.message || 'Successfully joined organization!')

        // Update localStorage if org info returned
        if (data.organization) {
          localStorage.setItem('user_organization_id', data.organization.id)
          localStorage.setItem('user_organization_name', data.organization.name)
        }
        if (data.role) {
          localStorage.setItem('user_role', data.role)
        }

        // Reload page with modal open to reflect new org membership
        setTimeout(() => {
          window.location.href = '/integrations?openOrgModal=true'
        }, 500)
      }
    } catch (error: any) {
      console.error('Error accepting invitation:', error)
      toast.error(error.message || 'Failed to accept invitation')
    } finally {
      setProcessingInvitationId(null)
    }
  }

  const handleRejectInvitation = async (invitationId: number) => {
    setProcessingInvitationId(invitationId)
    setConfirmingInvitationId(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_BASE}/api/invitations/reject/${invitationId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to reject invitation')
      }

      const data = await response.json()

      if (data.success) {
        toast.info('Invitation declined')
        await onRefreshOrgData()
      }
    } catch (error: any) {
      console.error('Error rejecting invitation:', error)
      toast.error(error.message || 'Failed to reject invitation')
    } finally {
      setProcessingInvitationId(null)
    }
  }

  const handleRemoveMember = async (userId: number, userName: string) => {
    setRemovingUserId(userId)
    setConfirmRemoveUserId(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_BASE}/auth/organizations/members/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to remove member')
      }

      const data = await response.json()

      if (data.success) {
        toast.success(`${userName} has been removed from the organization`)
        await onRefreshOrgData()
      }
    } catch (error: any) {
      console.error('Error removing member:', error)
      toast.error(error.message || 'Failed to remove member')
    } finally {
      setRemovingUserId(null)
    }
  }

  const handleTransferSuperAdmin = async (userId: number, userName: string) => {
    setTransferringSuperAdmin(userId)
    setConfirmTransferSuperAdmin(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_BASE}/auth/organizations/transfer-super-admin`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ target_user_id: userId })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to transfer super admin status')
      }

      const data = await response.json()
      toast.success(`${userName} is now a super admin`)
      await onRefreshOrgData()
    } catch (error: any) {
      console.error('Error promoting to super admin:', error)
      toast.error(error.message || 'Failed to promote to super admin')
    } finally {
      setTransferringSuperAdmin(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Users className="w-5 h-5" />
            <span>Organization Management</span>
          </DialogTitle>
          <DialogDescription>
            Invite new members and manage your organization
          </DialogDescription>
        </DialogHeader>

        {/* Role descriptions - at the top of modal */}
        <div className="mt-4 px-4 py-3 bg-purple-100 rounded-lg">
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
          {/* Received Invitations - Show at top if user has any */}
          {receivedInvitations.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 px-1">
                <Mail className="w-4 h-4 text-neutral-500" />
                <h3 className="text-sm font-medium text-neutral-700">
                  Pending Invitation{receivedInvitations.length > 1 ? 's' : ''}
                </h3>
              </div>

              <div className="space-y-2">
                {receivedInvitations.map((invitation) => (
                  <div key={invitation.id} className="group relative rounded-lg border border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-sm transition-all">
                    <div className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium text-neutral-900 truncate">{invitation.organization_name}</h4>
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize">
                              {invitation.role}
                            </span>
                          </div>
                          <p className="text-sm text-neutral-600">
                            From {invitation.invited_by?.name || 'Unknown'}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1">
                            Expires {new Date(invitation.expires_at).toLocaleDateString()}
                          </p>

                          {/* Warning when confirming org switch */}
                          {confirmingInvitationId === invitation.id && userInfo?.organization_id && (
                            <div className="mt-3 flex items-start gap-2 p-3 rounded-md bg-amber-50 border border-amber-200">
                              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                              <p className="text-xs text-amber-900">
                                You will leave your current organization to join <span className="font-medium">{invitation.organization_name}</span>
                              </p>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {confirmingInvitationId === invitation.id ? (
                            <>
                              <Button
                                size="sm"
                                onClick={() => handleAcceptInvitation(invitation.id, true)}
                                disabled={processingInvitationId !== null}
                                className="bg-neutral-900 hover:bg-neutral-800 text-white"
                              >
                                {processingInvitationId === invitation.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Confirm'
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setConfirmingInvitationId(null)}
                                disabled={processingInvitationId !== null}
                              >
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleRejectInvitation(invitation.id)}
                                disabled={processingInvitationId !== null}
                                className="text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100"
                              >
                                {processingInvitationId === invitation.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Decline'
                                )}
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleAcceptInvitation(invitation.id)}
                                disabled={processingInvitationId !== null}
                                className="bg-neutral-900 hover:bg-neutral-800 text-white"
                              >
                                {processingInvitationId === invitation.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Accept'
                                )}
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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
              {/* Current Members */}
              {orgMembers.filter(m => m.status === 'active').length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3 flex items-center space-x-2">
                    <Users className="w-5 h-5" />
                    <span>Organization Members ({orgMembers.filter(m => m.status === 'active').length})</span>
                  </h3>
                  <div className="border rounded-lg overflow-hidden">
                    <div className="bg-neutral-100 px-4 py-2 border-b">
                      <div className="grid grid-cols-4 gap-4 text-sm font-medium text-neutral-700">
                        <div>Name</div>
                        <div>Email</div>
                        <div>Role</div>
                        <div></div>
                      </div>
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                      {orgMembers.filter(m => m.status === 'active').map((member) => (
                        <div key={member.id} className="px-4 py-3 border-b last:border-b-0 hover:bg-neutral-100 bg-white">
                          <div className="grid grid-cols-4 gap-4 text-sm items-center">
                            <div className="font-medium text-neutral-900">
                              {member.name}
                              {member.is_current_user && (
                                <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">You</span>
                              )}
                            </div>
                            <div className="text-neutral-700">{member.email}</div>
                            <div>
                              {member.is_current_user || member.is_super_admin ? (
                                <span className="inline-block px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-800 capitalize">
                                  {member.role?.replace('_', ' ') || 'member'}
                                </span>
                              ) : (
                                <div className="relative group">
                                  <select
                                    value={member.role || 'member'}
                                    onChange={(e) => onRoleChange(member.id as number, e.target.value)}
                                    className="text-xs px-2 py-1 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white disabled:opacity-60 disabled:cursor-not-allowed"
                                    disabled={!['admin', 'super_admin'].includes(userInfo?.role || '')}
                                  >
                                    <option value="member">Member</option>
                                    <option value="admin">Admin</option>
                                  </select>
                                  {!['admin', 'super_admin'].includes(userInfo?.role || '') && (
                                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-neutral-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                      Only admins can change roles
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                            <div className="flex justify-end gap-2">
                              {/* Make Super Admin Button - only visible to current super admin for other admins */}
                              {!member.is_current_user && member.role === 'admin' && !member.is_super_admin && (userInfo as any)?.is_super_admin && (
                                confirmTransferSuperAdmin === member.id ? (
                                  <div className="flex items-center gap-2">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleTransferSuperAdmin(member.id as number, member.name)}
                                      disabled={transferringSuperAdmin !== null}
                                      className="h-7 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                    >
                                      {transferringSuperAdmin === member.id ? (
                                        <Loader2 className="w-3 h-3 animate-spin" />
                                      ) : (
                                        'Confirm'
                                      )}
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => setConfirmTransferSuperAdmin(null)}
                                      disabled={transferringSuperAdmin !== null}
                                      className="h-7 text-xs"
                                    >
                                      Cancel
                                    </Button>
                                  </div>
                                ) : (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setConfirmTransferSuperAdmin(member.id as number)}
                                    disabled={transferringSuperAdmin !== null}
                                    className="h-7 text-xs text-neutral-500 hover:text-amber-600 hover:bg-amber-50"
                                  >
                                    Make Super Admin
                                  </Button>
                                )
                              )}
                              {/* Remove Member Button - cannot remove super admins */}
                              {!member.is_current_user && !member.is_super_admin && ['admin', 'super_admin'].includes(userInfo?.role || '') && (
                                confirmRemoveUserId === member.id ? (
                                  <div className="flex items-center gap-2">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleRemoveMember(member.id as number, member.name)}
                                      disabled={removingUserId !== null}
                                      className="h-7 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                                    >
                                      {removingUserId === member.id ? (
                                        <Loader2 className="w-3 h-3 animate-spin" />
                                      ) : (
                                        'Confirm'
                                      )}
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => setConfirmRemoveUserId(null)}
                                      disabled={removingUserId !== null}
                                      className="h-7 text-xs"
                                    >
                                      Cancel
                                    </Button>
                                  </div>
                                ) : (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setConfirmRemoveUserId(member.id as number)}
                                    disabled={removingUserId !== null}
                                    className="h-7 text-xs text-neutral-500 hover:text-red-600 hover:bg-red-50"
                                  >
                                    <Trash2 className="w-3 h-3 mr-1" />
                                    Remove
                                  </Button>
                                )
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Pending Invitations */}
              {pendingInvitations.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3 flex items-center space-x-2">
                    <Mail className="w-5 h-5" />
                    <span>Pending Invitations ({pendingInvitations.length})</span>
                  </h3>
                  <div className="border rounded-lg overflow-hidden">
                    <div className="bg-neutral-100 px-4 py-2 border-b">
                      <div className="grid grid-cols-5 gap-4 text-sm font-medium text-neutral-700">
                        <div>Email</div>
                        <div>Role</div>
                        <div>Invited By</div>
                        <div>Sent</div>
                        <div>Expires</div>
                      </div>
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                      {pendingInvitations.map((invitation) => (
                        <div key={invitation.id} className="px-4 py-3 border-b last:border-b-0 bg-yellow-50">
                          <div className="grid grid-cols-5 gap-4 text-sm">
                            <div className="font-medium text-neutral-900">{invitation.email}</div>
                            <div>
                              <span className="inline-block px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 capitalize">
                                {invitation.role?.replace('_', ' ') || 'member'}
                              </span>
                            </div>
                            <div className="text-neutral-700">{invitation.invited_by?.name || 'Unknown'}</div>
                            <div className="text-neutral-500 text-xs">
                              {new Date(invitation.created_at).toLocaleDateString()}
                            </div>
                            <div className="text-neutral-500 text-xs">
                              {invitation.is_expired ? (
                                <span className="text-red-600">Expired</span>
                              ) : (
                                new Date(invitation.expires_at).toLocaleDateString()
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Empty State */}
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

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
