import os
import subprocess
import sys
import glob

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

    def run_hooks(self, event_name, payload=None):
        """
        Runs all hooks for a specific event.
        
        Args:
            event_name (str): The name of the event (start, line, stop).
            payload (str): Optional data to pass to the hook's stdin.
            
        Returns:
            int: A control code. 
                 0 = Continue
                 100 = Stop Listening
                 101 = Terminate Application
        """
        hooks = self._get_hooks(event_name)
        if not hooks:
            return 0

        print(f"Running hooks for event '{event_name}'...", file=sys.stderr)
        
        final_action = 0

        for hook in hooks:
            try:
                print(f"  Executing hook: {hook}", file=sys.stderr)
                process = subprocess.Popen(
                    [hook],
                    stdin=subprocess.PIPE if payload else None,
                    stdout=sys.stdout, # Forward stdout to main stdout
                    stderr=sys.stderr, # Forward stderr to main stderr
                    text=True
                )
                
                _, _ = process.communicate(input=payload)
                
                if process.returncode == 100:
                    print(f"  Hook '{hook}' requested STOP LISTENING (100).", file=sys.stderr)
                    final_action = 100
                elif process.returncode == 101:
                    print(f"  Hook '{hook}' requested TERMINATE (101).", file=sys.stderr)
                    return 101 # Immediate exit priority
                elif process.returncode != 0:
                    print(f"  Hook '{hook}' exited with code {process.returncode}.", file=sys.stderr)
                    
            except Exception as e:
                print(f"  Error executing hook '{hook}': {e}", file=sys.stderr)

        return final_action
