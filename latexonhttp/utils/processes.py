import os
import signal


def _signal_process_group(parent_pid, sig):
    """Signal the process group created by ``start_new_session=True``."""
    try:
        os.killpg(parent_pid, sig)
    except ProcessLookupError:
        # The complete process group exited between polling and signalling.
        pass


def terminate_process_group(parent_pid):
    _signal_process_group(parent_pid, signal.SIGTERM)


def kill_all_children_processes(parent_pid):
    """Kill the compilation process and every descendant in its group."""
    _signal_process_group(parent_pid, signal.SIGKILL)
