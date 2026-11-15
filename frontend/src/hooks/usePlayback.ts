import { useEffect, useState } from "react";

import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLES } from "@/config/variables";
import { stepWithin } from "@/lib/dates";

/**
 * Animación temporal: avanza un mes cada `intervalMs` mientras está activa y
 * se detiene sola al llegar al último mes disponible de la variable.
 * Solo empieza cuando la persona pulsa "Reproducir".
 */
export function usePlayback(intervalMs = 1400): { playing: boolean; toggle: () => void } {
  const { state, dispatch } = useAtlas();
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => {
      const next = stepWithin(state.date, 1, VARIABLES[state.variable].availability);
      if (next) dispatch({ type: "setDate", date: next });
      else setPlaying(false);
    }, intervalMs);
    return () => window.clearTimeout(timer);
  }, [playing, state.date, state.variable, dispatch, intervalMs]);

  return { playing, toggle: () => setPlaying((p) => !p) };
}
