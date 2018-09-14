#!/usr/bin/env python3
# salloc.py ---
#
# Filename: salloc.py
# Description:
# Author: Kwang Moo Yi
# Maintainer:
# Created: Tue Sep  4 16:33:02 2018 (-0700)
# Version:
#

# Commentary:
#
#
#
#

# Change Log:
#
#
#

# Code:

import argparse
import getpass
import json
import os
import subprocess
import sys
import time

from flufl.lock import Lock
from parse import parse

dir_sps = "/var/sps"
dir_gpu = os.path.join(dir_sps, "gpu")
dir_addqueue = os.path.join(dir_sps, "addqueue")
dir_queue = os.path.join(dir_sps, "queue")
lock_file = os.path.join(dir_sps, "locks/lock")


# -----------------------------------------------------------------------------
# Options and configurations

parser = argparse.ArgumentParser()

arg_lists = []

def add_argument_group(name):
    arg = parser.add_argument_group(name)
    arg_lists.append(arg)
    return arg

configs = add_argument_group("Configs")
configs.add_argument("--num_gpu", type=int, default=1, help="number of gpus")
configs.add_argument("--num_hour", type=float, default=1, help="number of hours")

def get_config():
    config, unparsed = parser.parse_known_args()

    return config, unparsed

def print_usage():
    parser.print_usage()

# -----------------------------------------------------------------------------
def add_interactive(num_gpu, num_hour):
    """TODO: docstring
    """

    # Get Username
    uname = getpass.getuser()

    # Get PID
    pid = os.getpid()

    # Check user queue directory
    dir_userqueue = os.path.join(dir_addqueue, uname)
    if not os.path.exists(dir_userqueue):
        raise RuntimeError("{} is not setup to use GPUs! Contact admin!")

    # Add an interactive job
    job_name = "{}-{}-{}-{}.job".format(
        time.time(), uname, "salloc", pid
    )
    job_file = os.path.join(dir_userqueue, job_name)
    job_spec = {
        "cmd": "",
        "life": str(num_hour),
        "num_gpu": str(num_gpu),
        "start": "",
        "end": "",
    }
    # Write the job
    write_job(job_file, job_spec)

    # Write the env
    sub_env = os.environ.copy()
    write_env(job_file, sub_env)


def write_job(job_fullpath, job_spec):
    """ TODO: Docstring
    """

    # Write the contents to a job
    with Lock(lock_file):
        with open(job_fullpath, "w") as ofp:
            ofp.write(job_spec["cmd"] + "\n")
            ofp.write(job_spec["life"] + "\n")
            ofp.write(job_spec["num_gpu"] + "\n")
            ofp.write(job_spec["start"] + "\n")
            ofp.write(job_spec["end"] + "\n")


def write_env(job_fullpath, env):
    """TODO: write"""

    env_fullpath = job_fullpath.replace(".job", ".env")

    # write env to env_fullpath
    with Lock(lock_file):
        with open(env_fullpath, "w") as ifp:
            env = json.dump(env, ifp)


def get_assigned_gpus():
    """ TODO: Docstring

    Returns
    -------
    assigned_gpus: list of int
        Assigned GPU numbers in ints
    """

    assigned_gpus = []

    # Get Username
    uname = getpass.getuser()

    # Get PID
    pid = os.getpid()

    # For all gpu directories
    dir_gpus = [os.path.join(dir_gpu, d) for d in os.listdir(dir_gpu)
                if os.path.isdir(os.path.join(dir_gpu, d))]
    # Look at assigned jobs
    for dir_cur_gpu in dir_gpus:
        # print("      -- Checking {}".format(dir_cur_gpu))
        for job in os.listdir(dir_cur_gpu):
            job_fullpath = os.path.join(dir_cur_gpu, job)
            # Pass if not a regular file
            if not os.path.isfile(job_fullpath):
                continue
            # Pass if not a job
            if not job_fullpath.endswith(".job"):
                continue
            # Parse and check job info
            parseres = parse("{time}-{user}-{type}-{pid}.job", job)
            # print("      -- job = {}".format(job))
            if parseres["type"] != "salloc":
                continue
            if parseres["user"] != uname:
                continue
            if parseres["pid"] != str(pid):
                continue
            # Add to assigned gpu
            assigned_gpus += [int(dir_cur_gpu.split("/")[-1])]

    return assigned_gpus


def wait_for_gpus(num_gpu):
    """TODO: docstring

    Returns
    -------

    gpu_str: string for the environment variable

    TODO: Add signal catching or some sort to undo the job allocation
    TODO: Add early termination if job disappears from queue
    """
    gpu_ids = []

    # Check GPU folders and see if anything is allocated with my job request
    while True:

        gpu_ids = get_assigned_gpus()
        # print("Assigne gpus = {}".format(gpu_ids))
        if len(gpu_ids) == num_gpu:
            break
        print("  -- waiting: my pid is {}".format(os.getpid()))

        # Sleep 10 seconds
        time.sleep(2)

    # Once job is allocated, return the GPU id in string
    gpu_str = ",".join([str(g) for g in gpu_ids])

    return gpu_str


def main(config):

    num_gpu = config.num_gpu
    num_hour = config.num_hour

    # Add job to addqueue
    print("* Adding interactive job to queue.")
    add_interactive(num_gpu, num_hour)

    # Wait until assigned
    print("* Waiting for an available GPU(s)...")
    gpu_str = wait_for_gpus(num_gpu)
    print("* GPU(s) with ID={} allocated.".format(gpu_str))

    # Run a sub-process with correct GPU exported
    sub_env = os.environ.copy()
    sub_env["CUDA_VISIBLE_DEVICES"] = gpu_str
    print("-----------------------------------------------------------------------")
    print("Starting shell with CUDA_VISIBLE_DEVICES set, do not edit this variable")
    print("")
    print("Remember to close this interactive once finished to release GPU")
    print("-----------------------------------------------------------------------")
    subprocess.run(
        os.getenv("SHELL", "bash"),
        env=sub_env
    )

    # Print message
    print("-----------------------------------------------------------------------")
    print("GPU(s) with ID={} now released.".format(gpu_str))
    print("-----------------------------------------------------------------------")

    exit(0)


if __name__ == "__main__":

    # ----------------------------------------
    # Parse configuration
    config, unparsed = get_config()
    # If we have unparsed arguments, print usage and exit
    if len(unparsed) > 0:
        print_usage()
        exit(1)

    main(config)


#
# salloc.py ends here
