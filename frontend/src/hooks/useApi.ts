import { useEffect, useState, type DependencyList } from "react";

import { useLanguage } from "@/i18n/language";
import { ApiError } from "@/services/api";

export type AsyncState<T> =
  | { status: "idle"; data: null; error: null }
  | { status: "loading"; data: T | null; error: null }
  | { status: "success"; data: T; error: null }
  | { status: "error"; data: null; error: ApiError };

/**
 * Ejecuta una consulta a la API cada vez que cambian sus dependencias.
 * Cancela la consulta anterior (AbortController) para que una respuesta
 * lenta nunca sobrescriba una más reciente. Si `fetcher` es null no consulta.
 * También vuelve a consultar al cambiar el idioma (la API responde en ese idioma).
 */
export function useApi<T>(fetcher: ((signal: AbortSignal) => Promise<T>) | null, deps: DependencyList): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: "idle", data: null, error: null });
  const { lang, t } = useLanguage();

  useEffect(() => {
    if (!fetcher) {
      setState({ status: "idle", data: null, error: null });
      return;
    }
    const controller = new AbortController();
    setState((previous) => ({ status: "loading", data: previous.data, error: null }));
    fetcher(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "success", data, error: null });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || (error as Error).name === "AbortError") return;
        const apiError =
          error instanceof ApiError ? error : new ApiError(t.api.unexpected, "desconocido", 0);
        setState({ status: "error", data: null, error: apiError });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, lang]);

  return state;
}
