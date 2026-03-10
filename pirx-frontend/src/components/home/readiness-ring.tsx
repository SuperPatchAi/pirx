"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const CIRCUMFERENCE = 2 * Math.PI * 52;

export interface ReadinessRingProps {
  score: number | null;
  staminaPct?: number | null;
}

export function ReadinessRing({ score, staminaPct }: ReadinessRingProps) {
  const displayScore = Math.min(100, Math.max(0, score ?? 0));
  const displayStamina = Math.min(100, Math.max(0, staminaPct ?? 0));
  const strokeDashoffset = CIRCUMFERENCE * (1 - displayScore / 100);

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          READINESS
        </h3>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div className="relative">
          <svg
            viewBox="0 0 120 120"
            className="h-[120px] w-[120px]"
            style={{
              filter: "drop-shadow(0 0 8px rgba(34,197,94,0.4))",
            }}
          >
            <defs>
              <linearGradient
                id="readiness-gradient"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="100%"
              >
                <stop offset="0%" stopColor="#16a34a" />
                <stop offset="100%" stopColor="#22c55e" />
              </linearGradient>
            </defs>
            {/* Background track */}
            <circle
              cx={60}
              cy={60}
              r={52}
              fill="none"
              stroke="hsl(var(--secondary))"
              strokeWidth={8}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
            />
            {/* Animated progress circle */}
            <motion.circle
              cx={60}
              cy={60}
              r={52}
              fill="none"
              stroke="url(#readiness-gradient)"
              strokeWidth={8}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={strokeDashoffset}
              transform="rotate(-90 60 60)"
              initial={{ strokeDashoffset: CIRCUMFERENCE }}
              animate={{ strokeDashoffset }}
              transition={{
                duration: 1.2,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
          </svg>
          {/* Centered score */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-[#22c55e]">
              {displayScore}
            </span>
            <span className="text-sm text-muted-foreground">/100</span>
          </div>
        </div>

        {/* Stamina bar */}
        <div className="w-full space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              STAMINA
            </span>
            <span className="text-xs text-muted-foreground">
              {Math.round(displayStamina)}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
            <motion.div
              className="h-full rounded-full bg-[#22c55e]"
              initial={{ width: 0 }}
              animate={{ width: `${displayStamina}%` }}
              transition={{
                duration: 0.8,
                delay: 0.3,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
