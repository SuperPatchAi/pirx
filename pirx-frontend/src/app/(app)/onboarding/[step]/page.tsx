"use client";

import { useRouter, useParams } from "next/navigation";
import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import { apiFetch } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  Watch,
  Smartphone,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Check,
  Zap,
} from "lucide-react";

const TOTAL_STEPS = 5;

const pageVariants = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -30 },
};

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-2 py-4">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-2 rounded-full transition-all duration-300 ${
            i + 1 === current
              ? "w-8 bg-primary"
              : i + 1 < current
                ? "w-2 bg-primary/60"
                : "w-2 bg-muted"
          }`}
        />
      ))}
    </div>
  );
}

function WelcomeStep({
  onNext,
  userEmail,
}: {
  onNext: () => void;
  userEmail?: string | null;
}) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-8"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 15 }}
      >
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10">
          <Zap className="h-10 w-10 text-primary" />
        </div>
      </motion.div>
      <div className="space-y-3">
        <h1 className="text-3xl font-bold tracking-tight">PIRX</h1>
        {userEmail && (
          <p className="text-sm text-muted-foreground">Signed in as {userEmail}</p>
        )}
        <p className="text-lg text-muted-foreground">
          Your running, projected forward
        </p>
        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
          AI-powered structural performance modeling that tells you what you can
          run today — and what&apos;s driving the change.
        </p>
      </div>
      <Button size="lg" onClick={onNext} className="w-full max-w-xs">
        Get Started <ChevronRight className="ml-2 h-4 w-4" />
      </Button>
    </motion.div>
  );
}

const WEARABLE_PROVIDERS = [
  { id: "strava", name: "Strava", icon: Activity, comingSoon: false },
  { id: "garmin", name: "Garmin", icon: Watch, comingSoon: true },
  { id: "apple_health", name: "Apple Health", icon: Smartphone, comingSoon: true },
  { id: "fitbit", name: "Fitbit", icon: Activity, comingSoon: true },
];

interface SyncConnection {
  provider: string;
  is_active: boolean;
  last_sync: string | null;
}

function ConnectStep({
  onNext,
  onBack,
}: {
  onNext: () => void;
  onBack: () => void;
}) {
  const [connections, setConnections] = useState<Map<string, SyncConnection>>(new Map());
  const [connecting, setConnecting] = useState<string | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiFetch("/sync/status");
        if (!cancelled && data.connections) {
          const map = new Map<string, SyncConnection>();
          data.connections.forEach((c: SyncConnection) => map.set(c.provider, c));
          setConnections(map);
        }
      } catch {
        // API may not be reachable during onboarding — continue with empty state
      }
      if (!cancelled) setLoadingStatus(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const handleConnect = async (providerId: string) => {
    const provider = WEARABLE_PROVIDERS.find((p) => p.id === providerId);
    if (!provider || provider.comingSoon) return;

    if (providerId === "strava") {
      setConnecting("strava");
      try {
        const redirectUri = window.location.origin + "/auth/callback?next=/onboarding/3";
        const data = await apiFetch(`/sync/connect/strava?redirect_uri=${encodeURIComponent(redirectUri)}`);
        if (data.authorization_url) {
          window.location.href = data.authorization_url;
        }
      } catch {
        setConnecting(null);
      }
    }
  };

  const isConnected = (id: string) => {
    const conn = connections.get(id);
    return conn?.is_active ?? false;
  };

  const hasAnyConnection = Array.from(connections.values()).some((c) => c.is_active);

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="space-y-6"
    >
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">
          Connect Your Wearable
        </h2>
        <p className="text-sm text-muted-foreground">
          Link at least one platform to start building your projection.
        </p>
      </div>

      <div className="space-y-3">
        {WEARABLE_PROVIDERS.map((w) => {
          const Icon = w.icon;
          const connected = isConnected(w.id);
          return (
            <Card
              key={w.id}
              className={`transition-all ${
                connected
                  ? "border-primary bg-primary/5"
                  : w.comingSoon
                    ? "opacity-60"
                    : "cursor-pointer"
              }`}
              onClick={() => !w.comingSoon && handleConnect(w.id)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="font-medium">{w.name}</span>
                    {connected && connections.get(w.id)?.last_sync && (
                      <p className="text-xs text-muted-foreground">
                        Last sync: {new Date(connections.get(w.id)!.last_sync!).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                {connected ? (
                  <Badge variant="default">
                    <Check className="mr-1 h-3 w-3" /> Connected
                  </Badge>
                ) : w.comingSoon ? (
                  <Badge variant="outline">Coming Soon</Badge>
                ) : connecting === w.id ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : loadingStatus ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
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

      <div className="flex gap-3 pt-4">
        <Button variant="ghost" onClick={onBack} className="flex-1">
          <ChevronLeft className="mr-2 h-4 w-4" /> Back
        </Button>
        <Button
          onClick={onNext}
          className="flex-1"
          disabled={!hasAnyConnection && connecting === null}
        >
          Continue <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
      <Button variant="link" onClick={onNext} className="w-full text-muted-foreground">
        Skip for now
      </Button>
    </motion.div>
  );
}

function LoadingStep({ onNext }: { onNext: () => void }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let fakeProgress = 0;

    const poll = async () => {
      while (!cancelled && fakeProgress < 100) {
        try {
          const data = await apiFetch("/sync/status");
          const hasConnection = data.connections?.some((c: { connected: boolean }) => c.connected);
          if (hasConnection) {
            fakeProgress = Math.min(fakeProgress + 15, 95);
          } else {
            fakeProgress = Math.min(fakeProgress + 5, 90);
          }
        } catch {
          fakeProgress = Math.min(fakeProgress + 3, 90);
        }
        if (!cancelled) setProgress(fakeProgress);
        await new Promise((r) => setTimeout(r, 1500));
      }
      if (!cancelled) {
        setProgress(100);
        setTimeout(onNext, 500);
      }
    };

    const timer = setTimeout(() => {
      setProgress(100);
      if (!cancelled) setTimeout(onNext, 500);
    }, 15000);

    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [onNext]);

  const messages = [
    { threshold: 0, text: "Connecting to your data..." },
    { threshold: 25, text: "Analyzing training history..." },
    { threshold: 50, text: "Computing structural drivers..." },
    { threshold: 75, text: "Building your projection..." },
    { threshold: 95, text: "Almost there..." },
  ];

  const currentMessage = messages
    .filter((m) => progress >= m.threshold)
    .pop()?.text;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-8"
    >
      <Loader2 className="h-12 w-12 text-primary animate-spin" />
      <div className="space-y-3 w-full max-w-xs">
        <p className="text-lg font-medium">{currentMessage}</p>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-primary rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <p className="text-xs text-muted-foreground">{progress}%</p>
      </div>
    </motion.div>
  );
}

function BaselineStep({
  onNext,
  onBack,
}: {
  onNext: () => void;
  onBack: () => void;
}) {
  const [mode, setMode] = useState<"detected" | "manual">("detected");
  const [event, setEvent] = useState("5000");
  const [minutes, setMinutes] = useState("20");
  const [seconds, setSeconds] = useState("00");
  const [detected, setDetected] = useState<{ event: string; time: string; date: string; time_seconds: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch("/onboarding/detect-baseline", { method: "POST" });
        if (data.baseline_source !== "cold_start") {
          const totalSec = data.baseline_time_seconds;
          const m = Math.floor(totalSec / 60);
          const s = Math.floor(totalSec % 60);
          setDetected({
            event: data.baseline_event,
            time: `${m}:${s.toString().padStart(2, "0")}`,
            date: data.detected_races?.[0]?.timestamp?.slice(0, 10) || "Recent",
            time_seconds: totalSec,
          });
          setEvent(data.baseline_event);
          setMinutes(String(m));
          setSeconds(String(s).padStart(2, "0"));
        }
      } catch {}
      setLoading(false);
    })();
  }, []);

  const handleConfirm = async () => {
    const timeSec = mode === "detected" && detected
      ? detected.time_seconds
      : parseInt(minutes) * 60 + parseInt(seconds);
    const ev = mode === "detected" && detected ? detected.event : event;
    try {
      await apiFetch("/onboarding/set-baseline", {
        method: "POST",
        body: JSON.stringify({ event: ev, time_seconds: timeSec, source: mode === "detected" ? "race_history" : "manual" }),
      });
    } catch {}
    onNext();
  };

  if (loading) {
    return (
      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="space-y-6"
    >
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">Your Baseline</h2>
        <p className="text-sm text-muted-foreground">
          {detected ? "We found a recent race result. Confirm or enter your own." : "Enter a recent race time to set your baseline."}
        </p>
      </div>

      {mode === "detected" && detected && (
        <Card className="border-primary bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Detected Race
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tabular-nums">
                {detected.time}
              </span>
              <Badge variant="secondary">{detected.event === "5000" ? "5K" : detected.event === "10000" ? "10K" : detected.event + "m"}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">{detected.date}</p>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-2">
        {detected && (
          <Button
            variant={mode === "detected" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("detected")}
          >
            Use Detected
          </Button>
        )}
        <Button
          variant={mode === "manual" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("manual")}
        >
          Enter Manually
        </Button>
      </div>

      {mode === "manual" && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Event Distance</Label>
            <select
              value={event}
              onChange={(e) => setEvent(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="1500">1500m</option>
              <option value="3000">3000m</option>
              <option value="5000">5K</option>
              <option value="10000">10K</option>
              <option value="21097">Half Marathon</option>
              <option value="42195">Marathon</option>
            </select>
          </div>
          <div className="flex gap-2 items-end">
            <div className="flex-1 space-y-2">
              <Label>Minutes</Label>
              <Input
                type="number"
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
                min={0}
                max={300}
              />
            </div>
            <span className="pb-2 text-xl font-bold">:</span>
            <div className="flex-1 space-y-2">
              <Label>Seconds</Label>
              <Input
                type="number"
                value={seconds}
                onChange={(e) => setSeconds(e.target.value)}
                min={0}
                max={59}
              />
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3 pt-4">
        <Button variant="ghost" onClick={onBack} className="flex-1">
          <ChevronLeft className="mr-2 h-4 w-4" /> Back
        </Button>
        <Button onClick={handleConfirm} className="flex-1">
          Confirm Baseline <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </motion.div>
  );
}

function RevealStep({ onFinish }: { onFinish: () => void }) {
  const [projections, setProjections] = useState<Array<{ event: string; time: string; change: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch("/onboarding/generate-projection", {
          method: "POST",
          body: JSON.stringify({ primary_event: "5000" }),
        });
        if (data.all_projections) {
          const eventLabels: Record<string, string> = { "1500": "1500m", "3000": "3K", "5000": "5K", "10000": "10K", "21097": "Half Marathon", "42195": "Marathon" };
          const items = Object.entries(data.all_projections).map(([key, proj]: [string, any]) => {
            const sec = proj.midpoint_seconds;
            const m = Math.floor(sec / 60);
            const s = Math.floor(sec % 60);
            let timeStr = `${m}:${s.toString().padStart(2, "0")}`;
            if (sec >= 3600) {
              const h = Math.floor(sec / 3600);
              const rm = Math.floor((sec % 3600) / 60);
              const rs = Math.floor(sec % 60);
              timeStr = `${h}:${rm.toString().padStart(2, "0")}:${rs.toString().padStart(2, "0")}`;
            }
            return { event: eventLabels[key] || key, time: timeStr, change: "baseline" };
          });
          setProjections(items);
        }
      } catch {
        setProjections([
          { event: "5K", time: "25:00", change: "baseline" },
        ]);
      }
      setLoading(false);
    })();
  }, []);

  if (loading) {
    return (
      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="space-y-6"
    >
      <div className="space-y-2 text-center">
        <h2 className="text-2xl font-bold tracking-tight">Your Projections</h2>
        <p className="text-sm text-muted-foreground">
          Here&apos;s what PIRX sees in your running right now.
        </p>
      </div>

      <div className="space-y-3">
        {projections.map((p, i) => (
          <motion.div
            key={p.event}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.15 }}
          >
            <Card>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm text-muted-foreground">{p.event}</p>
                  <p className="text-2xl font-bold tabular-nums">{p.time}</p>
                </div>
                <Badge
                  variant={p.change === "baseline" ? "secondary" : "default"}
                >
                  {p.change}
                </Badge>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <Button size="lg" onClick={onFinish} className="w-full">
        Go to Dashboard <ChevronRight className="ml-2 h-4 w-4" />
      </Button>
    </motion.div>
  );
}

export default function OnboardingStepPage() {
  const router = useRouter();
  const params = useParams();
  const { user, loading } = useAuth();
  const step = Number(params.step) || 1;

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  const goTo = (s: number) => router.push(`/onboarding/${s}`);
  const onNext = () => {
    if (step < TOTAL_STEPS) goTo(step + 1);
  };
  const onBack = () => {
    if (step > 1) goTo(step - 1);
  };
  const onFinish = () => router.push("/dashboard");

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-[80vh] flex flex-col">
      <StepIndicator current={step} total={TOTAL_STEPS} />
      <div className="flex-1">
        <AnimatePresence mode="wait">
          {step === 1 && (
            <WelcomeStep
              key="welcome"
              onNext={onNext}
              userEmail={user.email}
            />
          )}
          {step === 2 && (
            <ConnectStep key="connect" onNext={onNext} onBack={onBack} />
          )}
          {step === 3 && <LoadingStep key="loading" onNext={onNext} />}
          {step === 4 && (
            <BaselineStep key="baseline" onNext={onNext} onBack={onBack} />
          )}
          {step === 5 && <RevealStep key="reveal" onFinish={onFinish} />}
        </AnimatePresence>
      </div>
    </div>
  );
}
