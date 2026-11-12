from pathlib import Path
import numpy as np
import pandas as pd

RAW_PATH = Path(__file__).parent / "IIoT_Smart_Parking_Management.csv"
OUT_PATH = Path(__file__).parent / "parking_history.csv"

def make_dataset():
  raw = pd.read_csv(RAW_PATH)
  entry_times = pd.to_datetime(raw["Timestamp"])
  durations = raw["Parking_Duration"].astype(float)
  exit_times = entry_times + pd.to_timedelta(durations, unit="h")

  is_ev = raw["Vehicle_Type"] == "Electric Vehicle"
  is_handicap = (raw["Parking_Lot_Section"] == "Zone A") & (
      (raw["Parking_Spot_ID"] % 8).isin([0, 1, 2])
  )
  is_vip = raw["User_Type"].str.lower().isin(["staff", "vip"])

  vehicle_types = pd.Series("Regular", index=raw.index)
  vehicle_types[is_ev] = "EV"
  vehicle_types[is_handicap & ~is_ev] = "Handicap"
  vehicle_types[is_vip & ~is_ev & ~is_handicap] = "VIP"

  section_letters = raw["Parking_Lot_Section"].str.extract(r"Zone ([A-D])")[0]
  section_letters = section_letters.fillna("A")
  spot_nums = (raw["Parking_Spot_ID"] % 8) + 1
  spot_ids = section_letters + spot_nums.apply(lambda x: f"{x:02d}")

  rng = np.random.default_rng(42)
  letters = list("ABCDEFGHJKLMNPRSTUVXYZ")
  unique_plates = [
      f"{''.join(rng.choice(letters, 3))} {rng.integers(1000, 9999)}"
      for _ in range(300)
  ]
  license_plates = [
      unique_plates[i % len(unique_plates)] for i in raw["Parking_Spot_ID"]
  ]

  ticket_ids = [f"TCK-2021-{i+1:04d}" for i in range(len(raw))]

  pay_map = {
      "Paid": "Credit Card",
      "Unpaid": "Cash",
      "Overdue": "Mobile Wallet",
  }
  payment_methods = raw["Payment_Status"].map(pay_map).fillna("Cash")

  rates = {"Regular": 15.0, "EV": 25.0, "Handicap": 10.0, "VIP": 35.0}
  hourly_rates = vehicle_types.map(rates)
  fee_paid = np.round(durations * hourly_rates * 1.14, 2)

  df = pd.DataFrame({
      "ticket_id": ticket_ids,
      "license_plate": license_plates,
      "vehicle_type": vehicle_types,
      "spot_id": spot_ids,
      "entry_time": entry_times.dt.strftime("%Y-%m-%d %H:%M:%S"),
      "exit_time": exit_times.dt.strftime("%Y-%m-%d %H:%M:%S"),
      "duration_hours": durations,
      "hourly_rate": hourly_rates,
      "fee_paid": fee_paid,
      "payment_method": payment_methods,
      "day_of_week": entry_times.dt.day_name(),
      "entry_hour": entry_times.dt.hour,
  })

  df.to_csv(OUT_PATH, index=False)
  print(f"Dataset successfully updated, Total records: {len(df)}")
  return df

if __name__ == "__main__":
  make_dataset()
