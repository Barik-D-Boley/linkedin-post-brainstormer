"""Run the weekly LinkedIn post flow: python run.py"""

import sys

from generator import UserError
from generator.config import load_config
from generator.flow import run


def main() -> int:
    try:
        run(load_config())
    except UserError as e:
        print(f"\n{e}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\n\nStopped. Nothing was saved.")
        return 1
    except Exception as e:  # last resort: no raw stack traces
        print(f"\nSomething unexpected went wrong: {e}\n"
              "Please try again. If it keeps happening, open an issue on the repo.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
