# Class to handle getting information from TrueNAS by running 'midclt'
# on the host.

# midclt call apparently calls an API function.

# Filters aren't intuitive: A filter is a list of >= 0 elements, where
# each element is in turn an array. So to query the users with UID
# 1000, use
#
# midclt call user.query '[["id", "=", 1000]]'
#
# Example:
# midclt call user.query '[["username", "=", "root" ]]'
# midclt call plugin.defaults '{"plugin":"syncthing"}'

# XXX - There are multiple ways of controlling the middleware daemon:
# midclt is the command-lineversion, but I think the recommended way
# is to use the REST API.

# It'd be

__metaclass__ = type
"""
This module adds support for midclt on TrueNAS.
"""

import subprocess
import json
from json.decoder import JSONDecodeError

MIDCLT_CMD = "midclt"

class MidcltError(Exception):
    def __init__(self, value, progress=None, error=None, exception=None):
        self.value = value
        # progress: an object with job progress info:
        # {
        #     percent: int, percent completion
        #     description: str, running log of stdout (?)
        #     extra: ?, can be null.
        # }
        self.progress = progress
        # error: str, job stderr error message
        self.error = error
        # exception: str, failed job stack trace
        self.exception = exception

    def __str__(self):
        return f'{self.error}: {repr(self.value)}'

class Midclt:
    # XXX - Maybe other commands beside "call"?:
    # ping, waitready, sql, subscribe.

    @staticmethod
    def call(func, *args, opts=[]):
        """Call the API function 'func', with arguments 'args'.

        'opts' are additional options passed to 'midclt call', not to
        'func'.

        Return the status and return value.
        """

        # Build the command line
        mid_args = [MIDCLT_CMD, "call", *opts, func]

        # If we were passed arguments, convert them to JSON strings,
        # and add to the command line.
        if len(args) > 0:
            for arg in args:
                argstr = json.dumps(arg)
                mid_args.append(argstr)

        # Run 'midclt' and get its output.
        try:
            mid_out = subprocess.check_output(mid_args,
                                              stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # Exited with a non-zero code
            raise Exception(f"{MIDCLT_CMD} exited with status {e.returncode}: \"{e.stdout}\"")

        # Parse stdout as JSON
        try:
            retval = json.loads(mid_out)
        except JSONDecodeError as e:
            raise Exception(f"Can't parse {MIDCLT_CMD} output: {mid_out}: {e}")

        return retval

    @staticmethod
    def job(func, *args):
        """Run the API function 'func', with arguments 'args'.

        Jobs are different from calls in that jobs are asynchronous,
        since they may run for a long time.

        This method starts a job, then waits for it to complete. If it
        finishes successfully, 'job' returns the job's status.
        """

        try:
            err = Midclt.call(func,
                              opts=["-job", "-jp", "description"],
                              *args)
            # Returns an object with the same information as
            # systemdataset.config
        except Exception:
            raise

        return err
