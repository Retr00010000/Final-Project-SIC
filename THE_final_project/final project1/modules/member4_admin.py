import pandas as pd
import plotly.express as px
import streamlit as st

import data.analytics_engine as an
from algorithms.hash_table import HashTable
from algorithms.searching import benchmark_lookup, binary_search, range_search, sequential_find
from algorithms.sorting import merge_sort, quick_sort
from algorithms.stack_ds import AuditStack

SORT_FIELDS = {"Fee": "fee_paid", "Duration": "duration_hours", "Entry time": "entry_time"}
SHOW_COLS = ["ticket_id", "license_plate", "vehicle_type", "spot_id", "entry_time", "duration_hours", "fee_paid"]

@st.cache_data(show_spinner=False)
def _load_default():
    return an.load_clean()

def _get_data():
    """Team DataFrame from session state if present, else the CSV. Always cleaned the same way."""
    live = st.session_state.get("historical_df")
    if isinstance(live, pd.DataFrame) and not live.empty:
        return an.clean_history(live)
    return _load_default()

def _demo_stack(df):
    if "m4_demo_stack" not in st.session_state:
        stack = AuditStack()
        for r in df.tail(6).itertuples():
            stack.push(f"Car {r.license_plate} parked at spot {r.spot_id}")
        st.session_state.m4_demo_stack = stack
    return st.session_state.m4_demo_stack

def _undo_demo():
    try:
        st.session_state.m4_demo_stack.pop()
    except IndexError:
        pass

