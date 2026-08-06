import pandas as pd

files = [
'data/DAT_MT_GBPJPY_M1_202601.csv',
'data/DAT_MT_GBPJPY_M1_202602.csv',
'data/DAT_MT_GBPJPY_M1_202603.csv',
'data/DAT_MT_GBPJPY_M1_202604.csv',
'data/DAT_MT_GBPJPY_M1_202605.csv',
'data/DAT_MT_GBPJPY_M1_202606.csv',
'data/DAT_MT_GBPJPY_M1_2025.csv',
'data/DAT_MT_GBPJPY_M1_2024.csv'
]

# Baca dan gabungkan semua CSV
df = pd.concat(
    [pd.read_csv(file, header=None) for file in files],
    ignore_index=True
)

# Simpan hasil gabungan
output_file = r"data/DAT_MT_GBPJPY_M1_2024_2026.csv"


# Gabungkan kolom tanggal dan jam
df["timestamp"] = pd.to_datetime(
    df[0].astype(str) + " " + df[1].astype(str),
    format="%Y.%m.%d %H:%M",
    errors="coerce"
)

# Hapus data dengan timestamp tidak valid
df = df.dropna(subset=["timestamp"])

# Urutkan dari waktu paling lama ke paling baru
df = df.sort_values("timestamp", ascending=True).reset_index(drop=True)
df.drop(columns=['timestamp'], inplace=True)
df.to_csv(output_file, index=False)
print(f"Jumlah baris: {len(df):,}")
print(f"File tersimpan: {output_file}")
print(df.head())