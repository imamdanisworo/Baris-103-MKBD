import streamlit as st
import pandas as pd
import re
from datetime import datetime

def add_separator(df, cols):
    fmt_df = df.copy()
    for col in cols:
        if col in fmt_df.columns:
            fmt_df[col] = fmt_df[col].apply(lambda x: '{:,.2f}'.format(x) if pd.notnull(x) else '')
    return fmt_df

def extract_date_label(filename):
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
    if match:
        year, month, day = match.groups()
        return datetime(int(year), int(month), int(day)).strftime("%d %b %Y")
    return filename

def html_table_with_colgroup(df, numeric_cols, colgroup):
    def make_html(row):
        html = "<tr>"
        for col in df.columns:
            val = row[col]
            style = "text-align:right;" if col in numeric_cols else ""
            html += f"<td style='{style} padding:4px 10px'>{val}</td>"
        html += "</tr>"
        return html

    headers = "".join(f"<th style='text-align:left; padding:4px 10px'>{col}</th>" for col in df.columns)
    rows = "\n".join(make_html(row) for _, row in df.iterrows())
    return f"<table style='border-collapse:collapse; font-size:14px'>{colgroup}<thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"

# Shared column widths for Rank tabs
colgroup_html = """<colgroup>
<col style='width: 80px;'>
<col style='width: 248px;'>
<col style='width: 120px;'>
<col style='width: 96px;'>
<col style='width: 104px;'>
</colgroup>"""

st.set_page_config(page_title="Client Balance Comparison", layout="wide")
st.title("📊 Client Balance Changes & Rankings")

col1, col2 = st.columns(2)
with col1:
    yesterday_file = st.file_uploader("Upload YESTERDAY'S file", type="csv", key="yesterday")
with col2:
    current_file = st.file_uploader("Upload TODAY'S file", type="csv", key="current")

def file_signature(uploaded_file):
    return (uploaded_file.name, uploaded_file.size, getattr(uploaded_file, 'last_modified', None)) if uploaded_file else None

sig_yest = file_signature(yesterday_file)
sig_curr = file_signature(current_file)

if ('sig_yest' in st.session_state and st.session_state['sig_yest'] != sig_yest) or \
   ('sig_curr' in st.session_state and st.session_state['sig_curr'] != sig_curr):
    st.session_state.pop('final_result', None)
    st.session_state.pop('final_result_with_total', None)

st.session_state['sig_yest'] = sig_yest
st.session_state['sig_curr'] = sig_curr

if yesterday_file and current_file and st.button("🚦 Generate Comparison Table"):
    with st.spinner("Processing..."):
        df_y = pd.read_csv(yesterday_file, sep="|")
        df_c = pd.read_csv(current_file, sep="|")

        y = df_y.groupby('custcode', as_index=False).agg({'custname':'first','salesid':'first','currentbal':'sum'}).rename(columns={'currentbal':'yesterday_currentbal'})
        c = df_c.groupby('custcode', as_index=False).agg({'custname':'first','salesid':'first','currentbal':'sum','int_rate':'first','int_rate_daily':'first'}).rename(columns={'currentbal':'current_currentbal'})

        merged = pd.merge(y, c, on='custcode', how='outer')
        merged['custname'] = merged['custname_y'].combine_first(merged['custname_x'])
        merged['salesid'] = merged['salesid_y'].combine_first(merged['salesid_x'])
        merged = merged.fillna({'yesterday_currentbal': 0, 'current_currentbal': 0})
        merged['change'] = merged['current_currentbal'] - merged['yesterday_currentbal']

        final = merged[['custcode','custname','salesid','yesterday_currentbal','current_currentbal','change','int_rate','int_rate_daily']]
        totals = {
            'custcode':'', 'custname':'TOTAL','salesid':'',
            'yesterday_currentbal':final['yesterday_currentbal'].sum(),
            'current_currentbal':final['current_currentbal'].sum(),
            'change':final['change'].sum(),
            'int_rate':None, 'int_rate_daily':None
        }
        final_with = pd.concat([final, pd.DataFrame([totals])], ignore_index=True)
        st.session_state['final_result'] = final
        st.session_state['final_result_with_total'] = final_with

