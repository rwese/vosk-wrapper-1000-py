import os
import subprocess
import sys
from typing import List, Union


class HookManager:
    def __init__(self, hooks_dir="hooks"):
        self.hooks_dir = hooks_dir

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

    def run_hooks(self, event_name, payload=None, args=None):
        """
        Runs all hooks for a specific event.

        Args:
            event_name (str): The name of the event (start, line, stop).
            payload (str): Optional data to pass to the hook's stdin.
            args (list): Optional list of arguments to pass to the hook script.

        Returns:
            int: A control code.
                 0 = Continue
                 100 = Stop Listening
                 101 = Terminate Application
                 102 = Abort (Terminate immediately, skip cleanup)
        """
        hooks = self._get_hooks(event_name)
        if not hooks:
            return 0

        print(f"Running hooks for event '{event_name}'...", file=sys.stderr)

        final_action = 0

        for hook in hooks:
            try:
                print(f"  Executing hook: {hook}", file=sys.stderr)
                cmd = [hook]
                if args:
                    cmd.extend(args)

                # Use a temporary file for stdin to avoid pipe buffering issues
                # and to ensure the entire payload is available to the hook.
                # This is cleaner than piping large strings via communicate().
                import tempfile

                with tempfile.TemporaryFile(mode="w+") as tfile:
                    if payload:
                        tfile.write(payload)
                        tfile.seek(0)
                        stdin_arg = tfile
                    else:
                        stdin_arg = None

                    # Prepare command
                    cmd_target: Union[str, List[str]]
                    if os.name == "posix":
                        import shlex

                        # On POSIX, use shell=True to handle scripts without shebangs
                        # and use shlex.join to safely quote arguments.
                        cmd_target = shlex.join(cmd)
                        shell_mode = True
                    else:
                        # On Windows, shell=True allows executing .bat/.cmd files
                        # and subprocess handles list-to-string conversion.
                        cmd_target = cmd
                        shell_mode = True

                    process = subprocess.Popen(
                        cmd_target,
                        shell=shell_mode,
                        stdin=stdin_arg,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        text=True,
                    )

                    process.wait()

                if process.returncode == 100:
                    print(
                        f"  Hook '{hook}' requested STOP LISTENING (100).",
                        file=sys.stderr,
                    )
                    final_action = 100
                elif process.returncode == 101:
                    print(
                        f"  Hook '{hook}' requested TERMINATE (101).", file=sys.stderr
                    )
                    return 101  # Immediate exit priority
                elif process.returncode == 102:
                    print(f"  Hook '{hook}' requested ABORT (102).", file=sys.stderr)
                    return 102  # Immediate abort priority
                elif process.returncode != 0:
                    print(
                        f"  Hook '{hook}' exited with code {process.returncode}.",
                        file=sys.stderr,
                    )

            except Exception as e:
                print(f"  Error executing hook '{hook}': {e}", file=sys.stderr)

        return final_action
