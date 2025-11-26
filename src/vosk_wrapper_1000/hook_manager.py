import json
import logging
import os
import subprocess
import sys
import threading
import time

logger = logging.getLogger(__name__)


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

    def _execute_hook(self, hook, cmd, payload, event_name, callback=None):
        """
        Internal method to execute a single hook in a thread.

        Args:
            hook (str): The hook path.
            cmd (list): The command to execute.
            payload (str): Optional data to pass to the hook's stdin.
            callback (callable): Optional callback to call with the return code.
        """
        try:
            logger.debug(f"  Executing hook: {hook}")

            # Check if this is a JSON hook (contains "_json." in filename)
            hook_name = os.path.basename(hook)
            is_json_hook = "json" in hook_name

            # Format payload for JSON hooks
            if is_json_hook and payload is not None:
                json_payload = json.dumps(
                    {
                        "type": "transcript",
                        "data": payload,
                        "timestamp": time.time(),
                        "event": event_name,
                    }
                )
            else:
                json_payload = payload

            # Debug logging
            logger.debug(
                f"  Hook payload type: {type(json_payload).__name__}, length: {len(json_payload) if json_payload else 0}"
            )

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if json_payload is not None else None,
                stdout=sys.stdout,  # Forward stdout to main stdout
                stderr=sys.stderr,  # Forward stderr to main stderr
                text=True,
            )

            _, _ = process.communicate(input=json_payload)
            returncode = process.returncode

            if returncode == 100:
                logger.info(f"  Hook '{hook}' requested STOP LISTENING (100).")
            elif returncode == 101:
                logger.info(f"  Hook '{hook}' requested TERMINATE (101).")
            elif returncode == 102:
                logger.info(f"  Hook '{hook}' requested ABORT (102).")
            elif returncode != 0:
                logger.warning(f"  Hook '{hook}' exited with code {returncode}.")

            if callback:
                callback(returncode)

        except Exception as e:
            logger.error(f"  Error executing hook '{hook}': {e}")
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

        logger.debug(f"Running hooks for event '{event_name}' (async={async_mode})...")

        if async_mode:
            # Run hooks asynchronously
            for hook in hooks:
                try:
                    cmd = [hook]
                    if args:
                        cmd.extend(args)

                    thread = threading.Thread(
                        target=self._execute_hook,
                        args=(hook, cmd, payload, event_name, callback),
                        daemon=True,
                        name=f"Hook-{event_name}-{os.path.basename(hook)}",
                    )

                    with self._lock:
                        self._running_hooks.append(thread)

                    thread.start()

                except Exception as e:
                    logger.error(f"  Error starting hook '{hook}': {e}")

            return 0  # In async mode, always return 0
        else:
            # Run hooks synchronously (original behavior)
            final_action = 0

            for hook in hooks:
                try:
                    logger.debug(f"  Executing hook: {hook}")
                    cmd = [hook]
                    if args:
                        cmd.extend(args)

                    # Check if this is a JSON hook (contains "_json." in filename)
                    hook_name = os.path.basename(hook)
                    is_json_hook = "json" in hook_name

                    # Format payload for JSON hooks
                    if is_json_hook and payload is not None:
                        json_payload = json.dumps(
                            {
                                "type": "transcript",
                                "data": payload,
                                "timestamp": time.time(),
                                "event": event_name,
                            }
                        )
                    else:
                        json_payload = payload

                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE if json_payload is not None else None,
                        stdout=sys.stdout,  # Forward stdout to main stdout
                        stderr=sys.stderr,  # Forward stderr to main stderr
                        text=True,
                    )

                    _, _ = process.communicate(input=json_payload)

                    if process.returncode == 100:
                        logger.info(f"  Hook '{hook}' requested STOP LISTENING (100).")
                        final_action = 100
                    elif process.returncode == 101:
                        logger.info(f"  Hook '{hook}' requested TERMINATE (101).")
                        return 101  # Immediate exit priority
                    elif process.returncode == 102:
                        logger.info(f"  Hook '{hook}' requested ABORT (102).")
                        return 102  # Immediate abort priority
                    elif process.returncode != 0:
                        logger.warning(
                            f"  Hook '{hook}' exited with code {process.returncode}."
                        )

                except Exception as e:
                    logger.error(f"  Error executing hook '{hook}': {e}")

            return final_action

    def wait_for_hooks(self, timeout: float | None = None):
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
