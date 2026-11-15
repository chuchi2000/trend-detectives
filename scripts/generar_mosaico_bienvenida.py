import json, math

"""Genera el mosaico ILUSTRATIVO (valores simulados) de la pantalla de bienvenida.

Uso: python scripts/generar_mosaico_bienvenida.py
"""
# ---------- Contorno aproximado de México (lon, lat), digitalizado a mano ----------
MX = [
(-117.12,32.53),(-116.0,32.62),(-114.72,32.72),(-114.81,32.49),(-113.0,31.97),(-111.07,31.33),(-108.21,31.33),(-108.21,31.78),(-106.51,31.76),(-106.2,31.47),(-105.6,31.08),(-105.0,30.68),(-104.7,30.2),(-104.45,29.6),(-103.95,29.3),(-103.3,29.0),(-102.85,29.2),(-102.65,29.75),(-102.3,29.88),(-101.4,29.77),(-100.95,29.35),(-100.65,28.95),(-100.3,28.3),(-99.95,27.75),(-99.5,27.5),(-99.45,27.0),(-99.1,26.45),(-98.6,26.25),(-98.2,26.06),(-97.65,26.0),(-97.15,25.95),
(-97.25,25.4),(-97.45,24.9),(-97.7,24.2),(-97.75,23.4),(-97.8,22.6),(-97.65,22.0),(-97.3,21.2),(-97.15,20.65),(-96.5,19.95),(-96.3,19.5),(-96.1,19.15),(-95.6,18.75),(-95.0,18.6),(-94.45,18.15),(-93.6,18.4),(-92.8,18.5),(-92.0,18.65),(-91.5,18.5),(-91.0,18.8),(-90.75,19.35),(-90.6,19.85),(-90.45,20.5),(-90.35,21.0),(-89.7,21.3),(-88.8,21.45),(-88.0,21.55),(-87.1,21.55),(-86.8,21.15),(-86.85,20.85),(-87.25,20.45),(-87.45,20.05),(-87.6,19.6),(-87.45,19.3),(-87.7,18.9),(-87.85,18.4),(-88.1,18.45),(-88.3,18.48),
(-88.7,18.1),(-88.95,17.95),(-89.15,17.82),(-90.99,17.82),(-90.99,17.25),(-91.44,17.25),(-91.2,16.95),(-90.85,16.75),(-90.6,16.45),(-90.45,16.07),(-91.73,16.07),(-92.21,15.26),(-92.08,15.07),(-92.23,14.54),
(-92.8,15.05),(-93.4,15.6),(-93.95,15.95),(-94.4,16.15),(-94.85,16.25),(-95.2,16.15),(-95.75,15.9),(-96.25,15.7),(-96.55,15.66),(-97.1,15.85),(-97.75,16.0),(-98.3,16.2),(-98.8,16.5),(-99.45,16.65),(-99.9,16.83),(-100.5,17.15),(-101.15,17.45),(-101.65,17.7),(-102.2,17.95),(-102.75,18.05),(-103.4,18.3),(-103.8,18.7),(-104.3,19.05),(-104.75,19.25),(-105.05,19.55),(-105.3,20.0),(-105.55,20.35),(-105.25,20.65),(-105.35,21.05),(-105.25,21.55),(-105.55,22.0),(-105.75,22.5),(-106.15,23.0),(-106.45,23.25),(-106.95,23.85),(-107.5,24.4),(-107.9,24.75),(-108.35,25.15),(-108.95,25.5),(-109.3,25.8),(-109.45,26.3),(-109.85,26.75),(-110.35,27.2),(-110.6,27.65),(-110.95,27.95),(-111.4,28.35),(-111.85,28.75),(-112.15,29.0),(-112.3,29.45),(-112.65,29.9),(-113.1,30.5),(-113.1,31.0),(-113.55,31.3),(-114.0,31.5),(-114.55,31.75),(-114.8,31.8),
(-114.75,31.3),(-114.6,30.85),(-114.65,30.25),(-114.4,29.75),(-113.65,29.1),(-113.25,28.75),(-112.85,28.3),(-112.6,27.75),(-112.3,27.25),(-111.95,26.9),(-111.6,26.6),(-111.35,26.05),(-111.15,25.6),(-110.75,24.9),(-110.6,24.35),(-110.3,24.2),(-110.0,24.05),(-109.7,23.65),(-109.45,23.2),(-109.9,22.88),(-110.1,23.05),(-110.25,23.5),(-110.75,23.95),(-111.6,24.5),(-112.1,24.75),(-112.15,25.3),(-112.1,25.8),(-112.45,26.25),(-113.0,26.65),(-113.6,26.75),(-114.05,27.05),(-114.5,27.4),(-115.05,27.75),(-114.3,27.9),(-114.05,28.05),(-114.15,28.6),(-114.6,29.1),(-115.2,29.6),(-115.7,30.2),(-115.95,30.7),(-116.3,31.2),(-116.65,31.75),(-116.85,32.1),
]

