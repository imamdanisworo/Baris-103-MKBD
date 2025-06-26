import streamlit as st
import pandas as pd

def add_separator(df, cols):
    fmt_df = df.copy()
    for col in cols:
        if col in fmt_df.columns:
            fmt_df[col] = fmt_df[col].apply(lambda x: '{:,.2f}'.format(x) if pd.notnull(x) else '')
    return fmt_df

st.set_page_config(page_title="Client Balance Comparison", layout="wide")

st.markdown("""# 📊 Client Balance Changes & Rankings""")
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

        st.success("Data comparison and rankings are ready! Browse the tabs below for results.")

    if 'final_result_with_total' in st.session_state:
        final_result_with_total = st.session_state['final_result_with_total']
        final_result = st.session_state['final_result']

        st.markdown("### 🗂️ All Clients — Balance Change Table")
        st.dataframe(final_result_with_total, use_container_width=True)
        csv = final_result_with_total.to_csv(index=False)
        st.download_button("⬇️ Download Result as CSV", csv, "balance_changes.csv", "text/csv")

        st.divider()

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Analysis",
            "🥇 Rank IPOT",
            "🥇 Rank WM",
            "🥇 Rank Private Dealing",
            "🥇 Rank Others"
        ])

        # ANALYSIS TAB ------------------------------------------------
        with tab1:
            df = final_result.copy()
            df['Fee Type'] = df['int_rate'].apply(lambda x: 'Normal Fee' if pd.notnull(x) and x >= 0.36 else 'Special Fee')
            df['Group'] = df.apply(
                lambda row: 'Private Dealing' if row['salesid'] in ['Private Dealing', 'RT2'] else row['salesid'],
                axis=1
            )

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

            priv_mask = df['Group'] == 'Private Dealing'
            df_groups = df[~priv_mask].copy()
            df_priv = df[priv_mask].copy()

            group_summary = build_group_summary_v2(df_groups)
            priv_summary = build_group_summary_v2(df_priv)
            total_summary = build_group_summary_v2(df)

            st.markdown("#### 1️⃣ IPOT, WM, and Others")
            st.dataframe(add_separator(group_summary, ['yesterday_currentbal', 'current_currentbal', 'change']), use_container_width=True)

            st.markdown("#### 2️⃣ Private Dealing Only")
            st.dataframe(add_separator(priv_summary, ['yesterday_currentbal', 'current_currentbal', 'change']), use_container_width=True)

            st.markdown("#### 3️⃣ Total Seluruh Piutang")
            st.dataframe(add_separator(total_summary, ['yesterday_currentbal', 'current_currentbal', 'change']), use_container_width=True)

        # RANKING TABS ------------------------------------------------
        masks = {
            "IPOT": df['salesid'] == 'IPOT',
            "WM": df['salesid'].str.startswith('WM', na=False),
            "Private Dealing": df['salesid'].isin(['Private Dealing', 'RT2']),
            "Others": ~(df['salesid'].isin(['IPOT']) | df['salesid'].str.startswith('WM', na=False) | df['salesid'].isin(['Private Dealing', 'RT2']))
        }

        for tab, group_name in zip([tab2, tab3, tab4, tab5], masks.keys()):
            with tab:
                st.markdown(f"#### 🥇 Top 20 {group_name} by Changes")
                group_df = df[masks[group_name]]
                top_change = group_df.nlargest(20, 'change')
                st.dataframe(
                    add_separator(top_change[['custcode','custname','salesid','change','current_currentbal']], ['change', 'current_currentbal']),
                    use_container_width=True, height=400
                )

                st.markdown(f"#### 🥉 Bottom 20 {group_name} by Changes")
                bottom_change = group_df.nsmallest(20, 'change')
                st.dataframe(
                    add_separator(bottom_change[['custcode','custname','salesid','change','current_currentbal']], ['change', 'current_currentbal']),
                    use_container_width=True, height=400
                )

                st.markdown(f"#### 💰 Top 20 {group_name} by Today's Value")
                top_value = group_df.nlargest(20, 'current_currentbal')
                st.dataframe(
                    add_separator(top_value[['custcode','custname','salesid','current_currentbal','change']], ['current_currentbal', 'change']),
                    use_container_width=True, height=400
                )
                if group_df.empty:
                    st.warning(f"No data found for {group_name} group.")
else:
    st.info("Please upload both files to begin.")
