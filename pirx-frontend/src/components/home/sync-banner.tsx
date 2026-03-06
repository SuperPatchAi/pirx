"use client";

import { RefreshCw, Check } from "lucide-react";

export function SyncBanner() {
  // Mock: last synced 2 hours ago
  return (
    <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
      <div className="flex items-center gap-2">
        <Check className="h-3.5 w-3.5 text-green-500" />
        <span className="text-xs text-muted-foreground">
          Last synced 2 hours ago
        </span>
      </div>
      <button className="text-xs text-primary flex items-center gap-1 hover:underline">
        <RefreshCw className="h-3 w-3" />
        Sync Now
      </button>
    </div>
  );
}
