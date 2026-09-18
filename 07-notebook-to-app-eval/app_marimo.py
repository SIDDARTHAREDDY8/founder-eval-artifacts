"""Marimo version of the sales dashboard app.

Run:  marimo run app_marimo.py
Edit: marimo edit app_marimo.py
"""
import marimo as mo

app = mo.App()


@app.cell
def __():
    from data_logic import load_sales, categories, filter_and_summarize
    df = load_sales()
    return categories, df, filter_and_summarize


@app.cell
def __(categories, df):
    category_picker = mo.ui.dropdown(
        options=categories(df),
        value=categories(df)[0],
        label="Category",
    )
    category_picker
    return (category_picker,)


@app.cell
def __(category_picker, df, filter_and_summarize):
    summary, totals = filter_and_summarize(df, category_picker.value)
    mo.md(
        f"## {category_picker.value} "
        f"({totals['products']} products, "
        f"{totals['units']} units, ${totals['revenue']:,})"
    )
    return summary, totals


@app.cell
def __(summary):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.bar(summary["product"], summary["revenue"])
    ax.set_ylabel("Revenue ($)")
    ax.set_title("Revenue by product")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig
    return


@app.cell
def __(summary):
    mo.ui.table(summary)
    return


if __name__ == "__main__":
    app.run()
