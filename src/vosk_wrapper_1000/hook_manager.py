import os
import subprocess
import sys
import threading
from typing import Optional


class HookManager:
    def __init__(self, hooks_dir="hooks"):
        self.hooks_dir = hooks_dir
        self._running_hooks = []
        self._lock = threading.Lock()

    def _get_hooks(self, event_name):
        """
        Retrieves a sorted list of executable hook scripts for a given event.
        """
        event_dir = os.path.join(self.hooks_dir, event_name)
        if not os.path.isdir(event_dir):
            return []

        hooks = []
        # List all files in the directory
        for filename in os.listdir(event_dir):
            filepath = os.path.join(event_dir, filename)
            # Check if it's a file and executable
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                hooks.append(filepath)

        return sorted(hooks)

    def _execute_hook(self, hook, cmd, payload, callback=None):
        """
        Internal method to execute a single hook in a thread.

        Args:
            hook (str): The hook path.
            cmd (list): The command to execute.
            payload (str): Optional data to pass to the hook's stdin.
            callback (callable): Optional callback to call with the return code.
        """
        try:
            print(f"  Executing hook: {hook}", file=sys.stderr)

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if payload is not None else None,
                stdout=sys.stdout,  # Forward stdout to main stdout
                stderr=sys.stderr,  # Forward stderr to main stderr
                text=True,
            )

            _, _ = process.communicate(input=payload)
            returncode = process.returncode

            if returncode == 100:
                print(
                    f"  Hook '{hook}' requested STOP LISTENING (100).",
                    file=sys.stderr,
                )
            elif returncode == 101:
                print(f"  Hook '{hook}' requested TERMINATE (101).", file=sys.stderr)
            elif returncode == 102:
                print(f"  Hook '{hook}' requested ABORT (102).", file=sys.stderr)
            elif returncode != 0:
                print(
                    f"  Hook '{hook}' exited with code {returncode}.",
                    file=sys.stderr,
                )

            if callback:
                callback(returncode)

        except Exception as e:
            print(f"  Error executing hook '{hook}': {e}", file=sys.stderr)
        finally:
            with self._lock:
                if threading.current_thread() in self._running_hooks:
                    self._running_hooks.remove(threading.current_thread())

    def run_hooks(
        self, event_name, payload=None, args=None, async_mode=True, callback=None
    ):
        """
        Runs all hooks for a specific event.

        Args:
            event_name (str): The name of the event (start, line, stop).
            payload (str): Optional data to pass to the hook's stdin.
            args (list): Optional list of arguments to pass to the hook script.
            async_mode (bool): If True, runs hooks asynchronously. If False, runs synchronously.
            callback (callable): Optional callback to call with return codes (only for async mode).

        Returns:
            int: A control code (only meaningful in synchronous mode).
                 0 = Continue
                 100 = Stop Listening
                 101 = Terminate Application
                 102 = Abort (Terminate immediately, skip cleanup)

        Note: In async mode, return codes are passed to the callback function.
        """
        hooks = self._get_hooks(event_name)
        if not hooks:
            return 0

        print(
            f"Running hooks for event '{event_name}' (async={async_mode})...",
            file=sys.stderr,
        )

        if async_mode:
            # Run hooks asynchronously
            for hook in hooks:
                try:
                    cmd = [hook]
                    if args:
                        cmd.extend(args)

                    thread = threading.Thread(
                        target=self._execute_hook,
                        args=(hook, cmd, payload, callback),
                        daemon=True,
                        name=f"Hook-{event_name}-{os.path.basename(hook)}",
                    )

                    with self._lock:
                        self._running_hooks.append(thread)

                    thread.start()

                except Exception as e:
                    print(f"  Error starting hook '{hook}': {e}", file=sys.stderr)

            return 0  # In async mode, always return 0
        else:
            # Run hooks synchronously (original behavior)
            final_action = 0

            for hook in hooks:
                try:
                    print(f"  Executing hook: {hook}", file=sys.stderr)
                    cmd = [hook]
                    if args:
                        cmd.extend(args)

                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE if payload is not None else None,
                        stdout=sys.stdout,  # Forward stdout to main stdout
                        stderr=sys.stderr,  # Forward stderr to main stderr
                        text=True,
                    )

                    _, _ = process.communicate(input=payload)

                    if process.returncode == 100:
                        print(
                            f"  Hook '{hook}' requested STOP LISTENING (100).",
                            file=sys.stderr,
                        )
                        final_action = 100
                    elif process.returncode == 101:
                        print(
                            f"  Hook '{hook}' requested TERMINATE (101).",
                            file=sys.stderr,
                        )
                        return 101  # Immediate exit priority
                    elif process.returncode == 102:
                        print(
                            f"  Hook '{hook}' requested ABORT (102).", file=sys.stderr
                        )
                        return 102  # Immediate abort priority
                    elif process.returncode != 0:
                        print(
                            f"  Hook '{hook}' exited with code {process.returncode}.",
                            file=sys.stderr,
                        )

                except Exception as e:
                    print(f"  Error executing hook '{hook}': {e}", file=sys.stderr)

            return final_action

    def wait_for_hooks(self, timeout: Optional[float] = None):
        """
        Wait for all running hooks to complete.

        Args:
            timeout (float): Maximum time to wait in seconds. None = wait indefinitely.

        Returns:
            bool: True if all hooks completed, False if timeout occurred.
        """
        with self._lock:
            hooks = list(self._running_hooks)

        for hook in hooks:
            hook.join(timeout=timeout)
            if hook.is_alive():
                return False

        return True

    def get_running_hooks_count(self):
        """
        Get the number of currently running hooks.

        Returns:
            int: Number of running hook threads.
        """
        with self._lock:
            return len(self._running_hooks)
