import streamlit as st
import pandas as pd

st.title("Client Balance Changes Comparison")

# Upload fields for yesterday and current date files
yesterday_file = st.file_uploader("Upload YESTERDAY'S file", type=["csv"], key="yesterday")
current_file = st.file_uploader("Upload CURRENT file", type=["csv"], key="current")

if yesterday_file and current_file:
    # Read the CSVs with | as separator
    df_yest = pd.read_csv(yesterday_file, sep="|")
    df_curr = pd.read_csv(current_file, sep="|")
    
    # Sum currentbal for each custcode (avoid duplicate)
    yest_sum = df_yest.groupby('custcode', as_index=False).agg({
        'custname': 'first',      # Take the first name for simplicity
        'salesid': 'first',       # Take the first salesid for simplicity
        'currentbal': 'sum'
    }).rename(columns={'currentbal': 'yesterday_currentbal'})
    
    curr_sum = df_curr.groupby('custcode', as_index=False).agg({
        'custname': 'first',
        'salesid': 'first',
        'currentbal': 'sum'
    }).rename(columns={'currentbal': 'current_currentbal'})
    
    # Merge on custcode (outer join to keep all)
    result = pd.merge(
        yest_sum,
        curr_sum,
        on='custcode',
        how='outer',
        suffixes=('_yest', '_curr')
    )
    
    # Prefer today's custname and salesid if available
    result['custname'] = result['custname_curr'].combine_first(result['custname_yest'])
    result['salesid'] = result['salesid_curr'].combine_first(result['salesid_yest'])
    
    # Fill missing balances with zero
    result['yesterday_currentbal'] = result['yesterday_currentbal'].fillna(0)
    result['current_currentbal'] = result['current_currentbal'].fillna(0)
    
    # Calculate change
    result['change'] = result['current_currentbal'] - result['yesterday_currentbal']
    
    # Final columns order
    final_result = result[['custcode', 'custname', 'salesid', 'yesterday_currentbal', 'current_currentbal', 'change']]
    
    st.write("### Balance Changes Table")
    st.dataframe(final_result)
    
    # Download option
    csv = final_result.to_csv(index=False)
    st.download_button("Download Result as CSV", csv, "balance_changes.csv", "text/csv")
else:
    st.info("Please upload both files.")
