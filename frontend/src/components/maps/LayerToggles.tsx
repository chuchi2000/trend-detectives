import { Switch } from "@/components/ui/switch";
import { useAtlas } from "@/context/AtlasStateContext";
import { useLanguage } from "@/i18n/language";

/** Activar y desactivar capas del mapa. */
export function LayerToggles() {
  const { state, dispatch } = useAtlas();
  const { t } = useLanguage();
  return (
    <fieldset className="flex flex-col">
      <legend className="mb-1 font-display text-sm font-semibold text-texto">{t.layers.title}</legend>
      <Switch
        label={t.layers.data}
        checked={state.layers.data}
        onChange={() => dispatch({ type: "toggleLayer", layer: "data" })}
      />
      <Switch
        label={t.layers.states}
        checked={state.layers.states}
        onChange={() => dispatch({ type: "toggleLayer", layer: "states" })}
      />
      <Switch
        label={t.layers.municipalities}
        description={state.region ? undefined : t.layers.chooseState}
        checked={state.layers.municipalities}
        onChange={() => dispatch({ type: "toggleLayer", layer: "municipalities" })}
      />
    </fieldset>
  );
}
