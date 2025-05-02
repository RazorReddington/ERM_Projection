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
olb_array = np.array(mpf['Loan Amount']) #current outstanding loan balance
eff_rate_array = (1+np.array(mpf['AER']))**(1/freq)-1 #effective rate for each model point, allows for the projection frequency

n = proj_years*freq #projection period
olb_proj = [] #initialise an empty list
for i in range(1,n+1): #possibly a more efficient way of doing this
    olbi = olb_array*((1+eff_rate_array)**i)
    olb_proj.append(olbi)
olb_proj = pd.DataFrame(olb_proj)


#################### Projection - Scenario Dependent ####################
runlist = list(master_input['Name'])


######### Model Point Agnostic #############

#HPI projection
hpi = (1 + np.repeat(hpi_tables['base_HPI']['HPI'],freq))**(1/freq)
hpi = np.cumprod(hpi)
hpi.index = range(0,len(hpi)) #re-index
    
#Mortality Projection
mortality = mortality_tables['base_mortality']
n = len(mortality)

#convert to mortality survival rates
mort_survival_female = [np.prod(1-mortality['F'].iloc[:i + 1]) for i in range(n)] #calculate survival rates using list comprehension
mort_survival_male = (1-mortality['M']).cumprod() #calculate survival rates using pandas

#Reproduce mortality rates by period - i.e., quarterly, monthly etc.
mort_survival_male = (np.repeat(mort_survival_male,freq))**(1/freq)
mort_survival_male.index = range(0,len(mort_survival_male + 1)) #re-index expanded table
mort_survival_female = (np.repeat(mort_survival_female,freq))**(1/freq)
mort_survival_female.index = range(0,len(mort_survival_female + 1))


#VER Projection
ver = ver_tables['base_VER']
n = len(ver)

#convert to ver survival rates
ver_survival_female = (1 - ver['F']).cumprod()
ver_survival_male = [np.prod(1-ver['M'].iloc[:i+1]) for i in range (n)]

#Reproduce ver rates by period - i.e., quarterly, monthly etc.
'''
mort_survival_male = (np.repeat(mort_survival_male,freq))**(1/freq)
mort_survival_male.index = range(0,len(mort_survival_male + 1)) #re-index expanded table
mort_survival_female = (np.repeat(mort_survival_female,freq))**(1/freq)
mort_survival_female.index = range(0,len(mort_survival_female + 1))
'''


#Calculate all exit survival rates
survival_female = mort_survival_female * ver_survival_female
survival_male = mort_survival_male * ver_survival_male

#Construct decrements table
female_decrements= [survival_female[i-1] - survival_female[i] if i >0 else 1 - survival_female[i] for  i in range(n) ]
male_decrements = [survival_male[i-1] - survival_male[i] if i >0 else 1 - survival_male[i] for  i in range(n) ]
decrements = pd.DataFrame({'Age':mortality['Age'], 'M': male_decrements, 'F': female_decrements})

#Check
np.round(np.sum(decrements['M']),8) == 1
np.round(np.sum(decrements['F']),8) == 1

#need to allow for settlement delay
#need to extend size of table 


#Calculate t=0 property values 
base_property_values = list(mpf['Loan Amount']/mpf['LTV'])

#Project property values using HPI
n = len(base_property_values)
property_projection = [base_property_values[i] * hpi for i in range(n)]


#Cylce Through model points

prop_test = []
for i in range(len(mpf)):
    i=1
    property_projection[i]
    prop_test.append(property_projection)
    
    #Mortality
    gender1 = mpf['Gender 1'][i]
    age1 = mpf['Age 1'][i]
    
    #calculation
    
    current_olb = olb_proj[i]
    
    current_mort = mortality.loc[mortality['Age']>=age1][gender1] #Slice the mortality table based on modelpoint demographic
    current_mort.index = range(1,1 + len(current_mort)) #reset the index to start at 1
    #need current mort to have for 1, then trailing 0's
    
    mort_income = current_olb * current_mort #calculate expected income after allowing for mortality
    mort_income[np.isnan(mort_income)] = 0
    
    
    #VER
    current_ver = ver.loc[ver['Age']>=age1][gender1] #Slice the VER table based on modelpoint demographic
    current_ver.index = range(1,1 + len(current_ver)) #reset the index to start at 1
    
    ver_income = current_olb * current_ver #calculate expected income after allowing for mortality
    ver_income[np.isnan(ver_income)] = 0
    

    if mpf['Joint Life'][i] == "Joint Life":
        gender2 = mpf['Gender 2'][i]
        age2 = mpf['Age 2'][i]
        


