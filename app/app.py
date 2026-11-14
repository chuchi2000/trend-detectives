"""App de Detectives de Tendencias. (Persona 3)

Correr con:  streamlit run app/app.py
Lee los resultados reales de data/processed/ (los genera src/analisis/analizar_todo.py).
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATOS = Path(__file__).parent.parent / "data" / "processed"

st.set_page_config(page_title="Detectives de Tendencias", layout="wide")
st.title("Detectives de Tendencias")

catalogo = json.loads((DATOS / "catalogo.json").read_text(encoding="utf-8"))
variable = st.selectbox(
    "1. Variable",
    list(catalogo["variables"]),
    format_func=lambda v: catalogo["variables"][v]["nombre"],
)

datos = json.loads((DATOS / variable / "tendencias.json").read_text(encoding="utf-8"))
zonas = pd.DataFrame(datos["zonas"])

st.caption(f"{datos['fuente']} · {datos['periodo']['inicio']} a {datos['periodo']['fin']} · {datos['unidades']}")

# Rojo si sube, azul si baja; transparente si no es significativa
zonas["color"] = [
    ([226, 75, 74] if p > 0 else [55, 138, 221]) + ([230] if s else [90])
    for p, s in zip(zonas["pendiente_por_decada"], zonas["significativa"])
]

# TODO: cambiar por un mapa donde se pueda dar clic en la región (pydeck / folium)
st.map(zonas, latitude="lat", longitude="lon", color="color", size=40000)

st.dataframe(
    zonas[["nombre", "pendiente_por_decada", "ic95", "cambio_pct_por_decada", "p_valor", "significativa"]],
    width="stretch", hide_index=True,
)

region = st.selectbox("2. Región", zonas["id"], format_func=lambda r: catalogo["regiones"][r]["nombre"])
serie = json.loads((DATOS / variable / "series" / f"{region}.json").read_text(encoding="utf-8"))
st.line_chart(pd.DataFrame({"valor": serie["valores"]}, index=pd.to_datetime(serie["fechas"])))

fila = zonas.set_index("id").loc[region]
cambio = "sube" if fila["pendiente_por_decada"] > 0 else "baja"
st.metric(f"{cambio.capitalize()} por década", f"{fila['pendiente_por_decada']:+.2f} {datos['unidades']}")
if fila["significativa"]:
    st.success("Significativa: es muy poco probable que sea casualidad.")
else:
    st.info("No significativa: con estos datos todavía no se puede descartar que sea casualidad.")

# TODO: barra para elegir los años y recalcular la tendencia con src/analisis/tendencias.py
