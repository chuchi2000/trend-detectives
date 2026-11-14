"""App de Detectives de Tendencias. (Persona 3)

Correr con:  streamlit run app/app.py
Por ahora lee datos falsos de data/mock/. Cuando haya resultados reales,
cambiar RUTA a data/processed/<variable>/tendencias.json
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RUTA = Path(__file__).parent.parent / "data" / "mock" / "tendencias_ejemplo.json"

st.set_page_config(page_title="Detectives de Tendencias", layout="wide")
st.title("Detectives de Tendencias")

datos = json.loads(RUTA.read_text(encoding="utf-8"))
zonas = pd.DataFrame(datos["zonas"])

st.subheader(f"{datos['nombre']} ({datos['unidades']}) · {datos['fuente']}")
st.caption(f"Periodo: {datos['periodo']['inicio']} a {datos['periodo']['fin']}")

# TODO: reemplazar este mapa simple por el mapa de tendencias
#       (rojo sube, azul baja, marcar zonas significativas)
st.map(zonas, latitude="lat", longitude="lon")

st.dataframe(zonas, width="stretch")

# TODO: al elegir una zona, cargar series/<id>.json, graficarla
#       y mostrar la tarjeta en lenguaje simple
