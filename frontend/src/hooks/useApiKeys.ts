"use client"

import { useState, useEffect, useCallback } from "react"
import { toast } from "sonner"
import { ApiKey, CreateApiKeyRequest, CreateApiKeyResponse } from "@/types/apiKey"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function useApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem("auth_token")
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    }
  }, [])

  const fetchKeys = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/api/api-keys`, {
        headers: getAuthHeaders(),
      })
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Please sign in to view API keys")
        }
        throw new Error("Failed to fetch API keys")
      }
      const data = await response.json()
      setKeys(data.keys || [])
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load API keys"
      setError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }, [getAuthHeaders])

  const createKey = useCallback(async (request: CreateApiKeyRequest): Promise<CreateApiKeyResponse | null> => {
    try {
      const response = await fetch(`${API_BASE}/api/api-keys`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(request),
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || "Failed to create API key")
      }
      const newKey = await response.json()
      await fetchKeys()  // Refresh list
      toast.success("API key created successfully")
      return newKey
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create API key"
      toast.error(message)
      return null
    }
  }, [getAuthHeaders, fetchKeys])

  const revokeKey = useCallback(async (keyId: number): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/api/api-keys/${keyId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || "Failed to revoke API key")
      }
      await fetchKeys()  // Refresh list
      toast.success("API key revoked successfully")
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to revoke API key"
      toast.error(message)
      return false
    }
  }, [getAuthHeaders, fetchKeys])

  useEffect(() => {
    fetchKeys()
  }, [fetchKeys])

  return {
    keys,
    loading,
    error,
    fetchKeys,
    createKey,
    revokeKey,
  }
}
