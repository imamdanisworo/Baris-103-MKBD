import streamlit as st
import pandas as pd

def accounting_format(x):
    if pd.isnull(x):
        return ''
    if x < 0:
        return f"({abs(x):,.0f})"
    else:
        return f"{x:,.0f}"

st.title("Client Balance Changes Comparison")

yesterday_file = st.file_uploader("Upload YESTERDAY'S file", type=["csv"], key="yesterday")
current_file = st.file_uploader("Upload CURRENT file", type=["csv"], key="current")

if yesterday_file and current_file:
    if st.button("Generate Comparison Table"):
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
        
        # Format the number columns using accounting format
        display_df = final_result_with_total.copy()
        for col in ['yesterday_currentbal', 'current_currentbal', 'change']:
            display_df[col] = display_df[col].apply(accounting_format)
        
        st.write("### Balance Changes Table (Accounting Format)")
        st.table(display_df)

        # Download: CSV will keep raw numbers (sortable in Excel)
        csv = final_result_with_total.to_csv(index=False)
        st.download_button("Download Result as CSV", csv, "balance_changes.csv", "text/csv")
else:
    st.info("Please upload both files.")
