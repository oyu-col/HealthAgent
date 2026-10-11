import { useCallback, useEffect, useState } from "react";
import { requestJson } from "./api";

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "操作未完成，请稍后重试。";
}

export function useResource<T>(path: string | null, token: string) {
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<{
    path: string | null;
    data: T | null;
    loading: boolean;
    error: string | null;
  }>({ path, data: null, loading: !!path, error: null });
  const reload = useCallback(() => setVersion((value) => value + 1), []);
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    let active = true;
    setState((previous) => ({
      path,
      data: previous.path === path ? previous.data : null,
      loading: true,
      error: null,
    }));
    requestJson<T>(path, token, { signal: controller.signal })
      .then((data) => {
        if (active) setState({ path, data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (active)
          setState({
            path,
            data: null,
            loading: false,
            error: errorMessage(error),
          });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [path, token, version]);
  return {
    ...(state.path === path
      ? state
      : { path, data: null, loading: !!path, error: null }),
    reload,
  };
}

export function formatDate(value: string, timezone?: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(value));
}

export function localDateTime() {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}
