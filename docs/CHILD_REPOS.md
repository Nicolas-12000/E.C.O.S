# Repos hijos (ecos-api, ecos-data, ecos-front)

## Idea

| Dónde trabajas | Qué entregas / publicas |
|----------------|-------------------------|
| **Monorepo ECOS** (`E.C.O.S` o esta carpeta) | Commits diarios, features, integración |
| **Repos hijos** | Misma historia **filtrada**, una carpeta por capa |

No copias carpetas: `git filter-repo` reescribe el historial de un clon y deja solo los paths de cada hijo. Los commits que tocaron `backend/` aparecen en `ecos-api`; los de `frontend/` en `ecos-front`, etc.

## Cuándo exportar

- Antes de entregar al profesor
- Cuando quieras actualizar GitHub `ecos-api` / `ecos-data` / `ecos-front`
- **Después de commitear** en el monorepo (los cambios locales sin commit no entran)

## Requisito

```bash
pip install git-filter-repo
```

## Exportar (sin tocar tu copia de trabajo)

```bash
cd ~/proyectos/ECOS
./scripts/export_child_repos.sh --output ~/exports/ecos-children
```

Resultado:

```
~/exports/ecos-children/ecos-api/
~/exports/ecos-children/ecos-data/
~/exports/ecos-children/ecos-front/
```

Cada uno es un repo git con `git log` propio (filtrado).

## Publicar en GitHub

1. Crear tres repos vacíos en GitHub (sin README).
2. Añadir a `.env` local (no subir):

```bash
ECOS_API_REMOTE=git@github.com:TU_USUARIO/ecos-api.git
ECOS_DATA_REMOTE=git@github.com:TU_USUARIO/ecos-data.git
ECOS_FRONT_REMOTE=git@github.com:TU_USUARIO/ecos-front.git
```

3. Exportar y empujar:

```bash
set -a && source .env && set +a
./scripts/export_child_repos.sh --output ~/exports/ecos-children --densify --push
```

`--densify` parte commits con muchos archivos (misma historia lógica, ~150–200 commits repartidos entre los tres hijos). Ajuste fino: `DENSIFY_CHUNK_API`, `DENSIFY_CHUNK_DATA`, `DENSIFY_CHUNK_FRONT` (default 3 / 2 / 2).

`--push` usa **force** en `main` del hijo: el hijo es una vista del monorepo, no una línea de desarrollo paralela.

## Orden para quien evalúa

1. **ecos-data** — datos / Spark (opcional si ya hay Supabase cargado)
2. **ecos-api** — migraciones + API
3. **ecos-front** — `NEXT_PUBLIC_API_URL` apuntando al API

## Qué va en cada hijo

Definido en `scripts/export_child_repos.sh` (listas `API_PATHS`, `DATA_PATHS`, `FRONT_PATHS`). Ajusta ahí si mueves carpetas en el monorepo.

## Monorepo vs hijos a largo plazo

- **Sigue desarrollando solo en ECOS.**
- Los hijos son **snapshots con historia**, no el lugar donde abres PRs día a día.
- Si el profe pide “última versión”, vuelves a ejecutar el script (mismo flujo).

## Opcional: repo meta

Un cuarto repo `ecos` o la descripción del monorepo en GitHub puede ser solo un README con enlaces a los tres hijos + tag común `v1.0-entrega`.
