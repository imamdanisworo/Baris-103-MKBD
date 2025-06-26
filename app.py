import streamlit as st
import pandas as pd
import re
from datetime import datetime

def add_separator(df, cols):
    fmt = df.copy()
    for col in cols:
        if col in fmt.columns:
            fmt[col] = fmt[col].apply(lambda x: '{:,.2f}'.format(x) if pd.notnull(x) else '')
    return fmt

def extract_date_label(filename):
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
    if m:
        y, mo, d = m.groups()
        return datetime(int(y), int(mo), int(d)).strftime("%d %b %Y")
    return filename

def html_table(df, numeric_cols, colgroup=""):
    rows = []
    for _, row in df.reset_index(drop=True).iterrows():
        is_total = row.iloc[0] in ['Total','Grand Total']
        r = "<tr>"
        for col in df.columns:
            base = "text-align:right; white-space:nowrap;" if col in numeric_cols else "white-space:nowrap;"
            style = base + (" font-weight:bold; background-color:#f2f2f2;" if is_total else "")
            r += f"<td style='{style} padding:4px 10px'>{row[col]}</td>"
        r += "</tr>"
        rows.append(r)
    headers = "".join(
      f"<th style='text-align:left; padding:4px 10px; white-space:nowrap;'>{c}</th>"
      for c in df.columns
    )
    return f"<table style='border-collapse:collapse; font-size:14px'>{colgroup}<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"

def get_colgroup_by_width(df, numeric_cols):
    widths = {col: max(df[col].astype(str).map(len).max(), len(col)) * 8 for col in df.columns}
    cg = "<colgroup>"
    for col in df.columns:
        cg += f"<col style='width:{widths[col]}px; white-space:nowrap;'>"
    return cg + "</colgroup>"

st.set_page_config(page_title="Client Balance Comparison", layout="wide")
st.title("📊 Client Balance Changes & Rankings")

col_y, col_c = st.columns(2)
with col_y:
    file_y = st.file_uploader("Upload YESTERDAY'S file", type="csv", key="y")
with col_c:
    file_c = st.file_uploader("Upload TODAY'S file", type="csv", key="c")

def sig(f): return (f.name, f.size, getattr(f,'last_modified',None)) if f else None
sig_y, sig_c = sig(file_y), sig(file_c)

if ('sig_y' in st.session_state and st.session_state['sig_y'] != sig_y) or \
   ('sig_c' in st.session_state and st.session_state['sig_c'] != sig_c):
    st.session_state.pop('final', None)
    st.session_state.pop('total_row', None)

st.session_state['sig_y'], st.session_state['sig_c'] = sig_y, sig_c
