# Métodos estadísticos: tendencia sólida o variabilidad natural

El Atlas responde a una pregunta concreta: **¿el cambio que veo en una serie es una
tendencia real o puede explicarse solo por la variabilidad natural de un año a otro?**
Para eso combina una **prueba de Kendall** (Mann–Kendall) con un **intervalo de
confianza** de la pendiente, y corrige ambos por autocorrelación.

## 1. Datos de entrada

- Serie mensual de un punto (celda de 0.25°) o de una región (media ponderada por área,
  meses con ≥ 50 % del área con dato).
- Se convierte en **promedios anuales**, contando solo años con ≥ 9 meses válidos. Esto
  elimina el ciclo estacional (verano/invierno), que no es tendencia, y reduce el ruido.
- Se exigen **≥ 8 años** válidos; con menos, no se calcula tendencia.
- Los meses sin dato nunca se tratan como cero.

## 2. Pendiente: estimador de Theil–Sen

Pendiente = mediana de todas las pendientes entre pares de años:

    b = mediana{ (yⱼ − yᵢ) / (xⱼ − xᵢ) },  i < j

Se usa en lugar de la regresión lineal por mínimos cuadrados porque **no supone
normalidad** y un año extremo (por ejemplo, un huracán o un El Niño fuerte) no la
desvía. Se reporta por década.

## 3. Prueba de Kendall (Mann–Kendall)

Estadístico S: cuenta cuántos pares de años suben menos cuántos bajan.

    S = Σᵢ<ⱼ signo(yⱼ − yᵢ)
    Var(S) = [n(n−1)(2n+5) − Σ t(t−1)(2t+5)] / 18      (t = tamaño de cada grupo de empates)
    Z = (S − signo(S)) / √Var(S)

Hipótesis nula: no hay tendencia monótona. El valor p es bilateral (aproximación normal).

**Por qué Kendall y no una prueba t.** La prueba t de la pendiente supone residuos
normales e independientes. Los datos ambientales suelen tener años atípicos y
distribuciones sesgadas (la precipitación, sobre todo), y las series son cortas (10–25
años). Mann–Kendall usa solo el orden de los valores, así que no necesita normalidad y es
robusta a valores extremos. Es la prueba estándar en estudios de tendencias climáticas e
hidrológicas.

## 4. Corrección por autocorrelación (la clave para la variabilidad natural)

La variabilidad natural no es ruido independiente: fenómenos como El Niño/La Niña o
sequías de varios años hacen que **años consecutivos se parezcan** (autocorrelación).
Con eso, la prueba clásica confunde rachas naturales con tendencias.

Se infla la varianza de S según el tamaño de muestra efectivo (Hamed y Rao, 1998),
suponiendo un proceso AR(1) como en Yue y Wang (2004):

    Var*(S) = Var(S) · [1 + 2/(n(n−1)(n−2)) · Σₖ₌₁ⁿ⁻³ (n−k)(n−k−1)(n−k−2) ρ₁ᵏ]

ρ₁ es la autocorrelación de orden 1 de los residuos (serie menos la recta de Sen),
**corregida por el sesgo de muestras cortas** (en series cortas r₁ sale subestimado):

    ρ₁ = (n·r₁ + 1) / (n − 4),  limitada a [0, 0.95]

Solo se corrige cuando ρ₁ > 0: la corrección siempre hace la prueba más exigente.
La interfaz y el CSV muestran el valor p corregido y el original.

## 5. Intervalo de confianza de la pendiente (Sen, 1968; Gilbert, 1987)

Con N pendientes entre pares ordenadas y C = z₁₋α/₂ · √Var*(S):

    límite inferior = pendiente en la posición (N − C)/2
    límite superior = pendiente en la posición (N + C)/2 + 1

(con interpolación lineal entre posiciones). Por defecto, 95 %.

## 6. Veredicto

| Veredicto | Condición (α = 0.05) | Lectura |
|---|---|---|
| **Tendencia sólida** | p corregido < 0.05 **y** el IC 95 % no incluye el cero | Muy poco probable que sea solo variabilidad natural |
| **Indicio, no concluyente** | 0.05 ≤ p < 0.10 | Hay señal, pero faltan años para confirmarla |
| **Variabilidad natural** | p ≥ 0.10 | El cambio es compatible con fluctuaciones de un año a otro |

## 7. Validación por simulación

Se generaron 1 000 series sintéticas de 20 años para cada caso y se contó cuántas veces
el método declara «tendencia sólida» (prueba reproducible en
`backend/tests/test_trend_statistics.py`; cifras de la ejecución de desarrollo):

| Serie simulada | Mann–Kendall clásico (p < 0.05) | Veredicto «sólida» del Atlas |
|---|---|---|
| Ruido independiente, sin tendencia | ≈ 6 % | ≈ 5 % (lo esperado con α = 0.05) |
| Ruido con memoria AR(1), φ = 0.6, sin tendencia | ≈ 22 % (falsas alarmas) | ≈ 7 % |
| Tendencia moderada (0.1 desv. est. por año) | ≈ 65 % | ≈ 55 % |
| Tendencia fuerte (0.2 desv. est. por año) | — | ≈ 98 % |

La corrección reduce a un tercio las falsas tendencias causadas por la variabilidad
natural persistente, con una pérdida moderada de sensibilidad ante tendencias reales.

## 8. Correlación entre variables

- Pearson sobre **anomalías mensuales** (a cada mes se le resta el promedio de ese mes
  del año), para no confundir «ambas suben en verano» con una relación.
- Las anomalías también están autocorrelacionadas, así que se usa un **tamaño de muestra
  efectivo** (Bretherton et al., 1999): n_ef = n·(1 − r₁ₐ·r₁ᵦ)/(1 + r₁ₐ·r₁ᵦ).
- Valor p e **intervalo de confianza del 95 %** con la transformación z de Fisher:
  z = atanh(r), error estándar 1/√(n_ef − 3).
- Correlación no implica causalidad.

## 9. Limitaciones

- Con menos de ~15 años, solo tendencias grandes alcanzan el veredicto «sólida».
- MK detecta tendencias **monótonas**; un cambio en escalón o un ciclo largo puede
  aparecer como tendencia o pasar desapercibido.
- Temperatura de superficie: la deriva orbital de Terra desde 2020 puede introducir un
  enfriamiento artificial en la LST diurna (ver auditoría de productos).
- Precipitación: no mezclar IMERG V07 y V08 en una misma serie.

## Referencias

- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau.
  *Journal of the American Statistical Association*, 63(324), 1379–1389.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245–259.
- Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin, Londres.
- Gilbert, R. O. (1987). *Statistical Methods for Environmental Pollution Monitoring*,
  cap. 16. Van Nostrand Reinhold.
- Hamed, K. H. y Rao, A. R. (1998). A modified Mann–Kendall trend test for
  autocorrelated data. *Journal of Hydrology*, 204, 182–196.
- Yue, S. y Wang, C. (2004). The Mann–Kendall test modified by effective sample size to
  detect trend in serially correlated hydrological series. *Water Resources Management*,
  18, 201–218.
- Bretherton, C. S. et al. (1999). The effective number of spatial degrees of freedom of
  a time-varying field. *Journal of Climate*, 12, 1990–2009.
