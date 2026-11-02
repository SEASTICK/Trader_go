"""python -m traderlab.research_engine check --env-file /etc/tradergo/research.env"""
import argparse
import sys
from pathlib import Path

from .supabase import ConnectionFailure, SupabaseStore


def main():
    parser = argparse.ArgumentParser(description="TraderGO Research: serveranslutning")
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--env-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        store = SupabaseStore.from_env_file(args.env_file)
        for table in store.check_schema():
            print(f"OK {table}")
    except (ConnectionFailure, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError:
        print("Kunde inte läsa miljöfilen", file=sys.stderr)
        return 1
    print("Schema tillgängligt. RLS, datakvalitet och jobbexekvering måste verifieras separat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
