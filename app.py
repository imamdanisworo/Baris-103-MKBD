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
        date = datetime(int(year), int(month), int(day))
        return date.strftime("%d %b %Y")
    return filename

def style_df(df, numeric_cols):
    return df.style.set_properties(
        **{'text-align': 'right'},
        subset=numeric_cols
    ).set_table_styles([
        {"selector":"th","props":[("text-align","left")]}
    ])

st.set_page_config(page_title="Client Balance Comparison", layout="wide")
st.markdown("# 📊 Client Balance Changes & Rankings")
st.info("**Step 1:** Upload yesterday's and today's files (CSV, pipe delimited).<br>**Step 2:** Click 'Generate Comparison Table'.<br>**Step 3:** Browse tabs for insights & rankings.", icon="ℹ️")
st.divider()

col1, col2 = st.columns(2)
with col1:
    yesterday_file = st.file_uploader("⬅️ Upload YESTERDAY'S file", type=["csv"], key="yesterday")
with col2:
    current_file = st.file_uploader("➡️ Upload TODAY'S file", type=["csv"], key="current")

def file_signature(uploaded_file):
    if uploaded_file is None:
        return None
    return (uploaded_file.name, uploaded_file.size, getattr(uploaded_file, 'last_modified', None))

sig_yest = file_signature(yesterday_file)
sig_curr = file_signature(current_file)

if ('sig_yest' in st.session_state and st.session_state['sig_yest'] != sig_yest) or \
   ('sig_curr' in st.session_state and st.session_state['sig_curr'] != sig_curr):
    st.session_state.pop('final_result_with_total', None)
    st.session_state.pop('final_result', None)

st.session_state['sig_yest'] = sig_yest
st.session_state['sig_curr'] = sig_curr

