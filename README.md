# vdl-cli

CLI tooling for Data engineers. See [commands](./COMMANDS.md) for usage documentation.

## Installation

Recommended to be installed via `pipx` or `uvx`. See [installing uv](https://docs.astral.sh/uv/getting-started/installation/#installing-uv).

```shell
uv tool install "vdl-cli @ git+https://github.com/navikt/vdl-cli@<version>"
```

Example:

```shell
uv tool install "vdl-cli @ git+https://github.com/navikt/vdl-cli@v0.1"
```

## Upgrading

```shell
uv tool upgrade vdl-cli
```

## Release

Vi bruker [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) til versjonering. Versjonsnummereringen skal følge [semver](https://semver.org): `<major>.<minor>.<patch>` Eks: `0.1.0`. Siden vi enda ikke er på versjon 1 kan `minor` inkrementeres med 1 ved breaking changes i apiet og `patch` ved nye features eller bug fiks. Versjonsnr hentes fra [setup.py](setup.py)

Pass på at du har gjort følgende før du kjører `make release`:

* Koden er merget til `main`
* `version` i [setup.py](setup.py) er oppdatert. (Husk commit)

```shell
make release
```
