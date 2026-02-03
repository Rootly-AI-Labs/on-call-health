"use client";

import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import Image from "next/image";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { HelpCircle, ChevronDown, CheckCircle, AlertCircle, Loader2, Eye, EyeOff, ExternalLink } from "lucide-react";
import { UseFormReturn } from "react-hook-form";
import { useValidation } from "../hooks/useValidation";
import { StatusIndicator } from "./StatusIndicator";

interface LinearManualSetupFormData {
  token: string;
}

interface LinearManualSetupFormProps {
  form: UseFormReturn<LinearManualSetupFormData>;
  onSave: (data: { token: string; userInfo?: { displayName: string | null; email: string | null } }) => Promise<boolean>;
  onClose: () => void;
}

export function LinearManualSetupForm({ form, onSave, onClose }: LinearManualSetupFormProps) {
  const [showInstructions, setShowInstructions] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const saveAttempted = useRef(false);

  const {
    status,
    error,
    helpUrl,
    actionHint,
    userInfo,
    validateToken,
    isValidating,
    isConnected,
    hasError,
  } = useValidation({ provider: "linear" });

  const tokenValue = form.watch("token");

  // Auto-validate when token is provided
  useEffect(() => {
    if (tokenValue && tokenValue.trim()) {
      validateToken({ token: tokenValue });
    }
  }, [tokenValue, validateToken]);

  // Reset save attempt flag when token changes
  useEffect(() => {
    saveAttempted.current = false;
  }, [tokenValue]);

  // Auto-save when validation succeeds
  useEffect(() => {
    const shouldSave = isConnected && userInfo && !isSaving && !saveAttempted.current;

    if (shouldSave) {
      saveAttempted.current = true;
      handleAutoSave();
    }
  }, [isConnected, userInfo, isSaving]);

  const handleAutoSave = async () => {
    setIsSaving(true);
    try {
      const success = await onSave({
        token: tokenValue,
        userInfo,
      });

      if (success) {
        toast.success("Linear connected!", { duration: 3000 });
        onClose();
      } else {
        // Save failed, allow retry
        saveAttempted.current = false;
      }
    } catch (error) {
      toast.error("Failed to save integration");
      saveAttempted.current = false;
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card className="border-neutral-200 max-w-2xl mx-auto">
      <CardHeader className="p-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-neutral-100 rounded-lg flex items-center justify-center">
            <Image src="/images/linear-logo.png" alt="Linear" width={24} height={24} quality={100} />
          </div>
          <div className="flex-1">
            <CardTitle>Connect Linear with API Key</CardTitle>
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
            className="flex items-center space-x-2 text-sm text-neutral-600 hover:text-neutral-700"
          >
            <HelpCircle className="w-4 h-4" />
            <span>How to get your Linear API key</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showInstructions ? "rotate-180" : ""}`} />
          </button>
          {showInstructions && (
            <div className="mt-4">
              <Alert className="border-neutral-200 bg-neutral-50">
                <AlertDescription>
                  <a
                    href="https://linear.app/settings/account/security"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center text-neutral-600 hover:text-neutral-700"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Create your API key at Linear
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
              name="token"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Linear API Key</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        {...field}
                        type={showToken ? "text" : "password"}
                        placeholder="lin_api_..."
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
              <Alert className="border-neutral-200 bg-neutral-50">
                <Loader2 className="h-4 w-4 text-neutral-600 animate-spin" />
                <AlertDescription className="text-neutral-800">
                  Validating API key...
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
                      {isSaving ? "Saving..." : "API key validated!"}
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
