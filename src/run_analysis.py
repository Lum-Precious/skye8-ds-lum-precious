from dataclasses import dataclass
from pathlib import Path
import argparse
import logging
import pandas as pd


@dataclass
class Config:
    """Store paths used by the analysis."""
    raw_dir: Path
    figures_dir: Path
    report_dir: Path


def setup_logging() -> logging.Logger:
    """Set up logging for the analysis."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    return logging.getLogger(__name__)


def load_data(

    config: Config,

    logger: logging.Logger

) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the three Project 3 datasets."""
    logger.info("Loading cell sites data.")
    cell_sites = pd.read_csv(
        config.raw_dir / "cell_sites.csv"
    )
    logger.info("Loading sessions data.")
    sessions = pd.read_csv(
        config.raw_dir / "sessions.csv"
    )
    logger.info("Loading complaints data.")
    complaints = pd.read_csv(
        config.raw_dir / "complaints.csv"
    )
    return cell_sites, sessions, complaints


def normalize_dropped(value: object) -> int:
    """Convert dropped values into 1 for dropped and 0 for not dropped."""
    value = str(value).strip().lower()
    if value in {"true", "yes"}:
        return 1
    if value in {"false", "no"}:
        return 0
    raise ValueError(f"Unexpected dropped value: {value}")


def reproduce_operator_table(
    sessions: pd.DataFrame,
    cell_sites: pd.DataFrame,
    logger: logging.Logger
) -> pd.DataFrame:
    logger.info("Joining sessions with cell-site technology.")
    data = sessions.merge(
        cell_sites[["site_id", "technology"]],
        on="site_id",
        how="left"
    )
    logger.info("Normalizing dropped values.")
    data["dropped_flag"] = data["dropped"].apply(
        normalize_dropped
    )
    logger.info("Calculating network-wide drop rates.")
    table = (
        data.groupby("technology")
        .agg(
            sessions=("session_id", "count"),
            dropped=("dropped_flag", "sum")
        )
        .reset_index()
    )
    table["drop_rate_pct"] = (

        table["dropped"]

        / table["sessions"]

        * 100

    )

    table["drop_rate_pct"] = table[

        "drop_rate_pct"

    ].round(2)

    technology_order = ["3G", "4G", "5G"]

    table["technology"] = pd.Categorical(

        table["technology"],

        categories=technology_order,

        ordered=True

    )

    table = table.sort_values(

        "technology"

    ).reset_index(drop=True)

    return table


def save_operator_table(

    table: pd.DataFrame,

    config: Config,

    logger: logging.Logger

) -> None:
    """Save the operator's table as a Markdown report."""

    config.report_dir.mkdir(

        parents=True,

        exist_ok=True

    )

    report_path = (

        config.report_dir

        / "operator_table.md"

    )

    with report_path.open(

        "w",

        encoding="utf-8"

    ) as file:
        file.write("# Operator Network-Wide drop rate\n\n")

        file.write(

            "| Technology | Sessions | Dropped | Drop Rate |\n"

        )
        for _, row in table.iterrows():

            file.write(

                f"| {row['technology']} "

                f"| {row['sessions']:,} "

                f"| {row['dropped']:,} "

                f"| {row['drop_rate_pct']:.2f}% |\n"

            )

        file.write("\n")

    logger.info(

        "Operator table saved to %s",

        report_path

    )


def parse_arguments() -> Config:

    parser = argparse.ArgumentParser(

        description="Run Skye8 Project 3 Stage A analysis."
    )
    parser.add_argument(
        "--raw",
        type=Path,
        required=True,
        help="Path to the raw data directory."
    )
    parser.add_argument(
        "--figures",
        type=Path,
        required=True,
        help="Path to the figures directory."
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Path to the reports directory."
    )
    args = parser.parse_args()
    return Config(
        raw_dir=args.raw,
        figures_dir=args.figures,
        report_dir=args.report
    )


def main() -> None:

    logger = setup_logging()
    config = parse_arguments()
    config.figures_dir.mkdir(
        parents=True,
        exist_ok=True
    )
    cell_sites, sessions, complaints = load_data(
        config,
        logger
    )
    # Complaints will be used in later stages.
    _ = complaints
    operator_table = reproduce_operator_table(
        sessions,
        cell_sites,
        logger
    )
    save_operator_table(
        operator_table,
        config,
        logger
    )
    logger.info(
        "\n%s",
        operator_table.to_string(index=False)
    )


if __name__ == "__main__":

    main()
