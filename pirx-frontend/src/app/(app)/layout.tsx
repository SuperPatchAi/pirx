import { BottomTabBar } from "@/components/layout/bottom-tab-bar";
import { ChatFAB } from "@/components/layout/chat-fab";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-background pb-20">
      <main className="mx-auto max-w-lg px-4 py-6">{children}</main>
      <ChatFAB />
      <BottomTabBar />
    </div>
  );
}
