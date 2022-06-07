# --- Library Imports ---
import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data(stocklist: list):
    #Create empty dataframe
    df_fa = pd.DataFrame(columns = ['stock', 'ocf_trend_rank', 'net_margin_%_rank', 'Int_cvr_rank',
       'current_pe', '5_yr_pe', 'eps', 'value_rank', 'potential price',
       'tt_rank_pts'])
    #Create dict to capture scrapped results
    input_dict= {i:"" for i in df_fa.columns}
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)
    for stock in stocklist:        
        # Start here for the for loop
        driver.get('https://www.google.com/')
        # to automate searching the morningstar result on google for the ticker
        inputElement = driver.find_element(By.XPATH,"/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div/div[2]/input")
        inputElement.send_keys('morningstar'+' '+stock+'\n')


        # to click on the top most link to go to ticker morningstar page
        driver.find_element_by_partial_link_text('https://www.morningstar.com').click()


        # driver.find_element(By.XPATH,'//*[@id="__layout"]/div/div[2]/div[3]/main/nav/ul/a[8]').click()

        driver.find_element(By.XPATH,'//*[@id="stock__tab-valuation"]/a/span/span').click()

        time.sleep(5)
        df_valuation = pd.read_html(driver.page_source)[0]
        df_valuation = df_valuation.replace('––',0)

        input_dict['stock'] = stock.upper()

        input_dict.update({"current_pe": 0 if df_valuation.loc[2,"Current"] == '––' else df_valuation.loc[2,"Current"],
                           "5_yr_pe":0 if df_valuation.loc[2,"5-Yr"] == '––' else df_valuation.loc[2,"5-Yr"],
                           "value_rank": 0 if float(df_valuation.loc[2,"Current"]) >= float(df_valuation.loc[2,"5-Yr"]) else 1
                           })


        ### Click to key ratio, download csv, wrangle data and move to dict

        # To ensure that we go to Quote page by clicking on the hyperlink button

        driver.find_element(By.XPATH,'//*[@id="stock__tab-quote"]/a/span/span').click()


        #to click on key ratio tab (must be in full screen mode)
        element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH,'//*[@id="keyStats"]')))
        element.click()

        #To click on key ratio table
        element1 = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH,
                                                                        '''//*[@id="__layout"]/div/div/div[2]/div[3]/main/div[2]/div/div/div[1]/div[1]/div[2]/sal-components/div/sal-components-stocks-quote/div/div/div/div/div/div/div[2]/div[2]/div/div/div/div[1]/a''')))

        element1.click()

        #Choose the recently open tab with the key ratios
        driver.switch_to.window(driver.window_handles[-1])

        #click on download button
        element2 = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH,'//*[@id="financials"]/div[2]/div')))
        element2.click()


        time.sleep(10)
        df_ratio = pd.read_csv(f"C:/Users/edowi/Downloads/{stock} Key Ratios.csv", skiprows=2)

        #input eps value to dict
        input_dict.update({"eps":df_ratio.iloc[5,-1]})

        #slicing to show required rows OCF, Net Margin, Int Coverage for last 5 yrs
        df_ratio = df_ratio.iloc[[10,28,34],[0,-6,-5,-4,-3,-2]]
        df_ratio.reset_index(drop=True)

        # To change data into float
        df_ratio.iloc[0,1:] = df_ratio.iloc[0,1:].replace({',':''},regex=True).apply(pd.to_numeric,1)

        df_ratio.iloc[:,1:] = df_ratio.iloc[:,1:].astype(float)

        # Give rank value to OCF
        if df_ratio.iloc[0,-3]>0 and df_ratio.iloc[0,-2]>0 and df_ratio.iloc[0,-1]>0:
            input_dict['ocf_trend_rank'] = 1
        else:
            input_dict['ocf_trend_rank'] = 0

        # Give rank value to criteria net margin %
        lst_val = [df_ratio.iloc[1,-3],df_ratio.iloc[1,-2],df_ratio.iloc[1,-1]]
        if sum(lst_val)/len(lst_val)> 20:
            input_dict['net_margin_%_rank'] = 2
        elif sum(lst_val)/len(lst_val)> 10:
            input_dict['net_margin_%_rank'] = 1
        else:
            input_dict['net_margin_%_rank'] = 0

        # Give rank value to int coverage
        lst_val2 = [df_ratio.iloc[2,-3],df_ratio.iloc[2,-2],df_ratio.iloc[2,-1]]
        if sum(lst_val2)/len(lst_val2)> 10:
            input_dict['Int_cvr_rank'] = 2
        elif sum(lst_val2)/len(lst_val2)> 4:
            input_dict['Int_cvr_rank'] = 1
        else:
            input_dict['Int_cvr_rank'] = 0

        ### Calc potential price

        try:
            input_dict['potential price'] = float(input_dict['eps'])*float(input_dict['5_yr_pe'])
        except:
            input_dict['potential price'] = 0
        
        input_dict['tt_rank_pts'] = sum([input_dict['ocf_trend_rank'],
                                          input_dict['net_margin_%_rank'],
                                          input_dict['Int_cvr_rank'],
                                          input_dict['value_rank']])

        ### append row into df_fa for scoring¶

        df_fa = df_fa.append(input_dict, ignore_index = True)


        df_fa = df_fa.drop_duplicates(subset = 'stock')

        time.sleep(7)
        # End for loop here
    driver.quit()
    return df_fa
    
