import argparse
import re
import pandas as pd


SPEED_COL = "Time Taken (ms)"
ACCURACY_COL = "SSIM"
TRADEOFF_COL = "Tradeoff Score"

CATEGORY_ORDER = ["Speed", "Accuracy", "Tradeoff"]


def normalize_resolution(value: str) -> str:
    value = str(value).strip()
    numbers = re.findall(r"\d+", value)

    if len(numbers) >= 2:
        return f"{numbers[0]}x{numbers[1]}"

    return value.lower().replace(" ", "")


def percentage_behind_lower_is_better(values, best_value):
    """
    For metrics where lower is better.
    Example:
        best = 10
        value = 15
        percentage behind = 50%
    """
    if best_value == 0:
        return values - best_value

    return ((values - best_value) / abs(best_value)) * 100


def percentage_behind_higher_is_better(values, best_value):
    """
    For metrics where higher is better.
    Example:
        best = 0.95
        value = 0.90
        percentage behind = 5.26%
    """
    if best_value == 0:
        return best_value - values

    return ((best_value - values) / abs(best_value)) * 100


def calculate_group_scores(group: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates ranks and percentage gaps inside one benchmark scenario.

    One scenario means:
        Resolution x Target Colors
    """
    group = group.copy()

    fastest_time = group[SPEED_COL].min()
    best_ssim = group[ACCURACY_COL].max()
    best_tradeoff = group[TRADEOFF_COL].min()

    # Percentage gaps to best
    group["Speed % Behind Best"] = percentage_behind_lower_is_better(
        group[SPEED_COL],
        fastest_time,
    )

    group["Accuracy % Behind Best"] = percentage_behind_higher_is_better(
        group[ACCURACY_COL],
        best_ssim,
    )

    group["Tradeoff % Behind Best"] = percentage_behind_lower_is_better(
        group[TRADEOFF_COL],
        best_tradeoff,
    )

    # Ranks inside this benchmark scenario
    group["Speed Rank"] = group[SPEED_COL].rank(
        method="min",
        ascending=True,
    )

    group["Accuracy Rank"] = group[ACCURACY_COL].rank(
        method="min",
        ascending=False,
    )

    # IMPORTANT:
    # Tradeoff Score / Pareto score is LOWER = BETTER
    group["Tradeoff Rank"] = group[TRADEOFF_COL].rank(
        method="min",
        ascending=True,
    )

    return group


def summarize_category(
    detailed_df: pd.DataFrame,
    category: str,
) -> pd.DataFrame:
    rank_col = f"{category} Rank"
    gap_col = f"{category} % Behind Best"

    summary = (
        detailed_df
        .groupby("Algorithm")
        .agg(
            Average_Rank=(rank_col, "mean"),
            Median_Rank=(rank_col, "median"),
            Worst_Rank=(rank_col, "max"),
            Wins=(rank_col, lambda x: (x == 1).sum()),
            Comparisons=(rank_col, "count"),
            Average_Percentage_Behind_Best=(gap_col, "mean"),
            Median_Percentage_Behind_Best=(gap_col, "median"),
            Worst_Percentage_Behind_Best=(gap_col, "max"),
        )
        .reset_index()
    )

    summary["Category"] = category

    summary = summary[
        [
            "Category",
            "Algorithm",
            "Average_Rank",
            "Median_Rank",
            "Worst_Rank",
            "Wins",
            "Comparisons",
            "Average_Percentage_Behind_Best",
            "Median_Percentage_Behind_Best",
            "Worst_Percentage_Behind_Best",
        ]
    ]

    summary = summary.sort_values(
        by=[
            "Average_Rank",
            "Wins",
            "Median_Percentage_Behind_Best",
            "Worst_Rank",
        ],
        ascending=[
            True,
            False,
            True,
            True,
        ],
    )

    return summary

def choose_top_algorithms(summary_df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    top_algorithms = []

    for category in CATEGORY_ORDER:
        category_df = summary_df[summary_df["Category"] == category].copy()

        category_top = category_df.head(top_n).copy()
        category_top.insert(1, "Position", range(1, len(category_top) + 1))

        top_algorithms.append(category_top)

    return pd.concat(top_algorithms, ignore_index=True)


def run_analysis(
    csv_path: str,
    output_prefix: str,
    resolution_filter: str | None = None,
    excluded_resolutions: list[str] | None = None,
):
    df = pd.read_csv(csv_path)

    required_cols = {
        "Algorithm",
        "Resolution",
        "Target Colors",
        SPEED_COL,
        ACCURACY_COL,
        TRADEOFF_COL,
    }

    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df["Resolution Normalized"] = df["Resolution"].apply(normalize_resolution)

    if resolution_filter:
        wanted_resolution = normalize_resolution(resolution_filter)
        df = df[df["Resolution Normalized"] == wanted_resolution].copy()

        if df.empty:
            raise ValueError(f"No rows found for resolution: {resolution_filter}")

    if excluded_resolutions:
        excluded = {normalize_resolution(r) for r in excluded_resolutions}
        df = df[~df["Resolution Normalized"].isin(excluded)].copy()

        if df.empty:
            raise ValueError("No rows left after excluding resolutions.")

    scenario_count = df.groupby(["Resolution Normalized", "Target Colors"]).ngroups

    detailed_results = []

    for _, group in df.groupby(["Resolution Normalized", "Target Colors"]):
        scored_group = calculate_group_scores(group)
        detailed_results.append(scored_group)

    detailed_df = pd.concat(detailed_results, ignore_index=True)

    summary_parts = []

    for category in CATEGORY_ORDER:
        category_summary = summarize_category(detailed_df, category)
        summary_parts.append(category_summary)

    summary_df = pd.concat(summary_parts, ignore_index=True)
    winners_df = choose_top_algorithms(summary_df, top_n=3)

    detailed_output = f"{output_prefix}_detailed_per_scenario.csv"
    summary_output = f"{output_prefix}_summary_by_category.csv"
    winners_output = f"{output_prefix}_winners.csv"

    detailed_df.to_csv(detailed_output, index=False)
    summary_df.to_csv(summary_output, index=False)
    winners_df.to_csv(winners_output, index=False)

    print(f"\nScenario count: {scenario_count}")
    print("\n=== CATEGORY WINNERS ===\n")

    for _, row in winners_df.iterrows():
        print(f"{row['Category']}: {row['Algorithm']}")
        print(f"  Average rank: {row['Average_Rank']:.2f}")
        print(f"  Wins: {int(row['Wins'])}/{int(row['Comparisons'])}")
        print(
            f"  Median % behind best: "
            f"{row['Median_Percentage_Behind_Best']:.2f}%"
        )
        print(f"  Worst rank: {row['Worst_Rank']:.0f}")
        print()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "csv_path",
        help="Path to ranked_benchmarks.csv",
    )

    parser.add_argument(
        "--output-prefix",
        default="algorithm_selection",
        help="Prefix for output CSV files",
    )

    parser.add_argument(
        "--resolution",
        default=None,
        help='Optional. Example: "1920x1080". If omitted, uses all resolutions.',
    )

    parser.add_argument(
        "--exclude-resolution",
        action="append",
        default=[],
        help='Resolution to exclude. Can be used multiple times. Example: --exclude-resolution "640x360"',
    )

    args = parser.parse_args()

    run_analysis(
        csv_path=args.csv_path,
        output_prefix=args.output_prefix,
        resolution_filter=args.resolution,
        excluded_resolutions=args.exclude_resolution,
    )


if __name__ == "__main__":
    main()