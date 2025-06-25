import streamlit as st
import pandas as pd

st.title("Client Balance Changes Comparison")

yesterday_file = st.file_uploader("Upload YESTERDAY'S file", type=["csv"], key="yesterday")
current_file = st.file_uploader("Upload CURRENT file", type=["csv"], key="current")

if yesterday_file and current_file:
    if st.button("Generate Comparison Table"):
        # Read the CSVs with | as separator
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

        # === ANALYSIS TAB ===
        st.write("---")
        tab1, = st.tabs(["Analysis"])
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

            # WM only (salesid starts with WM)
            wm_mask = df['salesid'].str.startswith('WM', na=False)
            wm_yesterday = df.loc[wm_mask, 'yesterday_currentbal'].sum()
            wm_current = df.loc[wm_mask, 'current_currentbal'].sum()
            wm_change = df.loc[wm_mask, 'change'].sum()

            # Private Dealing: salesid is 'Private Dealing' or starts with 'RT'
            priv_mask = (df['salesid'] == 'Private Dealing') | (df['salesid'].str.startswith('RT', na=False))
            priv_yesterday = df.loc[priv_mask, 'yesterday_currentbal'].sum()
            priv_current = df.loc[priv_mask, 'current_currentbal'].sum()
            priv_change = df.loc[priv_mask, 'change'].sum()

            # Create the analysis summary table
            analysis_data = {
                "Position": ["Total", "IPOT only", "WM only", "Private Dealing"],
                "Yesterday": [total_yesterday, ipot_yesterday, wm_yesterday, priv_yesterday],
                "Current": [total_current, ipot_current, wm_current, priv_current],
                "Changes": [total_change, ipot_change, wm_change, priv_change]
            }
            analysis_df = pd.DataFrame(analysis_data)

            # Display analysis table (with thousand separators for readability)
            display_analysis = analysis_df.copy()
            for col in ['Yesterday', 'Current', 'Changes']:
                display_analysis[col] = display_analysis[col].apply(lambda x: '{:,.2f}'.format(x))

            st.write("### Analysis Summary Table")
            st.table(display_analysis)
else:
    st.info("Please upload both files.")
