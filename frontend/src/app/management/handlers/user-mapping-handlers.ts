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
    jira_email?: string
    linear_user_id?: string
  }
): Promise<boolean> {
  const authToken = localStorage.getItem("auth_token")
  if (!authToken) {
    toast.error("Please log in")
    return false
  }

  try {
    // Update each integration field with separate PATCH requests
    const promises: Promise<Response>[] = []

    if (updates.github_username !== undefined) {
      promises.push(
        fetch(
          `${API_BASE}/rootly/user-correlation/${userId}/github-username?github_username=${encodeURIComponent(updates.github_username)}`,
          {
            method: "PATCH",
            headers: { Authorization: `Bearer ${authToken}` },
          }
        )
      )
    }

    if (updates.jira_account_id !== undefined) {
      const params = new URLSearchParams()
      params.append("jira_account_id", updates.jira_account_id)
      if (updates.jira_email) {
        params.append("jira_email", updates.jira_email)
      }
      promises.push(
        fetch(
          `${API_BASE}/rootly/user-correlation/${userId}/jira-mapping?${params}`,
          {
            method: "PATCH",
            headers: { Authorization: `Bearer ${authToken}` },
          }
        )
      )
    }

    if (updates.linear_user_id !== undefined) {
      promises.push(
        fetch(
          `${API_BASE}/rootly/user-correlation/${userId}/linear-mapping?linear_user_id=${encodeURIComponent(updates.linear_user_id)}`,
          {
            method: "PATCH",
            headers: { Authorization: `Bearer ${authToken}` },
          }
        )
      )
    }

    // Wait for all requests to complete
    const responses = await Promise.all(promises)

    // Check if all responses are OK
    for (const response of responses) {
      if (!response.ok) {
        const error = await response.json()
        toast.error(error.detail || "Failed to update mappings")
        return false
      }
    }

    return true
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
      `${API_BASE}/integrations/github/org-members`,
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
      `${API_BASE}/integrations/jira/jira-users`,
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
      `${API_BASE}/integrations/linear/linear-users`,
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
