"use client";
import { useCallback, useSyncExternalStore } from "react";

const subscribe = (cb: () => void) => {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
};

/** selected index key kept in the URL hash (#metal / #nifty50), shared by every page */
export function useHashKey(keys: string[]) {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash.slice(1), () => "");
  const key = keys.includes(hash) ? hash : keys[0];
  const pick = useCallback((k: string) => {
    window.history.replaceState(null, "", "#" + k);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }, []);
  return [key, pick] as const;
}
