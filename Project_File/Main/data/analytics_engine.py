import math
import re
from pathlib import Path

import pandas as pd

from algorithms.sorting import merge_sort
from algorithms.searching import lower_bound

DATA_PATH = Path(__file__).parent / "parking_history.csv"

DEFAULT_RATES = {"Regular": 15.0, "EV": 25.0, "Handicap": 10.0, "VIP": 35.0}   # EGP per hour
GRACE_MINUTES = 15
VAT_RATE = 0.14

VEHICLE_TYPES = list(DEFAULT_RATES)
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND = ("Friday", "Saturday")                       # Egypt
REQUIRED = ["ticket_id", "license_plate", "vehicle_type", "spot_id", "entry_time", "exit_time",
            "fee_paid", "payment_method"]
PLATE_RE = re.compile(r"^[A-Z0-9\u0600-\u06FF\s-]{3,10}$")
TYPE_MAP = {"regular": "Regular", "ev": "EV", "electric": "EV", "handicap": "Handicap", "vip": "VIP"}


# ------------------------------------------------------------------ fees ------
def estimate_fee(duration_hours, vehicle_type, rates=None):
    """Fallback fee used ONLY to repair missing fee_paid values (Member 3's billing is the source of truth):
    free inside the grace period, then per started hour x rate, plus VAT."""
    rates = rates or DEFAULT_RATES
    if duration_hours is None or duration_hours != duration_hours or duration_hours < 0:
        raise ValueError("Duration must be a non-negative number")
    if duration_hours * 60 < GRACE_MINUTES:
        return 0.0
    subtotal = math.ceil(duration_hours) * rates.get(vehicle_type, rates["Regular"])
    return round(subtotal * (1 + VAT_RATE), 2)


# ----------------------------------------------------------- load & clean ------
def load_history(path=DATA_PATH):
    path = Path(path)
    if not path.exists():
        from data.generate_dataset import make_dataset
        make_dataset().to_csv(path, index=False)
    return pd.read_csv(path)


def clean_history(raw, rates=None):
    """Returns (clean_df, report). Bad rows are fixed or dropped and COUNTED - never a crash."""
    rates = rates or DEFAULT_RATES
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    df = raw.copy()
    report = {"rows_loaded": len(df)}

    n = len(df)
    df = df.drop_duplicates(subset="ticket_id", keep="first")
    report["duplicate_tickets_removed"] = n - len(df)

    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce", format="mixed")
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce", format="mixed")
    n = len(df)
    df = df[df["entry_time"].notna()]
    report["invalid_entry_time_dropped"] = n - len(df)

    n = len(df)
    df = df[~(df["exit_time"].notna() & (df["exit_time"] < df["entry_time"]))]
    report["exit_before_entry_dropped"] = n - len(df)

    norm = df["vehicle_type"].astype("string").str.strip().str.lower().map(TYPE_MAP)
    report["unknown_vehicle_type_set_to_Regular"] = int(norm.isna().sum())
    df["vehicle_type"] = norm.fillna("Regular").astype(str)

    plates = df["license_plate"].astype("string").str.strip().str.upper()
    bad_plate = ~plates.fillna("").map(lambda p: bool(PLATE_RE.match(p)))
    report["invalid_plates_marked_UNKNOWN"] = int(bad_plate.sum())
    df["license_plate"] = plates.where(~bad_plate, "UNKNOWN").astype(str)

    report["missing_payment_method"] = int(df["payment_method"].isna().sum())
    df["payment_method"] = df["payment_method"].fillna("Unknown").astype(str).str.strip().str.title()

    df["status"] = df["exit_time"].map(lambda t: "Parked" if pd.isna(t) else "Completed")
    now = max(df["entry_time"].max(), df["exit_time"].max()) if len(df) else pd.Timestamp.now()
    df["duration_hours"] = ((df["exit_time"].fillna(now) - df["entry_time"]).dt.total_seconds() / 3600).round(2)
    df["hourly_rate"] = df["vehicle_type"].map(rates)

    done = df["status"] == "Completed"
    df["fee_paid"] = pd.to_numeric(df["fee_paid"], errors="coerce")
    bad_fee = done & (df["fee_paid"].isna() | (df["fee_paid"] < 0))
    report["fees_recomputed"] = int(bad_fee.sum())
    df.loc[bad_fee, "fee_paid"] = [estimate_fee(h, t, rates) for h, t in
                                   zip(df.loc[bad_fee, "duration_hours"], df.loc[bad_fee, "vehicle_type"])]
    df.loc[~done, "fee_paid"] = 0.0

    df["day"] = df["entry_time"].dt.normalize()
    df["entry_hour"] = df["entry_time"].dt.hour
    df["day_of_week"] = df["entry_time"].dt.day_name()
    df = df.sort_values("entry_time").reset_index(drop=True)
    report["rows_final"] = len(df)
    return df, report


