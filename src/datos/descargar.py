"""Descarga de datos de NASA con earthaccess. (Persona 1)

Antes de correrlo:
  1. Crear cuenta en https://urs.earthdata.nasa.gov
  2. pip install -r requirements.txt

Punto de partida, aún sin probar: ajustar producto, fechas y región.
"""

import earthaccess

# Caja aproximada de México: (lon_min, lat_min, lon_max, lat_max)
MEXICO = (-118.5, 14.5, -86.5, 32.8)

# Producto de ejemplo: MERRA-2 mensual, variables de superficie (incluye T2M)
PRODUCTO = "M2TMNXSLV"
PERIODO = ("1990-01-01", "2025-12-31")


def main():
    earthaccess.login()  # pide usuario y contraseña de Earthdata la primera vez

    resultados = earthaccess.search_data(
        short_name=PRODUCTO,
        temporal=PERIODO,
        bounding_box=MEXICO,
    )
    print(f"Archivos encontrados: {len(resultados)}")

    earthaccess.download(resultados, f"data/raw/{PRODUCTO}")

    # TODO: abrir con xarray, recortar a MEXICO, quedarse con la variable
    #       y guardar algo ligero en data/processed/


if __name__ == "__main__":
    main()
