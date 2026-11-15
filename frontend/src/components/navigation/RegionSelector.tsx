import { Select } from "@/components/ui/select";
import { useAtlas } from "@/context/AtlasStateContext";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";

/**
 * Selección de región: todo el país, un estado o un municipio (INEGI).
 * Si los límites aún no están cargados en el backend, lo explica.
 */
export function RegionSelector() {
  const { state, dispatch } = useAtlas();
  const states = useApi((signal) => api.regions("state", undefined, signal), []);
  const stateCode = state.region?.code.slice(0, 2) ?? "";
  const municipalities = useApi(
    stateCode ? (signal) => api.regions("municipality", stateCode, signal) : null,
    [stateCode],
  );

  if (states.status === "success" && !states.data.available) {
    return (
      <p className="rounded-xl bg-panel-2 p-3 text-sm text-texto-suave">
        Por ahora solo hay estadísticas de todo el país: los límites estatales y municipales del INEGI aún no están
        cargados en el servidor.
      </p>
    );
  }

  const stateItems = states.data?.items ?? [];
  const muniItems = municipalities.data?.items ?? [];
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <Select
        label="Región"
        value={stateCode}
        onChange={(e) => {
          const item = stateItems.find((s) => s.code === e.target.value);
          dispatch({ type: "setRegion", region: item ? { level: "state", code: item.code, name: item.name } : null });
        }}
        options={[{ value: "", label: "Todo México" }, ...stateItems.map((s) => ({ value: s.code, label: s.name }))]}
      />
      <Select
        label="Municipio"
        value={state.region?.level === "municipality" ? state.region.code : ""}
        disabled={!stateCode || muniItems.length === 0}
        onChange={(e) => {
          const item = muniItems.find((m) => m.code === e.target.value);
          const parent = stateItems.find((s) => s.code === stateCode);
          dispatch({
            type: "setRegion",
            region: item
              ? { level: "municipality", code: item.code, name: item.name }
              : parent
                ? { level: "state", code: parent.code, name: parent.name }
                : null,
          });
        }}
        options={[
          { value: "", label: stateCode ? "Todo el estado" : "Elige un estado" },
          ...muniItems.map((m) => ({ value: m.code, label: m.name })),
        ]}
      />
    </div>
  );
}
