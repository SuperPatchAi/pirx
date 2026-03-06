"use client";

import { useEffect, useState, useCallback } from "react";

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const array = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    array[i] = raw.charCodeAt(i);
  }
  return array;
}

export function useNotifications() {
  const [permission, setPermission] =
    useState<NotificationPermission>("default");
  const [supported, setSupported] = useState(false);
  const [subscribed, setSubscribed] = useState(false);

  useEffect(() => {
    const isSupported =
      "Notification" in window && "serviceWorker" in navigator;
    setSupported(isSupported);
    if (isSupported) {
      setPermission(Notification.permission);
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if (!supported) return "denied" as NotificationPermission;
    const result = await Notification.requestPermission();
    setPermission(result);
    return result;
  }, [supported]);

  const registerServiceWorker = useCallback(async () => {
    if (!("serviceWorker" in navigator)) return null;
    try {
      const registration = await navigator.serviceWorker.register("/sw.js");
      return registration;
    } catch {
      return null;
    }
  }, []);

  const subscribeToPush = useCallback(
    async (token: string) => {
      if (!supported || !VAPID_PUBLIC_KEY) return false;
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY) as BufferSource,
        });
        const json = subscription.toJSON();
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/notifications/subscribe`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              endpoint: json.endpoint,
              keys: json.keys,
            }),
          }
        );
        const data = await res.json();
        const ok = data.status === "subscribed";
        setSubscribed(ok);
        return ok;
      } catch {
        return false;
      }
    },
    [supported]
  );

  const unsubscribeFromPush = useCallback(
    async (token: string) => {
      if (!supported) return false;
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription =
          await registration.pushManager.getSubscription();
        if (!subscription) return true;
        const json = subscription.toJSON();
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/notifications/unsubscribe`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              endpoint: json.endpoint,
              keys: json.keys,
            }),
          }
        );
        await subscription.unsubscribe();
        setSubscribed(false);
        return true;
      } catch {
        return false;
      }
    },
    [supported]
  );

  return {
    permission,
    supported,
    subscribed,
    requestPermission,
    registerServiceWorker,
    subscribeToPush,
    unsubscribeFromPush,
  };
}
