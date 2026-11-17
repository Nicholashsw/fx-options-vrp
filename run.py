"""Run the analysis layer: daily, strategy, stats, figures, rvforecast, rvstrategy."""
import argparse

from fxvrp import config, figures, panel, rvforecast, rvstrategy, stats, strategy

STAGES = [("daily", panel.run), ("strategy", strategy.run),
          ("stats", stats.run), ("figures", figures.run),
          ("rvforecast", rvforecast.run), ("rvstrategy", rvstrategy.run)]
NAMES = [name for name, _ in STAGES]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--from", dest="first", choices=NAMES, default=NAMES[0])
parser.add_argument("--to", dest="last", choices=NAMES, default=NAMES[-1])
args = parser.parse_args()

config.work_dir()
for name, run in STAGES[NAMES.index(args.first):NAMES.index(args.last) + 1]:
    print(f"== {name}")
    run()
