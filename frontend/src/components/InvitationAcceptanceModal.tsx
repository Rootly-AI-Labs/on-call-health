"use client"

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle, AlertCircle, Loader2, Building2, Users, Mail } from 'lucide-react'
import { toast } from 'sonner'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Invitation {
  id: number
  organization_id: number
  email: string
  role: string
  status: string
  created_at: string
  expires_at?: string
  organization_name: string
}

interface InvitationAcceptanceModalProps {
  invitationId: number | null
  isOpen: boolean
  onClose: () => void
  onAccepted?: () => void
}

export function InvitationAcceptanceModal({
  invitationId,
  isOpen,
  onClose,
  onAccepted
}: InvitationAcceptanceModalProps) {
  const [invitation, setInvitation] = useState<Invitation | null>(null)
  const [loading, setLoading] = useState(false)
  const [accepting, setAccepting] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentOrgName, setCurrentOrgName] = useState<string | null>(null)
  const [showOrgSwitchWarning, setShowOrgSwitchWarning] = useState(false)

  useEffect(() => {
    if (isOpen && invitationId) {
      fetchInvitation()
      checkCurrentOrganization()
    }
  }, [isOpen, invitationId])

  const checkCurrentOrganization = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) return

      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const userData = await response.json()
        if (userData.organization_id) {
          // User is already in an organization
          const orgName = localStorage.getItem('user_organization_name') || 'your current organization'
          setCurrentOrgName(orgName)
        }
      }
    } catch (error) {
      console.error('Error checking current organization:', error)
    }
  }

  const fetchInvitation = async () => {
    if (!invitationId) return

    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/api/invitations/${invitationId}`)

      if (!response.ok) {
        throw new Error('Invitation not found')
      }

      const data = await response.json()
      setInvitation(data.invitation)

      if (!data.is_pending) {
        if (data.is_expired) {
          setError('This invitation has expired')
        } else if (data.invitation.status === 'accepted') {
          setError('This invitation has already been accepted')
        } else {
          setError('This invitation is no longer valid')
        }
      }
    } catch (error) {
      console.error('Error fetching invitation:', error)
      setError('Failed to load invitation details')
    } finally {
      setLoading(false)
    }
  }

  const handleAccept = async () => {
    if (!invitation) return

    // If user has a current org and hasn't confirmed, show warning
    if (currentOrgName && !showOrgSwitchWarning) {
      setShowOrgSwitchWarning(true)
      return
    }

    setAccepting(true)
    setError(null)

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_BASE}/api/invitations/accept/${invitation.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to accept invitation')
      }

      if (data.success) {
        const message = data.left_organization
          ? `You have left ${data.left_organization.name} and joined ${invitation.organization_name}`
          : `Welcome to ${invitation.organization_name}!`

        toast.success(message, {
          description: `You've successfully joined as a ${invitation.role}.`,
          duration: 4000,
        })

        // Update local storage with new role/org
        if (data.organization) {
          localStorage.setItem('user_organization_id', data.organization.id)
          localStorage.setItem('user_organization_name', data.organization.name)
        }
        if (data.role) {
          localStorage.setItem('user_role', data.role)
        }

        onAccepted?.()
        onClose()

        // Redirect to integrations page after short delay
        setTimeout(() => {
          window.location.href = '/integrations'
        }, 500)
      }
    } catch (error: any) {
      console.error('Error accepting invitation:', error)
      setError(error.message || 'Failed to accept invitation')
      toast.error(error.message || 'Failed to accept invitation')
    } finally {
      setAccepting(false)
    }
  }

  const handleReject = async () => {
    if (!invitation) return

    setRejecting(true)
    setError(null)

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_BASE}/api/invitations/reject/${invitation.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to reject invitation')
      }

      if (data.success) {
        toast.info('Invitation declined')
        onClose()
      }
    } catch (error: any) {
      console.error('Error rejecting invitation:', error)
      setError(error.message || 'Failed to reject invitation')
      toast.error(error.message || 'Failed to reject invitation')
    } finally {
      setRejecting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Building2 className="w-5 h-5" />
            <span>Organization Invitation</span>
          </DialogTitle>
          <DialogDescription>
            You've been invited to join an organization
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-neutral-500" />
            <span className="ml-3 text-neutral-700">Loading invitation...</span>
          </div>
        ) : error ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : invitation ? (
          <div className="space-y-6">
            <div className="text-center space-y-3">
              <h3 className="text-lg font-semibold text-neutral-900">
                You're invited to join
              </h3>
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="flex items-center justify-center space-x-2 mb-2">
                  <Building2 className="h-5 w-5 text-slate-600" />
                  <span className="text-lg font-medium">{invitation.organization_name}</span>
                </div>
                <div className="flex items-center justify-center space-x-4 text-sm text-slate-600">
                  <div className="flex items-center space-x-1">
                    <Users className="h-4 w-4" />
                    <span>Role: {invitation.role}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Mail className="h-4 w-4" />
                    <span>{invitation.email}</span>
                  </div>
                </div>
              </div>
            </div>

            {invitation.expires_at && (
              <div className="text-center text-sm text-neutral-500">
                <p>This invitation expires on {new Date(invitation.expires_at).toLocaleDateString()}</p>
              </div>
            )}

            {currentOrgName && showOrgSwitchWarning && (
              <Alert className="bg-amber-50 border-amber-200">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <AlertDescription className="text-amber-900">
                  <strong>Warning:</strong> You are currently a member of <strong>{currentOrgName}</strong>.
                  <br /><br />
                  By accepting this invitation, you will leave {currentOrgName} and join {invitation.organization_name}.
                  <br /><br />
                  All your data (analyses and integrations) will be kept.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex space-x-3">
              <Button
                onClick={handleAccept}
                disabled={accepting || rejecting}
                className="flex-1"
                variant={showOrgSwitchWarning ? "destructive" : "default"}
              >
                {accepting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Accepting...
                  </>
                ) : showOrgSwitchWarning ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Confirm & Accept
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Accept
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={showOrgSwitchWarning ? () => setShowOrgSwitchWarning(false) : handleReject}
                disabled={accepting || rejecting}
                className="flex-1"
              >
                {rejecting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Declining...
                  </>
                ) : showOrgSwitchWarning ? (
                  'Cancel'
                ) : (
                  'Decline'
                )}
              </Button>
            </div>

            <div className="text-center">
              <p className="text-xs text-neutral-500">
                By accepting this invitation, you'll join the organization and gain access to team health analytics and integrations.
              </p>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
