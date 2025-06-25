import streamlit as st
import pandas as pd

def add_separator(df, cols):
    fmt_df = df.copy()
    for col in cols:
        if col in fmt_df.columns:
            fmt_df[col] = fmt_df[col].apply(lambda x: '{:,.2f}'.format(x) if pd.notnull(x) else '')
    return fmt_df

st.set_page_config(page_title="Client Balance Comparison", layout="wide")

# 1. Page title and instructions
st.markdown("""
# 📊 Client Balance Changes & Rankings
Compare balances, see group rankings, and analyze changes between **two dates**.
""")
st.info("**Step 1:** Upload yesterday's and today's files (CSV, pipe delimited).<br>**Step 2:** Click 'Generate Comparison Table'.<br>**Step 3:** Browse tabs for insights & rankings.", icon="ℹ️")

st.divider()

# 2. File upload, with instructions in columns
col1, col2 = st.columns(2)
with col1:
    yesterday_file = st.file_uploader("⬅️ Upload YESTERDAY'S file", type=["csv"], key="yesterday")
with col2:
    current_file = st.file_uploader("➡️ Upload TODAY'S file", type=["csv"], key="current")

# Signature and session state logic as before
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

# 3. Generate button with loading/progress indicator
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
                'currentbal': 'sum'
            }).rename(columns={'currentbal': 'current_currentbal'})

            result = pd.merge(
                yest_sum,
                curr_sum,
                on='custcode',
                how='outer',
                suffixes=('_yest', '_curr')
            )

            result['custname'] = result['custname_curr'].combine_first(result['custname_yest'])
            result['salesid'] = result['salesid_curr'].combine_first(result['salesid_yest'])
            result['yesterday_currentbal'] = result['yesterday_currentbal'].fillna(0)
            result['current_currentbal'] = result['current_currentbal'].fillna(0)
            result['change'] = result['current_currentbal'] - result['yesterday_currentbal']

            final_result = result[['custcode', 'custname', 'salesid', 'yesterday_currentbal', 'current_currentbal', 'change']]
            totals = {
                'custcode': '',
                'custname': 'TOTAL',
                'salesid': '',
                'yesterday_currentbal': final_result['yesterday_currentbal'].sum(),
                'current_currentbal': final_result['current_currentbal'].sum(),
                'change': final_result['change'].sum()
            }
            final_result_with_total = pd.concat([final_result, pd.DataFrame([totals])], ignore_index=True)

            st.session_state['final_result'] = final_result
            st.session_state['final_result_with_total'] = final_result_with_total

        st.success("Data comparison and rankings are ready! Browse the tabs below for results.")

    # 4. Main table and download (auto after processing)
    if 'final_result_with_total' in st.session_state:
        final_result_with_total = st.session_state['final_result_with_total']
        final_result = st.session_state['final_result']

        st.markdown("### 🗂️ All Clients — Balance Change Table")
        st.dataframe(final_result_with_total, use_container_width=True)
        csv = final_result_with_total.to_csv(index=False)
        st.download_button("⬇️ Download Result as CSV", csv, "balance_changes.csv", "text/csv")

        st.divider()

        # 5. Tabs, with emojis and clear names
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Analysis",
            "🥇 Rank IPOT",
            "🥇 Rank WM",
            "🥇 Rank Private Dealing",
            "🥇 Rank Others"
        ])

        # ------- TAB 1: ANALYSIS SUMMARY -------------
        with tab1:
            df = final_result.copy()
            ipot_mask = df['salesid'] == 'IPOT'
            wm_mask = df['salesid'].str.startswith('WM', na=False)
            priv_mask = (df['salesid'] == 'Private Dealing') | (df['salesid'] == 'RT2')
            others_mask = ~(ipot_mask | wm_mask | priv_mask)

            # Group sums
            total_yesterday = df['yesterday_currentbal'].sum()
            total_current = df['current_currentbal'].sum()
            total_change = df['change'].sum()
            ipot_yesterday = df.loc[ipot_mask, 'yesterday_currentbal'].sum()
            ipot_current = df.loc[ipot_mask, 'current_currentbal'].sum()
            ipot_change = df.loc[ipot_mask, 'change'].sum()
            wm_yesterday = df.loc[wm_mask, 'yesterday_currentbal'].sum()
            wm_current = df.loc[wm_mask, 'current_currentbal'].sum()
            wm_change = df.loc[wm_mask, 'change'].sum()
            priv_yesterday = df.loc[priv_mask, 'yesterday_currentbal'].sum()
            priv_current = df.loc[priv_mask, 'current_currentbal'].sum()
            priv_change = df.loc[priv_mask, 'change'].sum()
            others_yesterday = df.loc[others_mask, 'yesterday_currentbal'].sum()
            others_current = df.loc[others_mask, 'current_currentbal'].sum()
            others_change = df.loc[others_mask, 'change'].sum()

            analysis_data = {
                "Position": [
                    "Total",
                    "IPOT",
                    "WM",
                    "Private Dealing",
                    "Others"
                ],
                "Yesterday": [
                    total_yesterday,
                    ipot_yesterday,
                    wm_yesterday,
                    priv_yesterday,
                    others_yesterday
                ],
                "Current": [
                    total_current,
                    ipot_current,
                    wm_current,
                    priv_current,
                    others_current
                ],
                "Changes": [
                    total_change,
                    ipot_change,
                    wm_change,
                    priv_change,
                    others_change
                ]
            }
            analysis_df = pd.DataFrame(analysis_data)
            display_analysis = analysis_df.copy()
            for col in ['Yesterday', 'Current', 'Changes']:
                display_analysis[col] = display_analysis[col].apply(lambda x: '{:,.2f}'.format(x))
            st.markdown("#### 📋 Summary by Group")
            # Highlight Total row
            def highlight_total(row):
                return ['background-color: #e0f3ff' if row.Position == 'Total' else '' for _ in row]
            st.dataframe(display_analysis, use_container_width=True)

            st.caption("‘Others’ includes all clients not in IPOT, WM, or Private Dealing (RT2). Sums always reconcile to Total.")

        # ------- RANK TABS --------------------------
        for i, (tab, group_df, name) in enumerate([
            (tab2, df[ipot_mask], "IPOT"),
            (tab3, df[wm_mask], "WM"),
            (tab4, df[priv_mask], "Private Dealing"),
            (tab5, df[others_mask], "Others"),
        ]):
            with tab:
                st.markdown(f"#### 🥇 Top 20 {name} by Changes")
                top_change = group_df.nlargest(20, 'change')
                top_change = top_change.rename(columns={'current_currentbal': "Today's Value in IDR"})
                st.dataframe(
                    add_separator(
                        top_change[['custcode','custname','salesid','change',"Today's Value in IDR"] if name != "IPOT" else ['custcode','custname','change',"Today's Value in IDR"]],
                        ['change', "Today's Value in IDR"]
                    ),
                    use_container_width=True,
                    height=400
                )

                st.markdown(f"#### 🥉 Bottom 20 {name} by Changes")
                bottom_change = group_df.nsmallest(20, 'change')
                bottom_change = bottom_change.rename(columns={'current_currentbal': "Today's Value in IDR"})
                st.dataframe(
                    add_separator(
                        bottom_change[['custcode','custname','salesid','change',"Today's Value in IDR"] if name != "IPOT" else ['custcode','custname','change',"Today's Value in IDR"]],
                        ['change', "Today's Value in IDR"]
                    ),
                    use_container_width=True,
                    height=400
                )

                st.markdown(f"#### 💰 Top 20 {name} by Today's Value")
                top_value = group_df.nlargest(20, 'current_currentbal')
                top_value = top_value.rename(columns={'current_currentbal': "Today's Value in IDR"})
                st.dataframe(
                    add_separator(
                        top_value[['custcode','custname','salesid',"Today's Value in IDR",'change'] if name != "IPOT" else ['custcode','custname',"Today's Value in IDR",'change']],
                        ["Today's Value in IDR", 'change']
                    ),
                    use_container_width=True,
                    height=400
                )
                if group_df.empty:
                    st.warning(f"No data found for {name} group.")

else:
    st.info("Please upload both files to begin.")
