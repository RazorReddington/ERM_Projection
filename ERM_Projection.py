# -*- coding: utf-8 -*-
"""
Created on Fri Apr 11 21:47:54 2025

@author: UG423NJ
"""

#Packages

import numpy as np
import pandas as pd
import os


#Set Working Directory
os.chdir('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data')

############## Data ################


#Import Parameters
master_input = pd.read_excel('Master_Input.ods')
#Remove non running scenarios
master_input = master_input[master_input['Run'] == 'Y']

#Import MPF Data
mpf = pd.read_excel('MPF.xlsx')

#Clean MPF



#Create importlist


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
olb_array = np.array(mpf['Loan Amount'])
eff_rate_array = (1+np.array(mpf['AER']))**(1/freq)-1

n = proj_years*freq
olb_proj = []
for i in range(n+1):
    olbi = olb_array*((1+eff_rate_array)**i)
    olb_proj.append(olbi)
olb_proj = pd.DataFrame(olb_proj)




#################### Projection - Scenario Dependent ####################
runlist = list(master_input['Name'])


#Needs to be scenario dependent
#for run in runlist:
    #hpi_table= master_input['HPI']
    
    
    

base_property_values = list(mpf['Loan Amount']/mpf['LTV'])

prop_test = []
for i in range(len(mpf)):
    i=1
    property_value = base_property_values[i]
    hpi = np.cumprod(1 + hpi_tables['base_HPI']['HPI'])
    property_projection = property_value*hpi
    prop_test.append(property_projection)
    
    #Mortality
    
    gender1 = mpf['Gender 1'][i]
    age1 = mpf['Age 1'][i]
    mort = mortality_tables['base_mortality']
    mort_array = mort[mort[gender1]]
    
    index = np.array(range(0,proj_term))
    age1_projection = pd.DataFrame(np.floor(age1 + index/freq), columns = ['Age'])
    
    test = pd.merge(age1_projection,mort,on='Age', how='left')
    f = mort[mort['Age']==77][gender1]
    g = mort.loc['Age']
    test = []
    for i in age1_projection:
        i=77
        a = mort[i][gender1]
        
        
    #age1_projection[]
    #age1_projection = [age if != freq else age + 1, age in enumerate()]
   
    
    mod = np.mod(index,freq)
    test = (1 - mort)**(1/freq)

    if mpf['Joint Life'][i] == "Joint Life":
        gender2 = mpf['Gender 2'][i]
        age2 = mpf['Age 2'][i]
        



for run in runlist:
    indexed_property_values = base_property_values    



#Project Propoerty Value



#Project LTV









mortimportlist = []
verimportlist = []
hpiimportlist = []
n = len(runlist)
for i in range(n):
    mort_table = master_input["Mortality Table"][i]
    ver_table = master_input["VER Table"][i]
    hpi_table = master_input["HPI"][i]
    mortimportlist.append(mort_table)
    verimportlist.append(ver_table)
    hpiimportlist = hpiimportlist + [hpi_table] #alternative method to above

#Create run mapping
run_map = dict(zip(runnames,mortimportlist))




