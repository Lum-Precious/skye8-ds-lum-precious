from dataclasses import dataclass
from pathlib import Path
import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt


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


def check_data_quality(
        cell_sites: pd.DataFrame, sessions: pd.DataFrame, complaints: pd.DataFrame,
        logger: logging.Logger) -> None:
    logger.info("checkimg data quality")
    logger.info(

        "Sessions: %s rows, %s duplicate rows",

        len(sessions),

        sessions.duplicated().sum()

    )

    logger.info(

        "Missing complaint resolution times: %s",

        complaints["resolved_days"].isna().sum()

    )

    logger.info(

        "Dropped values: %s",

        sessions["dropped"].value_counts().to_dict()

    )

    logger.info(

        "Throughput range: %.2f to %.2f Mbps",

        sessions["throughput_mbps"].min(),

        sessions["throughput_mbps"].max()

    )

    logger.info(

        "Number of sites: %s",

        len(cell_sites)
    )


def check_duplicates(
        sessions: pd.DataFrame, logger: logging.Logger) -> None:
    duplicate_count = sessions.duplicated(subset="session_id").sum()
    logger.info("Duplicate session ids: %s", duplicate_count)


def check_faulty_site(
        sessions: pd.DataFrame, logger: logging.Logger
) -> pd.DataFrame:

    faulty = sessions[(sessions["throughput_mbps"] < 0)
                      | (sessions["throughput_mbps"] > 1000)]
    logger.info("Sessions with impossible throughput: %s", len(faulty))
    if not faulty.empty:
        logger.info("sites with impossible throughput:\n%s",
                    faulty["site_id"].value_counts().to_string())
        mean_with = sessions["throughput_mbps"].mean()
        mean_without = sessions.loc[sessions["site_id"]
                                    != "CS-0077", "throughput_mbps"].mean()
        logger.info(
            "Mean throughput with CS-0077: %.1f Mbps, without: %.1f Mbps", mean_with, mean_without)
        sessions_clean = sessions[sessions["site_id"] != "CS-0077"].copy()
        return sessions_clean


def clean_timestamps(sessions, logger):
    s = sessions["started_at"].astype(str)
    unix_mask = s.str.fullmatch(r"\d{9,10}")
    dmy_mask = s.str.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")
    iso_mask = ~(unix_mask | dmy_mask)
    parsed = pd.Series(pd.NaT, index=sessions.index, dtype="datetime64[ns]")
    parsed[unix_mask] = pd.to_datetime(s[unix_mask].astype(int), unit="s")
    parsed[dmy_mask] = pd.to_datetime(s[dmy_mask], format="%d/%m/%Y %H:%M")
    parsed[iso_mask] = pd.to_datetime(s[iso_mask], format="%Y-%m-%d %H:%M:%S")

    sessions["started_at_parsed"] = parsed

    return sessions


def clean_durations(
    sessions: pd.DataFrame,
    logger: logging.Logger
) -> pd.DataFrame:
    sessions = sessions.copy()
    sessions["duration_s"] = (
        sessions["duration_s"]
        .astype(str)
        .str.replace(" s", "", regex=False)
    )
    sessions["duration_s"] = pd.to_numeric(
        sessions["duration_s"],
        errors="coerce"
    )
    logger.info(
        "Invalid durations after conversion: %s",
        sessions["duration_s"].isna().sum()
    )
    return sessions


def clean_dropped(

    sessions: pd.DataFrame,

    logger: logging.Logger

) -> pd.DataFrame:

    sessions = sessions.copy()

    sessions["dropped"] = sessions["dropped"].astype(
        str).str.strip().str.lower()

    sessions["dropped_flag"] = sessions["dropped"].map({
        "true": 1,
        "yes": 1,
        "false": 0,
        "no": 0

    })

    logger.info(

        "Invalid dropped values: %s",

        sessions["dropped_flag"].isna().sum())
    return sessions


