# Commands

```text
Usage: vdc [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --version  Show version and exit
  --help         Show this message and exit.

Commands:
  clone  Clone a database
  diff   Compare two tables in Snowflake
  open   Setup and open the environment for the current user
  waste  Commands for marking db objects as waste or removing marked objects

Usage: vdc open [OPTIONS]

  Setup and open the environment for the current user

Options:
  --verbose  Print verbose output
  --help     Show this message and exit.

Usage: vdc clone [OPTIONS] DB TO

  Clone a database

Options:
  -u, --usage TEXT  Grant usage to role
  --help            Show this message and exit.

Usage: vdc diff [OPTIONS] TABLE PRIMARY_KEY

  Compare two tables in Snowflake

Options:
  -d, --compare-to-db TEXT      Database you want to compare against. Default
                                is dev_<devname>_<db> where <devname> is the value of the environment variable DEV_NAME
                                and <db> is the database of the
                                provided table. Will fallback to use USER environment variable if DEV_NAME is not set.
  -s, --compare-to-schema TEXT  Schema you want to compare against Default is
                                same as provided table
  -t, --compare-to-table TEXT   Table you want to compare against. Default is
                                same as provided table
  -c, --column TEXT             Only compare column
  -i, --ignore-column TEXT      Ignore column
  --help                        Show this message and exit.

Usage: vdc waste [OPTIONS] COMMAND [ARGS]...

  Commands for marking db objects as waste or removing marked objects

Options:
  --help  Show this message and exit.

Commands:
  disposal      Mark db objects for removal
  incineration  Drop database objects marked for removal

Usage: vdc waste disposal [OPTIONS]

  Mark db objects for removal

Options:
  -d, --dbt-project-dir TEXT  Path to dbt project directory
  -p, --dbt-profile-dir TEXT  Path to dbt profile directory
  -t, --dbt-target TEXT       dbt profile target
  --dry-run                   Dry run and print potential objects that can be
                              marked for removal
  -i, --ignore-table TEXT     Ignore table from search
  -s, --schema TEXT           What schema to search in
  --help                      Show this message and exit.

Usage: vdc waste incineration [OPTIONS]

  Drop database objects marked for removal

Options:
  --dry-run  Dry run and print potential removals
  --help     Show this message and exit.

```
