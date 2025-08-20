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
import matplotlib.pyplot as plt
from numba import njit

# Record start time
start_time = time.time()


#Set Working Directory
os.chdir('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection/Data')
    

############## Data ################
#Import Parameters
scenario_parameters = pd.read_excel('Master_Input.xlsx',sheet_name= 'Scenario_Parameters')
global_parameters = pd.read_excel('Master_Input.xlsx',sheet_name= 'Global_Parameters')

working_directory = global_parameters['Value'][0]
mpf = pd.read_csv(global_parameters['Value'][1])
valdate = global_parameters['Value'][2]
first_ipd = global_parameters['Value'][3]
proj_years = int(global_parameters['Value'][4])
freq = int(global_parameters['Value'][5])
proj_term = proj_years * freq + 1
date_proj = pd.date_range(start = valdate,end = None,periods = proj_term, freq= 'ME')
output_filepath = global_parameters['Value'][6]
output_freq = int(global_parameters['Value'][7])


#Remove non running scenarios
scenario_parameters = scenario_parameters[scenario_parameters['Run'] == 'Y']
scenario_parameters.index = range(len(scenario_parameters))
#Set the scenario list
runlist = list(scenario_parameters['Name'])


#Clean MPF

############## Functions ##############
'''
@njit(fastmath = True)
def black_scholes_76(F, X, r, sigma, T):
    d1 = (np.log(F / X) + T * (r + 0.5 * sigma ** 2)) / (np.sqrt(T) * sigma)    
    return d1

'''

@njit(fastmath=True)
def black_scholes_76(F, X, r, sigma, T):
    # Ensure all inputs are numpy arrays for vectorized operations
    F = np.asarray(F)
    X = np.asarray(X)
    r = np.asarray(r)
    sigma = np.asarray(sigma)
    T = np.asarray(T)

    # Precompute reused terms
    log_term = np.log(F / X)
    sigma_sq = sigma * sigma
    sqrt_T = np.sqrt(T)

    # Compute d1 using vectorized operations
    d1 = (log_term + T * (r + 0.5 * sigma_sq)) / (sqrt_T * sigma)
    return d1


def lin_interp(array, frequency): #linear interpolation function - set up for conservative, may need i-1 changed to - for Moody's
    for i in range(len(array)-frequency):
        j = i + frequency
        lower_scale = 1 - np.mod(i-1,frequency)/frequency 
        upper_scale = np.mod(i-1,frequency)/frequency 
        array[i] = array[i]*lower_scale + array[j]*upper_scale    
    return array

def load_tables(file_list):
    return {
        os.path.splitext(filename)[0]: pd.read_csv(filename)
        for filename in file_list
    }



def get_value(row, df):
    age = row['Age']
    year = row.name  # since year is the index in df2
    try:
        return df.loc[df['Age'] == age, str(year)].values[0]
    except IndexError:
        return None  


