"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "pirx-consent-dismissed";

export function ConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  }

  return (
    <div className="fixed inset-x-0 bottom-20 z-50 px-4">
      <Card className="mx-auto max-w-lg border-border/50 bg-card/95 backdrop-blur">
        <CardContent className="flex items-center justify-between gap-4 py-3">
          <p className="text-xs text-muted-foreground">
            PIRX uses essential cookies for authentication. We do not use
            tracking cookies.
          </p>
          <Button size="sm" variant="secondary" onClick={dismiss}>
            Got it
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
