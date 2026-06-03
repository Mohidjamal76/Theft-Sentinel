#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import faulthandler

# Dump Python stack trace to stderr on any C-level fatal signal
# (SIGSEGV, SIGABRT, Windows Access Violation, CUDA abort).
# Zero performance cost — must be the very first thing that runs.
faulthandler.enable()

# Allow PyTorch to split large VRAM blocks to reduce fragmentation.
# Must be set before any PyTorch import.
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