def load_clean(path=DATA_PATH):
    return clean_history(load_history(path))


# ------------------------------------------------------------ analytics ------
def completed(df):
    return df[df["status"] == "Completed"]


def kpis(df, total_spots):
    done = completed(df)
    parked = int((df["status"] == "Parked").sum())
    return {
        "revenue": float(done["fee_paid"].sum()),
        "transactions": int(len(done)),
        "parked_now": parked,
        "occupancy_now_pct": round(parked / total_spots * 100, 1) if total_spots else 0.0,
        "avg_stay_hours": float(done["duration_hours"].mean()) if len(done) else 0.0,
        "avg_fee": float(done["fee_paid"].mean()) if len(done) else 0.0,
    }


def revenue_by_day(df):
    return completed(df).groupby("day")["fee_paid"].sum()

def revenue_by_weekday(df):
    return completed(df).groupby("day_of_week")["fee_paid"].sum().reindex(WEEKDAYS).fillna(0)

def revenue_by_vehicle(df):
    return completed(df).groupby("vehicle_type")["fee_paid"].sum().sort_values(ascending=False)

def revenue_per_parked_hour(df):
    """EGP earned per hour of parking, by vehicle type (fair comparison between categories)."""
    g = completed(df).groupby("vehicle_type").agg(revenue=("fee_paid", "sum"), hours=("duration_hours", "sum"))
    return (g["revenue"] / g["hours"]).round(2).sort_values(ascending=False)

def revenue_by_zone(df):
    """Zone = first letter of spot_id (A, B, C, D = garage rows)."""
    return completed(df).groupby(completed(df)["spot_id"].str[0])["fee_paid"].sum()

def vehicle_distribution(df):
    return df["vehicle_type"].value_counts()

def payment_split(df):
    g = completed(df).groupby("payment_method")["fee_paid"].agg(["count", "sum"])
    return g.rename(columns={"count": "payments", "sum": "revenue"}).round(2)

def avg_entries_per_hour(df):
    days = max(1, df["day"].nunique())
    return (df.groupby("entry_hour").size().reindex(range(24), fill_value=0) / days).round(2)

def heatmap_pivot(df):
    p = df.groupby(["day_of_week", "entry_hour"]).size().unstack(fill_value=0)
    return p.reindex(index=WEEKDAYS, columns=range(24), fill_value=0)

def occupancy_slots(df):
    """Cars present in each clock-hour of the history (a car counts in every hour it touches).
    Parked cars count up to the last timestamp in the data."""
    now = max(df["entry_time"].max(), df["exit_time"].max())
    counts = {}
    for entry, exit_ in zip(df["entry_time"], df["exit_time"]):
        cur, end = entry.floor("h"), (exit_ if pd.notna(exit_) else now)
        while cur <= end:
            counts[cur] = counts.get(cur, 0) + 1
            cur += pd.Timedelta(hours=1)
    s = pd.Series(counts).sort_index()
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="h"), fill_value=0)

def occupancy_by_hour(df, total_spots):
    s = occupancy_slots(df)
    return (s.groupby(s.index.hour).mean().reindex(range(24), fill_value=0) / total_spots * 100).clip(upper=100).round(1)

def occupancy_by_weekday(df, total_spots):
    s = occupancy_slots(df)
    by = s.groupby(s.index.day_name()).mean().reindex(WEEKDAYS).fillna(0)
    return (by / total_spots * 100).clip(upper=100).round(1)

