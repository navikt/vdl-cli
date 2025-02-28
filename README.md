# vdl-cli

CLI tooling for Data engineers

## Installation

### Bare installation only for `open` command

Should be installed in the global python intepreter.

```shell
pip install git+https://github.com/navikt/vdl-cli@<version>
```

Example:

```shell
pip install git+https://github.com/navikt/vdl-cli@v0.0.1
```


### Full installation for diff, clone etc.

This should in most cases only be installed as dependency in the project environment.

```shell
pip install --ignore-installed "vdc[all] @ git+https://github.com/navikt/vdl-cli@<version>"
```

## Usage

### Open project development environment

Requires a setup_env.sh-file or a vdc_project.yaml-file (tba).

```shell
vdc
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
