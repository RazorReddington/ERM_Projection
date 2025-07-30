# -*- coding: utf-8 -*-
"""
Created on Wed Jul 30 10:51:04 2025

@author: UG423NJ
"""

import streamlit as st
import pandas as pd
import os
import subprocess
from openpyxl import load_workbook


# --- Configuration ---
st.set_page_config(page_title="ERM Projection Interface", layout="wide")

# --- Load Scenario Parameters ---
@st.cache_data
def load_scenarios(file_path, sheet_name):
    df = pd.read_excel(file_path, sheet_name, header=0)
    df.columns = [str(col).strip() for col in df.columns]
    # Rename duplicate columns
    seen = {}
    new_columns = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_columns.append(col)
    df.columns = new_columns
    return df


# --- Load Model Output ---
@st.cache_data
def load_output(file_path):
    cashflows = pd.read_excel(file_path, sheet_name="Cashflows")
    olb = pd.read_excel(file_path, sheet_name="OLB")
    return cashflows, olb



def save_edited_parameters(df, sheet_name, file_path = 'C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/Master_Input.xlsx'):
    # Load the existing workbook
    book = load_workbook(file_path)

    # Remove the sheet if it already exists to avoid duplication
    if sheet_name in book.sheetnames:
        std = book[sheet_name]
        book.remove(std)

    # Save the workbook temporarily without the target sheet
    temp_path = file_path.replace(".xlsx", "_temp.xlsx")
    book.save(temp_path)

    # Now write the updated sheet
    with pd.ExcelWriter(temp_path, engine='openpyxl', mode='a') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Replace the original file with the updated one

    os.replace(temp_path, file_path)

    st.success(f"Edited parameters saved to sheet '{sheet_name}' in {file_path}")




# --- Run ERM Model ---
def run_model():
    result = subprocess.run(["python", "ERM_Projection.py"], capture_output=True, text=True)
    if result.returncode == 0:
        st.success("Model executed successfully.")
        return load_output("C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/output.xlsx")
    else:
        st.error("Model execution failed.")
        st.text(result.stderr)
        return None, None




# --- UI Layout ---
st.title("ERM Projection")

tab1, tab2, tab3 = st.tabs(["Global Parameters", "Scenario Parameters", "Model Output"])

# --- Tab 1: Global Parameters ---
with tab1:
    st.subheader("Global Parameters")
    global_df = load_scenarios("C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/Master_Input.xlsx", 'Global_Parameters')
    global_df[global_df.columns[1]] = global_df[global_df.columns[1]].astype(str) #format the value column as string to allow editing. Model script converts to necesary formats
    edited_global_df = st.data_editor(
        global_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="global_editor",
        column_config={
                    global_df.columns[0]: st.column_config.TextColumn(disabled=True),
                    global_df.columns[1]: st.column_config.TextColumn(disabled=False)
                }

    )
    st.session_state["global_params"] = edited_global_df
    



# Save button clearly placed below the editor
    if st.button("💾 Save Global Parameters"):
        save_edited_parameters(edited_global_df, 'Global_Parameters')
        st.success("Parameters saved to Master_Input_Edited.xlsx. You can now run the model using these inputs.")





# --- Tab 1: Scenario Parameters ---
with tab2:
    st.subheader("Edit Scenario Parameters")
    scenario_df = load_scenarios("C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data/Master_Input.xlsx", 'Scenario_Parameters')
    edited_df = st.data_editor(
        scenario_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="scenario_editor"
    )
    
    
    st.session_state["edited_scenarios"] = edited_df

# Save button clearly placed below the editor
    if st.button("💾 Save Scenario Parameters"):
        save_edited_parameters(edited_df, 'Scenario_Parameters')
        st.success("Parameters saved to Master_Input_Edited.xlsx. You can now run the model using these inputs.")

    #st.session_state["edited_scenarios"] = edited_df



# --- Tab 3: Model Output ---
with tab3:
    st.subheader("Run Model and View Output")
    if st.button("Run ERM Model"):
        cashflows_df, olb_df = run_model()
        if cashflows_df is not None:
            st.subheader("Cashflows")
            st.dataframe(cashflows_df)
            st.subheader("OLB")
            st.dataframe(olb_df)

