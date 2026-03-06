"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Uncaught error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
          <AlertTriangle className="h-10 w-10 text-destructive" />
          <h2 className="text-lg font-semibold">Something went wrong</h2>
          <p className="text-sm text-muted-foreground">
            An unexpected error occurred. Please try again.
          </p>
          <Button onClick={reset} variant="outline">
            Try Again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
