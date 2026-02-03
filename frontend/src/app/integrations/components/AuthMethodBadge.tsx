"use client";

import { Badge } from "@/components/ui/badge";
import { Key, RefreshCw } from "lucide-react";
import type { AuthMethod } from "../types";

interface AuthMethodBadgeProps {
  authMethod: AuthMethod;
}

export function AuthMethodBadge({ authMethod }: AuthMethodBadgeProps) {
  if (authMethod === "oauth") {
    return (
      <Badge className="bg-blue-100 text-blue-700 border-blue-200">
        <RefreshCw className="w-3 h-3 mr-1" />
        OAuth
      </Badge>
    );
  }

  return (
    <Badge className="bg-neutral-200 text-neutral-700 border-neutral-300">
      <Key className="w-3 h-3 mr-1" />
      API Token
    </Badge>
  );
}
