# Feature Demo

Interactive Streamlit apps for the research system.

## SOL 1m RSI-S paper dashboard

Account equity, open position, win/loss log, win rate, avg R.
Reads local paper files written by `scripts/sol_1m_rsi_core_paper.py`.

```bash
pip install streamlit pandas
streamlit run demo/rsi_1m_dashboard.py
```

Opens in the browser (usually http://localhost:8501). Refresh the page to update.

## XRP / SOL Day feature demo

```bash
streamlit run demo/app.py
```
