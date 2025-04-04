# Commands

```text
Usage: vdc [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --version  Show version and exit
  --help         Show this message and exit.

Commands:
  clone
  diff
  open

Usage: vdc open [OPTIONS]

Options:
  --verbose  Print verbose output
  --help     Show this message and exit.

Usage: vdc clone [OPTIONS] DB TO

Options:
  -u, --usage TEXT  Grant usage to role
  --help            Show this message and exit.

Usage: vdc diff [OPTIONS] TABLE PRIMARY_KEY

Options:
  -d, --compare-to-db TEXT      Database you want to compare against. Default
                                is dev_<user>_<db> where <user> is your
                                username and <db> is the database of the
                                provided table
  -s, --compare-to-schema TEXT  Schema you want to compare against Default is
                                same as provided table
  -t, --compare-to-table TEXT   Table you want to compare against. Default is
                                same as provided table
  -c, --column TEXT             Only compare column
  -i, --ignore-column TEXT      Ignore column
  --help                        Show this message and exit.

```
