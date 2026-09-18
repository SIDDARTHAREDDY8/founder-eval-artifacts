# Notebook-to-app conversion eval: marimo vs Streamlit

Both apps implement the same data-app task: load `data/sales.csv`, filter
by a category widget, show totals, a revenue bar chart, and a table.
The harness scores lines of code, conversion correctness, functional output,
and time to interactive app.

## How it works

`app_marimo.py` is a real marimo notebook (`mo.App`, `mo.ui.dropdown`,
reactive cells). `app_streamlit.py` is a real Streamlit app
(`st.selectbox`, `st.pyplot`, `st.dataframe`). Both import the same
`data_logic.py` (pandas), so the numbers they show come from one place.

`eval.py` runs four scoring steps:

1. LOC (non-blank, non-comment lines).
2. Conversion correctness: 7 static checks per app (shared data logic,
   CSV load, category widget, widget options, filter call, revenue bar
   chart, summary table).
3. Functional check: runs the shared logic per category, verifies totals
   are consistent.
4. Time to interactive: launches each app server and times until the first
   HTTP 200. Reported honestly as "not measured" if a runtime is missing.

## Run

```bash
pip install marimo streamlit pandas matplotlib
python3 eval.py
python3 eval.py --skip-servers   # static + functional checks only
```

## Measured result

Machine: Linux x86_64, AMD EPYC 9D25, Python 3.12.3.

| metric | marimo | streamlit |
|---|---|---|
| lines of code | 44 | 19 |
| conversion checks passed | 7/7 | 7/7 |
| time to first HTTP 200 | 1.1 s | 1.2 s |

Functional check: gadgets (4 products, 570 units, $17,850), gizmos
(3 products, 730 units, $13,100), tools (5 products, 470 units, $11,800).
Totals consistent across categories.

Honest read: for this small task both convert cleanly and serve in about a
second. The marimo notebook takes more lines because each reactive step is
its own cell; the Streamlit app is shorter because it reruns top to bottom.
Neither number claims one framework is better in general.
