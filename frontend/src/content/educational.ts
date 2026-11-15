/**
 * Contenido educativo del modo Explorador.
 *
 * Regla: cada dato curioso es verificable y lleva su fuente. Si agregas uno,
 * agrega también la fuente; si no la tienes, no lo publiques.
 */
import type { VariableId } from "@/config/variables";
import type { Lang } from "@/lib/dates";

export interface Source {
  label: string;
  url: string;
}

export interface Fact {
  text: string;
  source: Source;
}

export interface VariableContent {
  whatWeSee: string;
  howToRead: string;
  facts: Fact[];
  questions: string[];
}

const EARTHDATA_IMERG = {
  label: "NASA Earthdata: GPM IMERG mensual",
  url: "https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergm-07",
};
const GPM_FINAL = { label: "NASA GPM: IMERG Final Run", url: "https://gpm.nasa.gov/taxonomy/term/1417" };
const EARTHDATA_OMNO2 = {
  label: "NASA Earthdata: OMI/Aura NO₂ (OMNO2d)",
  url: "https://www.earthdata.nasa.gov/data/catalog/ges-disc-omno2d-004",
};
const EARTHDATA_MOD16 = {
  label: "NASA Earthdata: MODIS MOD16A2GF",
  url: "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod16a2gf-061",
};
const EARTHDATA_MOD11 = {
  label: "NASA Earthdata: MODIS MOD11A2",
  url: "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod11a2-061",
};
const TERRA_DRIFT = { label: "NASA Terra: deriva orbital", url: "https://terra.nasa.gov/?p=190003" };

export const EDUCATIONAL: Record<VariableId, VariableContent> = {
  precipitation: {
    whatWeSee:
      "La cantidad de agua que cae del cielo, como lluvia, granizo o nieve, sumada durante todo el mes en cada zona del país.",
    howToRead:
      "Cada color representa un rango de milímetros acumulados en el mes. Un milímetro equivale a un litro de agua por cada metro cuadrado de suelo. Los colores más oscuros indican más lluvia.",
    facts: [
      {
        text: "IMERG estima la lluvia de todo el planeta cada media hora en cuadros de 0.1° (unos 10 km); el Atlas usa su total mensual.",
        source: EARTHDATA_IMERG,
      },
      {
        text: "El producto que usamos combina mediciones de varios satélites y, en su versión final, se ajusta con datos mensuales de pluviómetros en tierra.",
        source: GPM_FINAL,
      },
    ],
    questions: [
      "Compara enero con julio. ¿En qué parte del país cambia más la lluvia de un mes a otro?",
      "Busca la zona más seca y la más lluviosa en septiembre. ¿Qué diferencias de relieve o cercanía al mar hay entre ellas?",
      "Reproduce la animación de un año completo. ¿En qué mes empieza la temporada de lluvias en el sur?",
    ],
  },
  no2: {
    whatWeSee:
      "La cantidad de dióxido de nitrógeno (NO₂), un gas contaminante, que hay en la columna de aire sobre cada zona, desde el suelo hasta la parte baja de la atmósfera.",
    howToRead:
      "Los colores más oscuros indican más NO₂ en el aire. Ojo: el satélite mide toda la columna de aire, no lo que respiramos a nivel de la calle. Las zonas sin color no tuvieron suficientes días despejados para medir.",
    facts: [
      {
        text: "En la parte baja de la atmósfera, el NO₂ se produce en procesos de combustión y también en los rayos; por eso se usa como indicador de mala calidad del aire.",
        source: EARTHDATA_OMNO2,
      },
      {
        text: "El instrumento OMI no puede medir a través de las nubes: el mapa solo usa días en que la fracción de nubes fue menor a 30 %.",
        source: EARTHDATA_OMNO2,
      },
    ],
    questions: [
      "Ubica las ciudades más grandes del país. ¿Coinciden con los colores más oscuros?",
      "Compara un mes de invierno con uno de verano en la misma ciudad. ¿Ves diferencias?",
      "¿Por qué crees que hay menos días válidos en la temporada de lluvias?",
    ],
  },
  evapotranspiration: {
    whatWeSee:
      "El agua que regresa a la atmósfera desde el suelo y las plantas: suma la evaporación del suelo y la transpiración de las hojas.",
    howToRead:
      "Los colores más oscuros indican que más agua pasó del suelo y la vegetación al aire durante el mes. Las ciudades, los cuerpos de agua y los desiertos sin vegetación aparecen sin dato porque el modelo no los calcula.",
    facts: [
      {
        text: "Este dato no se mide directamente: se calcula con un modelo físico (Penman–Monteith) que combina observaciones del satélite con datos meteorológicos.",
        source: EARTHDATA_MOD16,
      },
      {
        text: "El producto original suma la evapotranspiración de 8 días; el Atlas reparte esos días entre los meses que corresponden.",
        source: EARTHDATA_MOD16,
      },
    ],
    questions: [
      "Compara el mapa de evapotranspiración con el de precipitación del mismo mes. ¿Se parecen?",
      "¿En qué regiones la evapotranspiración se mantiene alta casi todo el año?",
    ],
  },
  temperature: {
    whatWeSee:
      "Qué tan caliente está la superficie del terreno durante la mañana, cuando pasa el satélite. No es la temperatura del aire que reporta el pronóstico.",
    howToRead:
      "Los colores rojos más oscuros indican superficies más calientes. Las zonas sin dato estuvieron cubiertas por nubes en la mayoría de los pasos del satélite.",
    facts: [
      {
        text: "Cada valor del producto original es el promedio de las temperaturas diarias de un periodo de 8 días.",
        source: EARTHDATA_MOD11,
      },
      {
        text: "Desde 2020 el satélite Terra pasa cada vez más temprano; una hora de paso más temprana tiende a registrar superficies más frías.",
        source: TERRA_DRIFT,
      },
    ],
    questions: [
      "¿Por qué el norte del país se ve más caliente en mayo que el centro, aunque ambos estén lejos del mar?",
      "Compara una zona con mucha vegetación y una zona desértica en el mismo mes. ¿Cuál se calienta más?",
    ],
  },
};

