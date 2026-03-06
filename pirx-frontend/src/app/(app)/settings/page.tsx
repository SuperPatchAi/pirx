"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
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
} from "lucide-react";

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
  const [notifications, setNotifications] = useState({
    projectionShift: true,
    readinessChange: true,
    weeklySummary: true,
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
                user@example.com
              </span>
            </div>
            <Separator />
            <Button variant="destructive" className="w-full" size="sm">
              <LogOut className="mr-2 h-4 w-4" /> Sign Out
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
