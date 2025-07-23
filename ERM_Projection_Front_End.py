# -*- coding: utf-8 -*-
"""
Created on Wed Jul  9 13:15:59 2025

@author: UG423NJ
"""

import streamlit as st

import pandas as pd
import numpy as np

# Example financial model function
def financial_model(input1, input2, input3):
    # Simulate cash flow projections based on inputs
    cash_flows = np.random.rand(10) * input1 + input2 - input3
    return cash_flows

# Streamlit application
def main():
    st.title("Financial Model Dashboard")

    # Input fields for user parameters
    st.sidebar.header("Input Parameters")
    input1 = st.sidebar.number_input("Input 1 (e.g., Revenue)", min_value=0.0, value=100.0)
    input2 = st.sidebar.number_input("Input 2 (e.g., Expenses)", min_value=0.0, value=50.0)
    input3 = st.sidebar.number_input("Input 3 (e.g., Adjustments)", min_value=0.0, value=10.0)

    # Button to run the model
    if st.sidebar.button("Run Model"):
        cash_flows = financial_model(input1, input2, input3)
        
        # Display results
        st.subheader("Projected Cash Flows")
        st.write(cash_flows)

        # Create a DataFrame for better visualization
        cash_flows_df = pd.DataFrame(cash_flows, columns=["Cash Flow"])
        st.line_chart(cash_flows_df)

        # Additional metrics
        st.write("Total Cash Flow: ", cash_flows.sum())
        st.write("Average Cash Flow: ", cash_flows.mean())

if __name__ == "__main__":
    main()