LON0, LON1, LAT0, LAT1 = -118.6, -86.2, 13.9, 33.2
KX = math.cos(math.radians(23.5))
W = 720
S = W / ((LON1 - LON0) * KX)
H = round((LAT1 - LAT0) * S)

def proj(lon, lat):
    return ((lon - LON0) * KX * S, (LAT1 - lat) * S)

def unproj(x, y):
    return (x / (KX * S) + LON0, LAT1 - y / S)

def inside(lon, lat, poly=MX):
    c = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            c = not c
        j = i
    return c

def g(lon, lat, clon, clat, s):
    return math.exp(-(((lon - clon) ** 2) + ((lat - clat) ** 2)) / (2 * s * s))

def jitter(i, j, k):
    v = math.sin(i * 12.9898 + j * 78.233 + k * 37.719) * 43758.5453
    return (v - math.floor(v)) - 0.5

def smooth_noise(lon, lat, k):
    return (math.sin(lon * 0.9 + k) * math.cos(lat * 1.1 - k) + math.sin(lon * 2.3 - lat * 1.7 + 2 * k) * 0.5) / 1.5

CITIES = [(-99.13,19.43,1.0,0.55),(-100.31,25.67,0.62,0.42),(-103.35,20.67,0.55,0.4),(-98.2,19.04,0.4,0.35),(-99.66,19.29,0.35,0.3),(-99.34,20.05,0.45,0.3),(-117.03,32.5,0.35,0.35),(-106.44,31.69,0.3,0.32),(-100.39,20.59,0.3,0.3),(-101.68,21.12,0.3,0.3),(-115.45,32.62,0.25,0.3),(-110.95,29.07,0.18,0.3),(-97.87,22.25,0.22,0.3),(-89.62,20.97,0.15,0.3)]

def field(var, lon, lat, i, j):
    east = (lon + 118) / 32.0
    if var == 'precipitacion':
        v = 0.08 + 0.50 * math.exp(-((lat - 17.0) / 5.0) ** 2) * (0.5 + 0.5 * east)
        v += 0.50 * g(lon, lat, -93.2, 17.3, 1.9) + 0.18 * g(lon, lat, -96.8, 19.6, 1.0)
        v += 0.16 * g(lon, lat, -105.4, 23.0, 1.5) + 0.12 * g(lon, lat, -103.5, 19.2, 1.2)
        v += 0.06 * smooth_noise(lon, lat, 1)
    elif var == 'no2':
        v = 0.13 + 0.05 * smooth_noise(lon, lat, 2) + 0.05 * (1 - abs(lat - 21) / 12)
        for clon, clat, w, s in CITIES:
            v += w * g(lon, lat, clon, clat, s)
    elif var == 'evapotranspiracion':
        v = 0.08 + 0.88 * math.exp(-((lat - 17.0) / 4.8) ** 2) * (0.45 + 0.55 * east)
        v += 0.22 * g(lon, lat, -106.2, 24.5, 1.7) + 0.1 * g(lon, lat, -89.0, 20.5, 1.5)
        v -= 0.12 * g(lon, lat, -101.0, 21.0, 1.6)
        v += 0.06 * smooth_noise(lon, lat, 3)
    else:  # temperatura
        v = 0.30 + 0.48 * (lat - 14.5) / 18.0 + 0.18 * (1 - east)
        v -= 0.38 * g(lon, lat, -100.3, 20.3, 2.2) + 0.15 * g(lon, lat, -106.3, 25.5, 1.3)
        v -= 0.18 * math.exp(-((lat - 16.5) / 2.5) ** 2) * east
        v += 0.05 * smooth_noise(lon, lat, 4)
    v += 0.05 * jitter(i, j, len(var))
    return max(0.0, min(0.999, v))

# ---------- OKLab interpolation for 9-class ramps ----------
def srgb_to_lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def lin_to_srgb(c):
    c = max(0, min(1, c))
    v = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(v * 255)
