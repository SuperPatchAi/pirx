"use client";

import { useEffect, useState, useCallback } from "react";

export function useNotifications() {
  const [permission, setPermission] =
    useState<NotificationPermission>("default");
  const [supported, setSupported] = useState(false);

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

  return { permission, supported, requestPermission, registerServiceWorker };
}
