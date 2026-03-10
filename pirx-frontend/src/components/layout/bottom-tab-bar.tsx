"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, BarChart3, Heart, Settings, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/performance", label: "Performance", icon: BarChart3 },
  { href: "/coach", label: "Coach", icon: Users },
  { href: "/physiology", label: "Physiology", icon: Heart },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function BottomTabBar() {
  const pathname = usePathname();

  return (
    <nav data-tour="tab-bar" className="fixed bottom-0 left-0 right-0 z-50 border-t border-border/60 bg-card/90 backdrop-blur-xl pb-[env(safe-area-inset-bottom)]">
      <div className="flex h-14 items-center justify-around">
        {tabs.map(({ href, label, icon: Icon }) => {
          const isActive = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex flex-1 flex-col items-center gap-0.5 py-1 text-[10px] font-medium tracking-wide transition-colors",
                isActive
                  ? "text-green-500"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className={cn("h-5 w-5", isActive && "drop-shadow-[0_0_6px_rgba(34,197,94,0.4)]")} />
              <span className="uppercase">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
