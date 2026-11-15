import { useCallback, useEffect, useState } from "react";

export type Route = "inicio" | "atlas";

function routeFromPath(pathname: string): Route {
  return pathname.replace(/\/+$/, "").endsWith("/atlas") ? "atlas" : "inicio";
}

/**
 * Navegación mínima con la API de historial del navegador: "/" es la
 * bienvenida y "/atlas" el área de exploración. Con solo dos pantallas no
 * hace falta una librería de rutas.
 */
export function useRoute(): [Route, (to: Route, search?: string) => void] {
  const [route, setRoute] = useState<Route>(() => routeFromPath(window.location.pathname));

  useEffect(() => {
    const onPop = () => setRoute(routeFromPath(window.location.pathname));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback((to: Route, search = "") => {
    const path = to === "atlas" ? "/atlas" : "/";
    window.history.pushState({}, "", `${path}${search}`);
    setRoute(to);
    window.scrollTo(0, 0);
  }, []);

  return [route, navigate];
}
