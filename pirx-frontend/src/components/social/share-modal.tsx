"use client";

import { useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Share2, Copy, Check } from "lucide-react";
import { RaceCard } from "./race-card";

export interface CardData {
  event: string;
  event_display: string;
  projected_time: string;
  supported_range: string;
  improvement_seconds: number;
  twenty_one_day_change: number;
  driver_contributions: {
    name: string;
    display_name: string;
    contribution_seconds: number;
  }[];
  user_display_name?: string;
}

interface ShareModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  cardData: CardData | null;
  percentile?: number | null;
}

export function ShareModal({
  open,
  onOpenChange,
  cardData,
  percentile,
}: ShareModalProps) {
  const [copied, setCopied] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  if (!cardData) return null;

  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/share/${cardData.event}`
      : "";

  async function handleDownload() {
    try {
      const html2canvas = (await import("html2canvas")).default;
      const el = document.getElementById("pirx-race-card");
      if (!el) return;
      const canvas = await html2canvas(el, {
        backgroundColor: "#18181b",
        scale: 2,
      });
      const link = document.createElement("a");
      link.download = `pirx-${cardData!.event_display.toLowerCase().replace(/\s/g, "-")}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    } catch {
      // html2canvas not available
    }
  }

  async function handleShare() {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `My ${cardData!.event_display} Projection`,
          text: `I'm projected to run ${cardData!.event_display} in ${cardData!.projected_time}`,
          url: shareUrl,
        });
        return;
      } catch {
        // User cancelled or share failed
      }
    }
    await handleCopy();
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(
        `My ${cardData!.event_display} projection: ${cardData!.projected_time} | ${cardData!.supported_range} | pirx.app`,
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard failed
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Share Your Projection</DialogTitle>
        </DialogHeader>

        <div className="flex justify-center py-4" ref={cardRef}>
          <RaceCard
            event={cardData.event}
            eventDisplay={cardData.event_display}
            projectedTime={cardData.projected_time}
            supportedRange={cardData.supported_range}
            improvementSeconds={cardData.improvement_seconds}
            twentyOneDayChange={cardData.twenty_one_day_change}
            driverContributions={cardData.driver_contributions}
            percentile={percentile}
            userName={cardData.user_display_name}
          />
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            onClick={handleDownload}
          >
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          <Button variant="outline" className="flex-1" onClick={handleShare}>
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" onClick={handleCopy}>
            {copied ? (
              <Check className="h-4 w-4" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
