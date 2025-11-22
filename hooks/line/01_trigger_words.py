#!/usr/bin/env python3
"""
Trigger Word Hook - Python Implementation

This hook processes transcribed text to detect trigger words and execute actions.
Actions can include:
- Exiting with specific codes
- Calling external scripts
- Making HTTP requests to web services
- Custom Python functions

Arguments:
    1. Current line text (as argument)
    stdin: Full transcript context

Exit Codes:
    0   - Continue normally
    100 - Stop Listening
    101 - Terminate
    102 - Abort
"""

import logging
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


class ExitCode(IntEnum):
    """Exit codes for hook actions"""

    CONTINUE = 0
    STOP_LISTENING = 100
    TERMINATE = 101
    ABORT = 102


@dataclass
class TriggerAction:
    """Represents an action to take when a trigger is detected"""

    name: str
    exit_code: int
    script_path: Optional[str] = None
    webhook_url: Optional[str] = None
    custom_function: Optional[Callable] = None


class TriggerWordDetector:
    """Detects trigger words and executes configured actions"""

    def __init__(self, enable_triggers: bool = True):
        """
        Initialize the trigger word detector

        Args:
            enable_triggers: If False, all trigger detection is disabled
        """
        self.enable_triggers = enable_triggers
        self.triggers: Dict[str, Dict[str, Any]] = {}
        self._configure_default_triggers()

    def _configure_default_triggers(self):
        """Configure default trigger words and their actions"""
        # Default trigger words (can be overridden via configuration)
        self.add_trigger(
            pattern=r"\bbreaker\b",
            action=TriggerAction(name="breaker", exit_code=ExitCode.STOP_LISTENING),
            description="Stop Listening",
        )

        self.add_trigger(
            pattern=r"\bshutdown\b",
            action=TriggerAction(name="shutdown", exit_code=ExitCode.TERMINATE),
            description="Terminate",
        )

        self.add_trigger(
            pattern=r"\babort\b",
            action=TriggerAction(name="abort", exit_code=ExitCode.ABORT),
            description="Abort",
        )

    def add_trigger(
        self,
        pattern: str,
        action: TriggerAction,
        description: str = "",
        case_sensitive: bool = False,
    ):
        """
        Add a trigger pattern and associated action

        Args:
            pattern: Regex pattern to match
            action: Action to execute when triggered
            description: Human-readable description
            case_sensitive: Whether pattern matching is case-sensitive
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled_pattern = re.compile(pattern, flags)
        self.triggers[pattern] = {
            "pattern": compiled_pattern,
            "action": action,
            "description": description,
        }
        logger.debug(
            f"Added trigger: {pattern} -> {action.name} (exit {action.exit_code})"
        )

    def detect(
        self, text: str, full_context: Optional[str] = None
    ) -> Optional[TriggerAction]:
        """
        Detect trigger words in text

        Args:
            text: Current line text to check
            full_context: Full transcript context (optional)

        Returns:
            TriggerAction if a trigger is detected, None otherwise
        """
        if not self.enable_triggers:
            logger.debug("Triggers are disabled")
            return None

        for _pattern_str, trigger_info in self.triggers.items():
            pattern = trigger_info["pattern"]
            action: TriggerAction = trigger_info["action"]

            if pattern.search(text):
                logger.info(f"Trigger word '{action.name}' detected in: {text}")
                return action

        return None

    def execute_action(
        self, action: TriggerAction, text: str, context: Optional[str] = None
    ) -> int:
        """
        Execute the action associated with a trigger

        Args:
            action: The action to execute
            text: The current line text
            context: Full transcript context

        Returns:
            Exit code to return
        """
        logger.info(f"Executing action: {action.name} (exit code {action.exit_code})")

        # Execute custom script if configured
        if action.script_path:
            self._execute_script(action.script_path, text, context)

        # Call webhook if configured
        if action.webhook_url:
            self._call_webhook(action.webhook_url, action.name, text, context)

        # Execute custom function if configured
        if action.custom_function:
            try:
                action.custom_function(text, context)
            except Exception as e:
                logger.error(f"Error executing custom function: {e}")

        return action.exit_code

    def _execute_script(
        self, script_path: str, text: str, context: Optional[str] = None
    ):
        """
        Execute an external script with the trigger information

        Args:
            script_path: Path to script to execute
            text: Current line text
            context: Full transcript context
        """
        try:
            if not os.path.isfile(script_path):
                logger.error(f"Script not found: {script_path}")
                return

            # Make script executable if it isn't
            if not os.access(script_path, os.X_OK):
                logger.warning(
                    f"Script {script_path} is not executable, attempting to fix"
                )
                os.chmod(script_path, 0o755)

            # Execute script with text as argument and context via stdin
            input_data = context.encode() if context else None
            result = subprocess.run(
                [script_path, text], input=input_data, capture_output=True, timeout=10
            )

            if result.returncode != 0:
                logger.warning(
                    f"Script {script_path} exited with code {result.returncode}"
                )

            if result.stdout:
                logger.info(f"Script output: {result.stdout.decode().strip()}")

        except subprocess.TimeoutExpired:
            logger.error(f"Script {script_path} timed out")
        except Exception as e:
            logger.error(f"Error executing script {script_path}: {e}")

    def _call_webhook(
        self, url: str, trigger_name: str, text: str, context: Optional[str] = None
    ):
        """
        Call a webhook with trigger information

        Args:
            url: Webhook URL
            trigger_name: Name of the trigger
            text: Current line text
            context: Full transcript context
        """
        try:
            import json

            payload = {"trigger": trigger_name, "text": text, "context": context}

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                logger.info(f"Webhook called successfully: {url} (status {status})")

        except urllib.error.URLError as e:
            logger.error(f"Error calling webhook {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling webhook: {e}")


# Example custom action functions
def example_custom_action(text: str, context: Optional[str] = None):
    """Example of a custom Python function action"""
    logger.info(f"Custom action executed for text: {text}")
    # Add your custom logic here
    # - Send notifications
    # - Update databases
    # - Trigger other processes
    # etc.


def example_alert_action(text: str, context: Optional[str] = None):
    """Example action that could send an alert"""
    logger.warning(f"ALERT: Trigger detected in: {text}")
    # Could integrate with:
    # - Email services
    # - Slack/Discord webhooks
    # - SMS services
    # - Push notification services


def main():
    """Main entry point for the hook script"""
    if len(sys.argv) < 2:
        logger.error("Usage: trigger_words.py <current_line>")
        sys.exit(1)

    current_line = sys.argv[1]

    # Read full transcript context from stdin (if available)
    full_context = None
    if not sys.stdin.isatty():
        full_context = sys.stdin.read()

    # Initialize detector with triggers enabled
    # Set to False to disable all trigger detection
    enable_triggers = True  # Toggle this to enable/disable triggers
    detector = TriggerWordDetector(enable_triggers=enable_triggers)

    # --- CONFIGURATION EXAMPLES ---

    # Example 1: Add a custom trigger that calls a script
    # detector.add_trigger(
    #     pattern=r'\bhelp\b',
    #     action=TriggerAction(
    #         name="help",
    #         exit_code=ExitCode.CONTINUE,
    #         script_path="/path/to/help_script.sh"
    #     ),
    #     description="Call help script"
    # )

    # Example 2: Add a trigger that calls a webhook
    # detector.add_trigger(
    #     pattern=r'\balert\b',
    #     action=TriggerAction(
    #         name="alert",
    #         exit_code=ExitCode.CONTINUE,
    #         webhook_url="https://hooks.example.com/alert"
    #     ),
    #     description="Send webhook alert"
    # )

    # Example 3: Add a trigger with a custom function
    # detector.add_trigger(
    #     pattern=r'\bnotify\b',
    #     action=TriggerAction(
    #         name="notify",
    #         exit_code=ExitCode.CONTINUE,
    #         custom_function=example_custom_action
    #     ),
    #     description="Execute custom notification"
    # )

    # Example 4: Complex trigger with multiple actions
    # detector.add_trigger(
    #     pattern=r'\bemergency\b',
    #     action=TriggerAction(
    #         name="emergency",
    #         exit_code=ExitCode.STOP_LISTENING,
    #         script_path="/path/to/emergency_handler.sh",
    #         webhook_url="https://hooks.example.com/emergency",
    #         custom_function=example_alert_action
    #     ),
    #     description="Emergency stop with multiple actions"
    # )

    # Detect triggers in current line
    action = detector.detect(current_line, full_context)

    if action:
        exit_code = detector.execute_action(action, current_line, full_context)
        sys.exit(exit_code)

    # No triggers detected, continue normally
    sys.exit(ExitCode.CONTINUE)


if __name__ == "__main__":
    main()
