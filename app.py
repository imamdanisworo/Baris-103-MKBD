import streamlit as st
import pandas as pd

def add_separator(df, cols):
    fmt_df = df.copy()
    for col in cols:
        if col in fmt_df.columns:
            fmt_df[col] = fmt_df[col].apply(lambda x: '{:,.2f}'.format(x) if pd.notnull(x) else '')
    return fmt_df

st.title("Client Balance Changes Comparison")

yesterday_file = st.file_uploader("Upload YESTERDAY'S file", type=["csv"], key="yesterday")
current_file = st.file_uploader("Upload CURRENT file", type=["csv"], key="current")

if yesterday_file and current_file:
    if st.button("Generate Comparison Table"):
        # --- READ AND PREPARE DATA ---
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

        st.write("### Balance Changes Table (Sortable)")
        st.dataframe(final_result_with_total, use_container_width=True)

        csv = final_result_with_total.to_csv(index=False)
        st.download_button("Download Result as CSV", csv, "balance_changes.csv", "text/csv")

        # === MULTI TAB ANALYSIS & RANKING ===
        st.write("---")
        tab1, tab2, tab3, tab4 = st.tabs([
            "Analysis",
            "Rank IPOT",
            "Rank WM",
            "Rank Private Dealing"
        ])

        # ---------------------- TAB 1: ANALYSIS SUMMARY ----------------------
        with tab1:
            df = final_result.copy()
            # Total
            total_yesterday = df['yesterday_currentbal'].sum()
            total_current = df['current_currentbal'].sum()
            total_change = df['change'].sum()
            # IPOT only
            ipot_mask = df['salesid'] == 'IPOT'
            ipot_yesterday = df.loc[ipot_mask, 'yesterday_currentbal'].sum()
            ipot_current = df.loc[ipot_mask, 'current_currentbal'].sum()
            ipot_change = df.loc[ipot_mask, 'change'].sum()
            # WM only
            wm_mask = df['salesid'].str.startswith('WM', na=False)
            wm_yesterday = df.loc[wm_mask, 'yesterday_currentbal'].sum()
            wm_current = df.loc[wm_mask, 'current_currentbal'].sum()
            wm_change = df.loc[wm_mask, 'change'].sum()
            # Private Dealing
            priv_mask = (df['salesid'] == 'Private Dealing') | (df['salesid'].str.startswith('RT', na=False))
            priv_yesterday = df.loc[priv_mask, 'yesterday_currentbal'].sum()
            priv_current = df.loc[priv_mask, 'current_currentbal'].sum()
            priv_change = df.loc[priv_mask, 'change'].sum()
            analysis_data = {
                "Position": ["Total", "IPOT only", "WM only", "Private Dealing"],
                "Yesterday": [total_yesterday, ipot_yesterday, wm_yesterday, priv_yesterday],
                "Current": [total_current, ipot_current, wm_current, priv_current],
                "Changes": [total_change, ipot_change, wm_change, priv_change]
            }
            analysis_df = pd.DataFrame(analysis_data)
            display_analysis = analysis_df.copy()
            for col in ['Yesterday', 'Current', 'Changes']:
                display_analysis[col] = display_analysis[col].apply(lambda x: '{:,.2f}'.format(x))
            st.write("### Analysis Summary Table")
            st.dataframe(display_analysis, use_container_width=True)

        # ---------------------- TAB 2: IPOT RANK ----------------------
        with tab2:
            ipot_df = df[df['salesid'] == 'IPOT']
            top_change = ipot_df.nlargest(20, 'change')[['custcode','custname','change','current_currentbal']]
            top_value = ipot_df.nlargest(20, 'current_currentbal')[['custcode','custname','current_currentbal','change']]

            # Rename for display
            top_change = top_change.rename(columns={'current_currentbal': "Today's Value in IDR"})
            top_value = top_value.rename(columns={'current_currentbal': "Today's Value in IDR"})

            st.write("#### Top 20 IPOT by Changes")
            st.dataframe(add_separator(top_change, ['change', "Today's Value in IDR"]), use_container_width=True, height=400)
            st.write("#### Top 20 IPOT by Today's Value")
            st.dataframe(add_separator(top_value, ["Today's Value in IDR", 'change']), use_container_width=True, height=400)

        # ---------------------- TAB 3: WM RANK ----------------------
        with tab3:
            wm_df = df[df['salesid'].str.startswith('WM', na=False)]
            top_change = wm_df.nlargest(20, 'change')[['custcode','custname','salesid','change','current_currentbal']]
            top_value = wm_df.nlargest(20, 'current_currentbal')[['custcode','custname','salesid','current_currentbal','change']]

            # Rename for display
            top_change = top_change.rename(columns={'current_currentbal': "Today's Value in IDR"})
            top_value = top_value.rename(columns={'current_currentbal': "Today's Value in IDR"})

            st.write("#### Top 20 WM by Changes")
            st.dataframe(add_separator(top_change, ['change', "Today's Value in IDR"]), use_container_width=True, height=400)
            st.write("#### Top 20 WM by Today's Value")
            st.dataframe(add_separator(top_value, ["Today's Value in IDR", 'change']), use_container_width=True, height=400)

        # ---------------------- TAB 4: PRIVATE DEALING RANK ----------------------
        with tab4:
            priv_df = df[(df['salesid'] == 'Private Dealing') | (df['salesid'].str.startswith('RT', na=False))]
            top_change = priv_df.nlargest(20, 'change')[['custcode','custname','salesid','change','current_currentbal']]
            top_value = priv_df.nlargest(20, 'current_currentbal')[['custcode','custname','salesid','current_currentbal','change']]

            # Rename for display
            top_change = top_change.rename(columns={'current_currentbal': "Today's Value in IDR"})
            top_value = top_value.rename(columns={'current_currentbal': "Today's Value in IDR"})

            st.write("#### Top 20 Private Dealing by Changes")
            st.dataframe(add_separator(top_change, ['change', "Today's Value in IDR"]), use_container_width=True, height=400)
            st.write("#### Top 20 Private Dealing by Today's Value")
            st.dataframe(add_separator(top_value, ["Today's Value in IDR", 'change']), use_container_width=True, height=400)

else:
    st.info("Please upload both files.")
