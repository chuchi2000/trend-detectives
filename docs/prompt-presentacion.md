# Prompt: presentación de 5 minutos del Atlas Ambiental de México

> Copia todo este archivo y pégalo en el asistente que vaya a preparar la presentación.
> Las cifras vienen de los datos reales del proyecto (noviembre de 2026); no las cambies.

---

## Tu tarea

Prepara una presentación **hablada de 5 minutos como máximo** sobre el **Atlas Ambiental de
México**, para un jurado de hackathon con formación técnica pero no especialista en clima.
El foco son **los modelos matemáticos** y **cómo se procesaron los datos de NASA**. La
interfaz se menciona solo como el lugar donde se ven los resultados.

Entrega:

1. **Guion hablado** dividido en bloques con su tiempo (total ≤ 5:00, unas 650–700 palabras
   a ritmo normal). Español claro, frases cortas, sin jerga sin explicar.
2. **Esquema de 6–7 diapositivas**: título, 2–4 ideas por diapositiva y la imagen o gráfica
   sugerida (por ejemplo, una captura del mapa de tendencia).
3. **Tres preguntas probables del jurado** con una respuesta de 2–3 frases cada una.

Reglas:

- Usa solo los datos de este documento. No inventes cifras, fuentes ni resultados.
- Explica cada método con una idea intuitiva antes de la fórmula. Muestra como máximo una
  fórmula por diapositiva.
- Di las limitaciones con honestidad (sección «Limitaciones»): son parte del rigor.
- No digas que algo «causa» otra cosa: el proyecto mide tendencias y correlaciones, no causas.

## Estructura sugerida del tiempo

| Bloque | Tiempo | Contenido |
|---|---|---|
| 1. Problema y propuesta | 0:00–0:40 | Qué es el Atlas y por qué importa |
| 2. Datos de NASA | 0:40–1:30 | Cuatro variables, productos y periodo |
| 3. Procesamiento | 1:30–2:30 | De archivos satelitales a un cubo comparable |
| 4. Modelos matemáticos | 2:30–4:00 | Estadística, tendencias y significancia |
| 5. Resultados y validación | 4:00–4:40 | Lo que encontramos y cómo sabemos que es correcto |
| 6. Cierre | 4:40–5:00 | Limitaciones y siguiente paso |

## 1. El proyecto en una frase

Un atlas web que convierte observaciones satelitales de NASA de **2000 a 2025** en mapas,
estadísticas y **tendencias con significancia estadística** de cuatro variables ambientales
para todo México. Tiene un modo **Explorador** (público general y escuelas) y un modo
**Científico** (series de tiempo, pruebas estadísticas, metadatos y exportación de datos).
Funciona en español e inglés.

## 2. Datos: cuatro productos de NASA

| Variable | Producto NASA | Resolución nativa | Periodo usado |
|---|---|---|---|
| Precipitación | GPM IMERG Final mensual V07 (GPM_3IMERGM) | 0.1° (≈ 10 km), mensual | 2000-01 a 2025-09 |
| NO₂ (contaminación del aire) | OMI/Aura OMNO2d V004, columna troposférica | 0.25° (≈ 25 km), diario | 2004-10 a 2025-12 |
| Evapotranspiración | MODIS/Terra MOD16A2GF v061 | 500 m, compuestos de 8 días | 2000-03 a 2025-12 |
| Temperatura de la superficie | MODIS/Terra MOD11A2 v061 (LST diurna) | 1 km, compuestos de 8 días | 2000-03 a 2025-12 |

Acceso: precipitación, evapotranspiración y temperatura se calcularon en **Google Earth
Engine** a partir de las colecciones de NASA; NO₂ se descargó con **earthaccess** desde NASA
GES DISC. Cada producto se auditó contra el catálogo CMR de NASA (versión, unidades, valores
de relleno, banderas de calidad).

## 3. Procesamiento de los datos

Idea central: **cada valor del mapa tiene que ser trazable y comparable**.

