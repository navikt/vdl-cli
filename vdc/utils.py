import logging
from shutil import which

from alive_progress import alive_bar

LOGGER = logging.getLogger(__name__)


def _spinner(title: str):
    return alive_bar(
        title=title,
        elapsed=False,
        stats=False,
        monitor=False,
        refresh_secs=0.05,
    )


def _validate_program(program):
    if which(program) is None:
        LOGGER.error(f"\n{program} is not installed. Please install it.\n")
        exit(1)
    LOGGER.info(f"Found program: {program}")
