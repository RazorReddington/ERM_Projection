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


#Calculate t=0 property values 
base_property_values = list(mpf['Loan Amount']/mpf['LTV'])


#################### Projection - Scenario Dependent ####################
runlist = list(master_input['Name'])


######### Model Point Agnostic #############

#---------------HPI Projection------------------
hpi = (1 + np.repeat(hpi_tables['base_HPI']['HPI'],freq))**(1/freq)
hpi = np.cumprod(hpi)
hpi.index = range(0,len(hpi)) #re-index


#-------------Decrement Projection-----------------   

#Assign scenario decrement tables - needs addressing when expanding to multiple scenarios
mortality = mortality_tables['base_mortality']
ver = ver_tables['base_VER']


###################
youngest = min(mortality['Age'])
oldest = max(mortality['Age'])

female_decrement_table = {} #empty dictionary to store decrement probabilities
male_decrement_table = {}
for i in range(len(mortality)):
    mort_survival_female = (1-mortality['F'][i:]).cumprod() #calculate mortality survival probabilities 
    ver_survival_female = (1 - ver['F'][i:]).cumprod() #calculate ver survival  - THINK THIS IS WRONG
    survival_female = mort_survival_female * ver_survival_female #calculate total survival probabilities
    
    
    #This needs addressing
    female_decrements= [survival_female[j-1] - survival_female[j] if j >0 else 1 - survival_female[j] for  j in range(len(survival_female)) ]
    
    
    
    
    female_decrement_table[i + youngest] = female_decrements #Add to the dictionary
    
    mort_survival_male = (1-mortality['M'][i:]).cumprod()
    ver_survival_male = (1 - ver['M'][i:]).cumprod() 
    survival_male = mort_survival_male * ver_survival_male
    male_decrements= [survival_male[j-1] - survival_male[i] if j >0 else 1 - survival_male[j] for  j in range(len(survival_male)) ]
    male_decrement_table[i + youngest] = male_decrements #Add to the dictionary
    
np.sum(female_decrements)

    ver_survival_female = (1 - ver['F'][5:]).cumprod() 
###############

'''
#convert to mortality survival rates
mort_survival_female = (1-mortality['F']).cumprod() 
mort_survival_male = (1-mortality['M']).cumprod() 


#convert to ver survival rates
ver_survival_female = (1 - ver['F']).cumprod()
ver_survival_male = (1 - ver['M']).cumprod()


#Calculate all exit survival rates
survival_female = mort_survival_female * ver_survival_female
survival_male = mort_survival_male * ver_survival_male


#Construct decrements table
n = len(survival_female)
female_decrements= [survival_female[i-1] - survival_female[i] if i >0 else 1 - survival_female[i] for  i in range(n) ]
male_decrements = [survival_male[i-1] - survival_male[i] if i >0 else 1 - survival_male[i] for  i in range(n) ]
decrements = pd.DataFrame({'Age':mortality['Age'], 'M': male_decrements, 'F': female_decrements})


#Reproduce decrement table based on the valuation frequency
decrements = pd.concat([decrements]*freq)
decrements['M'] = decrements['M']/freq
decrements['F'] = decrements['F']/freq
decrements = decrements.sort_index(ascending=True)


#Check
np.round(np.sum(decrements['M']),8) == 1
np.round(np.sum(decrements['F']),8) == 1
'''
#need to allow for settlement delay




#Project property values using HPI
n = len(base_property_values)
property_projection = [base_property_values[i] * hpi for i in range(n)]


#Cylce Through model points

something = []
for i in range(len(mpf)):
    ##i=1 #remove

    #Model Point Financials
    ith_prop_proj = property_projection[i] #Property projection
    ith_olb_proj = olb_proj[i] #OLB Projection
    
    #Allow for NNEG - currently assumes instrinsic calculation (no time dependency)
    ith_olb_proj_nneg = pd.Series([ith_olb_proj[i] if ith_olb_proj[i] <= ith_prop_proj[i] else ith_prop_proj[i] for i in range(len(ith_olb_proj))])
    
    #Model Point Demographics - Life 1
    gender1 = mpf['Gender 1'][i]
    age1 = mpf['Age 1'][i]
    
    if gender1 == 'F':
        ith_decrement_proj = female_decrements[age1]
    elif gender1 == 'M':
        ith_decrement_proj = female_decrements[age1]
        
        
    ith_decrement_proj = pd.Series(decrements.loc[decrements['Age']>=age1][gender1])
    ith_decrement_proj.index = range(0,len(ith_decrement_proj))
  
    
  
    
  
    np.sum(ith_decrement_proj)
  
    #Calculate Cashflows
    mp_cfs = ith_olb_proj_nneg * ith_decrement_proj
    mp_cfs[np.isnan(mp_cfs)] = 0
    
    #Sense Check
    np.sum(mp_cfs) - ith_olb_proj[0]
    
    
    
    
    '''
    if mpf['Joint Life'][i] == "Joint Life":
        gender2 = mpf['Gender 2'][i]
        age2 = mpf['Age 2'][i]
    '''      


