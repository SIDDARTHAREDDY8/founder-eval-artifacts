"""Streamlit version of the sales dashboard app.

Run: streamlit run app_streamlit.py
"""
import matplotlib.pyplot as plt
import streamlit as st

from data_logic import load_sales, categories, filter_and_summarize

st.title("Sales dashboard")

df = load_sales()

category = st.selectbox("Category", options=categories(df))

summary, totals = filter_and_summarize(df, category)

st.header(f"{category} "
          f"({totals['products']} products, "
          f"{totals['units']} units, ${totals['revenue']:,})")

fig, ax = plt.subplots()
ax.bar(summary["product"], summary["revenue"])
ax.set_ylabel("Revenue ($)")
ax.set_title("Revenue by product")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
st.pyplot(fig)

st.dataframe(summary)
