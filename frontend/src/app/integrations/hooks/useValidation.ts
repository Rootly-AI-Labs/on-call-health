"use client";

import { useState, useCallback, useRef } from "react";
import type { ValidationState, ValidationResult, ValidationErrorType } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UseValidationOptions {
  provider: "jira" | "linear";
  debounceMs?: number;
}

interface ValidateTokenParams {
  token: string;
  siteUrl?: string; // Required for Jira
}

export function useValidation({ provider, debounceMs = 500 }: UseValidationOptions) {
  const [state, setState] = useState<ValidationState>({
    status: "disconnected",
    error: null,
    errorType: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const validateToken = useCallback(
    async ({ token, siteUrl }: ValidateTokenParams): Promise<ValidationResult> => {
      // Cancel any pending validation
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Empty token = disconnected, not error
      if (!token || !token.trim()) {
        setState({
          status: "disconnected",
          error: null,
          errorType: null,
        });
        return { valid: false, error: "Token is required", error_type: "format" };
      }

      // For Jira, site URL is required
      if (provider === "jira" && (!siteUrl || !siteUrl.trim())) {
        setState({
          status: "error",
          error: "Jira site URL is required",
          errorType: "site_url",
        });
        return { valid: false, error: "Jira site URL is required", error_type: "site_url" };
      }

      // Set validating state
      setState({
        status: "validating",
        error: null,
        errorType: null,
      });

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();

      return new Promise((resolve) => {
        debounceTimerRef.current = setTimeout(async () => {
          try {
            const endpoint = `${API_BASE}/integrations/${provider}/validate-token`;
            const body = provider === "jira"
              ? { token, site_url: siteUrl }
              : { token };

            const authToken = localStorage.getItem('auth_token');
            const response = await fetch(endpoint, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                ...(authToken && { "Authorization": `Bearer ${authToken}` }),
              },
              credentials: "include",
              signal: abortControllerRef.current?.signal,
              body: JSON.stringify(body),
            });

            if (!response.ok) {
              // Try to parse error response from backend
              try {
                const errorResult = await response.json();
                setState({
                  status: "error",
                  error: errorResult.error || `HTTP ${response.status}`,
                  errorType: errorResult.error_type || "unknown",
                });
                resolve({
                  valid: false,
                  error: errorResult.error || `HTTP ${response.status}`,
                  error_type: errorResult.error_type || "unknown",
                });
                return;
              } catch {
                // If JSON parsing fails, treat as unknown error
                const error = `Server error: HTTP ${response.status}`;
                setState({
                  status: "error",
                  error,
                  errorType: "unknown",
                });
                resolve({ valid: false, error, error_type: "unknown" });
                return;
              }
            }

            const result: ValidationResult = await response.json();

            if (result.valid) {
              setState({
                status: "connected",
                error: null,
                errorType: null,
                userInfo: result.user_info ? {
                  displayName: result.user_info.display_name,
                  email: result.user_info.email,
                } : undefined,
              });
            } else {
              setState({
                status: "error",
                error: result.error,
                errorType: result.error_type as ValidationErrorType,
                helpUrl: result.help_url,
                actionHint: result.action,
              });
            }

            resolve(result);
          } catch (error) {
            if (error instanceof Error && error.name === "AbortError") {
              // Request was cancelled, don't update state
              resolve({ valid: false, error: "Cancelled", error_type: null });
              return;
            }

            // Network or parsing error
            const errorMessage = error instanceof Error ? error.message : "Network error";
            setState({
              status: "error",
              error: `Failed to validate token: ${errorMessage}`,
              errorType: "network",
            });

            resolve({
              valid: false,
              error: `Failed to validate token: ${errorMessage}`,
              error_type: "network",
            });
          }
        }, debounceMs);
      });
    },
    [provider, debounceMs]
  );

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setState({
      status: "disconnected",
      error: null,
      errorType: null,
    });
  }, []);

  const setConnected = useCallback((userInfo?: { displayName: string | null; email: string | null }) => {
    setState({
      status: "connected",
      error: null,
      errorType: null,
      userInfo,
    });
  }, []);

  return {
    ...state,
    validateToken,
    reset,
    setConnected,
    isValidating: state.status === "validating",
    isConnected: state.status === "connected",
    hasError: state.status === "error",
  };
}
