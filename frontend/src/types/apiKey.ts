export interface ApiKey {
  id: number
  name: string
  masked_key: string
  created_at: string
  last_used_at: string | null
  expires_at: string | null
}

export interface CreateApiKeyRequest {
  name: string
  expires_at?: string | null
}

export interface CreateApiKeyResponse {
  id: number
  name: string
  key: string  // Full key - shown once only
  last_four: string
  created_at: string
  expires_at: string | null
}

export interface ApiKeysListResponse {
  keys: ApiKey[]
}
