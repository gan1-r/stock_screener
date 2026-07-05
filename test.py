import pandas as pd


df = pd.read_csv("data/results_2026-07-05_20-48-00.csv")
jumlah_unik = df['Ticker'].nunique()
print(jumlah_unik)

df2 = pd.read_csv("data/results_2026-07-05_20-53-11.csv")
jumlah_unik2 = df2['Ticker'].nunique()
print(jumlah_unik2)

df3 = pd.read_csv("data/results_2026-07-05_21-05-16.csv")
jumlah_unik3 = df3['Ticker'].nunique()
print(jumlah_unik3)