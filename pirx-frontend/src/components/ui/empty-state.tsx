import { Card, CardContent } from "@/components/ui/card";
import { type LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  message: string;
  submessage?: string;
}

export function EmptyState({ icon: Icon, message, submessage }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-8 text-center">
        {Icon && <Icon className="h-8 w-8 text-muted-foreground/50 mb-3" />}
        <p className="text-sm font-medium text-muted-foreground">{message}</p>
        {submessage && (
          <p className="text-xs text-muted-foreground/70 mt-1">{submessage}</p>
        )}
      </CardContent>
    </Card>
  );
}
