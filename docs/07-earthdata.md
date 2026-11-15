# 7. Cuenta NASA Earthdata y credenciales

Las descargas de NASA requieren una cuenta gratuita de Earthdata Login. Tus credenciales
se quedan en tu computadora: **no las compartas con nadie (tampoco con un asistente de
IA), no las pongas en el código ni en el frontend, y no las subas a Git.**

## 1. Crear la cuenta

1. Entra a <https://urs.earthdata.nasa.gov/users/new> y regístrate.
2. Confirma tu correo.

## 2. Autorizar los servicios de datos

Algunos centros de datos piden aprobar su aplicación una vez:

1. Inicia sesión en <https://urs.earthdata.nasa.gov/>.
2. Ve a **Applications → Authorized Apps** y pulsa **Approve More Applications**.
3. Busca y aprueba **NASA GESDISC DATA ARCHIVE** (necesaria para IMERG y OMI).
4. AppEEARS (MODIS) usa tu misma cuenta; no necesita aprobación aparte. Puedes probarla
   entrando a <https://appeears.earthdatacloud.nasa.gov/>.

Si al descargar ves un error 401 o una página de acceso en lugar del archivo, casi siempre
falta este paso.

## 3. Guardar las credenciales en tu computadora

Elige **una** de estas opciones.

### Opción A — archivo `.env` del proyecto (más simple)

En la raíz del proyecto (ya existe `.env` si seguiste la instalación):

```ini
EARTHDATA_USERNAME=tu_usuario
EARTHDATA_PASSWORD=tu_contraseña
```

`.env` está en `.gitignore`. Compruébalo con `git check-ignore .env` (debe imprimir `.env`).

### Opción B — archivo `.netrc` (estándar de NASA, sirve para todos tus proyectos)

Linux / macOS, en `~/.netrc`:

```
machine urs.earthdata.nasa.gov login tu_usuario password tu_contraseña
```

```bash
chmod 600 ~/.netrc
```

Windows: el archivo se llama `_netrc` y va en `C:\Users\<tu_usuario>\`.

`earthaccess` lo encuentra solo. **AppEEARS** necesita usuario y contraseña explícitos;
si usas `.netrc`, el proyecto los lee de ahí también.

### Opción C — token

En tu perfil de Earthdata, **Generate Token**. Ponlo en `.env` como
`EARTHDATA_TOKEN=…`. Caduca a los 60 días. Sirve para `earthaccess` (IMERG, OMI), pero
AppEEARS sigue necesitando usuario y contraseña (opciones A o B).

## 4. Comprobar

```bash
cd backend
source .venv/bin/activate
python -m processing.cli verificar-login
```

El comando indica qué fuente de credenciales usó (entorno o `.netrc`), **nunca** las imprime.

## Si alguna vez se filtra tu contraseña

Cámbiala de inmediato en <https://urs.earthdata.nasa.gov/> y revoca los tokens. Si llegó a
un repositorio, cambiarla es lo primero: borrar el commit no basta.
