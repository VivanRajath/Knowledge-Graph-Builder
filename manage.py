#!/usr/bin/env python
import os
import sys

def main():
    # Support both layouts: either `django_backend.settings` or
    # `django_backend.django_backend.settings` (when there's an extra nesting).
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        import importlib
        # try the nested settings first, then the flat layout
        candidates = ['django_backend.django_backend.settings', 'django_backend.settings']
        # First try a filesystem check (reliable when package import may fail due to path issues)
        root = os.path.dirname(os.path.abspath(__file__))
        found = False
        for cand in candidates:
            parts = cand.split('.')
            fs_path = os.path.join(root, *parts) + '.py'
            if os.path.exists(fs_path):
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', cand)
                found = True
                break
        if not found:
            # Fallback to trying to import the module (works when PYTHONPATH is correct)
            for cand in candidates:
                try:
                    importlib.import_module(cand)
                    os.environ.setdefault('DJANGO_SETTINGS_MODULE', cand)
                    found = True
                    break
                except Exception:
                    pass
        if not found:
            # Provide a clearer error than letting Django later complain about DATABASES
            sys.stderr.write(
                "Could not find a Django settings module. Tried: {}\n".format(', '.join(candidates))
            )
            sys.stderr.write("Make sure the settings file exists and DJANGO_SETTINGS_MODULE is set.\n")
            sys.exit(1)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
