/**
 * Contenido educativo del modo Explorador.
 *
 * Regla: cada dato curioso es verificable y lleva su fuente. Si agregas uno,
 * agrega también la fuente; si no la tienes, no lo publiques.
 */
import type { VariableId } from "@/config/variables";

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
