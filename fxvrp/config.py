"""Folders under FX_VRP_WORK used by the analysis steps."""
import os
import sys


def work_dir():
    """Return the folder named by FX_VRP_WORK, or stop if it is not set."""
    work = os.environ.get("FX_VRP_WORK")
    if not work:
        sys.exit("FX_VRP_WORK is not set; point it at the working folder.")
    return work


def vrp_dir():
    return os.path.join(work_dir(), "clean_v3", "vrp_v3")


def out_dir(name):
    """Return the named sub-folder of the VRP folder, creating it if needed."""
    path = os.path.join(vrp_dir(), name)
    os.makedirs(path, exist_ok=True)
    return path
