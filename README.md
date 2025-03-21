# vdl-cli

CLI tooling for Data engineers. See [commands](./COMMANDS.md) for usage documentation.

## Installation

### Bare installation, only for `open` command

Needs to be installed in the global python intepreter so you can use it outside of an 'venv'.

```shell
pip install "vdl-cli @ git+https://github.com/navikt/vdl-cli@<version>"
```

Example:

```shell
pip install "vdl-cli @ git+https://github.com/navikt/vdl-cli@v0.1"
```

### Full installation for diff, clone etc.

This should in most cases only be installed as a dependency in the project environment.

```shell
pip install "vdl-cli[all] @ git+https://github.com/navikt/vdl-cli@<version>"
```

## Upgrading

```shell
pip install --upgrade vdl-cli
```

## Release

Vi bruker [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) til versjonering. Versjonsnummereringen skal følge [semver](https://semver.org): `<major>.<minor>.<patch>` Eks: `0.1.0`. Siden vi enda ikke er på versjon 1 kan `minor` inkrementeres med 1 ved breaking changes i apiet og `patch` ved nye features eller bug fiks. Versjonsnr hentes fra [setup.py](setup.py)

Pass på at du har gjort følgende før du kjører `make release`:

* Koden er merget til `main`
* `version` i [setup.py](setup.py) er oppdatert. (Husk commit)

```shell
make release
```
