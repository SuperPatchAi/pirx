"use client";

import { useRouter, useParams } from "next/navigation";
import { useState, useEffect } from "react";
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

function WelcomeStep({ onNext }: { onNext: () => void }) {
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

const WEARABLES = [
  { id: "strava", name: "Strava", icon: Activity, connected: false },
  { id: "garmin", name: "Garmin", icon: Watch, connected: false },
  {
    id: "apple_health",
    name: "Apple Health",
    icon: Smartphone,
    connected: false,
  },
  { id: "fitbit", name: "Fitbit", icon: Activity, connected: false },
];

function ConnectStep({
  onNext,
  onBack,
}: {
  onNext: () => void;
  onBack: () => void;
}) {
  const [connected, setConnected] = useState<Set<string>>(new Set());

  const toggleConnect = (id: string) => {
    setConnected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

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
        {WEARABLES.map((w) => {
          const Icon = w.icon;
          const isConnected = connected.has(w.id);
          return (
            <Card
              key={w.id}
              className={`cursor-pointer transition-all ${
                isConnected ? "border-primary bg-primary/5" : ""
              }`}
              onClick={() => toggleConnect(w.id)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="font-medium">{w.name}</span>
                </div>
                {isConnected ? (
                  <Badge variant="default">
                    <Check className="mr-1 h-3 w-3" /> Connected
                  </Badge>
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
          disabled={connected.size === 0}
        >
          Continue <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </motion.div>
  );
}

function LoadingStep({ onNext }: { onNext: () => void }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>;
    intervalId = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(intervalId);
          setTimeout(onNext, 500);
          return 100;
        }
        return p + 2;
      });
    }, 80);
    return () => clearInterval(intervalId);
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

  // Mock detected baseline
  const detected = { event: "5000", time: "20:42", date: "Feb 15, 2026" };

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
          We found a recent race result. Confirm or enter your own.
        </p>
      </div>

      {mode === "detected" && (
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
              <Badge variant="secondary">5K</Badge>
            </div>
            <p className="text-xs text-muted-foreground">{detected.date}</p>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-2">
        <Button
          variant={mode === "detected" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("detected")}
        >
          Use Detected
        </Button>
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
        <Button onClick={onNext} className="flex-1">
          Confirm Baseline <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </motion.div>
  );
}

// Mock projection data for the reveal
const MOCK_PROJECTIONS = [
  { event: "1500m", time: "5:42", change: "-3s" },
  { event: "3K", time: "12:18", change: "-8s" },
  { event: "5K", time: "20:42", change: "baseline" },
  { event: "10K", time: "43:15", change: "-12s" },
];

function RevealStep({ onFinish }: { onFinish: () => void }) {
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
        {MOCK_PROJECTIONS.map((p, i) => (
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
  const step = Number(params.step) || 1;

  const goTo = (s: number) => router.push(`/onboarding/${s}`);
  const onNext = () => {
    if (step < TOTAL_STEPS) goTo(step + 1);
  };
  const onBack = () => {
    if (step > 1) goTo(step - 1);
  };
  const onFinish = () => router.push("/dashboard");

  return (
    <div className="min-h-[80vh] flex flex-col">
      <StepIndicator current={step} total={TOTAL_STEPS} />
      <div className="flex-1">
        <AnimatePresence mode="wait">
          {step === 1 && <WelcomeStep key="welcome" onNext={onNext} />}
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
