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


######### Model Point Agnostic #############

#HPI projection
hpi = (1 + np.repeat(hpi_tables['base_HPI']['HPI'],freq))**(1/freq)
hpi = np.cumprod(hpi)
    
#Master Mortality Table

mortality = mortality_tables['base_mortality']
n = len(mortality)
mortality['M'][0] = 0
mortality['F'][0] = 0

#convert to survival rates
survival_female = [(1 - mortality['F'][i-1]) * (1- mortality['F'][i]) if i> 0 else 1 - mortality['F'][i] for i in range(n)]
survival_male = [(1 - mortality['M'][i-1]) * (1- mortality['M'][i]) if i> 0 else 1 - mortality['M'][i] for i in range(n)]


#reconstruct mortality decrements table
male_mortality = [survival_male[i-1] - survival_male[i] if i >0 else 0 for  i in range(n) ]
female_mortality = [survival_female[i-1] - survival_female[i] if i >0 else 0 for  i in range(n) ]
mortality = pd.DataFrame({'Age': mortality['Age'],'M': male_mortality,'F': female_mortality})

#Check
mortality['F'].sum() == 1
mortality['M'].sum() == 1


#need to allow for settlement delay

#need to extend size of table 



#VER Projection
ver = ver_tables['base_VER']

n = len(ver)
#convert to ver survival rates
ver_survival_female = [(1 - ver['F'][i-1]) * (1- ver['F'][i]) if i> 0 else 1 - ver['F'][i] for i in range(n)]
ver_survival_male = [(1 - ver['M'][i-1]) * (1- ver['M'][i]) if i> 0 else 1 - ver['M'][i] for i in range(n)]


#reconstruct VER decrements table







#Extend for frequency
ver = ver.loc[ver.index.repeat(freq)]



base_property_values = list(mpf['Loan Amount']/mpf['LTV'])


#Cylce Through model points

prop_test = []
for i in range(len(mpf)):
    i=1
    property_value = base_property_values[i]
    
    property_projection = property_value*hpi
    prop_test.append(property_projection)
    
    #Mortality
    gender1 = mpf['Gender 1'][i]
    age1 = mpf['Age 1'][i]
    
    #calculation
    
    current_olb = olb_proj[i]
    current_mort = mortality.loc[mortality['Age']>=age1][gender1] #Slice the mortality table based on modelpoint demographic
    current_mort.index = range(1,1 + len(current_mort)) #reset the index to start at 1
    #need current mort to have for 1, then trailing 0's
    
    mort_income = current_olb * current_mort
    
    
    #VER
    current_ver = ver.loc[ver['Age']>=age1][gender1] #Slice the VER table based on modelpoint demographic
    current_ver.index = range(1,1 + len(current_ver)) #reset the index to start at 1
    
    
    #index = np.array(range(0,proj_term))
    #age1_projection = pd.DataFrame(np.floor(age1 + index/freq), columns = ['Age'])
    
 
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