1. **Limpieza por calidad.** Se eliminan los valores de relleno y los códigos especiales.
   Ejemplo: en evapotranspiración, los códigos de agua, ciudad o desierto **no son cero**, así
   que se marcan como «sin dato». En temperatura solo se aceptan píxeles con buena calidad o
   con error ≤ 2 K. **Regla del proyecto: un dato faltante nunca se convierte en cero.**
2. **Conversión de unidades.**
   - Precipitación: mm/mes = mm/h × 24 × días del mes.
   - Temperatura: valor × 0.02 = K, y °C = K − 273.15.
   - Evapotranspiración: valor × 0.1 = mm en el compuesto.
   - NO₂: se muestra en unidades de 10¹⁵ moléculas/cm².
3. **Agregación a meses.**
   - NO₂ diario → promedio de los días válidos, con un mínimo de 3 días por celda.
   - Compuestos de 8 días (MODIS) → se reparten entre los días que cubren y se suman o
     promedian por mes. El mes queda sin dato si no hay suficiente cobertura (≥ 80 % de días
     en evapotranspiración, ≥ 50 % en temperatura).
4. **Malla común de 0.25°** (130 × 76 celdas sobre México), para poder comparar variables.
   Se eligió 0.25° porque es la resolución del producto más grueso (OMI): **ningún dato se
   inventa con más detalle del que tiene**. Los productos finos se agregan con un **promedio
   conservativo ponderado por área**, y una celda necesita al menos 50 % de su área con dato
   válido.
5. **Resultado:** un **cubo de datos tiempo × latitud × longitud** por variable (unos 260
   meses × 76 × 130 celdas), más mapas mensuales en GeoTIFF optimizado (COG) y un catálogo
   que registra qué mes existe, de qué archivo sale y con qué cobertura.

## 4. Modelos matemáticos

### 4.1 Estadística descriptiva por región

Promedio y desviación estándar **ponderados por área** con el coseno de la latitud: una
celda de 0.25° es más pequeña hacia el norte, así que pesa menos. La mediana, el mínimo y el
máximo se calculan por celda. Una celda pertenece a un estado o municipio (límites del
INEGI) si su centro cae dentro.

### 4.2 Tendencia mensual (método principal)

Para cada serie mensual (un píxel, un punto o el promedio de una región):

1. **Quitar las estaciones (anomalías).** A cada mes se le resta el promedio de largo plazo
   de ese mes del calendario: cada enero se compara con los otros eneros. Lo que queda dice
   si ese mes estuvo arriba o abajo de lo normal. Sin este paso, el ciclo de lluvias o de
   calor esconde la tendencia.
2. **Pendiente por mínimos cuadrados** de las anomalías contra el tiempo, expresada como
   **cambio por década**.
3. **Corrección por autocorrelación.** Un mes caluroso suele seguir a otro caluroso, así que
   *n* meses no son *n* datos independientes. Se usa el **tamaño de muestra efectivo**

   n_eff = n · (1 − r₁) / (1 + r₁),

   donde r₁ es la autocorrelación de los residuos con desfase de un mes. Con n_eff se corrigen
   el error estándar, el **intervalo de confianza del 95 %** y la **prueba t** de la pendiente.
   Sin esta corrección, casi todo parecería «significativo».
4. **Pendiente de Sen.** Es la mediana de las pendientes entre todos los pares de meses;
   resiste valores extremos.
5. **Prueba de Mann–Kendall con la modificación de Hamed y Rao.** Es una prueba no
   paramétrica (no supone una distribución normal) y está corregida por autocorrelación. Da el
   **valor p principal**.
6. **Veredicto en lenguaje sencillo:** p < 0.05 → «Tendencia sólida»; p < 0.10 → «Indicio»;
   si no → «Variabilidad natural».

Detalle técnico que vale la pena contar: la librería de Hamed–Rao a veces calcula una
varianza negativa y devuelve p = NaN (≈ 1 % de los píxeles de precipitación). En ese caso el
sistema usa la versión AR(1) de la misma corrección (Yue y Wang, 2004) y lo avisa en pantalla,
en lugar de marcar la tendencia como no significativa por un error numérico.

