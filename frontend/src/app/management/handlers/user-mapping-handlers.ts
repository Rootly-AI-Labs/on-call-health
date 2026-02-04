import { API_BASE } from "@/app/integrations/types"
import { toast } from "sonner"

/**
 * Update user correlation mappings
 */
export async function updateUserCorrelation(
  userId: number,
  updates: {
    github_username?: string
    jira_account_id?: string
    linear_user_id?: string
  }
): Promise<boolean> {
  const authToken = localStorage.getItem("auth_token")
  if (!authToken) {
    toast.error("Please log in")
    return false
  }

  try {
    const response = await fetch(
      `${API_BASE}/rootly/user-correlation/${userId}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updates),
      }
    )

    if (response.ok) {
      return true
    } else {
      const error = await response.json()
      toast.error(error.detail || "Failed to update mappings")
      return false
    }
  } catch (error) {
    console.error("Error updating user correlation:", error)
    toast.error("Error updating mappings")
    return false
  }
}

/**
 * Fetch available GitHub users from organization
 */
export async function fetchGithubUsers(
  organizationId: string
): Promise<string[]> {
  const authToken = localStorage.getItem("auth_token")
  if (!authToken) return []

  try {
    const response = await fetch(
      `${API_BASE}/rootly/integrations/${organizationId}/github-members`,
      {
        headers: { Authorization: `Bearer ${authToken}` },
      }
    )

    if (response.ok) {
      const data = await response.json()
      return data.members || []
    }
    return []
  } catch (error) {
    console.error("Error fetching GitHub users:", error)
    return []
  }
}

/**
 * Fetch available Jira users from integration
 */
export async function fetchJiraUsers(
  integrationId: string
): Promise<any[]> {
  const authToken = localStorage.getItem("auth_token")
  if (!authToken) return []

  try {
    const response = await fetch(
      `${API_BASE}/rootly/integrations/${integrationId}/jira-users`,
      {
        headers: { Authorization: `Bearer ${authToken}` },
      }
    )

    if (response.ok) {
      const data = await response.json()
      return data.users || []
    }
    return []
  } catch (error) {
    console.error("Error fetching Jira users:", error)
    return []
  }
}

/**
 * Fetch available Linear users from integration
 */
export async function fetchLinearUsers(
  integrationId: string
): Promise<any[]> {
  const authToken = localStorage.getItem("auth_token")
  if (!authToken) return []

  try {
    const response = await fetch(
      `${API_BASE}/rootly/integrations/${integrationId}/linear-users`,
      {
        headers: { Authorization: `Bearer ${authToken}` },
      }
    )

    if (response.ok) {
      const data = await response.json()
      return data.users || []
    }
    return []
  } catch (error) {
    console.error("Error fetching Linear users:", error)
    return []
  }
}
