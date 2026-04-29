import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from layer0_ideas.aggregator import run_idea_generation
from layer6_feedback.main import run_feedback_loop
from pipeline.orchestrator import run_pipeline
from shared.config_loader import load_broker_tickers
from shared.logging_config import setup_logging


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Small-cap investment pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--discover",
        action="store_true",
        help="Warstwa 0: znajdź spółki przez Finviz/OpenInsider i dodaj do watchlist.yaml",
    )
    group.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Uruchom pipeline dla podanych tickerów",
    )
    group.add_argument(
        "--feedback",
        action="store_true",
        help="Uruchom tylko feedback loop (warstwa 6)",
    )
    group.add_argument(
        "--broker",
        action="store_true",
        help="Uruchom pipeline dla wszystkich tickerów dostępnych u brokera (available-tickers.pdf)",
    )
    parser.add_argument(
        "--portfolio-manager",
        action="store_true",
        help="Uruchom również warstwę 5: Portfolio Manager",
    )
    args = parser.parse_args()

    if args.discover:
        run_idea_generation()
    elif args.feedback:
        run_feedback_loop()
    elif args.tickers:
        run_pipeline(tickers=args.tickers, run_l5=args.portfolio_manager)
    elif args.broker:
        run_pipeline(tickers=load_broker_tickers(), run_l5=args.portfolio_manager)
    else:
        run_pipeline(run_l5=args.portfolio_manager)


if __name__ == "__main__":
    main()
