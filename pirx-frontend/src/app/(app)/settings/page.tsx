"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useNotifications } from "@/hooks/use-notifications";
import { useTourStore } from "@/stores/tour-store";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Activity,
  Watch,
  Smartphone,
  Check,
  X,
  LogOut,
  Bell,
  Target,
  Timer,
  User,
  ChevronRight,
  Download,
  Trash2,
  HelpCircle,
  Loader2,
  Plus,
  FlaskConical,
  Shield,
  Users,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const PROVIDER_META: Record<string, { name: string; icon: typeof Activity }> = {
  strava: { name: "Strava", icon: Activity },
  garmin: { name: "Garmin", icon: Watch },
  apple_health: { name: "Apple Health", icon: Smartphone },
  fitbit: { name: "Fitbit", icon: Activity },
  coros: { name: "COROS", icon: Watch },
  polar: { name: "Polar", icon: Watch },
  suunto: { name: "Suunto", icon: Watch },
  whoop: { name: "WHOOP", icon: Activity },
  oura: { name: "Oura", icon: Activity },
};

const ALL_PROVIDERS = [
  "strava", "garmin", "apple_health", "fitbit",
  "coros", "whoop", "oura", "polar", "suunto",
];

const EVENT_OPTIONS = [
  { id: "1500", name: "1500m" },
  { id: "3000", name: "3K" },
  { id: "5000", name: "5K" },
  { id: "10000", name: "10K" },
  { id: "21097", name: "Half Marathon" },
  { id: "42195", name: "Marathon" },
];

interface WearableConnection {
  provider: string;
  connected: boolean;
  last_sync: string | null;
}

interface Baseline {
  event: string;
  time_seconds: number;
  race_date: string | null;
  source: string;
}

interface NotificationPrefs {
  projection_shifts: boolean;
  readiness_changes: boolean;
  intervention_alerts: boolean;
  weekly_summary: boolean;
  race_reminders: boolean;
  new_insights: boolean;
}

interface Adjunct {
  id: string;
  name: string;
  statistical_status?: string;
}

