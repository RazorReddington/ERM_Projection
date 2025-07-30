# -*- coding: utf-8 -*-
"""
Created on Tue Jul 29 18:52:54 2025

@author: UG423NJ
"""



import os
os.chdir('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection')

import streamlit as st
import pandas as pd
#import ERM_Projection









# Load the master input file
@st.cache
def load_master_input(file_path):
    return pd.read_csv(file_path)  # Adjust based on your file format

# Load parameters

master_input = pd.read_excel('Master_Input.ods')
params = load_master_input('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/Master_Input.ods')

# Streamlit app title
st.title("Financial Projection Model")

# Create input widgets for each parameter
for param in params.columns:
    if params[param].dtype == 'float64':
        params[param] = st.number_input(param, value=params[param].iloc[0], format="%.2f")
    elif params[param].dtype == 'int64':
        params[param] = st.number_input(param, value=params[param].iloc[0], step=1)
    else:
        params[param] = st.text_input(param, value=params[param].iloc[0])

# Button to run the model
if st.button("Run Model"):
    results = your_model_module.run_model(params)  # Replace with your model's run function
    st.write("Model Results:")
    st.write(results)

# Optionally, allow users to download results
if st.button("Download Results"):
    results.to_csv('model_results.csv', index=False)
    st.success("Results saved as model_results.csv")