def hex2rgb(h):
    h = h.lstrip('#'); return [int(h[k:k+2], 16) for k in (0, 2, 4)]
def to_oklab(h):
    r, g_, b = [srgb_to_lin(c) for c in hex2rgb(h)]
    l = 0.4122214708*r + 0.5363325363*g_ + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g_ + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g_ + 0.6299787005*b
    l, m, s = [x ** (1/3) for x in (l, m, s)]
    return (0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
            1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
            0.0259040371*l + 0.7827717662*m - 0.8086757660*s)
def from_oklab(L, a, b):
    l = (L + 0.3963377774*a + 0.2158037573*b) ** 3
    m = (L - 0.1055613458*a - 0.0638541728*b) ** 3
    s = (L - 0.0894841775*a - 1.2914855480*b) ** 3
    r = 4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g_ = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    bb = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return '#%02X%02X%02X' % (lin_to_srgb(r), lin_to_srgb(g_), lin_to_srgb(bb))
def ramp(anchors, n=9):
    labs = [to_oklab(h) for h in anchors]
    out = []
    for k in range(n):
        t = k / (n - 1) * (len(labs) - 1)
        i = min(int(t), len(labs) - 2); f = t - i
        out.append(from_oklab(*[labs[i][q] + (labs[i+1][q] - labs[i][q]) * f for q in range(3)]))
    return out

ANCHORS = {
 'precipitacion': ['#F2F7F2','#BFE3DC','#73C0C8','#2F8FB3','#1F5C94','#202F63'],
 'no2':           ['#F5F3F8','#D9D1E8','#B09FD0','#8569B4','#5D3F92','#331F5E'],
 'evapotranspiracion': ['#F7F3DF','#DCE3A6','#A3CB78','#5FA45A','#2E7646','#133F2C'],
 'temperatura':   ['#FFF4D1','#FCD38C','#F6A05C','#E3663F','#B73A32','#6F1D28'],
}
RAMPS = {k: ramp(v) for k, v in ANCHORS.items()}

# ---------- Build pixel mosaic ----------
PITCH, SIZE = 9, 8
cells = []
for j in range(0, H // PITCH + 1):
    for i in range(0, W // PITCH + 1):
        x, y = i * PITCH, j * PITCH
        lon, lat = unproj(x + PITCH / 2, y + PITCH / 2)
        if inside(lon, lat):
            cells.append((i, j, x, y, lon, lat))

layers = {}
for var in RAMPS:
    by_class = {k: [] for k in range(9)}
    for (i, j, x, y, lon, lat) in cells:
        c = int(field(var, lon, lat, i, j) * 9)
        by_class[c].append(f"M{x} {y}h{SIZE}v{SIZE}h-{SIZE}z")
    layers[var] = [(RAMPS[var][k], ''.join(by_class[k])) for k in range(9) if by_class[k]]

coast = 'M' + 'L'.join(f"{proj(lo, la)[0]:.1f} {proj(lo, la)[1]:.1f}" for lo, la in MX) + 'Z'
grat = {
 'lat': [(la, round(proj(LON0, la)[1], 1)) for la in (15, 20, 25, 30)],
 'lon': [(lo, round(proj(lo, LAT0)[0], 1)) for lo in (-115, -110, -105, -100, -95, -90)],
}
# Escribe el módulo TypeScript que usa la pantalla de bienvenida.
from pathlib import Path
target = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "brand" / "mosaicData.ts"
lines = [
    "/**",
    " * Mosaico ILUSTRATIVO de México para la pantalla de bienvenida (valores simulados,",
    " * no son mediciones). Generado con scripts/generar_mosaico_bienvenida.py.",
    " * Cada variable es una lista de [color, trazo SVG] por clase.",
    " */",
    f"export const MOSAIC_VIEWBOX = {{ width: {W}, height: {H} }};",
    f'export const MOSAIC_COAST = "{coast}";',
    "export const MOSAIC_LAYERS: Record<string, Array<[string, string]>> = {",
]
IDS = {'precipitacion': 'precipitation', 'no2': 'no2', 'evapotranspiracion': 'evapotranspiration', 'temperatura': 'temperature'}
for var, items in layers.items():
    lines.append(f"  {IDS[var]}: [")
    lines += [f'    ["{c}", "{p}"],' for c, p in items]
    lines.append("  ],")
lines.append("};")
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Escrito", target)