const EARTHDATA_IMERG_EN = { ...EARTHDATA_IMERG, label: "NASA Earthdata: monthly GPM IMERG" };
const TERRA_DRIFT_EN = { ...TERRA_DRIFT, label: "NASA Terra: orbital drift" };

const EDUCATIONAL_EN: Record<VariableId, VariableContent> = {
  precipitation: {
    whatWeSee:
      "The amount of water that falls from the sky, as rain, hail or snow, added up over the whole month in each part of the country.",
    howToRead:
      "Each color is a range of millimeters accumulated over the month. One millimeter equals one liter of water per square meter of ground. Darker colors mean more rain.",
    facts: [
      {
        text: "IMERG estimates rainfall over the whole planet every half hour in 0.1° boxes (about 10 km); the Atlas uses its monthly total.",
        source: EARTHDATA_IMERG_EN,
      },
      {
        text: "The product we use combines measurements from several satellites and, in its final version, is adjusted with monthly rain-gauge data on the ground.",
        source: GPM_FINAL,
      },
    ],
    questions: [
      "Compare January with July. In which part of the country does rainfall change the most from one month to another?",
      "Find the driest and the rainiest areas in September. What differences in terrain or distance to the sea are there between them?",
      "Play the animation for a whole year. In which month does the rainy season start in the south?",
    ],
  },
  no2: {
    whatWeSee:
      "The amount of nitrogen dioxide (NO₂), a polluting gas, in the column of air above each area, from the ground to the lower part of the atmosphere.",
    howToRead:
      "Darker colors mean more NO₂ in the air. Note: the satellite measures the whole air column, not what we breathe at street level. Areas without color did not have enough clear days to measure.",
    facts: [
      {
        text: "In the lower atmosphere, NO₂ is produced by combustion and also by lightning; that is why it is used as an indicator of poor air quality.",
        source: EARTHDATA_OMNO2,
      },
      {
        text: "The OMI instrument cannot see through clouds: the map only uses days when the cloud fraction was below 30 %.",
        source: EARTHDATA_OMNO2,
      },
    ],
    questions: [
      "Locate the country's largest cities. Do they match the darkest colors?",
      "Compare a winter month with a summer month in the same city. Do you see differences?",
      "Why do you think there are fewer valid days in the rainy season?",
    ],
  },
  evapotranspiration: {
    whatWeSee:
      "The water that returns to the atmosphere from the soil and plants: evaporation from the soil plus transpiration from leaves.",
    howToRead:
      "Darker colors mean more water moved from the soil and vegetation into the air during the month. Cities, water bodies and unvegetated deserts show no data because the model does not compute them.",
    facts: [
      {
        text: "This value is not measured directly: it is computed with a physical model (Penman–Monteith) that combines satellite observations with meteorological data.",
        source: EARTHDATA_MOD16,
      },
      {
        text: "The original product adds up evapotranspiration over 8 days; the Atlas spreads those days over the months they belong to.",
        source: EARTHDATA_MOD16,
      },
    ],
    questions: [
      "Compare the evapotranspiration map with the precipitation map for the same month. Do they look alike?",
      "In which regions does evapotranspiration stay high almost all year?",
    ],
  },
  temperature: {
    whatWeSee:
      "How hot the ground surface is in the morning, when the satellite passes over. It is not the air temperature given in the weather forecast.",
    howToRead:
      "Darker red colors mean hotter surfaces. Areas without data were covered by clouds during most of the satellite's passes.",
    facts: [
      {
        text: "Each value of the original product is the average of the daily temperatures over an 8-day period.",
        source: EARTHDATA_MOD11,
      },
      {
        text: "Since 2020 the Terra satellite passes earlier and earlier; an earlier overpass tends to record cooler surfaces.",
        source: TERRA_DRIFT_EN,
      },
    ],
    questions: [
      "Why does the north of the country look hotter in May than the center, even though both are far from the sea?",
      "Compare an area with lots of vegetation and a desert area in the same month. Which one heats up more?",
    ],
  },
};

/** Contenido educativo en cada idioma. */
export const EDUCATIONAL_BY_LANG: Record<Lang, Record<VariableId, VariableContent>> = {
  es: EDUCATIONAL,
  en: EDUCATIONAL_EN,
};