def stay_buckets(df):
    labels = ["< 1h", "1-2h", "2-4h", "4-8h", "8h+"]
    cut = pd.cut(completed(df)["duration_hours"], bins=[0, 1, 2, 4, 8, float("inf")], labels=labels, right=False)
    return cut.value_counts().reindex(labels)

def top_customers(df, n=10):
    """Top customers by total paid, ranked with OUR merge_sort. Returns (DataFrame, SortMetrics)."""
    done = completed(df)
    done = done[done["license_plate"] != "UNKNOWN"]
    g = done.groupby("license_plate").agg(visits=("ticket_id", "count"), total_paid=("fee_paid", "sum"),
                                          avg_stay_h=("duration_hours", "mean")).reset_index()
    ranked, metrics = merge_sort(g.to_dict("records"), key=lambda r: r["total_paid"], reverse=True)
    out = pd.DataFrame(ranked[:n])
    if len(out):
        out["total_paid"] = out["total_paid"].round(2)
        out["avg_stay_h"] = out["avg_stay_h"].round(2)
    return out, metrics

def busiest_window(df, hours=3):
    """Busiest `hours` consecutive hours (sliding window, O(n)) over the avg-arrivals-per-hour profile."""
    values = list(avg_entries_per_hour(df))
    if hours <= 0 or hours > len(values):
        raise ValueError("Window must be between 1 and 24 hours")
    current = sum(values[:hours])
    best, start = current, 0
    for i in range(hours, len(values)):
        current += values[i] - values[i - hours]
        if current > best:
            best, start = current, i - hours + 1
    return start, start + hours, round(best, 1)

def insights(df, total_spots, surge_threshold=80):
    #Findings recomputed from whatever data is loaded 
    done = completed(df)
    if done.empty:
        return ["Not enough completed sessions to produce insights."]
    out = []

    occ = occupancy_by_hour(df, total_spots)
    hot = [h for h in range(24) if occ[h] >= surge_threshold]
    s, e, tot = busiest_window(df, 3)
    out.append(f"**Peak hours:** the busiest 3-hour block is {s:02d}:00-{e:02d}:00 (~{tot:.0f} arrivals/day); "
               f"peak average occupancy is {occ.max():.0f}% at {int(occ.idxmax()):02d}:00.")
    if hot:
        out.append(f"**Surge-pricing candidate:** occupancy is at or above {surge_threshold}% during "
                   f"{', '.join(f'{h:02d}:00' for h in hot)}.")
    else:
        out.append(f"No hour reaches {surge_threshold}% average occupancy, so surge pricing is not justified by this data.")

    per_hour = revenue_per_parked_hour(df)
    byv = revenue_by_vehicle(df)
    out.append(f"**Vehicle & revenue:** {per_hour.index[0]} earns the most per parked hour "
               f"({per_hour.iloc[0]:.1f} EGP/h), while {byv.index[0]} brings the biggest total "
               f"({byv.iloc[0] / byv.sum() * 100:.0f}% of revenue).")

    wd = occupancy_by_weekday(df, total_spots)
    weekend = wd[list(WEEKEND)].mean()
    weekday = wd.drop(list(WEEKEND)).mean()
    out.append(f"**Weekday vs weekend:** average occupancy is {weekday:.0f}% on weekdays and {weekend:.0f}% on "
               f"Fri-Sat; busiest day is {wd.idxmax()} ({wd.max():.0f}%).")

    short = (done["duration_hours"] <= 1).mean() * 100
    out.append(f"**Turnover:** average stay is {done['duration_hours'].mean():.1f} h and {short:.0f}% of visits "
               f"finish within the first hour.")

    rd = revenue_by_day(df)
    out.append(f"**Best day:** {rd.idxmax():%A %d %b %Y} with {rd.max():,.0f} EGP (daily average {rd.mean():,.0f} EGP).")
    return out

def sessions_between(sorted_records, start, end):
    lo, s1 = lower_bound(sorted_records, start, key=lambda r: r["entry_time"])
    hi, s2 = lower_bound(sorted_records, end, key=lambda r: r["entry_time"])
    return sorted_records[lo:hi], s1 + s2
