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

if file_y and file_c and st.button("🚦 Generate Comparison Table"):
    with st.spinner("Processing..."):
        dy = pd.read_csv(file_y, sep="|")
        dc = pd.read_csv(file_c, sep="|")

        y = dy.groupby('custcode', as_index=False).agg({
            'custname':'first', 'salesid':'first', 'currentbal':'sum'
        }).rename(columns={'currentbal':'bal_y'})

        c_agg = {'custname':'first','salesid':'first','currentbal':'sum'}
        if 'int_rate' in dc: c_agg['int_rate']='first'
        if 'int_rate_daily' in dc: c_agg['int_rate_daily']='first'

        c = dc.groupby('custcode', as_index=False).agg(c_agg).rename(columns={'currentbal':'bal_c'})

        merged = pd.merge(y, c, on='custcode', how='outer')
        merged['custname'] = merged['custname_y'].combine_first(merged['custname_x'])
        merged['salesid'] = merged['salesid_y'].combine_first(merged['salesid_x'])
        merged.fillna({'bal_y':0,'bal_c':0}, inplace=True)
        merged['change'] = merged['bal_c'] - merged['bal_y']

        for col in ('int_rate','int_rate_daily'):
            if col not in merged: merged[col] = None

        final = merged[['custcode','custname','salesid','bal_y','bal_c','change','int_rate','int_rate_daily']]
        total = {
            'custcode':'','custname':'Total','salesid':'',
            'bal_y': final['bal_y'].sum(),
            'bal_c': final['bal_c'].sum(),
            'change': final['change'].sum(),
            'int_rate': None, 'int_rate_daily': None
        }
        st.session_state['final'] = final
        st.session_state['total_row'] = pd.DataFrame([total])

if 'final' in st.session_state:
    lbl_y = f"Balance as of {extract_date_label(sig_y[0])}"
    lbl_c = f"Balance as of {extract_date_label(sig_c[0])}"
    cols = {'bal_y': lbl_y, 'bal_c': lbl_c, 'change': 'Changes'}

    df = st.session_state['final']
    total_df = st.session_state.get('total_row', pd.DataFrame())

    df_disp = df.rename(columns=cols)
    total_disp = total_df.rename(columns=cols)

    st.subheader("📋 All Clients Balance Comparison")
    st.dataframe(add_separator(df_disp, list(cols.values())), use_container_width=True)

    # Clean total only for display
    total_disp_clean = total_disp.drop(columns=['custcode', 'salesid', 'int_rate', 'int_rate_daily'], errors='ignore')
    cg = get_colgroup_by_width(total_disp_clean, list(cols.values()))
    st.markdown(html_table(add_separator(total_disp_clean, list(cols.values())), list(cols.values()), cg),
                unsafe_allow_html=True)

    tab_analysis, *rank_tabs = st.tabs(["📊 Analysis", "🥇 IPOT", "🥇 WM", "🥇 Private Dealing", "🥇 Others"])

    df['Fee Type'] = df['int_rate'].apply(lambda x: 'Normal Fee' if pd.notnull(x) and x >= 0.36 else 'Special Fee')
    def grp(s):
        if s == 'IPOT': return 'IPOT'
        if isinstance(s, str) and s.startswith('WM'): return 'WM'
        if s in ['Private Dealing','RT2']: return 'Private Dealing'
        return 'Others'
    df['Group'] = df['salesid'].apply(grp)

    def sum_table(d):
        s = d.groupby(['Group','Fee Type'], as_index=False)[['bal_y','bal_c','change']].sum()
        t = pd.DataFrame([{'Group':'Total','Fee Type':'','bal_y':s.bal_y.sum(),'bal_c':s.bal_c.sum(),'change':s.change.sum()}])
        return pd.concat([s,t], ignore_index=True)

    def total_only(d):
        t = d.groupby('Fee Type')[['bal_y','bal_c','change']].sum().reset_index()
        g = pd.DataFrame([{'Fee Type':'Grand Total','bal_y':t.bal_y.sum(),'bal_c':t.bal_c.sum(),'change':t.change.sum()}])
        return pd.concat([t,g], ignore_index=True)

    def total_by_group(d):
        s = d.groupby('Group', as_index=False)[['bal_y','bal_c','change']].sum()
        g = pd.DataFrame([{'Group':'Total','bal_y':s.bal_y.sum(),'bal_c':s.bal_c.sum(),'change':s.change.sum()}])
        return pd.concat([s,g], ignore_index=True)

    with tab_analysis:
        for title, tbl in [
            ("1️⃣ IPOT, WM, Others by Fee Type", sum_table(df[df['Group'].isin(['IPOT','WM','Others'])])),
            ("2️⃣ Private Dealing by Fee Type", sum_table(df[df['Group']=='Private Dealing'])),
            ("3️⃣ Total Seluruh Piutang by Fee Type", total_only(df)),
            ("4️⃣ Total by Group Only", total_by_group(df))
        ]:
            st.markdown(f"#### {title}")
            disp = tbl.rename(columns=cols)
            cg2 = get_colgroup_by_width(disp, list(cols.values()))
            st.markdown(html_table(add_separator(disp, list(cols.values())), list(cols.values()), cg2),
                        unsafe_allow_html=True)

    for tab, grp_name in zip(rank_tabs, ['IPOT','WM','Private Dealing','Others']):
        with tab:
            subset = df[df['Group'] == grp_name]
            for title, fn in [
                ("Top 20 by Changes", lambda d: d.nlargest(20, 'change')),
                ("Bottom 20 by Changes", lambda d: d.nsmallest(20, 'change')),
                ("Top 20 by Today Value", lambda d: d.nlargest(20, 'bal_c')),
            ]:
                st.markdown(f"#### {title}")
                sel = fn(subset)
                disp = sel[['custcode','custname','salesid','change','bal_c']].rename(columns=cols)
                cg3 = get_colgroup_by_width(disp, list(cols.values()))
                st.markdown(html_table(add_separator(disp, list(cols.values())), list(cols.values()), cg3),
                            unsafe_allow_html=True)