### 4.3 Mapa de tendencia de todo México, en tiempo real

Los pasos 1–3 se calculan **para las ~9 900 celdas a la vez** con operaciones vectorizadas
de NumPy, en **menos de 1 segundo por variable**. En el mapa, rojo significa que sube, azul
que baja y los colores tenues marcan cambios no significativos (p ≥ 0.05). Mann–Kendall es
demasiado lento para cada píxel, así que se calcula al hacer clic en un punto o región.

### 4.4 Otros métodos del Atlas

- **Tendencia anual (Theil–Sen + Mann–Kendall)** sobre promedios anuales, con el intervalo de
  confianza de Sen (1968). Es la vista complementaria del modo Científico.
- **Correlación entre variables:** Pearson sobre anomalías mensuales, con tamaño de muestra
  efectivo de Bretherton et al. (1999) y un intervalo de confianza por la transformación z de
  Fisher. Se aclara siempre que correlación no es causalidad.
- **Comparación de dos fechas:** diferencia B − A celda por celda, solo donde ambas fechas
  tienen dato, promediada por área.

## 5. Resultados y validación (datos reales)

**Validación del cálculo.** El mapa vectorizado se comparó contra el análisis completo de
cada serie en 20 píxeles reales: la diferencia máxima en la pendiente fue de 4 × 10⁻⁵ (el
redondeo) y en el valor p de 6 × 10⁻¹⁶. Las 99 pruebas automáticas del backend pasan.

**Contraste con una referencia independiente.** Los resultados se compararon con cuadros de
ciudades calculados con NASA Giovanni (proyecto trend-detectives). El NO₂ coincide en signo
y magnitud:

| Ciudad | Atlas (NO₂ por década) | Referencia |
|---|---|---|
| Ciudad de México | −12.5 % (significativo) | −13.8 % |
| Monterrey | +6.4 % (significativo) | +7.0 % |
| Hermosillo | +4.4 % (significativo) | +3.8 % |

**Hallazgos (2004 en adelante, malla de 0.25°):**

- **Temperatura de la superficie (2004–2021):** sube en el **85 %** de las celdas de México;
  la mediana es **+0.41 °C por década**, en línea con la referencia de +0.42 a +0.57 °C.
- **NO₂:** sube en el 74 % del país (32 % con tendencia significativa al alza), pero en el
  centro de la Ciudad de México **baja 22.8 % por década** (Mann–Kendall p < 0.001).
- **Precipitación:** el promedio nacional baja 4.9 % por década, pero es solo un **indicio**
  (p = 0.08), no una tendencia sólida.
- **Evapotranspiración:** sin un patrón nacional claro (4 % de las celdas significativas al
  alza y 4 % a la baja).

## 6. Limitaciones (decirlas es parte del rigor)

- **Deriva orbital del satélite Terra.** Desde 2020 Terra no corrige su órbita y pasa cada
  vez más temprano, cuando el suelo está más frío. Los datos de temperatura de 2022–2025 salen
  de 2 a 4 °C por debajo de lo normal. Con ellos, el mapa decía que México se **enfría**;
  cortando en 2021, el 85 % del país se calienta. Por eso la tendencia de temperatura usa
  **2004–2021** y lo explica en pantalla. **Es un buen ejemplo de por qué hay que revisar los
  datos antes de confiar en el modelo.**
- **El NO₂ satelital es la columna de aire troposférica**, no la concentración que se respira
  a nivel de calle.
- **La resolución de 0.25° (≈ 25 km)** mezcla ciudades con sus alrededores.
- **IMERG V07 termina en septiembre de 2025**; cuando salga V08 conviene reprocesar todo el
  registro.
- **La temperatura y la evapotranspiración solo existen en tierra.** Las nubes dejan huecos,
  que se muestran rayados como «sin dato».

## 7. Mensaje de cierre sugerido

Datos abiertos de NASA → limpieza y conversión trazables → una malla común sin inventar
detalle → tendencias con pruebas estadísticas corregidas por autocorrelación → resultados que
cualquiera puede explorar en un mapa y que coinciden con una referencia independiente.
