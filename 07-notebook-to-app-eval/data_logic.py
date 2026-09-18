"""Shared data logic used by both the marimo notebook and the Streamlit app.

The eval imports this module directly to verify the numbers both apps show.
"""
import os

import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "data", "sales.csv")


def load_sales(path=DATA_PATH):
    return pd.read_csv(path)


def categories(df):
    return sorted(df["category"].unique().tolist())


def filter_and_summarize(df, category):
    """Filter to one category; return per-product revenue table + totals."""
    sub = df[df["category"] == category].copy()
    summary = (sub.groupby("product", as_index=False)
                  .agg(units=("units", "sum"), revenue=("revenue", "sum"))
                  .sort_values("revenue", ascending=False))
    totals = {"units": int(sub["units"].sum()),
              "revenue": int(sub["revenue"].sum()),
              "products": int(sub["product"].nunique())}
    return summary, totals