st.set_page_config(page_title = 'Stock Fundamentals for Options', page_icon = ':tada:', layout = 'wide')

# --- Introduction ---
with st.container():
    st.subheader("Hi Options Traders!")
    st.title("The go-to to getting stock fundamentals in one glance")
    st.write("One of the key criteria in my options trading strategy is to have a good understanding of the stock fundamentals. \nThese fundamentals include:")
    st.markdown('''
                - uptrend in operating cashflow
                - uptrend in net margin %
                - uptrend in interest coverage
                - current PE vs 5-yr PE
                ''')
    st.write('''
            However, it can be quite a hassle to check the fundamentals stock by stock.
            At least that was my experience. Many at times, I will forget the details i just check. 
            I could of course write down but in these day and times, I guess all of us would prefer something less tedious.
            Thus, the creation of this app!   
            ''')
# --- Brief desc of the app ---
with st.container():
    
    left_col, right_col =st.columns(2)
    with left_col:
        st.subheader("So what will this app do?")
        st.write('Essentially, it will save you the time to look through every stock ticker to check their fundamentals, instead we will let the code do it.')
        st.markdown('''
                    1. Input the ticker codes in the space provided
                    2. Let the code run
                    3. View the info in dataframe
                    4. You may choose to download the data as a CSV too!
                    ''')
    
    with right_col:
        st.write('---')
        st.markdown("**Input the stock ticker code here. If you are inputting multiple ticker, separate them with a space**")
        ticker = st.text_input('Input in the box below and click on Execute button')
        execute = st.button('Execute')
        if 'txt' not in st.session_state:
            st.session_state.txt = ''
            
        


with st.container():
    if 'df' not in st.session_state:
        st.session_state.df = ''
                
    if execute:
        st.subheader('Stock Fundamentals Dataframe')
        stocklist = ticker.split()
        df = scrape_data(stocklist)
        st.dataframe(df.astype(str))
        
        @st.cache
        def convert_df(df):
        # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv().encode('utf-8')

        csv = convert_df(df)

        download = st.download_button(label="Download data as CSV",
                           data=csv,
                           file_name='stock_fundamentals.csv',
                           mime='text/csv',
                          )
                
        st.markdown('**How to read the dataframe?**')
        st.write("What I have done is to give a ranking value to some of the criteria. This rank value will then add up to a final value. The higher the final value the better the fundamentals of the stock.")
        # st.markdown('''
        #             - 
        #             ''')
