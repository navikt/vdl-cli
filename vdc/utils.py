from alive_progress import alive_bar


def _spinner(title: str):
    return alive_bar(
        title=title,
        elapsed=False,
        stats=False,
        monitor=False,
        refresh_secs=0.05,
    )
