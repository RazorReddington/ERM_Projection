# -*- coding: utf-8 -*-
"""
Created on Fri Apr 11 21:47:54 2025
@author: Ed Nancarrow
"""

#Packages
import numpy as np
import pandas as pd
import os
#import csv


import time
# Record start time
start_time = time.time()


#Set Working Directory
os.chdir('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data')
#os.chdir('/home/razorreddington/Documents/GitHub/ERM_Projection/Data')
############## Data ################

#Import Parameters
master_input = pd.read_excel('Master_Input.ods')
#Remove non running scenarios
master_input = master_input[master_input['Run'] == 'Y']

#Import MPF Data
#mpf = pd.read_csv('MPF.csv')
mpf = pd.read_csv('MPF_BIG.csv')


#Clean MPF




#Import Mortality Assumptions
mortality_tables ={}
for filename in master_input["Mortality Table"]:       
    df = pd.read_csv(filename)
    name = os.path.splitext(filename)[0]
    mortality_tables[name] = df

#Import VER Assumptions
ver_tables ={}
for filename in master_input["VER Table"]:       
    df = pd.read_csv(filename)
    name = os.path.splitext(filename)[0]
    ver_tables[name] = df

#Import HPI Assumptions
hpi_tables ={}
for filename in master_input["HPI"]:       
    df = pd.read_csv(filename)
    name = os.path.splitext(filename)[0]
    hpi_tables[name] = df
    
ltc_tables ={}
for filename in master_input["LTC"]:       
    df = pd.read_csv(filename)
    name = os.path.splitext(filename)[0]
    ltc_tables[name] = df    


############## Parameters ##############

valdate = "31/12/2024"
output_filepath = 'output.xlsx'
proj_years = 50
freq = 4
proj_term = proj_years * freq + 1



#################### Projection - Scenario Agnostic ####################

olb_array = np.array(mpf['Loan Amount']) #current outstanding loan balance
eff_rate_array = (1+np.array(mpf['AER']))**(1/freq)-1 #effective rate for each model point, allows for the projection frequency
n = proj_years*freq #projection period
periods = np.arange(1, n+1).reshape(-1, 1)  #Term factor vector
growth_factors = (1 + eff_rate_array) ** periods 

olb_proj = pd.DataFrame(olb_array * growth_factors) #Projected outstanding loan balance
base_property_values = list(mpf['Loan Amount']/mpf['LTV']) #Calculate t=0 property values 

#################### Projection - Scenario Dependent ####################

#Set the scenario list
runlist = list(master_input['Name'])

output_dictionary = {}
#Loop Through All scenarios
for j in range(len(runlist)):
    scenario = runlist[j]
    mortality = mortality_tables[master_input['Mortality Table'][j][:-4]]
    ver = ver_tables[master_input['VER Table'][j][:-4]]
    hpi = hpi_tables[master_input['HPI'][j][:-4]]
    set_delay = master_input['Settlement Delay (Alive)'][j]
    prop_haircut = master_input['Property Haircut'][j]
    sales_cost = master_input['Sales Cost'][j]

    
    #---------------HPI Projection------------------
    hpi = (1 + np.repeat(hpi['HPI'],freq))**(1/freq)
    hpi = np.cumprod(hpi)
    hpi.index = range(0,len(hpi)) #re-index
    
    base_property_values = np.array(base_property_values) * (1 - prop_haircut) * (1 - sales_cost) #Allow for property haircut and cost of sale
    property_projection = [base_property_values[i] * hpi for i in range(len(base_property_values))] #Project property values using HPI
    
    #-------------Decrement Projection-----------------   
    youngest = min(mortality['Age'])
    oldest = max(mortality['Age'])
    
    ''''Dictionaries should ultimately be nested'''
    female_decrement_table = {} #initialise dictionary
    male_decrement_table = {}
    for i in range(len(mortality)):
        mort_survival_female = (1-mortality['F'][i:]).values.cumprod() #calculate mortality survival probabilities 
        ver_survival_female = (1 - ver['F'][i:]).values.cumprod() #calculate ver survival  - THINK THIS IS WRONG
        survival_female = mort_survival_female * ver_survival_female #calculate total survival probabilities
        female_decrements = np.concatenate(([1-survival_female[0]],survival_female[:-1] - survival_female[1:]))   
        female_decrements = np.repeat(female_decrements/freq, freq)
        female_decrement_table[i + youngest] = female_decrements #Add to the dictionary
    
        
        mort_survival_male = (1-mortality['M'][i:]).values.cumprod()
        ver_survival_male = (1 - ver['M'][i:]).values.cumprod() 
        survival_male = mort_survival_male * ver_survival_male
        male_decrements = np.concatenate(([1-survival_male[0]],survival_male[:-1] - survival_male[1:]))   
        male_decrements = np.repeat(male_decrements/freq, freq)
        male_decrement_table[i + youngest] = male_decrements #Add to the dictionary
        

 
    
    income = [] #Create an empty list to collect individual cashflows
    for i in range(len(mpf)):
        
        #Produce economic projections for the ith model point
        ith_prop_proj = np.array(property_projection[i])
        ith_olb_proj = np.array(olb_proj[i])
        
        #Get demographics for current model point
        gender1 = mpf['Gender 1'][i]
        age1 = mpf['Age 1'][i]
        
        #Allow for NNEG
        ith_olb_proj_nneg = np.minimum(ith_olb_proj, ith_prop_proj)
        
        #Get decrement projection based on gender and age -THIS CAN  BE OPTIMISED FURTHER
        if gender1 == 'F':
            ith_decrement_proj = female_decrement_table[age1]
        else:  # gender1 == 'M'
            ith_decrement_proj = male_decrement_table[age1]
        
        #Ensure same length
        min_len = min(len(ith_olb_proj_nneg), len(ith_decrement_proj))
        mp_cfs = ith_olb_proj_nneg[:min_len] * ith_decrement_proj[:min_len]
        mp_cfs = np.nan_to_num(mp_cfs)
        mp_cfs = pd.Series(mp_cfs)
        
        # Allow for settlement delay
        delayed_cfs = int(set_delay * (freq/12))
        if delayed_cfs > 0:
            # Calculate sum of early cashflows
            early_sum = mp_cfs.iloc[:delayed_cfs+1].sum()
            
            # Set early cashflows to zero
            mp_cfs.iloc[:delayed_cfs] = 0
            
            # Set delayed position to the sum
            if delayed_cfs < len(mp_cfs):
                mp_cfs.iloc[delayed_cfs] = early_sum
        
        # Append to income list
        income.append(mp_cfs)
    
    # Calculate total income
    try:
        # Try pandas concat if all are series with compatible indexes
        total_income = pd.concat(income).groupby(level=0).sum()
    except:
        # Fall back to simple sum if concat doesn't work
        total_income = sum(income)
    
    # Store in output dictionary
    output_dictionary[runlist[j]] = total_income
    
    


    
#########################################

#Output results to an excel document
my_output = pd.DataFrame(data = output_dictionary)
my_output.to_excel(output_filepath)

end_time = time.time()
execution_time = end_time - start_time

print(f"Script executed in {execution_time:.2f} seconds")

    
'''
        if mpf['Joint Life'][i] == "Joint Life":
            gender2 = mpf['Gender 2'][i]
            age2 = mpf['Age 2'][i]
'''      

