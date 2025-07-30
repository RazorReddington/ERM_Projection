# -*- coding: utf-8 -*-
"""
Created on Fri Apr 11 21:47:54 2025
@author: Ed Nancarrow
"""

#Packages
import numpy as np
import pandas as pd
import os
import scipy
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
master_input.index = range(len(master_input))
#Set the scenario list
runlist = list(master_input['Name'])


#Import MPF Data
mpf = pd.read_csv('MPF_Phoenix_Internal.csv')
#mpf = pd.read_csv('MPF_BIG.csv')


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

mort_improv_tables = {}
for filename in master_input["Mortality Improvement"]:       
    df = pd.read_csv(filename)
    name = os.path.splitext(filename)[0]
    mort_improv_tables[name] = df 



############## Parameters ##############

valdate = "31/12/2024"
output_filepath = 'output.xlsx'
proj_years = 50
freq = 12
proj_term = proj_years * freq + 1
output_freq = 4


#################### Projection - Scenario Agnostic ####################

olb_array = np.array(mpf['Loan Amount']) #current outstanding loan balance
eff_rate_array = (1+np.array(mpf['AER']))**(1/freq)-1 #effective rate for each model point, allows for the projection frequency
service_fee = np.array(mpf['Servicing Fee'])
#n = proj_years*freq #projection period
periods = np.arange(0, proj_term).reshape(-1, 1)  #Term factor vector
growth_factors = (1 + eff_rate_array) ** periods 

olb_proj = pd.DataFrame(olb_array * growth_factors) #Projected outstanding loan balance
base_property_values = list(mpf['Loan Amount']/mpf['LTV']) #Calculate t=0 property values 



#################### Projection - Scenario Dependent ####################


