/** Glosario ambiental del modo Explorador (definiciones generales). */
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
