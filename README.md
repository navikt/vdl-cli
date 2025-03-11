# vdl-cli

CLI tooling for Data engineers

## Installation

### Bare installation only for `open` command

Should be installed in the global python intepreter.

```shell
pip install "vdl-cli @ git+https://github.com/navikt/vdl-cli@<version>"
```

Example:

```shell
pip install "vdl-cli @ git+https://github.com/navikt/vdl-cli@v0.1"
```


### Full installation for diff, clone etc.

This should in most cases only be installed as dependency in the project environment.

```shell
pip install "vdl-cli[all] @ git+https://github.com/navikt/vdl-cli@<version>"
```

## Upgrading

```shell
pip install --upgrade vdl-cli
```

## Usage

### Open project development environment

Requires a Makefile with a 'install' command

```shell
o
```

or

```shell
vdc open
```

### Check diff for a table between the dev- and prod-database

**Requirements**

* The full installation of vdc
* Sysadmin priveleges in snowflake

This command vill compare the table with the equivalent table in you're dev-database and give you a brief summary in the cli with the option to export the result to excel.

```shell
vdc diff <table> <primary_key>
```

Example:

```shell
vdc diff prod.marts.my_table pk_my_table
```

## Release

Vi bruker [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) til versjonering og bygg av nytt docker-image. Versjonsnummereringen skal følge [semver](https://semver.org): `<major>.<minor>.<patch>` Eks: `0.1.0`. Siden vi enda ikke er på versjon 1 kan `minor` inkrementeres med 1 ved breaking changes i apiet og `patch` ved nye features eller bug fiks.

For å release en ny versjon må en gjøre følgende:
* Merge koden til main
* Oppdatere `version` i [setup.py](setup.py) (Husk å commite og pushe endringer)
* Opprett/oppdater `<major>.<minor>` tag. Eks: `git tag -f v0.2` (Må gjøres selv om major eller minor ikke endrer seg)
* Opprett `<major>.<minor>.<patch>` tag. Eks: `git tag v0.2.0` (tagen skal ikke eksistere fra før)
* Push tags til github med: `git push -f origin v0.2 v0.2.0`
* Opprett ny release på [github](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
    * Steg 1: Velg den nye `<major>.<minor>.<patch>` taggen.
    * Steg 2: Trykk Generate release notes for å få utfylt relevant informasjon
    * Steg 3: Trykk Publish release.