cf_output_dictionary = {}
olb_output_dictionary = {}
property_output_dictionary = {}
#Loop Through All scenarios
for j in range(len(runlist)):
    scenario = runlist[j]
    mortality = mortality_tables[master_input['Mortality Table'][j][:-4]]
    mortality_improvement = mort_improv_tables[master_input['Mortality Improvement'][j][:-4]]
    ver = ver_tables[master_input['VER Table'][j][:-4]]
    hpi = hpi_tables[master_input['HPI'][j][:-4]]
    ltc = ltc_tables[master_input['LTC'][j][:-4]]
    set_delay = master_input['Settlement Delay (Alive)'][j]
    prop_haircut = master_input['Property Haircut'][j]
    sales_cost = master_input['Sales Cost'][j]
    valuation_method = master_input['Valuation Method'][j] #Moodys or Fitch
    nneg_method = master_input['NNEG Approach'][j]



    if valuation_method == "Moodys":


        #---------------HPI Projection------------------
        hpi = (1 + np.repeat(hpi['HPI'],freq))**(1/freq)
        hpi = np.cumprod(hpi[:proj_term-1])
        hpi = pd.Series(np.insert(hpi,0,1))
        hpi.index = range(0,len(hpi)) #re-index
        
        base_property_values = np.array(base_property_values) * (1 - prop_haircut) * (1 - sales_cost) #Allow for property haircut and cost of sale
        property_projection = [base_property_values[i] * hpi for i in range(len(base_property_values))] #Project property values using HPI
        
        #-------------Decrement Projection-----------------   
        youngest = min(mortality['Age'])
        oldest = max(mortality['Age'])
        max_rates = (oldest - youngest + 1) * freq
        
        #Mortality Improvement
        
        test = mortality_improvement['M']
        
        
        #Uplift Mortality rates by LTC rates
        mortality['M'] = np.minimum(mortality['M'] * (1 + ltc['M']) * (1 - mortality_improvement['M']),1)
        mortality['F'] = np.minimum(mortality['F'] * (1 + ltc['F']) * (1 - mortality_improvement['F']),1)
        
        #Produce Mortality rates by period
        mortality['F'] = 1 - np.power(1 - mortality['F'],1/freq)
        mortality['M'] = 1 - np.power(1 - mortality['M'],1/freq)
        
        #Produce qx projections
        female_qx = np.repeat(mortality['F'],freq)
        female_qx.index = range(0,len(female_qx))
        male_qx = np.repeat(mortality['M'],freq)
        male_qx.index = range(0,len(male_qx))
        
        #Smooth Mortality rates
        def lin_interp(array, frequency): #linear interpolation function
            for i in range(len(array)-frequency):
                j = i + frequency
                lower_scale = 1 - np.mod(i,frequency)/frequency 
                upper_scale = np.mod(i,frequency)/frequency 
                array[i] = array[i]*lower_scale + array[j]*upper_scale
                
            return array
        
        female_qx = lin_interp(female_qx, freq)
        male_qx = lin_interp(male_qx, freq)
        
        
        #Produce ver exit rates
        female_ver = 1 - np.power((1 - ver['F']),1/12)
        female_ver = np.repeat(female_ver,freq)
        female_ver.index = range(len(female_ver))
        
        male_ver = 1 - np.power((1 - ver['M']),1/12)
        male_ver = np.repeat(male_ver,freq)
        male_ver.index = range(len(male_ver))
 
        #ver_rates = {}
        #ver_rates['Male'] = male_ver
        #ver_rates['Female'] = female_ver
 

        female_decrement_table = {} #initialise dictionaries
        female_ver_table = {}
        female_survival_table = {}
        female_ver_rates = {}
        male_decrement_table = {}
        male_ver_table = {}
        male_survival_table = {}
        male_ver_rates = {}
        for i in range(len(mortality)):
            #i=0
            n = proj_term - 1
            k = i * freq
            l = k + n 
            
            #VER
            ver_survival_female = (1-female_ver[k:l]).values.cumprod() #determine survival rates from exit rates
            ver_survival_female = np.pad(ver_survival_female,(1,n - len(ver_survival_female)) , mode = 'constant', constant_values = (1,0)) #standardise array length
            female_ver_table[i + youngest] = ver_survival_female #collate arrays into a dictionary
            female_ver_rates[i + youngest] = np.pad(female_ver[k:l],(1,n - len(female_ver[k:l])), mode = 'constant', constant_values = 0)   
            
                     
            ver_survival_male = (1-male_ver[k:l]).values.cumprod()
            ver_survival_male = np.pad(ver_survival_male,(1,n - len(ver_survival_male)) , mode = 'constant', constant_values = (1,0))
            male_ver_table[i + youngest] = ver_survival_male
            male_ver_rates[i + youngest] = np.pad(male_ver[k:l],(1,n - len(male_ver[k:l])), mode = 'constant', constant_values = 0) 
        
            #Mortality
            mort_survival_female = (1-female_qx[k:l]).values.cumprod()
            mort_survival_female = np.pad(mort_survival_female,(1,n - len(mort_survival_female)) , mode = 'constant', constant_values = (1,0))
            female_survival_table [i + youngest] = mort_survival_female
            #female_decrements = np.concatenate(([1-mort_survival_female[0]],(mort_survival_female[:-1] - mort_survival_female[1:])*ver_survival_female[:-1]))
            #female_decrements = np.pad(female_decrements,(0,n - len(female_decrements)) , mode = 'constant', constant_values = 1)
            #female_decrement_table[i + youngest] = female_decrements #Add to the dictionary
        
            mort_survival_male = (1-male_qx[k:l]).values.cumprod()
            mort_survival_male = np.pad(mort_survival_male,(1,n - len(mort_survival_male)) , mode = 'constant', constant_values = (1,0))
            male_survival_table [i + youngest] = mort_survival_male
           #male_decrements = np.concatenate(([1-mort_survival_male[0]],(mort_survival_male[:-1] - mort_survival_male[1:])*ver_survival_male[:-1]))   
            #male_decrements = np.pad(male_decrements,(0,n - len(male_decrements)) , mode = 'constant', constant_values = 1)
            #male_decrement_table[i + youngest] = male_decrements #Add to the dictionary
        
        #Compile rate dictionaries into parent dictionaries - avoids if statments later in the code 
        survival_rates = {}
        decrement_rates = {}
        ver_survival = {}
        ver_rates = {}
        survival_rates['Male'] = male_survival_table
        survival_rates['Female'] = female_survival_table
        decrement_rates['Male'] = male_decrement_table
        decrement_rates['Female'] = female_decrement_table  
        ver_survival['Male'] = male_ver_table
        ver_survival['Female'] = female_ver_table
        ver_rates['Male'] = male_ver_rates
        ver_rates['Female'] = female_ver_rates
        