const DEFAULT_PREFS: NotificationPrefs = {
  projection_shifts: true,
  readiness_changes: true,
  intervention_alerts: true,
  weekly_summary: true,
  race_reminders: true,
  new_insights: true,
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function eventLabel(id: string): string {
  return EVENT_OPTIONS.find((e) => e.id === id)?.name ?? id;
}

function formatSyncTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const { permission, supported, subscribed, requestPermission, subscribeToPush, unsubscribeFromPush } = useNotifications();
  const supabase = createClient();
  const router = useRouter();
  const { resetCompleted } = useTourStore();
  const [pushLoading, setPushLoading] = useState(false);

  const [connections, setConnections] = useState<WearableConnection[]>([]);
  const [connectionsLoading, setConnectionsLoading] = useState(true);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);

  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [baselineLoading, setBaselineLoading] = useState(true);

  const [notifications, setNotifications] = useState<NotificationPrefs>(DEFAULT_PREFS);
  const [notifLoading, setNotifLoading] = useState(true);

  const [adjuncts, setAdjuncts] = useState<Adjunct[]>([]);
  const [adjunctsLoading, setAdjunctsLoading] = useState(true);
  const [showAddAdjunct, setShowAddAdjunct] = useState(false);
  const [newAdjunctName, setNewAdjunctName] = useState("");
  const [addAdjunctLoading, setAddAdjunctLoading] = useState(false);
  const [deletingAdjunctId, setDeletingAdjunctId] = useState<string | null>(null);

  const [isCoach, setIsCoach] = useState(false);
  const [myCoaches, setMyCoaches] = useState<
    { coach_id: string; display_name: string; organization?: string; status: string; invited_at?: string }[]
  >([]);
  const [coachAccessLoading, setCoachAccessLoading] = useState(true);
  const [coachActionLoading, setCoachActionLoading] = useState<string | null>(null);

  const fetchConnections = useCallback(async () => {
    try {
      const data = await apiFetch("/sync/status");
      setConnections(data.connections ?? []);
    } catch {
      setConnections([]);
    } finally {
      setConnectionsLoading(false);
    }
  }, []);

  const fetchBaseline = useCallback(async () => {
    try {
      const data = await apiFetch("/account/baseline");
      setBaseline(data);
    } catch {
      setBaseline(null);
    } finally {
      setBaselineLoading(false);
    }
  }, []);

  const fetchPreferences = useCallback(async () => {
    try {
      const data = await apiFetch("/preferences");
      setNotifications(data);
    } catch {
      const stored = localStorage.getItem("pirx_notification_prefs");
      if (stored) {
        try { setNotifications(JSON.parse(stored)); } catch { /* use defaults */ }
      }
    } finally {
      setNotifLoading(false);
    }
  }, []);

  const fetchAdjuncts = useCallback(async () => {
    try {
      const data = await apiFetch("/account/adjunct-library");
      setAdjuncts(data.adjuncts ?? []);
    } catch {
      setAdjuncts([]);
    } finally {
      setAdjunctsLoading(false);
    }
  }, []);

  const fetchCoachAccess = useCallback(async () => {
    try {
      const [profileRes, coachesRes] = await Promise.allSettled([
        apiFetch("/coach/profile"),
        apiFetch("/coach/my-coaches"),
      ]);
      if (profileRes.status === "fulfilled") {
        setIsCoach(profileRes.value.is_coach === true);
      }
      if (coachesRes.status === "fulfilled") {
        setMyCoaches(coachesRes.value.coaches ?? []);
      }
    } catch {
      // ignore
    } finally {
      setCoachAccessLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConnections();
    fetchBaseline();
    fetchPreferences();
    fetchAdjuncts();
    fetchCoachAccess();
  }, [fetchConnections, fetchBaseline, fetchPreferences, fetchAdjuncts, fetchCoachAccess]);

  const mergedConnections = ALL_PROVIDERS.map((provider) => {
    const live = connections.find((c) => c.provider === provider);
    return {
      provider,
      connected: live?.connected ?? false,
      last_sync: live?.last_sync ?? null,
    };
  });

  const [connecting, setConnecting] = useState<string | null>(null);

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    if (provider === "strava") {
      try {
        const redirectUri = `${window.location.origin}/settings/strava-callback`;
        const data = await apiFetch(
          `/sync/connect/strava?redirect_uri=${encodeURIComponent(redirectUri)}`
        );
        if (data.authorization_url) {
          window.location.href = data.authorization_url;
          return;
        }
      } catch { toast.error("Failed to connect Strava"); }
    } else {
      try {
        const data = await apiFetch(`/sync/connect/${provider}`, {
          method: "POST",
        });
        if (data.widget_url) {
          window.open(data.widget_url, "_blank");
          toast.success(`Opening ${PROVIDER_META[provider]?.name ?? provider} connection...`);
        }
      } catch { toast.error(`Failed to connect ${PROVIDER_META[provider]?.name ?? provider}`); }
    }
    setConnecting(null);
  };

  const handleDisconnect = async (provider: string) => {
    setDisconnecting(provider);
    try {
      await apiFetch(`/sync/disconnect/${provider}`, { method: "POST" });
      await fetchConnections();
    } catch { toast.error("Failed to disconnect provider"); }
    setDisconnecting(null);
  };

  const handleNotificationChange = async (
    key: keyof NotificationPrefs,
    checked: boolean
  ) => {
    const updated = { ...notifications, [key]: checked };
    setNotifications(updated);
    localStorage.setItem("pirx_notification_prefs", JSON.stringify(updated));
    try {
      await apiFetch("/preferences", {
        method: "PUT",
        body: JSON.stringify(updated),
      });
    } catch { /* backend save failed — localStorage persists as fallback */ }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  const handleExport = async () => {
    try {
      const data = await apiFetch("/account/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pirx-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Failed to export data"); }
  };

  const handleDelete = async () => {
    try {
      await apiFetch("/account/delete", { method: "DELETE" });
      await supabase.auth.signOut();
      window.location.href = "/login";
    } catch { toast.error("Failed to delete account"); }
  };

  const handleAddAdjunct = async () => {
    const name = newAdjunctName.trim();
    if (!name) return;
    setAddAdjunctLoading(true);
    try {
      await apiFetch("/account/adjunct-library", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setNewAdjunctName("");
      setShowAddAdjunct(false);
      await fetchAdjuncts();
    } catch { toast.error("Failed to add adjunct"); }
    setAddAdjunctLoading(false);
  };

  const handleDeleteAdjunct = async (id: string) => {
    setDeletingAdjunctId(id);
    try {
      await apiFetch(`/account/adjunct-library/${id}`, { method: "DELETE" });
      await fetchAdjuncts();
    } catch { toast.error("Failed to delete adjunct"); }
    setDeletingAdjunctId(null);
  };

  const handleAcceptInvite = async (coachId: string) => {
    setCoachActionLoading(coachId);
    try {
      await apiFetch(`/coach/accept-invite/${coachId}`, { method: "POST" });
      toast.success("Invite accepted");
      await fetchCoachAccess();
    } catch {
      toast.error("Failed to accept invite");
    }
    setCoachActionLoading(null);
  };

  const handleDeclineInvite = async (coachId: string) => {
    setCoachActionLoading(coachId);
    try {
      await apiFetch(`/coach/decline-invite/${coachId}`, { method: "POST" });
      toast.success("Invite declined");
      await fetchCoachAccess();
    } catch {
      toast.error("Failed to decline invite");
    }
    setCoachActionLoading(null);
  };

  const handleRevokeCoach = async (coachId: string) => {
    setCoachActionLoading(coachId);
    try {
      await apiFetch(`/coach/revoke-coach/${coachId}`, { method: "POST" });
      toast.success("Coach access revoked");
      await fetchCoachAccess();
    } catch {
      toast.error("Failed to revoke access");
    }
    setCoachActionLoading(null);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>

      {/* Wearable Connections */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Watch className="h-4 w-4" />
          Wearable Connections
        </h2>
        {connectionsLoading ? (
          <Card>
            <CardContent className="flex items-center justify-center p-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        ) : (
          mergedConnections.map((w) => {
            const meta = PROVIDER_META[w.provider] ?? {
              name: w.provider,
              icon: Activity,
            };
            const Icon = meta.icon;
            return (
              <Card key={w.provider}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{meta.name}</p>
                      {w.connected && w.last_sync && (
                        <p className="text-xs text-muted-foreground">
                          Last sync: {formatSyncTime(w.last_sync)}
                        </p>
                      )}
                    </div>
                  </div>
                  {w.connected ? (
                    <div className="flex items-center gap-2">
                      <Badge variant="default">
                        <Check className="mr-1 h-3 w-3" /> Connected
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={disconnecting === w.provider}
                        onClick={() => handleDisconnect(w.provider)}
                      >
                        {disconnecting === w.provider ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <X className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={connecting === w.provider}
                      onClick={() => handleConnect(w.provider)}
                    >
                      {connecting === w.provider ? (
                        <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                      ) : null}
                      Connect
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      <Separator />

      {/* Baseline Race */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Timer className="h-4 w-4" />
          Baseline Race
        </h2>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            {baselineLoading ? (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            ) : baseline ? (
              <>
                <div>
                  <p className="text-sm font-medium">
                    {eventLabel(baseline.event)} —{" "}
                    {formatTime(baseline.time_seconds)}
                  </p>
                  {baseline.race_date && (
                    <p className="text-xs text-muted-foreground">
                      {new Date(baseline.race_date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push("/onboarding/2")}
                >
                  Edit <ChevronRight className="ml-1 h-3 w-3" />
                </Button>
              </>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">No baseline set</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push("/onboarding/2")}
                >
                  Set Baseline <ChevronRight className="ml-1 h-3 w-3" />
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Primary Event Selection */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Target className="h-4 w-4" />
          Primary Event
        </h2>
        <Card>
          <CardContent className="p-4 space-y-3">
            {EVENT_OPTIONS.map((e) => (
              <div key={e.id} className="flex items-center justify-between">
                <Label htmlFor={`event-${e.id}`} className="text-sm">
                  {e.name}
                </Label>
                <input
                  type="radio"
                  id={`event-${e.id}`}
                  name="primary-event"
                  className="h-4 w-4 accent-primary"
                  checked={baseline?.event === e.id}
                  onChange={async () => {
                    if (!baseline) return;
                    const updated = { ...baseline, event: e.id };
                    setBaseline(updated);
                    try {
                      await apiFetch("/account/baseline", {
                        method: "PUT",
                        body: JSON.stringify({
                          event: e.id,
                          time_seconds: baseline.time_seconds,
                          race_date: baseline.race_date,
                          source: baseline.source,
                        }),
                      });
                    } catch { toast.error("Failed to update primary event"); }
                  }}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Push Notifications */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Bell className="h-4 w-4" />
          Push Notifications
        </h2>
        <Card>
          <CardContent className="p-4">
            {!supported ? (
              <p className="text-sm text-muted-foreground">
                Push notifications are not supported in this browser.
              </p>
            ) : subscribed ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-green-500" />
                  <span className="text-sm">Push notifications enabled</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pushLoading}
                  onClick={async () => {
                    setPushLoading(true);
                    try {
                      const { data } = await supabase.auth.getSession();
                      const token = data?.session?.access_token;
                      if (token) await unsubscribeFromPush(token);
                    } catch { toast.error("Failed to unsubscribe"); }
                    setPushLoading(false);
                  }}
                >
                  {pushLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Unsubscribe"}
                </Button>
              </div>
            ) : permission !== "granted" ? (
              <Button
                variant="outline"
                className="w-full"
                size="sm"
                disabled={pushLoading}
                onClick={async () => {
                  setPushLoading(true);
                  try {
                    await requestPermission();
                    const { data } = await supabase.auth.getSession();
                    const token = data?.session?.access_token;
                    if (token) await subscribeToPush(token);
                  } catch { toast.error("Failed to enable push notifications"); }
                  setPushLoading(false);
                }}
              >
                {pushLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Bell className="mr-2 h-4 w-4" />
                )}
                Enable Push Notifications
              </Button>
            ) : (
              <Button
                variant="outline"
                className="w-full"
                size="sm"
                disabled={pushLoading}
                onClick={async () => {
                  setPushLoading(true);
                  try {
                    const { data } = await supabase.auth.getSession();
                    const token = data?.session?.access_token;
                    if (token) await subscribeToPush(token);
                  } catch { toast.error("Failed to subscribe"); }
                  setPushLoading(false);
                }}
              >
                {pushLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Bell className="mr-2 h-4 w-4" />
                )}
                Subscribe to Push
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Notifications */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Bell className="h-4 w-4" />
          Notifications
        </h2>
        <Card>
          <CardContent className="p-4 space-y-3">
            {notifLoading ? (
              <div className="flex justify-center py-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Projection Shifts</Label>
                    <p className="text-xs text-muted-foreground">
                      When projection changes ≥ 2 seconds
                    </p>
                  </div>
                  <Switch
                    checked={notifications.projection_shifts}
                    onCheckedChange={(checked) =>
                      handleNotificationChange("projection_shifts", checked)
                    }
                  />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Readiness Changes</Label>
                    <p className="text-xs text-muted-foreground">
                      When readiness shifts ≥ 5 points
                    </p>
                  </div>
                  <Switch
                    checked={notifications.readiness_changes}
                    onCheckedChange={(checked) =>
                      handleNotificationChange("readiness_changes", checked)
                    }
                  />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Intervention Signals</Label>
                    <p className="text-xs text-muted-foreground">
                      When unusual training patterns detected (ACWR spike)
                    </p>
                  </div>
                  <Switch
                    checked={notifications.intervention_alerts}
                    onCheckedChange={(checked) =>
                      handleNotificationChange("intervention_alerts", checked)
                    }
                  />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Weekly Summary</Label>
                    <p className="text-xs text-muted-foreground">
                      Monday recap of training + projections
                    </p>
                  </div>
                  <Switch
                    checked={notifications.weekly_summary}
                    onCheckedChange={(checked) =>
                      handleNotificationChange("weekly_summary", checked)
                    }
                  />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Race Approaching</Label>
                    <p className="text-xs text-muted-foreground">
                      Reminder when target race is within 2 weeks
                    </p>
                  </div>
                  <Switch
                    checked={notifications.race_reminders}
                    onCheckedChange={(checked) =>
                      handleNotificationChange("race_reminders", checked)
                    }
                  />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">New Insights</Label>
                    <p className="text-xs text-muted-foreground">
                      When new training patterns are discovered
                    </p>
                  </div>
                  <Switch
                    checked={notifications.new_insights}
                    onCheckedChange={(checked) =>
                      handleNotificationChange("new_insights", checked)
                    }
                  />
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Adjunct Library */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <FlaskConical className="h-4 w-4" />
          Adjunct Library
        </h2>
        <Card>
          <CardContent className="p-4 space-y-3">
            {adjunctsLoading ? (
              <div className="flex justify-center py-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  {adjuncts.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div>
                        <p className="text-sm font-medium">{a.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {a.statistical_status ?? "observational"}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deletingAdjunctId === a.id}
                        onClick={() => handleDeleteAdjunct(a.id)}
                      >
                        {deletingAdjunctId === a.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  ))}
                  {adjuncts.length === 0 && !showAddAdjunct && (
                    <p className="text-sm text-muted-foreground py-2">
                      No adjuncts yet. Add one to track how supplements or habits
                      correlate with your projections.
                    </p>
                  )}
                </div>
                {showAddAdjunct ? (
                  <div className="flex gap-2">
                    <Input
                      placeholder="Adjunct name"
                      value={newAdjunctName}
                      onChange={(e) => setNewAdjunctName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleAddAdjunct();
                      }}
                      className="flex-1"
                    />
                    <Button
                      size="sm"
                      onClick={handleAddAdjunct}
                      disabled={!newAdjunctName.trim() || addAdjunctLoading}
                    >
                      {addAdjunctLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        "Add"
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowAddAdjunct(false);
                        setNewAdjunctName("");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAddAdjunct(true)}
                  >
                    <Plus className="mr-2 h-4 w-4" /> Add Adjunct
                  </Button>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Coach Access */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Shield className="h-4 w-4" />
          Coach Access
        </h2>
        <Card>
          <CardContent className="p-4 space-y-3">
            {coachAccessLoading ? (
              <div className="flex justify-center py-2">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <Button
                  variant={isCoach ? "outline" : "secondary"}
                  size="sm"
                  className="w-full"
                  onClick={() => router.push("/coach")}
                >
                  <Users className="mr-2 h-4 w-4" />
                  {isCoach ? "Open Coach Dashboard" : "Become a Coach"}
                </Button>
                {myCoaches.length > 0 && <Separator />}
                {myCoaches.filter((c) => c.status === "pending").map((c) => (
                  <div
                    key={c.coach_id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{c.display_name}</p>
                      {c.organization && (
                        <p className="text-xs text-muted-foreground">{c.organization}</p>
                      )}
                      <Badge variant="secondary" className="mt-1 text-[10px]">
                        Pending Invite
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        disabled={coachActionLoading === c.coach_id}
                        onClick={() => handleAcceptInvite(c.coach_id)}
                      >
                        {coachActionLoading === c.coach_id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Check className="h-3.5 w-3.5" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={coachActionLoading === c.coach_id}
                        onClick={() => handleDeclineInvite(c.coach_id)}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
                {myCoaches.filter((c) => c.status === "active").map((c) => (
                  <div
                    key={c.coach_id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{c.display_name}</p>
                      {c.organization && (
                        <p className="text-xs text-muted-foreground">{c.organization}</p>
                      )}
                      <Badge variant="default" className="mt-1 text-[10px]">
                        Active
                      </Badge>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={coachActionLoading === c.coach_id}
                      onClick={() => handleRevokeCoach(c.coach_id)}
                    >
                      {coachActionLoading === c.coach_id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        "Revoke"
                      )}
                    </Button>
                  </div>
                ))}
                {!isCoach && myCoaches.length === 0 && (
                  <p className="text-sm text-muted-foreground py-2">
                    No coach connections
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Help */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <HelpCircle className="h-4 w-4" />
          Help
        </h2>
        <Card>
          <CardContent className="p-4">
            <Button
              variant="outline"
              className="w-full"
              size="sm"
              onClick={() => {
                resetCompleted();
                router.push("/dashboard");
              }}
            >
              <HelpCircle className="mr-2 h-4 w-4" /> Take a Tour
            </Button>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Account */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <User className="h-4 w-4" />
          Account
        </h2>
        <Card>
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Email</span>
              <span className="text-sm text-muted-foreground">
                {user?.email || "Not signed in"}
              </span>
            </div>
            <Separator />
            <Button
              variant="outline"
              className="w-full"
              size="sm"
              onClick={handleExport}
            >
              <Download className="mr-2 h-4 w-4" /> Export My Data
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" className="w-full" size="sm">
                  <Trash2 className="mr-2 h-4 w-4" /> Delete All Data
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete all your data?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. All your training data,
                    projections, and account information will be permanently
                    deleted.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDelete}>
                    Delete Everything
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <Separator />
            <Button
              variant="destructive"
              className="w-full"
              size="sm"
              onClick={handleSignOut}
            >
              <LogOut className="mr-2 h-4 w-4" /> Sign Out
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