if 'final_result_with_total' in st.session_state:
    hey, cur = sig_yest[0], sig_curr[0]
    lbl_y = f"Balance as of {extract_date_label(hey)}"
    lbl_c = f"Balance as of {extract_date_label(cur)}"
    colnames = {'yesterday_currentbal':lbl_y, 'current_currentbal':lbl_c, 'change':'Changes'}

    main = st.session_state['final_result_with_total'].rename(columns=colnames)
    st.subheader("📋 All Clients Balance Comparison")
    st.dataframe(add_separator(main, [c for c in colnames.values() if c in main.columns]), use_container_width=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Analysis", "🥇 IPOT", "🥇 WM", "🥇 Private Dealing", "🥇 Others"])

    df = st.session_state['final_result'].copy()
    df['Fee Type'] = df['int_rate'].apply(lambda x: 'Normal Fee' if pd.notnull(x) and x >= 0.36 else 'Special Fee')
    def grp(s): 
        if s == 'IPOT': return 'IPOT'
        if isinstance(s, str) and s.startswith('WM'): return 'WM'
        if s in ['Private Dealing', 'RT2']: return 'Private Dealing'
        return 'Others'
    df['Group'] = df['salesid'].apply(grp)

    def sum_table(d):
        s = d.groupby(['Group','Fee Type'], as_index=False)[['yesterday_currentbal','current_currentbal','change']].sum()
        tot = pd.DataFrame([{'Group':'Total','Fee Type':'','yesterday_currentbal':s.yesterday_currentbal.sum(),'current_currentbal':s.current_currentbal.sum(),'change':s.change.sum()}])
        return pd.concat([s,tot], ignore_index=True)

    def total_only(d):
        t = d.groupby('Fee Type')[['yesterday_currentbal','current_currentbal','change']].sum().reset_index()
        g = pd.DataFrame([{
            'Fee Type': 'Grand Total',
            'yesterday_currentbal': t['yesterday_currentbal'].sum(),
            'current_currentbal': t['current_currentbal'].sum(),
            'change': t['change'].sum()
        }])
        return pd.concat([t[['Fee Type','yesterday_currentbal','current_currentbal','change']], g], ignore_index=True)

    def total_by_group_only(d):
        return d.groupby('Group', as_index=False)[['yesterday_currentbal','current_currentbal','change']].sum()

    with tab1:
        st.markdown("#### 1️⃣ IPOT, WM, Others by Fee Type")
        df1 = sum_table(df[df['Group'].isin(['IPOT','WM','Others'])]).rename(columns=colnames)
        st.markdown(html_table_with_colgroup(add_separator(df1, list(colnames.values())), list(colnames.values()), colgroup_html), unsafe_allow_html=True)

        st.markdown("#### 2️⃣ Private Dealing by Fee Type")
        df2 = sum_table(df[df['Group'] == 'Private Dealing']).rename(columns=colnames)
        st.markdown(html_table_with_colgroup(add_separator(df2, list(colnames.values())), list(colnames.values()), colgroup_html), unsafe_allow_html=True)

        st.markdown("#### 3️⃣ Total Seluruh Piutang by Fee Type")
        df3 = total_only(df).rename(columns=colnames)
        st.markdown(html_table_with_colgroup(add_separator(df3, list(colnames.values())), list(colnames.values()), colgroup_html), unsafe_allow_html=True)

        st.markdown("#### 4️⃣ Total by Group Only")
        df4 = total_by_group_only(df).rename(columns=colnames)
        st.markdown(html_table_with_colgroup(add_separator(df4, list(colnames.values())), list(colnames.values()), colgroup_html), unsafe_allow_html=True)

    masks = {
        'IPOT': df['salesid'] == 'IPOT',
        'WM': df['salesid'].str.startswith('WM', na=False),
        'Private Dealing': df['salesid'].isin(['Private Dealing','RT2']),
        'Others': ~(df['salesid'] == 'IPOT') & ~df['salesid'].str.startswith('WM', na=False) & ~df['salesid'].isin(['Private Dealing','RT2'])
    }

    for t, name in zip([tab2, tab3, tab4, tab5], masks):
        with t:
            subset = df[masks[name]]
            for lbl, f in [
                ('Top 20 by Changes', lambda d: d.nlargest(20, 'change')),
                ('Bottom 20 by Changes', lambda d: d.nsmallest(20, 'change')),
                ('Top 20 by Today Value', lambda d: d.nlargest(20, 'current_currentbal'))
            ]:
                st.markdown(f"#### {lbl}")
                dt = f(subset)[['custcode','custname','salesid','change','current_currentbal']].rename(columns=colnames)
                styled = add_separator(dt, [c for c in colnames.values() if c in dt.columns])
                st.markdown(html_table_with_colgroup(styled, [c for c in colnames.values() if c in dt.columns], colgroup_html), unsafe_allow_html=True)
