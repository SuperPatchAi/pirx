"use client";

import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { motion } from "framer-motion";

export function ChatFAB() {
  return (
    <motion.div
      data-tour="chat-fab"
      className="fixed bottom-20 right-4 z-50 pb-[env(safe-area-inset-bottom)]"
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.3 }}
    >
      <Link
        href="/chat"
        className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 active:scale-95"
      >
        <MessageCircle className="h-6 w-6" />
      </Link>
    </motion.div>
  );
}
