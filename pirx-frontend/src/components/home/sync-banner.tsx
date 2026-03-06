"use client";

import { RefreshCw, Check, Loader2 } from "lucide-react";

function formatLastSync(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface SyncBannerProps {
  lastSync?: string | null;
  syncing?: boolean;
  onSyncNow?: () => void;
}

export function SyncBanner({ lastSync, syncing, onSyncNow }: SyncBannerProps) {
  const label = lastSync ? `Last synced ${formatLastSync(lastSync)}` : "Not synced yet";
  return (
    <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
      <div className="flex items-center gap-2">
        <Check className="h-3.5 w-3.5 text-green-500" />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <button
        onClick={onSyncNow}
        disabled={syncing}
        className="text-xs text-primary flex items-center gap-1 hover:underline disabled:opacity-50"
      >
        {syncing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
        {syncing ? "Syncing…" : "Sync Now"}
      </button>
    </div>
  );
}
