#!/usr/bin/env python3
"""entry point. lazy-load heavy stuff to keep startup fast."""
import sys

if sys.version_info < (3, 11):
    print("need python 3.11+")
    sys.exit(1)

def main():
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    from app import App
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
