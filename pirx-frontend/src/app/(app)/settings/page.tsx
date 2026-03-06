"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useTourStore } from "@/stores/tour-store";
import { createClient } from "@/lib/supabase/client";
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
} from "lucide-react";

// TODO: Fetch wearable status from API when available
const WEARABLE_CONNECTIONS = [
  {
    id: "strava",
    name: "Strava",
    icon: Activity,
    connected: true,
    lastSync: "2 hours ago",
  },
  {
    id: "garmin",
    name: "Garmin",
    icon: Watch,
    connected: false,
    lastSync: null,
  },
  {
    id: "apple_health",
    name: "Apple Health",
    icon: Smartphone,
    connected: false,
    lastSync: null,
  },
  {
    id: "fitbit",
    name: "Fitbit",
    icon: Activity,
    connected: false,
    lastSync: null,
  },
];

const EVENTS = [
  { id: "1500", name: "1500m", selected: true },
  { id: "3000", name: "3K", selected: true },
  { id: "5000", name: "5K", selected: true },
  { id: "10000", name: "10K", selected: true },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const supabase = createClient();
  const router = useRouter();
  const { resetCompleted } = useTourStore();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  const handleExport = async () => {
    try {
      const { apiFetch } = await import("@/lib/api");
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
    } catch {
      // TODO: surface error via toast
    }
  };

  const handleDelete = async () => {
    try {
      const { apiFetch } = await import("@/lib/api");
      await apiFetch("/account/delete", { method: "DELETE" });
      await supabase.auth.signOut();
      window.location.href = "/login";
    } catch {
      // TODO: surface error via toast
    }
  };

  // TODO: Persist notification toggles to Supabase when API available
  const [notifications, setNotifications] = useState({
    projectionShift: true,
    readinessChange: true,
    intervention: true,
    weeklySummary: true,
    raceApproaching: true,
    newInsight: true,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>

      {/* Wearable Connections */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Watch className="h-4 w-4" />
          Wearable Connections
        </h2>
        {WEARABLE_CONNECTIONS.map((w) => {
          const Icon = w.icon;
          return (
            <Card key={w.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{w.name}</p>
                    {w.connected && (
                      <p className="text-xs text-muted-foreground">
                        Last sync: {w.lastSync}
                      </p>
                    )}
                  </div>
                </div>
                {w.connected ? (
                  <div className="flex items-center gap-2">
                    <Badge variant="default">
                      <Check className="mr-1 h-3 w-3" /> Connected
                    </Badge>
                    <Button variant="ghost" size="sm">
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ) : (
                  <Button variant="outline" size="sm">
                    Connect
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
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
            <div>
              <p className="text-sm font-medium">5K — 20:42</p>
              <p className="text-xs text-muted-foreground">Feb 15, 2026</p>
            </div>
            <Button variant="outline" size="sm">
              Edit <ChevronRight className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Event Selection */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Target className="h-4 w-4" />
          Event Selection
        </h2>
        <Card>
          <CardContent className="p-4 space-y-3">
            {EVENTS.map((e) => (
              <div key={e.id} className="flex items-center justify-between">
                <Label htmlFor={`event-${e.id}`} className="text-sm">
                  {e.name}
                </Label>
                <Switch id={`event-${e.id}`} defaultChecked={e.selected} />
              </div>
            ))}
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
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm">Projection Shifts</Label>
                <p className="text-xs text-muted-foreground">
                  When projection changes ≥ 2 seconds
                </p>
              </div>
              <Switch
                checked={notifications.projectionShift}
                onCheckedChange={(checked) =>
                  setNotifications((n) => ({ ...n, projectionShift: checked }))
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
                checked={notifications.readinessChange}
                onCheckedChange={(checked) =>
                  setNotifications((n) => ({ ...n, readinessChange: checked }))
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
                checked={notifications.intervention}
                onCheckedChange={(checked) =>
                  setNotifications((n) => ({ ...n, intervention: checked }))
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
                checked={notifications.weeklySummary}
                onCheckedChange={(checked) =>
                  setNotifications((n) => ({ ...n, weeklySummary: checked }))
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
                checked={notifications.raceApproaching}
                onCheckedChange={(checked) =>
                  setNotifications((n) => ({ ...n, raceApproaching: checked }))
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
                checked={notifications.newInsight}
                onCheckedChange={(checked) =>
                  setNotifications((n) => ({ ...n, newInsight: checked }))
                }
              />
            </div>
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
