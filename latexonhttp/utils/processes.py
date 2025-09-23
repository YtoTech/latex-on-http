import psutil


def kill_all_children_processes(parent_pid):
    """Kill the process with all its children processes."""
    # https://stackoverflow.com/a/27034438/1956471
    parent = psutil.Process(parent_pid)
    for child in parent.children(recursive=True):
        child.kill()
    parent.kill()
