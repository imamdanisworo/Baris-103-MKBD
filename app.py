import streamlit as st
import pandas as pd
import os
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

st.set_page_config(page_title="Client Balance Comparison", layout="wide")
st.markdown("# 📊 Client Balance Changes & Rankings")
st.info("Upload yesterday's & today's files (CSV, pipe-delimited). Then click Generate.")
st.divider()

col1, col2 = st.columns(2)
with col1:
    yesterday_file = st.file_uploader("Upload YESTERDAY'S file", type="csv", key="yesterday")
with col2:
    current_file = st.file_uploader("Upload TODAY'S file", type="csv", key="current")

def file_signature(uploaded_file):
    if not uploaded_file: return None
    return (uploaded_file.name, uploaded_file.size, getattr(uploaded_file, 'last_modified', None))

sig_yest = file_signature(yesterday_file)
sig_curr = file_signature(current_file)
if ('sig_yest' in st.session_state and st.session_state['sig_yest'] != sig_yest) or \
   ('sig_curr' in st.session_state and st.session_state['sig_curr'] != sig_curr):
    st.session_state.pop('final_result', None)
    st.session_state.pop('final_result_with_total', None)
st.session_state['sig_yest'], st.session_state['sig_curr'] = sig_yest, sig_curr

if yesterday_file and current_file and st.button("Generate Comparison Table"):
    with st.spinner("Processing..."):
        df_y = pd.read_csv(yesterday_file, sep="|")
        df_c = pd.read_csv(current_file, sep="|")

        y = df_y.groupby('custcode', as_index=False).agg({'custname':'first','salesid':'first','currentbal':'sum'}).rename(columns={'currentbal':'yesterday_currentbal'})
        c = df_c.groupby('custcode', as_index=False).agg({'custname':'first','salesid':'first','currentbal':'sum','int_rate':'first','int_rate_daily':'first'}).rename(columns={'currentbal':'current_currentbal'})
        merged = pd.merge(y, c, on='custcode', how='outer', suffixes=('_y','_c'))
        merged['custname'] = merged['custname_c'].fillna(merged['custname_y'])
        merged['salesid']  = merged['salesid_c'].fillna(merged['salesid_y'])
        merged = merged.fillna({'yesterday_currentbal':0, 'current_currentbal':0})
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
        st.session_state['final_result'], st.session_state['final_result_with_total'] = final, final_with

if 'final_result_with_total' in st.session_state:
    hey, cur = sig_yest[0], sig_curr[0]
    lbl_y = f"Balance as of {extract_date_label(hey)}"
    lbl_c = f"Balance as of {extract_date_label(cur)}"
    colnames = {'yesterday_currentbal':lbl_y,'current_currentbal':lbl_c,'change':'Changes'}

    # Main table
    st.markdown("### All Clients")
    main = st.session_state['final_result_with_total'].rename(columns=colnames)
    st.dataframe(add_separator(main, list(colnames.values())), use_container_width=True)

    st.divider()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Analysis","IPOT","WM","Private Dealing","Others"])

    # Analysis
    df = st.session_state['final_result'].copy()
    df['Fee Type'] = df['int_rate'].apply(lambda x:'Normal Fee' if pd.notnull(x) and x>=0.36 else 'Special Fee')
    def grp(s): 
        if s=='IPOT': return 'IPOT'
        if isinstance(s,str) and s.startswith('WM'): return 'WM'
        if s in ['Private Dealing','RT2']: return 'Private Dealing'
        return 'Others'
    df['Group'] = df['salesid'].apply(grp)

    def sum_table(d):
        s = d.groupby(['Group','Fee Type'], as_index=False)[['yesterday_currentbal','current_currentbal','change']].sum()
        tot = pd.DataFrame([{'Group':'Total','Fee Type':'','yesterday_currentbal':s.yesterday_currentbal.sum(),'current_currentbal':s.current_currentbal.sum(),'change':s.change.sum()}])
        return pd.concat([s,tot],ignore_index=True)

    def total_only(d):
        t = d.groupby('Fee Type')[['yesterday_currentbal','current_currentbal','change']].sum().reset_index()
        t['Group'] = 'Total '+t['Fee Type']
        g = pd.DataFrame([{'Fee Type':'','Group':'Grand Total','yesterday_currentbal':t.yesterday_currentbal.sum(),'current_currentbal':t.current_currentbal.sum(),'change':t.change.sum()}])
        return pd.concat([t,g],ignore_index=True)

    with tab1:
        # IPOT/WM/Others
        tab_df= sum_table(df[df['Group'].isin(['IPOT','WM','Others'])]).rename(columns=colnames)
        st.dataframe(add_separator(tab_df, list(colnames.values())), use_container_width=True)
        # Private Dealing
        tab_p = sum_table(df[df['Group']=='Private Dealing']).rename(columns=colnames)
        st.dataframe(add_separator(tab_p, list(colnames.values())), use_container_width=True)
        # Total Piutang
        tab_t = total_only(df).rename(columns=colnames)
        st.dataframe(add_separator(tab_t, list(colnames.values())), use_container_width=True)

    # Ranking tabs
    masks = {
        'IPOT': df['salesid']=='IPOT',
        'WM': df['salesid'].str.startswith('WM', na=False),
        'Private Dealing': df['salesid'].isin(['Private Dealing','RT2']),
        'Others':~(df['salesid']=='IPOT')&~df['salesid'].str.startswith('WM', na=False)&~df['salesid'].isin(['Private Dealing','RT2'])
    }
    for t, name in zip([tab2,tab3,tab4,tab5],masks):
        with t:
            subset=df[masks[name]]
            for lbl,f in [('Top 20 by Changes',lambda d:d.nlargest(20,'change')),
                          ('Bottom 20 by Changes',lambda d:d.nsmallest(20,'change')),
                          ('Top 20 by Today Value',lambda d:d.nlargest(20,'current_currentbal'))]:
                dt=f(subset)[['custcode','custname','salesid','change','current_currentbal']].rename(columns=colnames)
                st.markdown(f"#### {lbl}")
                st.dataframe(add_separator(dt, list(colnames.values())), use_container_width=True)