def profile_data(
    cell_sites: pd.DataFrame,
    sessions: pd.DataFrame,
    complaints: pd.DataFrame,
    logger: logging.Logger
) -> pd.DataFrame:

    logger.info("Profiling all columns")

    frames = {
        "cell_sites": cell_sites,
        "sessions": sessions,
        "complaints": complaints
    }

    rows = []

    for table_name, df in frames.items():

        for column in df.columns:

            series = df[column]

            rows.append({
                "table": table_name,
                "column": column,
                "dtype": str(series.dtype),
                "missing": int(series.isna().sum()),
                "unique": int(series.nunique()),
                "min": series.min()
                if pd.api.types.is_numeric_dtype(series)
                else "",
                "max": series.max()
                if pd.api.types.is_numeric_dtype(series)
                else ""
            })

    profile = pd.DataFrame(rows)

    logger.info("Profile completed")

    return profile


def create_eda_figures(
    sessions: pd.DataFrame,
    config: Config,
    logger: logging.Logger
) -> None:

    logger.info("Creating EDA figures")

    config.figures_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    clean_sessions = sessions[
        (sessions["throughput_mbps"] >= 0)
        & (sessions["throughput_mbps"] <= 1000)
        & (sessions["duration_s"] > 0)
        & (sessions["duration_s"] <= 3600)
    ].copy()

    plt.figure(figsize=(8, 5))
    clean_sessions["throughput_mbps"].hist(bins=50)
    plt.xlabel("Throughput (Mbps)")
    plt.ylabel("Sessions")
    plt.title("Throughput Distribution")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.savefig(
        config.figures_dir / "throughput_distribution.png"
    )
    plt.close()

    plt.figure(figsize=(8, 5))
    clean_sessions["duration_s"].hist(bins=50)
    plt.xlabel("Duration (seconds)")
    plt.ylabel("Sessions")
    plt.title("Session Duration Distribution")
    plt.xlim(0, 600)
    plt.tight_layout()
    plt.savefig(
        config.figures_dir / "duration_distribution.png"
    )
    plt.close()

    drop_by_device = (
        sessions.groupby("device_type")["dropped_flag"]
        .mean()
        .mul(100)
    )

    plt.figure(figsize=(8, 5))
    drop_by_device.plot(kind="bar")
    plt.xlabel("Device Type")
    plt.ylabel("Drop Rate (%)")
    plt.title("Drop Rate by Device Type")
    plt.tight_layout()
    plt.savefig(
        config.figures_dir / "drop_rate_by_device.png"
    )
    plt.close()

    logger.info("EDA figures saved")


def distribution_stats(
    series: pd.Series, name: str, logger: logging.Logger
) -> dict:
    mean, median = series.mean(), series.median()
    skew = series.skew()
    stats = {
        "metric": name,
        "mean": round(mean, 2),
        "median": round(median, 2),
        "q1": round(series.quantile(0.25), 2),
        "q3": round(series.quantile(0.75), 2),
        "skew": round(skew, 2),
        "recommended_stat": "median" if abs(skew) > 1 else "mean",
    }
    logger.info("Distribution stats for %s: %s", name, stats)
    return stats


def drop_rate_breakdowns(
    sessions: pd.DataFrame, cell_sites: pd.DataFrame, logger: logging.Logger
) -> dict[str, pd.DataFrame]:
    df = sessions.merge(
        cell_sites[["site_id", "region", "backhaul"]],
        on="site_id", how="left", validate="m:1",
    )
    df["hour"] = df["started_at_parsed"].dt.hour

    factors = ["hour", "region", "device_type", "backhaul"]
    results = {}
    for factor in factors:
        table = (
            df.groupby(factor)["dropped_flag"]
            .agg(sessions="count", drop_rate="mean")
            .reset_index()
        )
        logger.info("Drop rate by %s:\n%s", factor,
                    table.to_string(index=False))
        results[factor] = table
    return results


