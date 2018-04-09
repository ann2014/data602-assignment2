# Assignment 2
# Based on Jamiel Sheikh's template code

# Resources:
# https://www.youtube.com/watch?v=vVx1737auSE
# https://github.com/jamiels/trader-web
# https://code.tutsplus.com/tutorials/creating-a-web-app-from-scratch-using-python-flask-and-mysql--cms-22972
# https://www.w3schools.com/bootstrap/default.asp
# https://www.w3schools.com/bootstrap/bootstrap_buttons.asp

import re
from flask import Flask, render_template, request
import urllib.request as req
import numpy as np
import scipy as sp
import pandas as pd
import matplotlib as mp
from bs4 import BeautifulSoup
from flask_pymongo import PyMongo
from datetime import datetime
import time
import requests

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'trade'
app.config['MONGO_URI'] = 'mongodb://pretty:pretty@ds161483.mlab.com:61483/trade'

mongo = PyMongo(app)

def load(url,printout=False,delay=0,remove_bottom_rows=0,remove_columns=[]):
    time.sleep(delay)
    header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
    r = requests.get(url, headers=header)
    df = pd.read_json(r.text)
    if remove_bottom_rows > 0:
        df.drop(df.tail(remove_bottom_rows).index,inplace=True)
    df.drop(columns=remove_columns,axis=1)
    df = df.dropna(axis=1)
    if printout:
        print(df)
    return df

def get_products():
    prd = load('https://api.gdax.com/products',printout=False)
    df = pd.DataFrame(prd)
    df = df.loc[df['quote_currency']=='USD']
    return df['base_currency']

def get_price(pair):
    pair = pair + '-USD'
    df = load('https://api.gdax.com/products/'+pair+'/book',printout=False)
    ask = df.iloc[0]['asks'][0]
    bid = df.iloc[0]['bids'][0]
    return float(bid), float(ask)

def calc_vwap(current_qty,current_vwap,qty,price):
    dollar = current_qty * current_vwap
    new_dollar = dollar + (qty * price)
    new_qty = current_qty + qty
    new_vwap = new_dollar / new_qty
    return new_vwap

def update_pl(pl,pair,qty,price):
    funds = 10000000
    if qty > 0: # buy
        current_qty = pl.at[pair,'Position']
        current_vwap = pl.at[pair,'VWAP']
        new_vwap = calc_vwap(current_qty,current_vwap,qty,price)
        pl.at[pair,'Position'] = current_qty + qty
        pl.at[pair,'VWAP'] = new_vwap
        pl.at[pair,'UPL'] = current_qty * (price - current_vwap)
        pl.at[pair,'Cash'] = funds - (qty * price)
        pl.at[pair,'Total PL'] = current_qty * (price - current_vwap)
    elif qty < 0: #sell # TODO recalc UPL, RPL, position
        current_qty = pl.at[pair,'Position']
        current_vwap = pl.at[pair,'VWAP']
        pl.at[pair,'Position'] = current_qty - qty
        pl.at[pair,'UPL'] = price * (current_qty - qty)
        pl.at[pair,'RPL'] = current_qty * (price - current_vwap)
        pl.at[pair,'Cash'] = price * (current_qty - qty) + current_qty * (price - current_vwap)
        pl.at[pair,'Total PL'] = current_qty * (price - current_vwap)
        
    pl.at[pair,'Allocation By Shares'] = (current_qty + qty)/pl['Position'].sum()
    pl.at[pair,'Allocation By Dollar'] = (funds - (qty * price))/pl['Cash'].sum()
        
    return pl

def initialize_blotter():
    col_names = ['Side', 'Ticker', 'Quantity', 'Executed Price', 'Execution Timestamp', 'Money In/Out', 'Cash']
    return pd.DataFrame(columns=col_names)

def initialize_pl(pairs):
    col_names = ['Pairs','Position','VWAP','UPL','RPL', 'Total PL', 'Allocation By Shares', 'Allocation By Dollar']
    pl = pd.DataFrame(columns=col_names)
    for p in pairs:
        data = pd.DataFrame([[p,0,0,0,0,0,0,0]] ,columns=col_names)
        pl = pl.append(data, ignore_index=True)
    pl = pl.set_index('Pairs')
    return pl

@app.route("/")
def show_main_page():
    bl = initialize_blotter()
    return render_template('main.html', bl = bl)

@app.route("/trade")
def show_trade_screen():
    return render_template('trade.html', symbollist = get_products()) 

@app.route("/blotter", methods=['GET'])
def show_blotter(): 
    blotter = mongo.db.blotter
    bl = list(blotter.find())
    df = pd.DataFrame(bl)
    del df['_id']
    return render_template('blotter.html', name = 'Blotter', data=df.to_html()), df

@app.route("/pl")
def show_pl():
    pairs = get_products()
    pl = initialize_pl(pairs)
    pl.index.name = None
    return render_template('pl.html', data=pl.to_html()), pl

@app.route("/submitTrade",methods=['POST'])
def execute_trade():
    symbol = request.form.get('ticker')
    side = request.form.get('side')
    funds = 100000000.00
    # use ask price for buy, bid for sell
    if side == 'Buy':
        quantity = int(request.form['quantity']) * -1
        price = float(get_price(symbol)[1])
        money = round(price*quantity, 2)
        cash = funds - money
    else:
        quantity = int(request.form['quantity'])
        price = float(get_price(symbol)[0])
        money = round(price*quantity, 2)
        cash = funds + money

    blotter = mongo.db.blotter
    blotter.insert({'Side': side, 'Ticker': symbol, 'Quantity': quantity, 'Executed Price' : round(price,2), 'Execution Timestamp' : datetime.now(), 'Money In/Out' : money, 'Cash':  cash})
    # pull quote
    # calculate trade value
    # insert into blotter
    # calculate impact to p/l and cash
    #return "You traded at " + price
    pl = show_pl()[1]
    updated_pl = update_pl(pl, symbol, quantity, price)
    blotter_show = show_blotter()[1]
    return render_template('sample.html', symbol = symbol, quantity = quantity, side = side, price = price, money = money, cash = cash, blotter = blotter_show.to_html(), pl = updated_pl.to_html())

def get_price(pair):
    df = load('https://api.gdax.com/products/'+str(pair)+'-USD/book',printout=False)
    ask = df.iloc[0]['asks'][0]
    bid = df.iloc[0]['bids'][0]
    return float(bid), float(ask)

@app.route("/sample")
def show_sample():
    return render_template('sample.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0') # host='0.0.0.0' needed for docker
#    app.run(debug=True)
