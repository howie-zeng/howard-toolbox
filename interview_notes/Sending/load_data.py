# %%
from pathlib import Path

import pandas as pd

DATA_PATH = Path(
    r"S:\QR\hzeng\howard-toolbox\interview_notes\Sending\loan_panel.parquet"
)

# %%
loan_panel = pd.read_parquet(DATA_PATH)

# %%
print(f"Shape: {loan_panel.shape}")
print("\nColumns and dtypes:")
print(loan_panel.dtypes)
loan_panel.head()

print(loan_panel.columns)

# %%




# %%
