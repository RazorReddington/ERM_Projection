# -*- coding: utf-8 -*-
"""
Created on 
@author: Ed Nancarrow
"""



import streamlit as st
import pandas as pd

# --- Load parameters from Master_Input.xlsx ---
def load_parameters(file_path):
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    return df



# --- Load scenario parameters ---
def load_scenarios(file_path):
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df.columns = df.iloc[0]  # Set first row as header
    df = df[1:]  # Remove header row
    df.reset_index(drop=True, inplace=True)
    return df



# --- Load model output from output.xlsx ---
def load_output(file_path):
    cashflows = pd.read_excel(file_path, sheet_name="Cashflows")
    olb = pd.read_excel(file_path, sheet_name="OLB")
    return cashflows, olb

# --- Dummy model function (replace with your actual model logic) ---
def run_model(params_df):
    # Placeholder: return the same dataframe for now
    return params_df





# --- Streamlit UI ---

st.set_page_config(page_title="Model Interface", layout="wide")
st.title("Model Parameter Interface")



# Tabs for scenario and global parameters
tab1, tab2 = st.tabs(["Scenario Parameters", "Global Parameters"])




# --- Tab 1: Scenario Parameters ---
with tab1:
    st.subheader("Edit Scenario Parameters")
    scenario_df = load_scenarios("C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/Master_Input.xlsx")

    edited_df = st.data_editor(
        scenario_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Run Model with Edited Scenarios"):
        st.success("Model executed successfully.")
        st.write("Edited Parameters:")
        st.dataframe(edited_df)


# --- Tab 2: Global Parameters ---
with tab2:
    st.subheader("Global Parameters")
    # Example global parameters (customize as needed)
    global_params = {
        "Discount Rate": 0.03,
        "Inflation Rate": 0.02,
        "Model Version": "v1.0"
    }

    updated_globals = {}
    for key, val in global_params.items():
        if isinstance(val, (int, float)):
            updated_globals[key] = st.number_input(key, value=val)
        else:
            updated_globals[key] = st.text_input(key, value=str(val))

    if st.button("Save Global Parameters"):
        st.success("Global parameters saved.")
        st.json(updated_globals)



# Load parameters and output
#params_df = load_parameters("C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/Master_Input.xlsx")
cashflows_df, olb_df = load_output("C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/output.xlsx")
'''
# Select a scenario to edit
scenario_names = params_df["Name"].dropna().unique()
selected_scenario = st.selectbox("Select Scenario", scenario_names)

# Filter parameters for selected scenario
scenario_params = params_df[params_df["Name"] == selected_scenario].iloc[0]

st.subheader("Edit Parameters")
edited_params = {}
for col in params_df.columns[2:]:  # Skip 'Run' and 'Name'
    val = scenario_params[col]
    if isinstance(val, (int, float)):
        edited_params[col] = st.number_input(col, value=val)
    elif isinstance(val, str):
        edited_params[col] = st.text_input(col, value=val)
    else:
        edited_params[col] = st.text_input(col, value=str(val))
'''
# Run model
if st.button("Run Model"):
    result = run_model(pd.DataFrame([edited_params]))
    st.success("Model executed successfully.")
    st.write("Model Output (placeholder):")
    st.dataframe(result)

# Display output from output.xlsx
st.subheader("Cashflows")
st.dataframe(cashflows_df)

st.subheader("OLB")
st.dataframe(olb_df)
