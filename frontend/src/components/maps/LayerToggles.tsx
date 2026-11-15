import { Switch } from "@/components/ui/switch";
import { useAtlas } from "@/context/AtlasStateContext";

/** Activar y desactivar capas del mapa. */
export function LayerToggles() {
  const { state, dispatch } = useAtlas();
  return (
    <fieldset className="flex flex-col">
      <legend className="mb-1 font-display text-sm font-semibold text-texto">Capas del mapa</legend>
      <Switch
        label="Datos de la variable"
        checked={state.layers.data}
        onChange={() => dispatch({ type: "toggleLayer", layer: "data" })}
      />
      <Switch
        label="Límites estatales"
        checked={state.layers.states}
        onChange={() => dispatch({ type: "toggleLayer", layer: "states" })}
      />
      <Switch
        label="Límites municipales"
        description={state.region ? undefined : "Elige primero un estado"}
        checked={state.layers.municipalities}
        onChange={() => dispatch({ type: "toggleLayer", layer: "municipalities" })}
      />
    </fieldset>
  );
}
