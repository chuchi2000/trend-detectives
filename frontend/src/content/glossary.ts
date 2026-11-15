/** Glosario ambiental del modo Explorador (definiciones generales). */
import type { Lang } from "@/lib/dates";

export interface GlossaryTerm {
  term: string;
  definition: string;
}

export const GLOSSARY: GlossaryTerm[] = [
  {
    term: "Precipitación",
    definition: "Agua que cae de la atmósfera a la superficie en forma de lluvia, llovizna, granizo o nieve. Se mide en milímetros.",
  },
  {
    term: "Evapotranspiración",
    definition: "Suma del agua que se evapora del suelo y de la que las plantas liberan por sus hojas (transpiración).",
  },
  {
    term: "Dióxido de nitrógeno (NO₂)",
    definition: "Gas de color pardo que se forma al quemar combustibles y en los rayos. En la atmósfera baja indica contaminación del aire.",
  },
  {
    term: "Temperatura superficial",
    definition: "Temperatura de la superficie del terreno (suelo, rocas, vegetación, techos). Puede ser muy distinta de la temperatura del aire.",
  },
  {
    term: "Satélite",
    definition: "Objeto que gira alrededor de la Tierra. Los satélites de observación llevan instrumentos que miden la luz y el calor que emite o refleja el planeta.",
  },
  {
    term: "Teledetección",
    definition: "Obtener información de algo sin tocarlo, por ejemplo midiendo desde un satélite la radiación que viene de la superficie.",
  },
  {
    term: "Resolución espacial",
    definition: "Tamaño del área que representa cada píxel del mapa. Con 1 km, cada cuadrito resume lo que ocurre en un kilómetro cuadrado.",
  },
  {
    term: "Resolución temporal",
    definition: "Cada cuánto tiempo hay un nuevo dato: diario, cada 8 días, mensual…",
  },
  {
    term: "Píxel",
    definition: "Cada uno de los cuadritos que forman una imagen o un mapa de datos. Tiene un solo valor.",
  },
  {
    term: "Columna troposférica",
    definition: "Cantidad total de un gas en una columna de aire imaginaria que va del suelo hasta el límite de la troposfera, la capa más baja de la atmósfera.",
  },
  {
    term: "Compuesto de 8 días",
    definition: "Imagen que resume varias pasadas del satélite durante 8 días para tener menos huecos por nubes.",
  },
  {
    term: "Sin dato",
    definition: "Zona donde no hubo una medición confiable (por nubes, por ser agua o ciudad, etc.). No significa cero.",
  },
];

const GLOSSARY_EN: GlossaryTerm[] = [
  {
    term: "Precipitation",
    definition: "Water that falls from the atmosphere to the surface as rain, drizzle, hail or snow. It is measured in millimeters.",
  },
  {
    term: "Evapotranspiration",
    definition: "The sum of the water that evaporates from the soil and the water plants release through their leaves (transpiration).",
  },
  {
    term: "Nitrogen dioxide (NO₂)",
    definition: "A brownish gas formed when fuels are burned and by lightning. In the lower atmosphere it indicates air pollution.",
  },
  {
    term: "Land surface temperature",
    definition: "Temperature of the ground surface (soil, rocks, vegetation, roofs). It can be very different from the air temperature.",
  },
  {
    term: "Satellite",
    definition: "An object that orbits the Earth. Observation satellites carry instruments that measure the light and heat the planet emits or reflects.",
  },
  {
    term: "Remote sensing",
    definition: "Getting information about something without touching it, for example by measuring from a satellite the radiation coming from the surface.",
  },
  {
    term: "Spatial resolution",
    definition: "The size of the area each map pixel represents. At 1 km, each square summarizes what happens in one square kilometer.",
  },
  {
    term: "Temporal resolution",
    definition: "How often there is a new value: daily, every 8 days, monthly…",
  },
  {
    term: "Pixel",
    definition: "Each of the small squares that make up an image or a data map. It has a single value.",
  },
  {
    term: "Tropospheric column",
    definition: "The total amount of a gas in an imaginary column of air from the ground to the top of the troposphere, the lowest layer of the atmosphere.",
  },
  {
    term: "8-day composite",
    definition: "An image that summarizes several satellite passes over 8 days to have fewer gaps caused by clouds.",
  },
  {
    term: "No data",
    definition: "An area where there was no reliable measurement (because of clouds, water, a city, etc.). It does not mean zero.",
  },
];

/** Glosario en cada idioma. */
export const GLOSSARY_BY_LANG: Record<Lang, GlossaryTerm[]> = { es: GLOSSARY, en: GLOSSARY_EN };
