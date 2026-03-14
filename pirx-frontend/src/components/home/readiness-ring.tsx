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
        <h3 className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Readiness
        </h3>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div className="relative">
          <svg
            viewBox="0 0 120 120"
            className="h-[120px] w-[120px]"
            style={{
              filter: "drop-shadow(0 0 8px rgba(15,170,234,0.4))",
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
                <stop offset="0%" stopColor="#0faaea" />
                <stop offset="100%" stopColor="#3dc0f5" />
              </linearGradient>
            </defs>
            <circle
              cx={60}
              cy={60}
              r={52}
              fill="none"
              stroke="#232522"
              strokeWidth={8}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
            />
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
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-5xl tracking-wide text-foreground">
              {displayScore}
            </span>
            <span className="text-[11px] text-muted-foreground">/ 100</span>
          </div>
        </div>

        <div className="w-full space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Stamina
            </span>
            <span className="text-xs font-medium text-foreground">
              100% <span className="text-muted-foreground">→</span> <span className="text-[#dc9518]">{Math.round(displayStamina)}%</span>
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-[#282b27] shadow-[inset_0px_1px_3px_0px_rgba(10,11,9,0.4)]">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-primary to-[#dc9518]"
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
