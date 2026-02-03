"use client";

import { Badge } from "@/components/ui/badge";
import { CheckCircle, Loader2, AlertTriangle, XCircle } from "lucide-react";
import type { ConnectionStatus, AuthMethod } from "../types";

interface StatusIndicatorProps {
  status: ConnectionStatus;
  authMethod?: AuthMethod;
  className?: string;
}

const statusConfig = {
  connected: {
    badgeClass: "bg-green-100 text-green-700",
    Icon: CheckCircle,
    getText: (authMethod?: AuthMethod) =>
      `Connected${authMethod ? ` via ${authMethod === "oauth" ? "OAuth" : "API Token"}` : ""}`,
    animate: false,
  },
  validating: {
    badgeClass: "bg-blue-100 text-blue-700",
    Icon: Loader2,
    getText: () => "Validating...",
    animate: true,
  },
  error: {
    badgeClass: "bg-red-100 text-red-700",
    Icon: AlertTriangle,
    getText: () => "Connection Error",
    animate: false,
  },
  disconnected: {
    badgeClass: "bg-gray-100 text-gray-600",
    Icon: XCircle,
    getText: () => "Not Connected",
    animate: false,
  },
};

export function StatusIndicator({ status, authMethod, className }: StatusIndicatorProps) {
  const config = statusConfig[status];
  const { badgeClass, Icon, getText, animate } = config;

  return (
    <Badge variant="secondary" className={`${badgeClass} ${className || ""}`}>
      <Icon className={`w-3 h-3 mr-1 ${animate ? "animate-spin" : ""}`} />
      {getText(authMethod)}
    </Badge>
  );
}
