# -*- coding: utf-8 -*-
"""
Created on Fri Apr 11 21:47:54 2025

@author: Ed Nancarrow
"""

#Packages
import numpy as np
import pandas as pd
import os


#Set Working Directory
#os.chdir('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data')
os.chdir('/home/razorreddington/Documents/GitHub/ERM_Projection/Data')
############## Data ################

#Import Parameters
master_input = pd.read_excel('Master_Input.ods')
#Remove non running scenarios
master_input = master_input[master_input['Run'] == 'Y']

#Import MPF Data
mpf = pd.read_excel('MPF.xlsx')
#mpf = pd.concat([mpf]*1600)
#mpf.index = range(0,len(mpf))

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

############## Parameters ##############

valdate = "31/12/2024"

proj_years = 50
freq = 4
proj_term = proj_years * freq + 1



#################### Projection - Scenario Agnostic ####################

#Project OLB
olb_array = np.array(mpf['Loan Amount']) #current outstanding loan balance
eff_rate_array = (1+np.array(mpf['AER']))**(1/freq)-1 #effective rate for each model point, allows for the projection frequency

n = proj_years*freq #projection period
olb_proj = [] #initialise an empty list
for i in range(1,n+1): #possibly a more efficient way of doing this
    olbi = olb_array*((1+eff_rate_array)**i)
    olb_proj.append(olbi)
olb_proj = pd.DataFrame(olb_proj)


#Calculate t=0 property values 
base_property_values = list(mpf['Loan Amount']/mpf['LTV'])


#################### Projection - Scenario Dependent ####################

#Set the scenario list
runlist = list(master_input['Name'])


#Loop Through All scenarios
for i in range(len(runlist)):
    i=1
    mortality = mortality_tables[master_input['Mortality Table'][i][:-4]]
    ver = ver_tables[master_input['VER Table'][i][:-4]]
    hpi = hpi_tables[master_input['HPI'][i][:-4]]
    set_delay = master_input['Settlement Delay (Alive)'][i]

    
    #---------------HPI Projection------------------
    hpi = (1 + np.repeat(hpi['HPI'],freq))**(1/freq)
    hpi = np.cumprod(hpi)
    hpi.index = range(0,len(hpi)) #re-index
    
    
    #-------------Decrement Projection-----------------   
    youngest = min(mortality['Age'])
    oldest = max(mortality['Age'])
    
    ''''Dictionaries should ultimately be nested'''
    female_decrement_table = {} #empty dic
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
        

    #Project property values using HPI
    n = len(base_property_values)
    property_projection = [base_property_values[i] * hpi for i in range(n)]
    
    
    #Loop Through All Model Points
    income = []
    for i in range(len(mpf)):
        
    
        #Model Point Financials
        ith_prop_proj = property_projection[i] #Property projection
        ith_olb_proj = olb_proj[i] #OLB Projection
        
        #Allow for NNEG - currently assumes instrinsic calculation (no time dependency)
        ith_olb_proj_nneg = pd.Series([ith_olb_proj[i] if ith_olb_proj[i] <= ith_prop_proj[i] else ith_prop_proj[i] for i in range(len(ith_olb_proj))])
        
        #Model Point Demographics - Life 1
        gender1 = mpf['Gender 1'][i]
        age1 = mpf['Age 1'][i]
        
        if gender1 == 'F':
            ith_decrement_proj = female_decrement_table[age1]
        elif gender1 == 'M':
            ith_decrement_proj = male_decrement_table[age1]
    
    
        #Calculate Cashflows
        mp_cfs = pd.Series(ith_olb_proj_nneg) * pd.Series(ith_decrement_proj)
        mp_cfs[np.isnan(mp_cfs)] = 0
        
        #Sense Check
        #np.sum(mp_cfs) - ith_olb_proj[0]
    
        #Allow for settlement delay
        delayed_cfs = int(set_delay/freq)
        mp_cfs[delayed_cfs] = np.sum(mp_cfs[0:delayed_cfs+1])
        mp_cfs[0:delayed_cfs]=0


        income.append(mp_cfs)
        
        
       
        
    
    #Output
    
    
        
    

    
        '''
        if mpf['Joint Life'][i] == "Joint Life":
            gender2 = mpf['Gender 2'][i]
            age2 = mpf['Age 2'][i]
        '''      


