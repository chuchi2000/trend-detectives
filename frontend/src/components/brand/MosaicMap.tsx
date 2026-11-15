import { MOSAIC_COAST, MOSAIC_LAYERS, MOSAIC_VIEWBOX } from "@/components/brand/mosaicData";
import type { VariableId } from "@/config/variables";
import { useLanguage, useVariables } from "@/i18n/language";

const GRATICULE_LAT = [15, 20, 25, 30];
const GRATICULE_LON = [-115, -110, -105, -100, -95, -90];
// Misma proyección que generó el mosaico (equirectangular con cos 23.5°).
const LON0 = -118.6;
const LAT1 = 33.2;
const KX = Math.cos((23.5 * Math.PI) / 180);
const S = MOSAIC_VIEWBOX.width / ((-86.2 - LON0) * KX);

/**
 * Mapa-mosaico ILUSTRATIVO de la bienvenida: cada píxel es una celda de un
 * campo simulado. Las cuatro capas se apilan y solo la activa es visible
 * (transición suave de opacidad).
 */
export function MosaicMap({ variable }: { variable: VariableId }) {
  const { lang, t } = useLanguage();
  const name = useVariables()[variable].name;
  return (
    <div className="overflow-hidden rounded-[18px] bg-[#D9E7EA]">
      <svg
        viewBox={`0 0 ${MOSAIC_VIEWBOX.width} ${MOSAIC_VIEWBOX.height}`}
        className="block h-auto w-full"
        role="img"
        aria-label={t.welcome.mosaicAria(lang === "en" ? name : name.toLowerCase())}
      >
        <path d={MOSAIC_COAST} fill="#E3E9E5" />
        <g stroke="#C3D2CE" strokeWidth="1" fill="none">
          {GRATICULE_LAT.map((lat) => (
            <path key={lat} d={`M0 ${(LAT1 - lat) * S}H${MOSAIC_VIEWBOX.width}`} />
          ))}
          {GRATICULE_LON.map((lon) => (
            <path key={lon} d={`M${(lon - LON0) * KX * S} 0V${MOSAIC_VIEWBOX.height}`} />
          ))}
        </g>
        {Object.entries(MOSAIC_LAYERS).map(([id, layers]) => (
          <g key={id} style={{ opacity: id === variable ? 1 : 0, transition: "opacity 700ms ease" }}>
            {layers.map(([color, d]) => (
              <path key={color} fill={color} d={d} />
            ))}
          </g>
        ))}
        <path d={MOSAIC_COAST} fill="none" stroke="#7E948E" strokeWidth="1" strokeLinejoin="round" />
        <g fontSize="12" fill="#4A625C" fontFamily="Archivo, system-ui, sans-serif">
          {GRATICULE_LAT.map((lat) => (
            <text key={lat} x="10" y={(LAT1 - lat) * S - 5}>
              {lat}° N
            </text>
          ))}
          {GRATICULE_LON.map((lon) => (
            <text key={lon} x={(lon - LON0) * KX * S} y="20" textAnchor="middle">
              {Math.abs(lon)}° {t.welcome.west}
            </text>
          ))}
        </g>
      </svg>
    </div>
  );
}
