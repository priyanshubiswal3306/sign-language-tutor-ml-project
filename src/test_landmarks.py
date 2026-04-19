import pandas as pd

file_path = "data/landmarks/A.csv"

df = pd.read_csv(file_path, header=None)

print("Shape:", df.shape)

print("\nFirst row sample:")
print(df.iloc[0])

print("\nTotal samples:", len(df))