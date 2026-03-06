"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Loader2, Users, UserPlus, Building2 } from "lucide-react";
import { toast } from "sonner";
import { AthleteCard } from "@/components/coach/athlete-card";
import { InviteModal } from "@/components/coach/invite-modal";

interface CoachProfile {
  is_coach: boolean;
  display_name?: string;
  organization?: string;
  tier?: string;
  max_athletes?: number;
  current_athletes?: number;
}

interface Athlete {
  id: string;
  email: string;
  status: string;
  invited_at?: string;
  display_name?: string;
  primary_event?: string;
  projected_time?: string;
  projected_time_seconds?: number;
  twenty_one_day_change?: number;
  readiness_score?: number | null;
}

export default function CoachDashboardPage() {
  const [profile, setProfile] = useState<CoachProfile | null>(null);
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteOpen, setInviteOpen] = useState(false);

  const [registerName, setRegisterName] = useState("");
  const [registerOrg, setRegisterOrg] = useState("");
  const [registering, setRegistering] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      const { apiFetch } = await import("@/lib/api");
      const data = await apiFetch("/coach/profile");
      setProfile(data);
    } catch {
      setProfile({ is_coach: false });
    }
  }, []);

  const fetchAthletes = useCallback(async () => {
    try {
      const { apiFetch } = await import("@/lib/api");
      const data = await apiFetch("/coach/athletes");
      setAthletes(data.athletes ?? []);
    } catch {
      setAthletes([]);
    }
  }, []);

  useEffect(() => {
    async function load() {
      await fetchProfile();
      setLoading(false);
    }
    load();
  }, [fetchProfile]);

  useEffect(() => {
    if (profile?.is_coach) {
      fetchAthletes();
    }
  }, [profile, fetchAthletes]);

  async function handleRegister() {
    if (!registerName.trim()) return;
    setRegistering(true);
    try {
      const { apiFetch } = await import("@/lib/api");
      await apiFetch("/coach/register", {
        method: "POST",
        body: JSON.stringify({
          display_name: registerName.trim(),
          organization: registerOrg.trim() || null,
        }),
      });
      toast.success("Registered as coach");
      await fetchProfile();
    } catch {
      toast.error("Failed to register");
    } finally {
      setRegistering(false);
    }
  }

  async function handleInvite(email: string) {
    const { apiFetch } = await import("@/lib/api");
    const result = await apiFetch("/coach/invite", {
      method: "POST",
      body: JSON.stringify({ athlete_email: email }),
    });
    if (result.status === "already_active") {
      toast.info("Athlete is already on your roster");
    } else if (result.status === "already_pending") {
      toast.info("Invite already pending");
    } else {
      toast.success("Invite sent");
    }
    await fetchAthletes();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!profile?.is_coach) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Coach Dashboard</h1>
        <Card>
          <CardContent className="p-6 space-y-4">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold">Register as a Coach</h2>
              <p className="text-sm text-muted-foreground">
                Create a coach profile to monitor your athletes&apos;
                projections, drivers, and readiness.
              </p>
            </div>
            <Separator />
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="coach-name">Display Name</Label>
                <Input
                  id="coach-name"
                  placeholder="Coach Smith"
                  value={registerName}
                  onChange={(e) => setRegisterName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="coach-org">Organization (optional)</Label>
                <Input
                  id="coach-org"
                  placeholder="Track Club XYZ"
                  value={registerOrg}
                  onChange={(e) => setRegisterOrg(e.target.value)}
                />
              </div>
              <Button
                onClick={handleRegister}
                disabled={registering || !registerName.trim()}
                className="w-full"
              >
                {registering ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Users className="mr-2 h-4 w-4" />
                )}
                Register as Coach
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const activeAthletes = athletes.filter((a) => a.status === "active");
  const pendingAthletes = athletes.filter((a) => a.status === "pending");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Coach Dashboard
          </h1>
          <div className="flex items-center gap-2 mt-1">
            {profile.organization && (
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Building2 className="h-3.5 w-3.5" />
                {profile.organization}
              </span>
            )}
            <Badge variant="secondary">{profile.tier}</Badge>
            <span className="text-xs text-muted-foreground">
              {profile.current_athletes}/{profile.max_athletes} athletes
            </span>
          </div>
        </div>
        <Button size="sm" onClick={() => setInviteOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Invite
        </Button>
      </div>

      {activeAthletes.length === 0 && pendingAthletes.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-10 text-center">
            <Users className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground">
              No athletes yet. Invite your first athlete to get started.
            </p>
          </CardContent>
        </Card>
      )}

      {activeAthletes.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Active Athletes
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {activeAthletes.map((a) => (
              <AthleteCard
                key={a.id}
                id={a.id}
                displayName={a.display_name ?? "Unknown"}
                email={a.email}
                primaryEvent={a.primary_event ?? "5000"}
                projectedTime={a.projected_time ?? "—"}
                readinessScore={a.readiness_score ?? null}
                twentyOneDayChange={a.twenty_one_day_change ?? 0}
                status={a.status}
              />
            ))}
          </div>
        </div>
      )}

      {pendingAthletes.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Pending Invites
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {pendingAthletes.map((a) => (
              <AthleteCard
                key={a.id}
                id={a.id}
                displayName=""
                email={a.email}
                primaryEvent=""
                projectedTime=""
                readinessScore={null}
                twentyOneDayChange={0}
                status={a.status}
              />
            ))}
          </div>
        </div>
      )}

      <InviteModal
        open={inviteOpen}
        onOpenChange={setInviteOpen}
        onInvite={handleInvite}
      />
    </div>
  );
}