def drop_rate_by_region_and_tech(
    sessions: pd.DataFrame, cell_sites: pd.DataFrame, logger: logging.Logger
) -> pd.DataFrame:
    df = sessions.merge(
        cell_sites[["site_id", "region", "technology"]],
        on="site_id", how="left", validate="m:1",
    )
    table = (
        df.groupby(["region", "technology"])["dropped_flag"]
        .agg(session="count", drop_rate="mean")
        .reset_index()
    )
    table["drop_rate_pct"] = (table["drop_rate"] * 100). round(2)
    logger.info("Drop rate by region and technology:\n%s",
                table.to_string(index=False))
    return table


def tech_distribution_by_region(
    sessions: pd.DataFrame, cell_sites: pd.DataFrame, logger: logging.Logger
) -> pd.DataFrame:
    df = sessions.merge(
        cell_sites[["site_id", "region", "technology"]],
        on="site_id", how="left", validate="m:1",
    )
    counts = df.groupby(["region", "technology"]). size().unstack(fill_value=0)
    pct = counts.div(counts.sum(axis=1), axis=0).mul(100).round(1)
    logger.info("technology mix by region(%% of session):\n%s",
                pct.to_string())
    return pct


def region_technology_analysis(
    sessions: pd.DataFrame,
    cell_sites: pd.DataFrame,
    logger: logging.Logger
) -> pd.DataFrame:

    logger.info("Calculating region and technology drop rates")

    data = sessions.merge(
        cell_sites[["site_id", "region", "technology"]],
        on="site_id",
        how="left"
    )

    table = (
        data.groupby(["region", "technology"])
        .agg(
            sessions=("session_id", "count"),
            dropped=("dropped_flag", "sum")
        )
        .reset_index()
    )

    table["drop_rate_pct"] = (
        table["dropped"] / table["sessions"] * 100
    ).round(2)

    logger.info(
        "Region and technology analysis completed"
    )

    return table


def plot_regional_4g_vs_5g(
    region_tech_table: pd.DataFrame,
    figures_dir: Path,
    logger: logging.Logger
) -> None:

    logger.info("Creating regional 4G versus 5G drop-rate chart")

    comparison = region_tech_table[
        region_tech_table["technology"].isin(["4G", "5G"])
    ].copy()

    pivot = comparison.pivot(
        index="region",
        columns="technology",
        values="drop_rate_pct"
    )

    ax = pivot.plot(
        kind="bar",
        figsize=(10, 6)
    )

    ax.set_title("4G vs 5G Drop Rate by Region")
    ax.set_xlabel("Region")
    ax.set_ylabel("Drop Rate (%)")
    ax.legend(title="Technology")

    fig = ax.get_figure()
    fig.tight_layout()

    output_path = figures_dir / "regional_4g_vs_5g_drop_rate.png"
    fig.savefig(output_path)
    plt.close(fig)

    logger.info(
        "Saved regional comparison chart to %s",
        output_path
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
    check_data_quality(
        cell_sites, sessions, complaints, logger
    )
    sessions = clean_timestamps(sessions, logger)
    sessions = clean_durations(sessions, logger)
    sessions = clean_dropped(sessions, logger)
    profile = profile_data(cell_sites, sessions, complaints, logger)
    create_eda_figures(sessions, config, logger)
    check_duplicates(sessions, logger)
    sessions = check_faulty_site(sessions, logger)
    throughput_stats = distribution_stats(
        sessions["throughput_mbps"], "throughput_mbps", logger)
    duration_stats = distribution_stats(
        sessions["duration_s"], "duration_s", logger)
    breakdown = drop_rate_breakdowns(sessions, cell_sites, logger)
    region_tech_table = drop_rate_by_region_and_tech(
        sessions, cell_sites, logger)
    tech_mix = tech_distribution_by_region(
        sessions, cell_sites, logger)
    region_tech_table = region_technology_analysis(
        sessions, cell_sites, logger)
    region_tech_table = region_technology_analysis(
        sessions,
        cell_sites,
        logger
    )

    plot_regional_4g_vs_5g(region_tech_table, config.figures_dir, logger)

    operator_table = reproduce_operator_table(
        sessions, cell_sites,
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