######### Load Data ################
mortality_tables = load_tables(scenario_parameters["Mortality Table"])
ver_tables = load_tables(scenario_parameters["VER Table"])
hpi_tables = load_tables(scenario_parameters["HPI"])
ltc_tables = load_tables(scenario_parameters["LTC"])
male_mort_improv_tables = load_tables(scenario_parameters["Male Mortality Improvement"])
female_mort_improv_tables = load_tables(scenario_parameters["Female Mortality Improvement"])




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
    mortality = mortality_tables[scenario_parameters['Mortality Table'][j][:-4]]
    mortality.index = mortality['Age']
    male_mortality_improvement = male_mort_improv_tables[scenario_parameters['Male Mortality Improvement'][j][:-4]]
    female_mortality_improvement = female_mort_improv_tables[scenario_parameters['Female Mortality Improvement'][j][:-4]]
    ver = ver_tables[scenario_parameters['VER Table'][j][:-4]]
    hpi = hpi_tables[scenario_parameters['HPI'][j][:-4]]
    ltc = ltc_tables[scenario_parameters['LTC'][j][:-4]]
    ltc.index = ltc['Age']
    set_delay = scenario_parameters['Settlement Delay (Alive)'][j]
    prop_haircut = scenario_parameters['Property Haircut'][j]
    sales_cost = scenario_parameters['Sales Cost'][j]
    valuation_method = scenario_parameters['Valuation Method'][j] #Moodys or Fitch or Conservative
    nneg_method = scenario_parameters['NNEG Approach'][j]



    if valuation_method == "Conservative" or "Moodys":


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
        male_mortality = {}
        female_mortality = {}

        if valuation_method == "Conservative":
        #Uplift Mortality rates by LTC rates
            mortality['M'] = np.minimum(mortality['M'] * (1 + ltc['M']),1) 
            mortality['F'] = np.minimum(mortality['F'] * (1 + ltc['F']),1) 
            
            
            #Allow fo Mortality Improvement
            for i in range(len(mortality)):
                #Calculate male monthly qx rates, allowing for LTC and mortality improvement
                m_mort_improvement = pd.DataFrame(index = date_proj.year)
                m_age = int(male_mortality_improvement.iloc[i].iloc[0])
                m_age_array = np.floor(m_age + periods/freq).astype(int) #this is 1 month out of excel model
                m_mort_improvement['Age'] = m_age_array
                m_mort_improvement['Factor'] = m_mort_improvement.apply(lambda row: get_value(row, male_mortality_improvement), axis=1)
                m_mort_improvement.index = (m_mort_improvement['Age'])
                m_mort_improvement['qx'] = m_mort_improvement.index.map(mortality['M'])
                
                m_qx = 1 - (1 - m_mort_improvement['Factor'] * m_mort_improvement['qx'])**(1/freq)
                m_qx.index = range(proj_term)  
                m_qx = lin_interp(m_qx, freq)
                m_qx.fillna(1,inplace = True)
                m_qx[0] = 0
                male_mortality[m_age] = m_qx
                
                #Calculate female monthly qx rates, allowing for LTC and mortality improvement
                f_mort_improvement = pd.DataFrame(index = date_proj.year)
                f_age = int(female_mortality_improvement.iloc[i].iloc[0])
                f_age_array = np.floor(f_age-0.0001 + periods/freq).astype(int) #this is same as excel model
                f_mort_improvement['Age'] = f_age_array
                f_mort_improvement['Factor'] = f_mort_improvement.apply(lambda row: get_value(row, female_mortality_improvement), axis=1)
                f_mort_improvement.index = (f_mort_improvement['Age'])
                f_mort_improvement['qx'] = f_mort_improvement['Age'].map(mortality['F'])
                f_qx = 1 - (1 - f_mort_improvement['Factor'] * f_mort_improvement['qx'])**(1/freq)
                f_qx.index = range(proj_term)
                f_qx = lin_interp(f_qx, freq)
                f_qx.fillna(1, inplace = True)
                f_qx[0]=0
                female_mortality[f_age] = f_qx
                


        
        elif valuation_method == 'Moodys':
            mortality['M'] = np.minimum(mortality['M'], 1)
            mortality['F'] = np.minimum(mortality['F'], 1)
            mortality_improvement = male_mortality_improvement #could try and tidy this - Moody's improv factor tables not split by sex
            mortality_improvement.index = mortality_improvement['Age']
            
            #Allow for Mortality Improvement
            for i in range(len(mortality)):
                #Calculate male monthly qx rates, allowing for mortality improvement only
                mort_improv_array = np.cumprod(1 - mortality_improvement['M'][i:])
                m_qx = 1 - (1 - mort_improv_array * mortality['M'][i:])**(1/freq)
                m_qx = np.repeat(m_qx, freq)
                m_qx = np.pad(m_qx,(1,max(proj_term - len(m_qx) - 1,0)),mode = 'constant', constant_values = (0,1) )
                m_qx = m_qx[:proj_term]
                m_qx = lin_interp(m_qx[:proj_term], freq)
                m_qx[0] = 0
                m_qx = pd.Series(m_qx)
                male_mortality[i + youngest] = m_qx
                
                
                f_qx = 1 - (1 - mort_improv_array * mortality['F'][i:])**(1/freq)
                f_qx = np.repeat(f_qx, freq)
                f_qx = np.pad(f_qx,(1,max(proj_term - len(f_qx) - 1,0)),mode = 'constant', constant_values = (0,1) )
                f_qx = f_qx[:proj_term]
                f_qx = lin_interp(f_qx[:proj_term], freq)
                f_qx[0] = 0
                f_qx = pd.Series(f_qx)
                female_mortality[i + youngest] = f_qx


        #Produce ver exit rates
        female_ver = 1 - np.power((1 - ver['F']),1/12)
        female_ver = np.repeat(female_ver,freq)
        female_ver.index = range(len(female_ver))
        
        male_ver = 1 - np.power((1 - ver['M']),1/12)
        male_ver = np.repeat(male_ver,freq)
        male_ver.index = range(len(male_ver))
 

        female_decrement_table = {} #initialise dictionaries
        female_ver_table = {}
        female_survival_table = {}
        female_ver_rates = {}
        male_decrement_table = {}
        male_ver_table = {}
        male_survival_table = {}
        male_ver_rates = {}
        
        #Project age dependent decrement arrays
        for age in mortality.index:
            i= age - youngest
            n = proj_term - 1
            k = i * freq
            l = k + n 
            
            #VER
            ver_survival_female = (1-female_ver[k:l]).values.cumprod() #determine survival rates from exit rates
            ver_survival_female = np.pad(ver_survival_female,(1,n - len(ver_survival_female)) , mode = 'constant', constant_values = (1,0)) #standardise array length
            female_ver_table[i + youngest] = ver_survival_female #collate arrays into a dictionary
            female_ver_rates[i + youngest] = np.pad(female_ver[k:l],(1,n - len(female_ver[k:l])), mode = 'constant', constant_values = 0)   
                   
            ver_survival_male = (1-male_ver[k:l]).values.cumprod() #previously k:l
            ver_survival_male = np.pad(ver_survival_male,(1,n - len(ver_survival_male)) , mode = 'constant', constant_values = (1,0))
            male_ver_table[i + youngest] = ver_survival_male
            male_ver_rates[i + youngest] = np.pad(male_ver[k:l],(1,n - len(male_ver[k:l])), mode = 'constant', constant_values = 0) 
        
            #Mortality
            mort_survival_female = (1-female_mortality[age]).values.cumprod()
            #mort_survival_female = np.pad(mort_survival_female,(1,n - len(mort_survival_female)) , mode = 'constant', constant_values = (1,0))
            female_survival_table [i + youngest] = mort_survival_female
   
            mort_survival_male = (1-male_mortality[age]).values.cumprod()
            #mort_survival_male = np.pad(mort_survival_male,(1,n - len(mort_survival_male)) , mode = 'constant', constant_values = (1,0))
            male_survival_table [i + youngest] = mort_survival_male
   

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
                F = ith_prop_proj.flatten() #spot
                X = ith_olb_proj.flatten() #strike
                r=0 #rfr - should also allow for deferrment rate
                sigma = 0.11 #implied vol
                T = (periods/12).flatten() #time to maturity
                               
                #d1 = (np.log(F/X) + np.array(T * (r +(sigma**2)/2)).reshape(len(T))) / (np.sqrt(T) * sigma).reshape(len(T))
                d1 = black_scholes_76(F, X, r, sigma, T)
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
            
            
          
            #Calculate Prepayment Cashflows
            initial_ver_rate = ([ith_mort_survival[0] * ith_ver_rate[0]])
            ver_rate = np.concatenate([initial_ver_rate,ith_ver_proj[:-1] * ith_mort_survival[1:] * ith_ver_rate[1:]])         
            ver_cfs = pd.Series(ver_rate * ith_olb_proj_nneg)


            #Allow for settlement delay
            mortality_cfs = np.pad(mortality_cfs, int((freq/12)*set_delay), mode = 'constant', constant_values = 0)
            mortality_cfs = mortality_cfs[:proj_term]
            ver_cfs = np.pad(ver_cfs, int((freq/12)*set_delay), mode = 'constant', constant_values = 0)
            ver_cfs = ver_cfs[:proj_term]
            
            #Calculate servicing fee cashflows
            service_fee_cfs = ith_olb_proj[1:] * ith_mort_survival[:-1] * ith_ver_proj[:-1] * ith_service_fee/freq
            service_fee_cfs = np.insert(service_fee_cfs, 0, 0)
            service_fee_cfs = pd.Series(service_fee_cfs)[:proj_term]

            
            #Calculate OLB after allowing for decrements
            ith_outstanding_olb = ith_olb_proj * ith_mort_survival
            
            # Append to income list
            decrement_income.append(mortality_cfs)
            prepayment_income.append(ver_cfs)
            service_fee_outgo.append(service_fee_cfs)
            outstanding_olb.append(ith_outstanding_olb)
            
           
                        
        from itertools import zip_longest
        total_decrement_income = np.array([sum(x) for x in zip_longest(*decrement_income, fillvalue=0)])
        total_prepayment_income = np.array([sum(x) for x in zip_longest(*prepayment_income, fillvalue=0)])
        total_service_fee = np.array([sum(x) for x in zip_longest(*service_fee_outgo, fillvalue=0)])
        total_olb = np.array([sum(x) for x in zip_longest(*outstanding_olb, fillvalue=0)])
        total_net_cfs = total_decrement_income + total_prepayment_income - total_service_fee
        
        
        cf_output_df = pd.DataFrame({'Net CFs': total_net_cfs, 
                                  'Decrement CFs': total_decrement_income,
                                  'Prepayment CFs': total_prepayment_income, 
                                  'Service Fee': total_service_fee}, 
                                  index = date_proj,
                                  )
        
        olb_output_df = pd.DataFrame({'Total OLB': total_olb},
                                  index = date_proj
                                   )
        
        #Set cashflows to output frequency
        cf_before_ipd = cf_output_df[cf_output_df.index <= first_ipd]
        cf_before_ipd = pd.DataFrame(cf_before_ipd[1:].sum()).T
        cf_before_ipd.index = [pd.Timestamp(first_ipd)]
        cf_before_ipd = pd.concat([cf_output_df.iloc[[0]],cf_before_ipd])
        cf_after_ipd = cf_output_df[cf_output_df.index > first_ipd]
        cf_after_ipd = cf_after_ipd.resample('QE').sum()
        cf_output_df = pd.concat([cf_before_ipd, cf_after_ipd])
        

        olb_output_df = olb_output_df.resample('QE').last()
        
        
        # Store in output dictionary
        cf_output_dictionary[f'{runlist[j]} mortality income'] = cf_output_df['Decrement CFs']
        cf_output_dictionary[f'{runlist[j]} prepayment income'] = cf_output_df['Prepayment CFs']
        cf_output_dictionary[f'{runlist[j]} service fee'] = cf_output_df['Service Fee'] #total_service_fee
        cf_output_dictionary[f'{runlist[j]} net cfs'] = cf_output_df['Net CFs'] 
        olb_output_dictionary[f'{runlist[j]} OLB'] = olb_output_df['Total OLB']
        
        
        
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




chart_dict = {}
for i in range(len(runlist)):
    plt.Figure(figsize=(10,6))
    fig, ax1 = plt.subplots()
    plt.plot(olb_output[f'{runlist[i]} OLB'], color = 'b')
    plt.legend([ f'{runlist[i]} OLB'], loc = 1, fontsize = 10)
    plt.xlabel('Year')
    plt.ylabel('OLB')

    ax2 = ax1.twinx()
    plt.plot(cf_output[f'{runlist[i]} net cfs'], color = 'r')
    plt.legend([f'{runlist[i]} net cfs'], loc = 9, fontsize = 10)
    plt.ylabel('Cashflows')
    chart_dict[f'{runlist[i]}'] = fig





#os.chdir('C:/Users/UG423NJ/OneDrive - EY/Documents/GitHub/ERM_Projection')

#Open the workbook
#import xlwings as xw
#xw.Book(output_filepath)


end_time = time.time()
execution_time = end_time - start_time

print(f"Script executed in {execution_time:.2f} seconds")


