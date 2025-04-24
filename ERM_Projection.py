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
os.chdir('/home/razorreddington/Documents/Project Q/Projects/Data')

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

base_property_values = list(mpf['Loan Amount']/mpf['LTV'])

a = np.array(hpi_tables['base_HPI']['HPI'])
a= a+1

b = base_property_values[0]

b*a

for run in runlist:
    indexed_property_values = base_property_values    



#Project Propoerty Value



#Project LTV









mortimportlist = []
verimportlist = []
hpiimportlist = []
n = len(runnames)
for i in range(n):
    mort_table = master_input["Mortality Table"][i]
    ver_table = master_input["VER Table"][i]
    hpi_table = master_input["HPI"][i]
    mortimportlist.append(mort_table)
    verimportlist.append(ver_table)
    hpiimportlist = hpiimportlist + [hpi_table] #alternative method to above

#Create run mapping
run_map = dict(zip(runnames,mortimportlist))




