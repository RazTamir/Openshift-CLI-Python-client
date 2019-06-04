from ocp_client.exceptions import TimeoutExpiredError, CommandFailed
import time
import logging
import subprocess
import shlex

log = logging.getLogger(__name__)


def run_cmd(cmd, **kwargs):
    """
    Run an arbitrary command locally

    Args:
        cmd (str): command to run

    Raises:
        CommandFailed: In case the command execution fails

    Returns:
        (str) Decoded stdout of command

    """
    log.info(f"Executing command: {cmd}")
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    r = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        **kwargs
    )
    log.debug(f"CMD output: {r.stdout.decode()}")
    if r.stderr:
        log.error(f"CMD error:: {r.stderr.decode()}")
    if r.returncode:
        raise CommandFailed(
            f"Error during execution of command: {cmd}."
            f"\nError is {r.stderr.decode()}"
        )
    return r.stdout.decode()


class TimeoutSampler(object):
    """
    Samples the function output.

    This is a generator object that at first yields the output of function
    `func`. After the yield, it either raises instance of `timeout_exc_cls` or
    sleeps `sleep` seconds.

    Yielding the output allows you to handle every value as you wish.

    Feel free to set the instance variables.
    """

    def __init__(self, timeout, sleep, func, *func_args, **func_kwargs):
        self.timeout = timeout
        ''' Timeout in seconds. '''
        self.sleep = sleep
        ''' Sleep interval seconds. '''

        self.func = func
        ''' A function to sample. '''
        self.func_args = func_args
        ''' Args for func. '''
        self.func_kwargs = func_kwargs
        ''' Kwargs for func. '''

        self.start_time = None
        ''' Time of starting the sampling. '''
        self.last_sample_time = None
        ''' Time of last sample. '''

        self.timeout_exc_cls = TimeoutExpiredError
        ''' Class of exception to be raised.  '''
        self.timeout_exc_args = (self.timeout,)
        ''' An args for __init__ of the timeout exception. '''

    def __iter__(self):
        if self.start_time is None:
            self.start_time = time.time()
        while True:
            self.last_sample_time = time.time()
            try:
                yield self.func(*self.func_args, **self.func_kwargs)
            except Exception:
                pass

            if self.timeout < (time.time() - self.start_time):
                raise self.timeout_exc_cls(*self.timeout_exc_args)
            time.sleep(self.sleep)

    def wait_for_func_status(self, result):
        """
        Get function and run it for given time until success or timeout.
        (using __iter__ function)

        Args:
            result (bool): Expected result from func.

        Examples:
            sample = TimeoutSampler(
                timeout=60, sleep=1, func=some_func, func_arg1="1",
                func_arg2="2"
            )
            if not sample.waitForFuncStatus(result=True):
                raise Exception
        """
        try:
            for res in self:
                if result == res:
                    return True

        except self.timeout_exc_cls:
            log.error(
                f"({self.func.__name__}) return incorrect status after timeout"
            )
            return False