#################### Projection - Model Point Dependent #################### 


        decrement_income = [] #Create empty lists to collect individual cashflows
        prepayment_income = []
        service_fee_outgo =[]
        outstanding_olb = []

        for i in range(len(mpf)):            
            #Produce economic projections for the ith model point
            #i=13
            ith_service_fee = service_fee[i]
            ith_prop_proj = np.array(property_projection[i])
            ith_olb_proj = np.array(olb_proj[i])
            
            #Get demographics for current model point
            gender1 = mpf['Gender 1'][i]
            age1 = mpf['Age 1'][i]
            gender2 = mpf['Gender 2'][i]
            age2 = mpf['Age 2'][i]
            policy_type = mpf['Joint Life'][i]
            
            #Allow for NNEG
            if nneg_method == "Intrinsic":
                ith_olb_proj_nneg = np.minimum(ith_olb_proj, ith_prop_proj)
                
            elif nneg_method == "BS":    
                F = ith_prop_proj #spot
                X = ith_olb_proj #strike
                r=0 #rfr - should also allow for deferrment rate
                sigma = 0.11 #implied vol
                T = periods/12 #time to maturity
                               
                d1 = (np.log(F/X) + np.array(T * (r +(sigma**2)/2)).reshape(len(T))) / (np.sqrt(T) * sigma).reshape(len(T))
                d2 = d1 -  (np.sqrt(T) * sigma).reshape(len(T))
                
                put_value = X * np.exp(-r*T).reshape(len(T)) * scipy.stats.norm.cdf(-d2) - F * scipy.stats.norm.cdf(-d1)
                                
                recovery_rate = 1 - (put_value / ith_olb_proj)
                ith_olb_proj_nneg = ith_olb_proj * recovery_rate
                 
            else: print ("select a valid nneg methodology")
            
            #Decrement rate adjustment for nneg
                      
            rational_ver = ith_olb_proj < ith_prop_proj
            
            
            
            
  
            if policy_type == 'Single':
                ith_mort_survival = survival_rates[gender1][age1]
                
                ith_ver_proj = ver_survival[gender1][age1] 
                ith_ver_proj[~rational_ver] = 1 #Need to be careful of this - if a scenario exists such that NNEG can move from inside to outside the money - this projeciton will be wrong
                
                ith_ver_rate = ver_rates[gender1][age1]
                ith_ver_rate[~rational_ver] = 0 
                
                ith_decrement_proj = (ith_mort_survival[:-1] - ith_mort_survival[1:]) * ith_ver_proj[:-1]
                ith_decrement_proj = np.insert(ith_decrement_proj,0,0)
                
                
            elif policy_type == 'Joint Life':
                
                ith_mort_survival = survival_rates[gender1][age1] + survival_rates[gender2][age2] - (survival_rates[gender1][age1] * survival_rates[gender2][age2])
                
                ith_ver_proj = ver_survival[gender1][min(age1,age2)]
                ith_ver_proj[~rational_ver] = 1
                
                ith_ver_rate = ver_rates[gender1][age1]
                ith_ver_rate[~rational_ver] = 0
           
                ith_decrement_proj = (ith_mort_survival[:-1] - ith_mort_survival[1:]) * ith_ver_proj[:-1]
                ith_decrement_proj = np.insert(ith_decrement_proj,0,0)
           
                #ith_decrement_proj = decrement_rates[gender1][age1] * decrement_rates[gender2][age2]
            
            
   
            
            #Calculate Mortality Cashflows
            mortality_cfs = ith_olb_proj_nneg * ith_decrement_proj
            mortality_cfs = np.nan_to_num(mortality_cfs)
            mortality_cfs = pd.Series(mortality_cfs)
            
          
            #Calculate Prepayment Cashflows
            initial_ver_rate = ([ith_mort_survival[0] * ith_ver_rate[0]])
            ver_rate = np.concatenate([initial_ver_rate,ith_ver_proj[:-1] * ith_mort_survival[1:] * ith_ver_rate[1:]])         
            ver_cfs = pd.Series(ver_rate * ith_olb_proj_nneg)


            #Allow for settlement delay
            mortality_cfs = np.pad(mortality_cfs, int((freq/12)*set_delay), mode = 'constant', constant_values = 0)
            ver_cfs = np.pad(ver_cfs, int((freq/12)*set_delay), mode = 'constant', constant_values = 0)
            
            #Calculate servicing fee cashflows
            service_fee_cfs = ith_olb_proj[1:] * ith_mort_survival[:-1] * ith_ver_proj[:-1] * ith_service_fee/freq
            service_fee_cfs = np.insert(service_fee_cfs, 0, 0)

            test = ith_mort_survival[1:] * ith_ver_proj[1:]
            
            #Calculate OLB after allowing for decrements
            ith_outstanding_olb = ith_olb_proj * ith_mort_survival
            
            # Append to income list
            decrement_income.append(mortality_cfs)
            prepayment_income.append(ver_cfs)
            service_fee_outgo.append(service_fee_cfs)
            outstanding_olb.append(ith_outstanding_olb)
        
        # Calculate total income
        try:
            # Try pandas concat if all are series with compatible indexes
            total_decrement_income = pd.concat(decrement_income).groupby(level=0).sum()
            total_prepayment_income = pd.concat(prepayment_income).groupby(level=0).sum()
            total_service_fee = pd.concat(service_fee_outgo).groupby(level=0).sum()
            total_olb = pd.concat(outstanding_olb).groupby(level=0).sum()
            total_nneg = 1
            
        except:
            # Fall back to simple sum if concat doesn't work
            from itertools import zip_longest
            total_decrement_income = [sum(x) for x in zip_longest(*decrement_income, fillvalue=0)]
            total_prepayment_income = [sum(x) for x in zip_longest(*prepayment_income, fillvalue=0)]
            total_service_fee = [sum(x) for x in zip_longest(*service_fee_outgo, fillvalue=0)]           
            total_olb = [sum(x) for x in zip_longest(*outstanding_olb, fillvalue=0)]
            
            
        # Store in output dictionary
        cf_output_dictionary[f'{runlist[j]} mortality income'] = total_decrement_income
        cf_output_dictionary[f'{runlist[j]} prepayment income'] = total_prepayment_income
        #cf_output_dictionary[f'{runlist[j]} service fee'] = total_service_fee
        
        olb_output_dictionary[f'{runlist[j]} OLB'] = total_olb
        
    elif valuation_method == "Fitch":
        ''' Create Fitch methodology 
        '''

    else: print ("Select a valid valuation method")

    
#########################################

#Output results to an excel document

with pd.ExcelWriter("output.xlsx", engine = 'xlsxwriter') as writer:

    #Loan Cashflow Projection
    cf_output = pd.DataFrame(data = cf_output_dictionary)
    cf_output.to_excel(writer, sheet_name="Cashflows")
    
    #OLB Projection
    olb_output = pd.DataFrame(olb_output_dictionary)
    olb_output.to_excel(writer, sheet_name="OLB")



import xlwings as xw

xw.Book(output_filepath)
#open(output_filepath)

end_time = time.time()
execution_time = end_time - start_time

print(f"Script executed in {execution_time:.2f} seconds")


