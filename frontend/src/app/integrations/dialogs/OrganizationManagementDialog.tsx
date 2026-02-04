import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Users, Mail, Loader2, Check, X, Building2, AlertCircle } from "lucide-react"
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

        // Close modal and refresh page to reflect new org membership
        onClose()
        setTimeout(() => {
          window.location.reload()
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
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
            <div className="p-6 border-2 border-blue-200 rounded-lg bg-blue-50">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1 space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-blue-900">You Have Pending Invitations!</h3>
                    <p className="text-sm text-blue-700 mt-1">You've been invited to join {receivedInvitations.length === 1 ? 'an organization' : `${receivedInvitations.length} organizations`}</p>
                  </div>

                  <div className="space-y-3">
                    {receivedInvitations.map((invitation) => (
                      <div key={invitation.id} className="bg-white rounded-lg p-4 border border-blue-200">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-semibold text-neutral-900">{invitation.organization_name}</h4>
                            <p className="text-sm text-neutral-600 mt-1">
                              Invited by {invitation.invited_by?.name || 'Unknown'} as <span className="font-medium capitalize">{invitation.role}</span>
                            </p>
                            <p className="text-xs text-neutral-500 mt-1">
                              Sent {new Date(invitation.created_at).toLocaleDateString()} • Expires {new Date(invitation.expires_at).toLocaleDateString()}
                            </p>

                            {/* Warning when confirming org switch */}
                            {confirmingInvitationId === invitation.id && userInfo?.organization_id && (
                              <Alert className="mt-3 bg-amber-50 border-amber-200">
                                <AlertCircle className="h-4 w-4 text-amber-600" />
                                <AlertDescription className="text-amber-900 text-xs">
                                  <strong>Warning:</strong> You will leave your current organization and join {invitation.organization_name}.
                                </AlertDescription>
                              </Alert>
                            )}
                          </div>
                          <div className="flex items-center space-x-2 ml-4">
                            {confirmingInvitationId === invitation.id ? (
                              <>
                                <Button
                                  size="sm"
                                  onClick={() => handleAcceptInvitation(invitation.id, true)}
                                  disabled={processingInvitationId !== null}
                                  className="bg-red-600 hover:bg-red-700 text-white"
                                >
                                  {processingInvitationId === invitation.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <>
                                      <Check className="w-4 h-4 mr-1" />
                                      Confirm
                                    </>
                                  )}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
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
                                  onClick={() => handleAcceptInvitation(invitation.id)}
                                  disabled={processingInvitationId !== null}
                                  className="bg-green-600 hover:bg-green-700 text-white"
                                >
                                  {processingInvitationId === invitation.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <>
                                      <Check className="w-4 h-4 mr-1" />
                                      Accept
                                    </>
                                  )}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleRejectInvitation(invitation.id)}
                                  disabled={processingInvitationId !== null}
                                  className="border-red-300 text-red-600 hover:bg-red-50"
                                >
                                  {processingInvitationId === invitation.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <>
                                      <X className="w-4 h-4 mr-1" />
                                      Decline
                                    </>
                                  )}
                                </Button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
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
              {orgMembers.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3 flex items-center space-x-2">
                    <Users className="w-5 h-5" />
                    <span>Organization Members ({orgMembers.length})</span>
                  </h3>
                  <div className="border rounded-lg overflow-hidden">
                    <div className="bg-neutral-100 px-4 py-2 border-b">
                      <div className="grid grid-cols-4 gap-4 text-sm font-medium text-neutral-700">
                        <div>Name</div>
                        <div>Email</div>
                        <div>Status</div>
                        <div>Role</div>
                      </div>
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                      {orgMembers.map((member) => (
                        <div key={member.id} className={`px-4 py-3 border-b last:border-b-0 hover:bg-neutral-100 ${member.status === 'pending' ? 'bg-yellow-50' : 'bg-white'}`}>
                          <div className="grid grid-cols-4 gap-4 text-sm items-center">
                            <div className="font-medium text-neutral-900">
                              {member.name}
                              {member.is_current_user && (
                                <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">You</span>
                              )}
                            </div>
                            <div className="text-neutral-700">{member.email}</div>
                            <div>
                              {member.status === 'pending' ? (
                                <span className="inline-block px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">
                                  Pending
                                </span>
                              ) : (
                                <span className="inline-block px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                                  Active
                                </span>
                              )}
                            </div>
                            <div>
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