def render_member4_admin(total_spots=32):
    st.header("Admin Intelligence & Algorithms Lab")
    try:
        df, report = _get_data()
    except Exception as exc:                           # a bad dataset must never crash the app
        st.error(f"Could not load parking history: {exc}")
        return
    if df.empty:
        st.warning("No parking history yet.")
        return

    # ---- sidebar-style filters (kept in an expander so they work inside a tab) ----
    with st.expander("Filters", expanded=False):
        c1, c2 = st.columns(2)
        dmin, dmax = df["day"].min().date(), df["day"].max().date()
        picked = c1.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax, key="m4_dates")
        types = c2.multiselect("Vehicle type", an.VEHICLE_TYPES, default=an.VEHICLE_TYPES, key="m4_types")
    if isinstance(picked, (tuple, list)):
        start, end = (picked[0], picked[-1]) if picked else (dmin, dmax)
    else:
        start = end = picked
    view = df[(df["day"] >= pd.Timestamp(start)) & (df["day"] <= pd.Timestamp(end)) & (df["vehicle_type"].isin(types))]
    if view.empty or an.completed(view).empty:
        st.info("No completed sessions for these filters - widen the date range or vehicle types.")
        return

    tab_kpi, tab_viz, tab_alg, tab_ds, tab_dq = st.tabs(
        [" KPIs & Insights", " Charts", " Algorithms Lab", " Data-structure inspectors", " Data quality"])

    # ===================================== KPIs & Insights =====================================
    with tab_kpi:
        k = an.kpis(view, total_spots)
        m = st.columns(5)
        m[0].metric("Total revenue", f"{k['revenue']:,.0f} EGP")
        m[1].metric("Occupancy now", f"{k['occupancy_now_pct']:.0f}%", f"{k['parked_now']} of {total_spots} spots", delta_color="off")
        m[2].metric("Transactions", f"{k['transactions']:,}")
        m[3].metric("Avg stay", f"{k['avg_stay_hours']:.1f} h")
        m[4].metric("Avg fee", f"{k['avg_fee']:,.0f} EGP")

        st.subheader("Business insights (computed from the data)")
        for line in an.insights(view, total_spots):
            st.markdown(f"- {line}")

        daily = an.revenue_by_day(view).rename("revenue").reset_index()
        st.download_button(" Export daily revenue (CSV)", daily.to_csv(index=False).encode(),
                           "daily_revenue.csv", "text/csv")

    # ========================================= Charts =========================================
    with tab_viz:
        a, b = st.columns(2)
        occ = an.occupancy_by_hour(view, total_spots).rename("occupancy_pct").reset_index()
        occ.columns = ["hour", "occupancy_pct"]
        fig = px.line(occ, x="hour", y="occupancy_pct", markers=True, title="Hourly occupancy trend (avg %)")
        fig.update_layout(yaxis_range=[0, 105], xaxis=dict(dtick=2))
        a.plotly_chart(fig, use_container_width=True)

        rev = an.revenue_by_day(view).reset_index()
        rev.columns = ["day", "revenue"]
        b.plotly_chart(px.bar(rev, x="day", y="revenue", title="Daily revenue (EGP)"), use_container_width=True)

        c, d = st.columns(2)
        dist = an.vehicle_distribution(view).reset_index()
        dist.columns = ["vehicle_type", "vehicles"]
        c.plotly_chart(px.pie(dist, names="vehicle_type", values="vehicles", hole=0.5,
                              title="Vehicle type distribution"), use_container_width=True)
        per_hour = an.revenue_per_parked_hour(view).reset_index()
        per_hour.columns = ["vehicle_type", "egp_per_parked_hour"]
        d.plotly_chart(px.bar(per_hour, x="vehicle_type", y="egp_per_parked_hour",
                              title="Revenue per parked hour (EGP/h)"), use_container_width=True)

        st.plotly_chart(px.imshow(an.heatmap_pivot(view), aspect="auto", color_continuous_scale="Blues",
                                  labels=dict(x="Hour", y="Day", color="Entries"),
                                  title="Arrivals heatmap: day of week x hour"), use_container_width=True)

        e, f = st.columns(2)
        wd = an.occupancy_by_weekday(view, total_spots).reset_index()
        wd.columns = ["day", "occupancy_pct"]
        e.plotly_chart(px.bar(wd, x="day", y="occupancy_pct", title="Occupancy by day of week (avg %)"),
                       use_container_width=True)
        f.subheader("Payment methods")
        f.dataframe(an.payment_split(view), use_container_width=True)
        st.subheader("Top 10 customers (ranked with our Merge Sort)")
        top, metrics = an.top_customers(view, 10)
        st.dataframe(top, use_container_width=True, hide_index=True)
        st.caption(f"Merge Sort: {metrics.comparisons:,} comparisons, {metrics.swaps:,} moves, {metrics.calls:,} calls.")

    # ===================================== Algorithms Lab =====================================
    with tab_alg:
        records = an.completed(view).to_dict("records")

        st.subheader("1) Sorting engine - Merge Sort vs Quick Sort")
        c1, c2, c3, c4 = st.columns(4)
        label = c1.selectbox("Sort transactions by", list(SORT_FIELDS), key="m4_sort_field")
        algo = c2.selectbox("Algorithm", ["Merge Sort", "Quick Sort"], key="m4_sort_algo")
        desc = c3.radio("Order", ["Descending", "Ascending"], horizontal=True, key="m4_sort_order") == "Descending"
        topn = c4.slider("Rows to show", 5, 50, 10, key="m4_sort_n")
        field = SORT_FIELDS[label]
        sorter = merge_sort if algo == "Merge Sort" else quick_sort
        ranked, met = sorter(records, key=lambda r: r[field], reverse=desc)
        st.dataframe(pd.DataFrame(ranked[:topn])[SHOW_COLS], use_container_width=True, hide_index=True)
        mm = st.columns(4)
        mm[0].metric("Comparisons", f"{met.comparisons:,}")
        mm[1].metric("Swaps / moves", f"{met.swaps:,}")
        mm[2].metric("Recursive calls", f"{met.calls:,}")
        mm[3].metric("Time", f"{met.elapsed_ms:.1f} ms")

        n_max = max(11, len(records))
        n = st.slider("Compare both algorithms on the first N transactions", 10, n_max, min(500, n_max), key="m4_cmp_n")
        sample = records[:n]
        rows = [f(sample, key=lambda r: r[field], reverse=desc)[1].as_dict() for f in (merge_sort, quick_sort)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Merge Sort: stable, always O(n log n), needs O(n) extra memory. "
                   "Quick Sort: in-place, O(n log n) on average (3-way partition handles repeated fees).")

        st.divider()
        st.subheader("2) Searching engine - Sequential vs Binary search")
        by_ticket, _ = merge_sort(records, key=lambda r: r["ticket_id"])      # binary search needs SORTED data
        tickets = [r["ticket_id"] for r in by_ticket]
        default_id = tickets[len(tickets) // 2]
        wanted = st.text_input("Ticket ID", value=default_id, key="m4_ticket").strip().upper()
        i_seq, s_seq = sequential_find(records, wanted, key=lambda r: r["ticket_id"])
        i_bin, s_bin = binary_search(by_ticket, wanted, key=lambda r: r["ticket_id"])
        if i_bin == -1:
            st.warning("Ticket not found in the selected data.")
        else:
            st.dataframe(pd.DataFrame([by_ticket[i_bin]])[SHOW_COLS], use_container_width=True, hide_index=True)
        x, y, z = st.columns(3)
        x.metric("Sequential steps (O(n))", f"{s_seq:,}")
        y.metric("Binary steps (O(log n))", f"{s_bin:,}")
        z.metric("Data size", f"{len(records):,}")
        if st.button("Run benchmark on 200 random lookups", key="m4_bench"):
            bench = benchmark_lookup(by_ticket, key=lambda r: r["ticket_id"], samples=200)
            st.dataframe(pd.DataFrame([{"samples": bench["samples"],
                                        "avg sequential steps": round(bench["sequential_avg"], 1),
                                        "avg binary steps": round(bench["binary_avg"], 1)}]),
                         use_container_width=True, hide_index=True)

        st.markdown("**Time-window search (binary search on entries sorted by time)**")
        by_time, _ = merge_sort(records, key=lambda r: r["entry_time"])
        t_lo, t_hi = by_time[0]["entry_time"].date(), by_time[-1]["entry_time"].date()
        d1, d2 = st.columns(2)
        w1 = d1.date_input("From", t_lo, min_value=t_lo, max_value=t_hi, key="m4_w1")
        w2 = d2.date_input("To (inclusive)", t_hi, min_value=t_lo, max_value=t_hi, key="m4_w2")
        if w2 < w1:
            st.error("'To' date must not be before 'From' date.")
        else:
            lo, hi = pd.Timestamp(w1), pd.Timestamp(w2) + pd.Timedelta(days=1)
            hits, steps = range_search(by_time, lo, hi, key=lambda r: r["entry_time"])
            st.write(f"**{len(hits):,}** transactions found with **{steps}** binary-search steps "
                     f"(a sequential scan needs {len(records):,}).")

    # =============================== Data-structure inspectors ===============================
    with tab_ds:
        st.subheader("Hash Table inspector")
        cap = st.select_slider("Initial capacity", [16, 32, 64, 128, 256], value=64, key="m4_cap")
        table = HashTable(capacity=cap)
        for r in an.completed(view).to_dict("records"):
            table.insert(r["ticket_id"], r)
        h = st.columns(5)
        h[0].metric("Entries", f"{len(table):,}")
        h[1].metric("Capacity", f"{table.capacity:,}")
        h[2].metric("Load factor", f"{table.load_factor():.2f}")
        h[3].metric("Collisions", f"{table.collisions():,}")
        h[4].metric("Longest chain", table.longest_chain())
        lengths = pd.Series(table.bucket_lengths()).value_counts().sort_index().reset_index()
        lengths.columns = ["entries in bucket", "number of buckets"]
        st.plotly_chart(px.bar(lengths, x="entries in bucket", y="number of buckets",
                               title="Bucket distribution (how evenly the hash spreads keys)"), use_container_width=True)
        probe_id = st.text_input("Look up a ticket in the hash table", value=default_id, key="m4_probe").strip().upper()
        found = table.get(probe_id)
        st.write(f"Found: **{found is not None}** - checked **{table.last_probes}** entr{'y' if table.last_probes == 1 else 'ies'} "
                 f"inside one bucket (vs {len(table):,} for a full scan).")

        st.divider()
        st.subheader("LIFO Audit Stack inspector")
        live = st.session_state.get("history_stack")
        is_live = hasattr(live, "get_all_events")
        stack = live if is_live else _demo_stack(view)
        st.caption("Live garage audit trail (read-only here)." if is_live else
                   "Demo stack (no live ParkingLot stack found in session state).")
        st.metric("Events on stack", stack.size())
        events = stack.get_all_events()
        if events:
            st.dataframe(pd.DataFrame({"position (top = newest)": range(1, len(events) + 1),
                                       "event": [str(e) for e in events]}), use_container_width=True, hide_index=True)
        else:
            st.caption("Stack is empty.")
        if not is_live:
            st.button(" Undo last event (pop)", on_click=_undo_demo, disabled=stack.is_empty(), key="m4_undo")

    # ======================================= Data quality =======================================
    with tab_dq:
        st.subheader("Cleaning report")
        st.dataframe(pd.DataFrame({"step": list(report), "rows": list(report.values())}),
                     use_container_width=True, hide_index=True)
        st.subheader("Cleaned data preview")
        st.dataframe(view.head(200), use_container_width=True)