if yesterday_file and current_file:
    if st.button("🚦 Generate Comparison Table"):
        with st.spinner("Processing and analyzing your data..."):
            df_yest = pd.read_csv(yesterday_file, sep="|")
            df_curr = pd.read_csv(current_file, sep="|")

            yest_sum = df_yest.groupby('custcode', as_index=False).agg({
                'custname': 'first',
                'salesid': 'first',
                'currentbal': 'sum'
            }).rename(columns={'currentbal': 'yesterday_currentbal'})

            curr_sum = df_curr.groupby('custcode', as_index=False).agg({
                'custname': 'first',
                'salesid': 'first',
                'currentbal': 'sum',
                'int_rate': 'first',
                'int_rate_daily': 'first'
            }).rename(columns={'currentbal': 'current_currentbal'})

            result = pd.merge(yest_sum, curr_sum, on='custcode', how='outer', suffixes=('_yest', '_curr'))
            result['custname'] = result['custname_curr'].combine_first(result['custname_yest'])
            result['salesid'] = result['salesid_curr'].combine_first(result['salesid_yest'])
            result['yesterday_currentbal'] = result['yesterday_currentbal'].fillna(0)
            result['current_currentbal'] = result['current_currentbal'].fillna(0)
            result['change'] = result['current_currentbal'] - result['yesterday_currentbal']

            final_result = result[['custcode', 'custname', 'salesid', 'yesterday_currentbal', 'current_currentbal', 'change', 'int_rate', 'int_rate_daily']]
            totals = {
                'custcode': '',
                'custname': 'TOTAL',
                'salesid': '',
                'yesterday_currentbal': final_result['yesterday_currentbal'].sum(),
                'current_currentbal': final_result['current_currentbal'].sum(),
                'change': final_result['change'].sum(),
                'int_rate': None,
                'int_rate_daily': None
            }
            final_result_with_total = pd.concat([final_result, pd.DataFrame([totals])], ignore_index=True)

            st.session_state['final_result'] = final_result
            st.session_state['final_result_with_total'] = final_result_with_total

    if 'final_result_with_total' in st.session_state:
        final_result_with_total = st.session_state['final_result_with_total']
        final_result = st.session_state['final_result']

        yesterday_label = extract_date_label(sig_yest[0]) if sig_yest else "Yesterday"
        today_label = extract_date_label(sig_curr[0]) if sig_curr else "Today"
        col_rename = {
            'yesterday_currentbal': f'Balance as of {yesterday_label}',
            'current_currentbal': f'Balance as of {today_label}',
            'change': 'Changes'
        }
        numeric_cols = list(col_rename.values())

        st.markdown("### 🗂️ All Clients — Balance Change Table")
        main_table = final_result_with_total.rename(columns=col_rename)
        styled = style_df(add_separator(main_table, numeric_cols), numeric_cols)
        st.write(styled, use_container_width=True)
        csv = main_table.to_csv(index=False)
        st.download_button("⬇️ Download Result as CSV", csv, "balance_changes.csv", "text/csv")

        st.divider()
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Analysis",
            "🥇 Rank IPOT",
            "🥇 Rank WM",
            "🥇 Rank Private Dealing",
            "🥇 Rank Others"
        ])

        with tab1:
            df = final_result.copy()
            df['Fee Type'] = df['int_rate'].apply(lambda x: 'Normal Fee' if pd.notnull(x) and x >= 0.36 else 'Special Fee')
            def classify_group(salesid):
                if salesid == 'IPOT':
                    return 'IPOT'
                elif isinstance(salesid, str) and salesid.startswith('WM'):
                    return 'WM'
                elif salesid in ['Private Dealing', 'RT2']:
                    return 'Private Dealing'
                else:
                    return 'Others'
            df['Group'] = df['salesid'].apply(classify_group)

            def build_group_summary_v2(data):
                summary = data.groupby(['Group', 'Fee Type'], as_index=False).agg({
                    'yesterday_currentbal': 'sum',
                    'current_currentbal': 'sum',
                    'change': 'sum'
                })
                total_row = pd.DataFrame([{
                    'Group': 'Total',
                    'Fee Type': '',
                    'yesterday_currentbal': summary['yesterday_currentbal'].sum(),
                    'current_currentbal': summary['current_currentbal'].sum(),
                    'change': summary['change'].sum()
                }])
                return pd.concat([summary, total_row], ignore_index=True)

            def build_total_summary_only(df):
                fee_totals = df.groupby('Fee Type', as_index=False).agg({
                    'yesterday_currentbal': 'sum',
                    'current_currentbal': 'sum',
                    'change': 'sum'
                })
                fee_totals['Group'] = 'Total ' + fee_totals['Fee Type']
                grand_total = pd.DataFrame([{
                    'Group': 'Grand Total',
                    'Fee Type': '',
                    'yesterday_currentbal': fee_totals['yesterday_currentbal'].sum(),
                    'current_currentbal': fee_totals['current_currentbal'].sum(),
                    'change': fee_totals['change'].sum()
                }])
                return pd.concat([fee_totals[['Group', 'Fee Type', 'yesterday_currentbal', 'current_currentbal', 'change']], grand_total], ignore_index=True)

            df_main = df[df['Group'].isin(['IPOT', 'WM', 'Others'])]
            df_priv = df[df['Group'] == 'Private Dealing']

            for title, summary_func in zip(
                ["1️⃣ IPOT, WM, and Others", "2️⃣ Private Dealing Only", "3️⃣ Total Seluruh Piutang"],
                [lambda: build_group_summary_v2(df_main), lambda: build_group_summary_v2(df_priv), lambda: build_total_summary_only(df)]
            ):
                st.markdown(f"#### {title}")
                styled = style_df(add_separator(summary_func().rename(columns=col_rename), numeric_cols), numeric_cols)
                st.write(styled, use_container_width=True)

        masks = {
            "IPOT": df['salesid'] == 'IPOT',
            "WM": df['salesid'].str.startswith('WM', na=False),
            "Private Dealing": df['salesid'].isin(['Private Dealing', 'RT2']),
            "Others": ~(df['salesid'].isin(['IPOT']) | df['salesid'].str.startswith('WM', na=False) | df['salesid'].isin(['Private Dealing', 'RT2']))
        }

        for tab, group_name in zip([tab2, tab3, tab4, tab5], masks.keys()):
            with tab:
                group_df = df[masks[group_name]]
                for label, data_func in [
                    (f"🥇 Top 20 {group_name} by Changes", lambda df: df.nlargest(20, 'change')),
                    (f"🥉 Bottom 20 {group_name} by Changes", lambda df: df.nsmallest(20, 'change')),
                    (f"💰 Top 20 {group_name} by Today's Value", lambda df: df.nlargest(20, 'current_currentbal'))
                ]:
                    st.markdown(f"#### {label}")
                    cols = ['custcode','custname','salesid','change','current_currentbal'] if 'Value' not in label else ['custcode','custname','salesid','current_currentbal','change']
                    df_out = data_func(group_df)[cols].rename(columns=col_rename)
                    styled = style_df(add_separator(df_out, numeric_cols), numeric_cols)
                    st.write(styled, use_container_width=True, height=400)
else:
    st.info("Please upload both files to begin.")
