"""CLI: latam-synth generate --users 1000 --out ./out --format csv"""
import argparse
from datetime import date
from pathlib import Path

from latam_synth.engine import GeneratorConfig, SyntheticGenerator


def main() -> None:
    p = argparse.ArgumentParser(prog="latam-synth",
        description="Generador de datos sinteticos de comportamiento financiero LatAm")
    p.add_argument("command", choices=["generate"])
    p.add_argument("--users", type=int, default=1000)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--start", type=date.fromisoformat, default=date(2023, 1, 1))
    p.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    p.add_argument("--countries", nargs="*", default=None)
    p.add_argument("--format", choices=["csv", "json", "parquet"], default="csv")
    p.add_argument("--out", type=Path, default=Path("./output"))
    a = p.parse_args()

    gen = SyntheticGenerator(GeneratorConfig(
        n_users=a.users, seed=a.seed, start_date=a.start, end_date=a.end, countries=a.countries))
    data = gen.generate()
    a.out.mkdir(parents=True, exist_ok=True)
    for name, frame in data.items():
        path = a.out / f"{name}.{a.format}"
        if a.format == "csv":
            frame.to_csv(path, index=False)
        elif a.format == "json":
            frame.to_json(path, orient="records", date_format="iso")
        else:
            frame.to_parquet(path, index=False)
        print(f"  {path}  ({len(frame):,} filas)")


if __name__ == "__main__":
    main()
