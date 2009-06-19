#!/usr/bin/python
#
#    powernap - monitor a system process table; if IDLE amount of time
#               goes by with no MONITORED_PROCESSES running, run ACTION
#    Copyright (C) 2009 Canonical Ltd.
#
#    Authors: Dustin Kirkland <kirkland@canonical.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Imports
import commands
import os
import re
import signal
import sys
import time

# Define globals
global PKG, LOCK, CONFIG
PKG = "powernap"
LOCK = "/var/run/%s.pid" % PKG
CONFIG = "/etc/%s/config" % PKG

# CONFIG values should override these (default: monitor no processes)
global INTERVAL_SECONDS, MONITORED_PROCESSES, ACTION, ABSENT_SECONDS, DEBUG
MONITORED_PROCESSES = []
ABSENT_SECONDS = sys.maxint
ACTION = ""
INTERVAL_SECONDS = 1
DEBUG = 0

# Generic error function
def error(msg):
    print("ERROR: %s" % msg)
    sys.exit(1)

# Load configuration file
try:
    execfile(CONFIG)
except:
    error("Invalid configuration [%s]" % CONFIG)

# Define Process object to hold regex and absence counter
class Process(object):
    def __init__(self, process):
        self.process = process
        self.regex = re.compile(process)
        self.absent_seconds = 0

# Generic debug function
def debug(msg):
    if DEBUG:
        print("DEBUG: %s" % msg)

# Lock function, using a pidfile in /var/run
def establish_lock(lock):
    if os.path.exists(lock):
        f = open(lock,'r')
        pid = f.read()
        f.close()
        error("Another instance is running [%s]" % pid)
    else:
        f = open(LOCK,'w')
        f.write(str(os.getpid()))
        f.close()
        # Set signal handlers
        signal.signal(signal.SIGHUP, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGQUIT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

# Clean up lock file on termination signals
def signal_handler(signal, frame):
    if os.path.exists(LOCK):
        os.remove(LOCK)
    sys.exit(1)

# Search process list for regex, return on first match
def find_process(ps, p):
    for str in ps:
        if p.search(str):
            return 1
    return 0

# TODO: notify authorities about action taken
def notify_authorities(action):
    debug("Taking action [%s], email authorities" % action)

# Main loop, search process table, increment counters, take actions, sleep
def powernap_loop(processes, absent_seconds, action, interval_seconds):
    debug("Starting %s, sleeping [%d] seconds" % (PKG, interval_seconds))
    while 1:
        time.sleep(interval_seconds)
        # Examine process table, compute absent time of each monitored process
        debug("Examining process table")
        absent_processes = 0
        ps = commands.getoutput("ps -eo args").splitlines()
        for p in processes:
            debug("  Looking for [%s]" % p.process)
            if find_process(ps, p.regex):
                # process running, so reset absent time
                p.absent_seconds = 0
                debug("    Process found, reset absent time [%d/%d]" % (p.absent_seconds, absent_seconds))
            else:
                # process not running, increment absent time
                p.absent_seconds += interval_seconds
                debug("    Process not found, increment absent time [%d/%d]" % (p.absent_seconds, absent_seconds))
                if p.absent_seconds >= absent_seconds:
                    # process missing for >= absent_seconds threshold, mark absent
                    debug("    Process absent for >= threshold, so mark absent")
                    absent_processes += 1
        # Determine if action needs to be taken
        if absent_processes > 0 and absent_processes == len(processes):
            # All processes are absent, take action!
            notify_authorities(action)
            for p in processes:
                p.absent_seconds = 0
            os.system(action)
        debug("Done with powernap_loop, sleeping [%d] seconds" % interval_seconds)


# Main program
if __name__ == '__main__':
    # Ensure that only one instance runs
    establish_lock(LOCK)
    try:
        # Run the main powernap loop
        processes = [Process(p) for p in MONITORED_PROCESSES]
        powernap_loop(processes, ABSENT_SECONDS, ACTION, INTERVAL_SECONDS)
    finally:
        # Clean up the lock file
        if os.path.exists(LOCK):
            os.remove(LOCK)
