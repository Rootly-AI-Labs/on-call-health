"use client";

import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { HelpCircle, ChevronDown, CheckCircle, AlertCircle, Loader2, Eye, EyeOff, ExternalLink } from "lucide-react";
import { UseFormReturn } from "react-hook-form";
import { useValidation } from "../hooks/useValidation";
import { StatusIndicator } from "./StatusIndicator";

interface JiraManualSetupFormData {
  siteUrl: string;
  email: string;
  token: string;
}

interface JiraManualSetupFormProps {
  form: UseFormReturn<JiraManualSetupFormData>;
  onSave: (data: { token: string; siteUrl: string; email: string; userInfo?: { displayName: string | null; email: string | null } }) => Promise<boolean>;
  onClose: () => void;
}

export function JiraManualSetupForm({ form, onSave, onClose }: JiraManualSetupFormProps) {
  const [showInstructions, setShowInstructions] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const saveAttempted = useRef(false);

  const {
    status,
    error,
    errorType,
    helpUrl,
    actionHint,
    userInfo,
    validateToken,
    isValidating,
    isConnected,
    hasError,
  } = useValidation({ provider: "jira" });

  const tokenValue = form.watch("token");
  const siteUrlValue = form.watch("siteUrl");
  const emailValue = form.watch("email");

  // Auto-validate when token, siteUrl, and email are all provided
  useEffect(() => {
    if (tokenValue && tokenValue.trim() && siteUrlValue && siteUrlValue.trim() && emailValue && emailValue.trim()) {
      validateToken({ token: tokenValue, siteUrl: siteUrlValue, email: emailValue });
    }
  }, [tokenValue, siteUrlValue, emailValue, validateToken]);

  // Reset save attempt flag when inputs change
  useEffect(() => {
    saveAttempted.current = false;
  }, [tokenValue, siteUrlValue, emailValue]);

  // Auto-save when validation succeeds
  useEffect(() => {
    const hasValidInputs = tokenValue && tokenValue.trim() && siteUrlValue && siteUrlValue.trim() && emailValue && emailValue.trim();
    const shouldSave = hasValidInputs && isConnected && userInfo && !isSaving && !saveAttempted.current;

    if (!shouldSave) {
      return;
    }

    saveAttempted.current = true;
    setIsSaving(true);

    onSave({ token: tokenValue, siteUrl: siteUrlValue, email: emailValue, userInfo })
      .then((success) => {
        if (success) {
          toast.success("Jira connected!", { duration: 3000 });
          onClose();
        } else {
          saveAttempted.current = false;
        }
      })
      .catch(() => {
        toast.error("Failed to save integration");
        saveAttempted.current = false;
      })
      .finally(() => {
        setIsSaving(false);
      });
  }, [isConnected, userInfo, isSaving, tokenValue, siteUrlValue, emailValue, onSave, onClose]);

  return (
    <Card className="border-blue-200 max-w-2xl mx-auto">
      <CardHeader className="p-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-6 h-6" fill="#0052CC">
              <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005zm5.723-5.756H5.736a5.215 5.215 0 0 0 5.215 5.214h2.129v2.058a5.218 5.218 0 0 0 5.215 5.232V6.758a1.001 1.001 0 0 0-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 0 0 5.215 5.215h2.129v2.057A5.215 5.215 0 0 0 24 12.483V1.005A1.001 1.001 0 0 0 23.013 0Z"/>
            </svg>
          </div>
          <div className="flex-1">
            <CardTitle>Connect Jira with API Token</CardTitle>
          </div>
          <StatusIndicator status={status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-8 pt-0">
        {/* Instructions */}
        <div>
          <button
            type="button"
            onClick={() => setShowInstructions(!showInstructions)}
            className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700"
          >
            <HelpCircle className="w-4 h-4" />
            <span>How to get your Jira API token</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showInstructions ? "rotate-180" : ""}`} />
          </button>
          {showInstructions && (
            <div className="mt-4">
              <Alert className="border-blue-200 bg-blue-50">
                <AlertDescription>
                  <a
                    href="https://id.atlassian.com/manage-profile/security/api-tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center text-blue-600 hover:text-blue-700"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Create your API token at Atlassian
                  </a>
                </AlertDescription>
              </Alert>
            </div>
          )}
        </div>

        {/* Form */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(() => {})} className="space-y-4">
            <FormField
              control={form.control}
              name="siteUrl"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Jira Site URL</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="url"
                      placeholder="https://your-company.atlassian.net"
                    />
                  </FormControl>
                  <FormDescription>
                    Your Atlassian site URL (e.g., https://acme.atlassian.net)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Atlassian Account Email</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="email"
                      placeholder="you@company.com"
                    />
                  </FormControl>
                  <FormDescription>
                    The email address associated with your Atlassian account
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="token"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Token</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        {...field}
                        type={showToken ? "text" : "password"}
                        placeholder="Enter your Jira API token"
                        className="pr-10"
                        onChange={(e) => field.onChange(e.target.value.trim())}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute inset-y-0 right-0 h-full px-3"
                        onClick={() => setShowToken(!showToken)}
                      >
                        {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Validating Status */}
            {isValidating && (
              <Alert className="border-blue-200 bg-blue-50">
                <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
                <AlertDescription className="text-blue-800">
                  Validating token and checking permissions...
                </AlertDescription>
              </Alert>
            )}

            {/* Success Status */}
            {isConnected && userInfo && (
              <Alert className="border-green-200 bg-green-50">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  <div className="space-y-2">
                    <p className="font-semibold">
                      {isSaving ? "Saving..." : "Token validated!"}
                    </p>
                    <div className="space-y-1 text-sm">
                      {userInfo.displayName && <p><span className="font-medium">Name:</span> {userInfo.displayName}</p>}
                      {userInfo.email && <p><span className="font-medium">Email:</span> {userInfo.email}</p>}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Error Status */}
            {hasError && error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2">
                    <p className="font-semibold">{error}</p>
                    {actionHint && <p className="text-sm">{actionHint}</p>}
                    {helpUrl && (
                      <a
                        href={helpUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center text-sm text-red-700 underline"
                      >
                        <ExternalLink className="w-3 h-3 mr-1" />
                        View documentation
                      </a>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
