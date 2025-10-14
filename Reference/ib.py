# -*- coding: utf-8 -*-
from queue import Queue
import warnings
from ib_insync import *
import numpy as np
import time
import datetime
import shutil
from sheet import zac_sheet

# from pandas._libs.tslibs import Hour
import pandas as pd
import datetime
import os.path
import sqlite3
import os
import sys
import math
import smtplib
import pickle
from ib_insync import IB, util, order
import os.path
import configparser
import uuid
import logging
import os
from multiprocessing.connection import Client
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from zoneinfo import ZoneInfo

util.patchAsyncio()
p = os.path.dirname(os.path.realpath(__file__))
warnings.filterwarnings("ignore")

OPEN = 0
HIGH = 1
LOW = 2
CLOSE = 3
VOLUME = 4
msg_dates = {}


def restart_program():
    """Restarts the current program, with file objects and descriptors
       cleanup
    """
    python = sys.executable
    os.execl(python, python, *sys.argv)


def ExecutionErrors(reqId, errorCode, errorString, contract):
    print("In Error function")
    print(reqId, errorCode, errorString, contract)


class LimitTrailOrder(Order):
    def __init__(self, action, totalQuantity, lmtPriceOffset, trailStopPrice, trailingAmount, **kwargs):
        Order.__init__(
            self, orderType='TRAIL LIMIT', action=action,
            totalQuantity=totalQuantity, lmtPriceOffset=lmtPriceOffset, trailStopPrice=trailStopPrice, auxPrice=trailingAmount, **kwargs)


# now we will Create and configure logger
# set file name to current date
fname = datetime.datetime.now().strftime("%Y%m%d")
logging.basicConfig(filename = fname + '.log',
                    format='%(asctime)s %(message)s', 
                    filemode='a') # Changed from 'w' to 'a' for append mode
logger = logging.getLogger()
logger.setLevel(logging.ERROR)
time.sleep(2)


config = configparser.ConfigParser()
config.read(p + '/cfg.ini')
client_alert = Client(
    ('localhost', int(config.get("General", "Port"))), authkey=b'secret password')


def send_alert(msg, subj=""):
    if subj == "":
        subj = msg
    client_alert.send(msg+"&&&"+subj)


tz = ZoneInfo('America/New_York')
d = {}


def save_obj(d, name):
    with open(p + '/' + name + '.pkl', 'wb') as f:
        pickle.dump(d, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open(p + '/' + name, 'rb') as f:
        return pickle.load(f)


def l(df, n):
    return min(n, df.shape[0])


SCOPES = ['https://mail.google.com/',
          'https://www.googleapis.com/auth/spreadsheets.readonly']
SAMPLE_RANGE_NAME = 'A1:B300'


class Strategy():
    def __init__(self, s, ib, cfg, symbol, cash_pct, account_id):
        self.s = s
        self.ib = ib
        self.symbol = symbol
        self.cfg = cfg
        self.main_order = None
        self.profit_take_order = None
        self.stop_loss_order = None
        self.trades = []
        self.cash_pct = cash_pct
        self.account_id = account_id
        self.condition1 = False
        self.confition2 = False
        self.condition3 = False
        self.condition4 = False
        self.condition5 = False
        self.last_condition = ""
        self.last_execution_date_symbol = datetime.datetime(
            2000, 1, 1, tzinfo=tz)
        self.last_execution_date_c1 = datetime.datetime(2000, 1, 1, tzinfo=tz)
        self.last_execution_date_c2 = datetime.datetime(2000, 1, 1, tzinfo=tz)
        self.last_execution_date_c3 = datetime.datetime(2000, 1, 1, tzinfo=tz)
        self.last_execution_date_c4 = datetime.datetime(2000, 1, 1, tzinfo=tz)
        self.last_execution_date_c5 = datetime.datetime(2000, 1, 1, tzinfo=tz)
        self.last_update_trade_start_time = datetime.datetime(
            2000, 1, 1, tzinfo=tz)
        self.trade_start_time = None
        self.trade_start_time_actionx = False
        self.trade_start_time_actiony = False
        self.state = "waiting"
        if symbol == "ES" or symbol == "NQ":
            self.contract = Contract(symbol=symbol, secType='CONTFUT',
                                     exchange='GLOBEX', currency='USD', includeExpired=True)
        else:
            self.contract = Stock(symbol, 'SMART', 'USD')
        self.contract = self.ib.qualifyContracts(self.contract)[0]
        self.size = 0
        self.qty = 0
        self.avgp = 0
        self.cond12_price = None
        self.cond45_price = None
        self.cond3_price = None
        self.c1 = 0
        self.c2 = 0
        self.c3 = 0
        self.c4 = 0
        self.c5 = 0
        self.conditions_dates_cache = {}

    def vwap_reset(self, vwap_price, range_price_7dma, open_trades):
        #logger.error(f"vwap_reset function called for {self.symbol}")
        if vwap_price == 0 or vwap_price == None:
            return
        for trade in open_trades:
            if "orderStatus" in dir(trade) and "OrderStatus" in dir(order):
                if self.account_id == trade.order.account and self.symbol == trade.contract.symbol and trade.orderStatus.status == order.OrderStatus.PreSubmitted:
                    if "Short" in trade.order.orderRef: 
                        soft_vwap_condition = vwap_price > 0 and abs(vwap_price) >=  ((self.cfg.vwap_pct * range_price_7dma/100.0) - (self.cfg.vwap_margin * range_price_7dma/100.0))
                        if not soft_vwap_condition:
                            logger.error(f"Symbol: {self.symbol}, vwap_price: {vwap_price}, range_price_7dma: {range_price_7dma}, vwap_pct: {self.cfg.vwap_pct}, vwap_margin: {self.cfg.vwap_margin}, soft_vwap_condition: {soft_vwap_condition}")
                            self.ib.cancelOrder(trade.order)
                            if "cond1" in trade.order.orderRef: self.c1 = True
                            if "cond2" in trade.order.orderRef: self.c2 = True
                            if "cond3" in trade.order.orderRef: self.c3 = True
                            if "cond4" in trade.order.orderRef: self.c4 = True
                            if "cond5" in trade.order.orderRef: self.c5 = True 
                    if "Buy" in trade.order.orderRef: 
                        soft_vwap_condition = vwap_price < 0 and abs(vwap_price) >= ((self.cfg.vwap_pct * range_price_7dma/100.0) - (self.cfg.vwap_margin * range_price_7dma/100.0))
                        if not soft_vwap_condition:
                            logger.error(f"Symbol: {self.symbol}, vwap_price: {vwap_price}, range_price_7dma: {range_price_7dma}, vwap_pct: {self.cfg.vwap_pct}, vwap_margin: {self.cfg.vwap_margin}, soft_vwap_condition: {soft_vwap_condition}")
                            self.ib.cancelOrder(trade.order)
                            if "cond1" in trade.order.orderRef: self.c1 = True
                            if "cond2" in trade.order.orderRef: self.c2 = True
                            if "cond3" in trade.order.orderRef: self.c3 = True
                            if "cond4" in trade.order.orderRef: self.c4 = True
                            if "cond5" in trade.order.orderRef: self.c5 = True

    def setQuantity(self, qty):
        self.qty = qty

    def set_state(self, state):
        self.state = state

    def trade_time_action(self, last_price):
        if self.symbol in self.cfg.eod_exceptions:
            return

        if self.cfg.pauseAlgo == 1:
            return
        if self.trade_start_time == None:
            return
        nw = datetime.datetime.now(tz)
        if (nw - self.last_update_trade_start_time).seconds > 10:
            diff_minutes = (nw - self.trade_start_time).seconds / 60.0
            self.last_update_trade_start_time = datetime.datetime.now(tz)

            if not self.trade_start_time_actionx and self.cfg.action1_time <= diff_minutes:
                self.trade_start_time_actionx = True
                avg_price = 0
                global order
                if len(self.ib.positions()) > 0:
                    for position in self.ib.positions():
                        if self.account_id == position.account and self.symbol == position.contract.symbol:
                            if (last_price < position.avgCost and position.position > 0) or (last_price > position.avgCost and position.position < 0):
                                for trade in self.ib.openTrades():
                                    if "orderStatus" in dir(trade) and "OrderStatus" in dir(order):
                                        if self.account_id == trade.order.account and self.symbol == trade.contract.symbol and ("-TP" in trade.order.orderRef or "TP-" in trade.order.orderRef) and trade.orderStatus.status not in order.OrderStatus.DoneStates:
                                            trade.order.lmtPrice = round(
                                                position.avgCost, 2)
                                            self.ib.placeOrder(
                                                trade.contract, trade.order)
                            else:
                                for trade in self.ib.openTrades():
                                    if "orderStatus" in dir(trade) and "OrderStatus" in dir(order):
                                        if self.account_id == trade.order.account and self.symbol == trade.contract.symbol and ("-SL" in trade.order.orderRef or "SL-" in trade.order.orderRef) and trade.orderStatus.status not in order.OrderStatus.DoneStates:
                                            trade.order.auxPrice = round(
                                                position.avgCost, 2)
                                            self.ib.placeOrder(
                                                trade.contract, trade.order)

            if not self.trade_start_time_actiony and self.cfg.action2_time <= diff_minutes:
                self.trade_start_time_actiony = True
                for trade in self.ib.openTrades():
                    if self.account_id == trade.order.account and self.symbol == trade.contract.symbol and "eod" not in trade.order.orderRef:
                        self.ib.cancelOrder(trade.order)
                        self.s.setTimeCancelOrder(trade.order.orderRef, self)
                if len(self.ib.positions()) > 0:
                    for position in self.ib.positions():
                        if self.account_id == position.account and self.symbol == position.contract.symbol:
                            contract = None
                            contract = Stock(
                                position.contract.symbol, 'SMART', 'USD')
                            contract = self.ib.qualifyContracts(contract)[0]
                            order = None
                            if position.position > 0:
                                order = MarketOrder('SELL', position.position)
                            else:
                                order = MarketOrder(
                                    'BUY', abs(position.position))
                            order.account = position.account
                            order.orderRef = "eod"
                            self.ib.placeOrder(contract, order)

                            # New Implementation
                            size = abs(float(position.position))
                            avgCost = float(position.avgCost)
                            pnl = 0
                            if position.position > 0:
                                pnl = size * (last_price - avgCost)
                            else:
                                pnl = size * (avgCost - last_price)
                            subject = "Position Closed: " + \
                                str(self.symbol) + " " + str(order.account)
                            message = "Price: " + \
                                str(round(last_price, 2)) + "\n"
                            if position.position > 0:
                                message += "Shares Sold: " + str(size) + "\n"
                            else:
                                message += "Shares Bought: " + str(size) + "\n"
                            if pnl > 0:
                                message += "Profit: $" + \
                                    str(round(pnl, 2)) + "\n"
                                message += "Profit %: " + \
                                    str(round(abs(pnl)*100/(avgCost*size), 2)) + "%\n"
                            else:
                                message += "Loss: $" + \
                                    str(abs(round(pnl, 2))) + "\n"
                                message += "Loss %: " + \
                                    str(round(abs(pnl)*100/(avgCost*size), 2)) + "%\n"
                            send_alert(message, subject)
                            # ##################

    def set_conditions(self, c1, c2, c3, c4, c5):
        self.condition1 = c1
        self.condition2 = c2
        self.condition3 = c3
        self.condition4 = c4
        self.condition5 = c5

    def write_condition_tracker(self, cond):
        with open(p + '/conditions_db.csv', 'a') as fd:
            # datetime, symbol,
            if cond == "cond1":
                row = datetime.datetime.now(tz).strftime(
                    "%m/%d/%Y %H:%M:%S") + "," + self.symbol + "," + "1" + "\n"
            elif cond == "cond2":
                row = datetime.datetime.now(tz).strftime(
                    "%m/%d/%Y %H:%M:%S") + "," + self.symbol + "," + "2" + "\n"
            elif cond == "cond3":
                row = datetime.datetime.now(tz).strftime(
                    "%m/%d/%Y %H:%M:%S") + "," + self.symbol + "," + "3" + "\n"
            elif cond == "cond4":
                row = datetime.datetime.now(tz).strftime(
                    "%m/%d/%Y %H:%M:%S") + "," + self.symbol + "," + "4" + "\n"
            else:
                row = datetime.datetime.now(tz).strftime(
                    "%m/%d/%Y %H:%M:%S") + "," + self.symbol + "," + "5" + "\n"
            fd.write(row)

    def send_sl_tp_short(self, avg_price, size, orderRef):
        fill_price = avg_price
        size = int((size * (self.cfg.sharestosell / 100.0)))
        cond = orderRef.split("-")[1]
        symbol = orderRef.split("-")[2]
        orderRefTP = "TP"+"-"+cond+"-"+symbol+"-" + str(avg_price)
        orderRefSL = "SL"+"-"+cond+"-"+symbol + "-" + str(avg_price)

        profit_take = self.cfg.profittakeC4
        if cond == "cond5":
            profit_take = self.cfg.profittakeC5

        tardeTP = None
        tardeSL = None

        for trade in self.ib.openTrades():
            if len(trade.order.orderRef.split('-')) == 4:
                if trade.order.orderRef.split('-')[:3] == orderRefTP.split('-')[:3] and trade.order.account == self.account_id:
                    tardeTP = trade
                if trade.order.orderRef.split('-')[:3] == orderRefSL.split('-')[:3] and trade.order.account == self.account_id:
                    tardeSL = trade

        if tardeTP != None and tardeSL != None:
            tardeTP.order.totalQuantity = abs(self.qty) + size
            tardeTP.order.account = self.account_id
            tardeTP.order.orderRef = orderRefTP
            tardeSL.order.orderRef = orderRefSL
            if cond == "cond4":
                tardeTP.order.transmit = self.cfg.automaticSellC4
            elif cond == "cond5":
                tardeTP.order.transmit = self.cfg.automaticSellC5

            tardeSL.order.auxPrice = round(
                fill_price + fill_price * self.cfg.stoploss * (self.s.metric_range_price30DMA/100) / 100.0, 2)
            self.tp = round(fill_price - fill_price * profit_take *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)
            self.sl = round(fill_price + fill_price * self.cfg.stoploss *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)
            tardeSL.order.totalQuantity = abs(self.qty) + size
            tardeSL.order.account = self.account_id
            if cond == "cond4":
                tardeSL.order.transmit = self.cfg.automaticSellC4
            elif cond == "cond5":
                tardeSL.order.transmit = self.cfg.automaticSellC5

            tardeTP.order.outsideRth = True
            tardeTP.order.lmtPrice = round(
                fill_price - fill_price * profit_take * (self.s.metric_range_price30DMA/100) / 100.0, 2)

            tardeTP.order.tif = "GTC"
            tardeSL.order.tif = "GTC"
            self.ib.placeOrder(tardeTP.contract, tardeTP.order)
            self.ib.placeOrder(tardeSL.contract, tardeSL.order)
            self.qty += abs(size)
        else:
            # Take Profit Order
            lmt_price = round(fill_price - fill_price * profit_take *
                              (self.s.metric_range_price30DMA/100) / 100.0, 2)
            profit_take_order = LimitOrder('BUY', size, lmt_price)
            profit_take_order.outsideRth = True
            profit_take_order.account = self.account_id
            profit_take_order.tif = "GTC"

            if cond == "cond4":
                profit_take_order.transmit = self.cfg.automaticSellC4
            elif cond == "cond5":
                profit_take_order.transmit = self.cfg.automaticSellC5

            profit_take_order.orderRef = "TP-" + cond + \
                "-" + self.symbol + "-" + str(avg_price)
            self.tp = round(fill_price - fill_price * profit_take *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)

            # StopLoss Order
            stop_loss = round(fill_price + fill_price * self.cfg.stoploss *
                              (self.s.metric_range_price30DMA/100) / 100.0, 2)
            stop_loss_order = StopOrder("BUY", size, stop_loss)
            stop_loss_order.outsideRth = True
            stop_loss_order.tif = "GTC"

            if cond == "cond4":
                stop_loss_order.transmit = self.cfg.automaticSellC4
            elif cond == "cond5":
                stop_loss_order.transmit = self.cfg.automaticSellC5

            stop_loss_order.account = self.account_id
            stop_loss_order.orderRef = "SL-" + cond + \
                "-" + self.symbol + "-" + str(avg_price)
            self.sl = round(fill_price + fill_price * self.cfg.stoploss *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)
            orders = self.ib.oneCancelsAll(
                [profit_take_order, stop_loss_order], str(uuid.uuid1()), 2)
            for order in orders:
                self.ib.placeOrder(self.contract, order)
            self.qty = abs(size)

    def send_sl_tp(self, avg_price, size, orderRef):
        fill_price = avg_price
        size = int((size * (self.cfg.sharestosell / 100.0)))

        cond = orderRef.split("-")[1]
        symbol = orderRef.split("-")[2]

        orderRefTP = "TP"+"-"+cond+"-"+symbol+"-" + str(avg_price)
        orderRefSL = "SL"+"-"+cond+"-"+symbol + "-" + str(avg_price)
        profit_take = self.cfg.profittakeC1
        if cond == "cond1":
            profit_take = self.cfg.profittakeC1
        elif cond == "cond2":
            profit_take = self.cfg.profittakeC2
        else:
            profit_take = self.cfg.profittakeC3

        tardeTP = None
        tardeSL = None

        for trade in self.ib.openTrades():
            if len(trade.order.orderRef.split('-')) == 4:
                if trade.order.orderRef.split('-')[:3] == orderRefTP.split('-')[:3] and trade.order.account == self.account_id:
                    tardeTP = trade
                if trade.order.orderRef.split('-')[:3] == orderRefSL.split('-')[:3] and trade.order.account == self.account_id:
                    tardeSL = trade

        if tardeTP != None and tardeSL != None:
            tardeTP.order.totalQuantity = self.qty + size
            tardeTP.order.account = self.account_id
            tardeTP.order.orderRef = orderRefTP
            tardeSL.order.orderRef = orderRefSL
            if cond == "cond1":
                tardeTP.order.transmit = self.cfg.automaticSellC1
            elif cond == "cond2":
                tardeTP.order.transmit = self.cfg.automaticSellC2
            else:
                tardeTP.order.transmit = self.cfg.automaticSellC3

            tardeSL.order.auxPrice = round(
                fill_price - fill_price * self.cfg.stoploss * (self.s.metric_range_price30DMA/100) / 100.0, 2)
            self.tp = round(fill_price + fill_price * profit_take *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)
            self.sl = round(fill_price - fill_price * self.cfg.stoploss *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)
            tardeSL.order.totalQuantity = self.qty + size
            tardeSL.order.account = self.account_id
            if cond == "cond1":
                tardeSL.order.transmit = self.cfg.automaticSellC1
            elif cond == "cond2":
                tardeSL.order.transmit = self.cfg.automaticSellC2
            else:
                tardeSL.order.transmit = self.cfg.automaticSellC3

            tardeTP.order.outsideRth = True
            tardeTP.order.lmtPrice = round(
                fill_price + fill_price * profit_take * (self.s.metric_range_price30DMA/100) / 100.0, 2)

            tardeTP.order.tif = "GTC"
            tardeSL.order.tif = "GTC"
            self.ib.placeOrder(tardeTP.contract, tardeTP.order)
            self.ib.placeOrder(tardeSL.contract, tardeSL.order)
            self.qty += size

        else:
            # Take Profit Order
            lmt_price = round(fill_price + fill_price * profit_take *
                              (self.s.metric_range_price30DMA/100) / 100.0, 2)
            profit_take_order = LimitOrder('SELL', size, lmt_price)
            profit_take_order.outsideRth = True
            profit_take_order.account = self.account_id
            profit_take_order.tif = "GTC"

            if cond == "cond1":
                profit_take_order.transmit = self.cfg.automaticSellC1
            elif cond == "cond2":
                profit_take_order.transmit = self.cfg.automaticSellC2
            else:
                profit_take_order.transmit = self.cfg.automaticSellC3

            profit_take_order.orderRef = "TP-" + cond + \
                "-" + self.symbol + "-" + str(avg_price)
            self.tp = round(fill_price + fill_price * profit_take *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)

            # StopLoss Order
            stop_loss = round(fill_price - fill_price * self.cfg.stoploss *
                              (self.s.metric_range_price30DMA/100) / 100.0, 2)
            stop_loss_order = StopOrder("SELL", size, stop_loss)
            stop_loss_order.outsideRth = True
            stop_loss_order.tif = "GTC"

            if cond == "cond1":
                stop_loss_order.transmit = self.cfg.automaticSellC1
            elif cond == "cond2":
                stop_loss_order.transmit = self.cfg.automaticSellC2
            else:
                stop_loss_order.transmit = self.cfg.automaticSellC3
            stop_loss_order.account = self.account_id
            stop_loss_order.orderRef = "SL-" + cond + \
                "-" + self.symbol + "-" + str(avg_price)
            self.sl = round(fill_price - fill_price * self.cfg.stoploss *
                            (self.s.metric_range_price30DMA/100) / 100.0, 2)
            orders = self.ib.oneCancelsAll(
                [profit_take_order, stop_loss_order], str(uuid.uuid1()), 2)
            for order in orders:
                self.ib.placeOrder(self.contract, order)
            self.qty = size

    def get_remaining_available_cash(self):
        account_values = self.ib.accountValues(account='')
        netLiquidation = 0
        for elem in account_values:
            if elem.tag == "NetLiquidation" and elem.account == self.account_id:
                netLiquidation = float(elem.value) * 1
        cash_used = 0
        positions = self.ib.positions(account=self.account_id)
        for position in positions:
            cash_used += abs(float(position.avgCost) * abs(float(position.position)))
        cash = self.cash_pct * netLiquidation / 100.0
        max_cash = self.cfg.maxCapitalPct * netLiquidation / 100.0
        if max_cash >= cash + cash_used:
            return cash
        else:
            return 0

    def send_order_short(self, price, nominal_range, condition, algo_on, strategy_enabled):
        nw = datetime.datetime.now(tz)
        algo_off_before_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_before.split(":")[0]), int(self.cfg.algo_off_before.split(":")[1]), tzinfo=tz)
        algo_off_after_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_after.split(":")[0]), int(self.cfg.algo_off_after.split(":")[1]), tzinfo=tz)
        strategy_enabled_time_condition = nw >= algo_off_before_time and nw <= algo_off_after_time

        cash = self.get_remaining_available_cash()
        self.size = int(cash / price)
        if self.size <= 0:
            return

        lmt_price = None
        trailingAmount = None
        trailStopPrice = None
        lmtPriceOffset = None

        profit_take = self.cfg.profittakeC4
        if condition == "cond4":
            profit_take = self.cfg.profittakeC4
        elif condition == "cond5":
            profit_take = self.cfg.profittakeC5

        lmt_price = round(price - (self.cfg.param4 / 100) * nominal_range, 2)
        trailingAmount = round((self.cfg.param4 / 100) * nominal_range, 2)
        self.cond45_price = price
        trailStopPrice = lmt_price
        lmtPriceOffset = round((self.cfg.offsetpct/100.0 * lmt_price), 2)
        logger.error(f"{self.symbol}: LimitTrailOrder parameters - size:{self.size}, lmtPriceOffset:{lmtPriceOffset}, trailStopPrice:{trailStopPrice}, trailingAmount:{trailingAmount}, nominal_range:{nominal_range}")
        self.main_order_order = LimitTrailOrder(
            'SELL', self.size, lmtPriceOffset, trailStopPrice, trailingAmount)
        if condition == "cond4":
            self.main_order_order.transmit = self.cfg.automaticBuyC4
        elif condition == "cond5":
            self.main_order_order.transmit = self.cfg.automaticBuyC5
        self.main_order_order.account = self.account_id
        self.main_order_order.outsideRth = False
        self.main_order_order.orderRef = "Short-" + condition + "-" + self.symbol
        if algo_on and strategy_enabled:
            self.main_order = self.ib.placeOrder(
                self.contract, self.main_order_order)
            
        if algo_on and not strategy_enabled and strategy_enabled_time_condition:
            self.s.app.disable_target_pnl_reached.append(self.account_id)
            self.main_order_order.transmit = False
            self.main_order = self.ib.placeOrder(
                self.contract, self.main_order_order)

        c_subj = ""
        c_message = ""
        if condition == "cond4":
            c_subj = "C4"
            c_message = "Condition 4"
        if condition == "cond5":
            c_subj = "C5"
            c_message = "Condition 5"

        take_profit_price = round(
            lmt_price - lmt_price * (self.s.metric_range_price30DMA/100) * profit_take / 100.0, 2)
        stop_loss_price = round(
            lmt_price + lmt_price * (self.s.metric_range_price30DMA/100) * self.cfg.stoploss / 100.0, 2)

        subject = "Sell Order Placed: " + self.symbol + \
            " " + c_subj + " " + str(self.account_id)
        message = c_message + "\n"
        message += "Price: " + str(lmt_price) + "\n"
        message += "Shares: " + str(self.size) + "\n"

        message += "Profit: $" + \
            str(round(self.size * (self.cfg.sharestosell / 100.0)
                * abs(lmt_price - take_profit_price), 2)) + "\n"
        message += "Profit %: " + \
            str(round(((lmt_price - take_profit_price)/lmt_price)
                * 100 * (self.cfg.sharestosell / 100.0), 2)) + "%\n"
        message += "Profit Take Price: $" + str(take_profit_price) + "\n"

        message += "Loss: $" + \
            str(round(self.size * (self.cfg.sharestosell / 100.0)
                * abs(lmt_price - stop_loss_price), 2)) + "\n"
        message += "Loss %: " + str(round(((stop_loss_price - lmt_price)/lmt_price)
                                    * 100 * (self.cfg.sharestosell / 100.0), 2)) + "%\n"
        message += "Stop Loss Price: $" + str(stop_loss_price) + "\n"

        message += "Shares to be sold: " + \
            str((self.size * (self.cfg.sharestosell / 100.0))) + "\n"
        if self.s.metric_vwap_pct != None:
            message += "VWAP PCT: " + str(round(self.s.metric_vwap_pct, 2)) + "\n"
        if algo_on and strategy_enabled:
            message += "Position Equity Amount: $" + \
                str(round(self.size * lmt_price, 2)) + "\n"
            #logger.error(subject + " " + message)
            self.s.send_alert(msg=message, subj=subject)

        if (not algo_on or not strategy_enabled) and ((self.symbol, condition) not in self.conditions_dates_cache or datetime.datetime.now(tz) - self.conditions_dates_cache[self.symbol, condition] > datetime.timedelta(minutes=60)):
            self.conditions_dates_cache[(self.symbol, condition)] = datetime.datetime.now(tz)
            self.write_condition_tracker(cond=condition)

        if algo_on and strategy_enabled:
            self.write_condition_tracker(cond=condition)

    def send_order(self, price, nominal_range, condition, algo_on, strategy_enabled):
        nw = datetime.datetime.now(tz)
        algo_off_before_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_before.split(":")[0]), int(self.cfg.algo_off_before.split(":")[1]), tzinfo=tz)
        algo_off_after_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_after.split(":")[0]), int(self.cfg.algo_off_after.split(":")[1]), tzinfo=tz)
        strategy_enabled_time_condition = nw >= algo_off_before_time and nw <= algo_off_after_time

        cash = self.get_remaining_available_cash()
        self.size = int(cash / price)
        if self.size <= 0:
            return
        lmt_price = None
        trailingAmount = None
        trailStopPrice = None
        lmtPriceOffset = None

        profit_take = self.cfg.profittakeC1
        if condition == "cond1":
            profit_take = self.cfg.profittakeC1
        elif condition == "cond2":
            profit_take = self.cfg.profittakeC2
        else:
            profit_take = self.cfg.profittakeC3

        if condition == "cond1" or condition == "cond2":
            lmt_price = round(price + (self.cfg.param4 / 100)
                              * nominal_range, 2)
            trailingAmount = round((self.cfg.param4 / 100) * nominal_range, 2)
            self.cond12_price = price
        else:
            lmt_price = round(price + (self.cfg.param5 / 100) * price, 2)
            trailingAmount = round((self.cfg.param5 / 100) * price, 2)
            self.cond3_price = price

        trailStopPrice = lmt_price
        lmtPriceOffset = round((self.cfg.offsetpct/100.0 * lmt_price), 2)
        logger.error(f"{self.symbol}: LimitTrailOrder parameters - size:{self.size}, lmtPriceOffset:{lmtPriceOffset}, trailStopPrice:{trailStopPrice}, trailingAmount:{trailingAmount}, nominal_range:{nominal_range}")
        self.main_order_order = LimitTrailOrder(
            'BUY', self.size, lmtPriceOffset, trailStopPrice, trailingAmount)
        if condition == "cond1":
            self.main_order_order.transmit = self.cfg.automaticBuyC1
        elif condition == "cond2":
            self.main_order_order.transmit = self.cfg.automaticBuyC2
        else:
            self.main_order_order.transmit = self.cfg.automaticBuyC3
        self.main_order_order.account = self.account_id
        self.main_order_order.outsideRth = False
        self.main_order_order.orderRef = "Buy-" + condition + "-" + self.symbol
    
        if algo_on and strategy_enabled:
            self.main_order = self.ib.placeOrder(
                self.contract, self.main_order_order)
            
        if algo_on and not strategy_enabled and strategy_enabled_time_condition:
            self.s.app.disable_target_pnl_reached.append(self.account_id)
            self.main_order_order.transmit = False
            self.main_order = self.ib.placeOrder(
                self.contract, self.main_order_order)

        c_subj = ""
        c_message = ""
        if condition == "cond1":
            c_subj = "C1"
            c_message = "Condition 1"
        if condition == "cond2":
            c_subj = "C2"
            c_message = "Condition 2"
        if condition == "cond3":
            c_subj = "C3"
            c_message = "Condition 3"

        take_profit_price = round(
            lmt_price + lmt_price * (self.s.metric_range_price30DMA/100) * profit_take / 100.0, 2)
        stop_loss_price = round(
            lmt_price - lmt_price * (self.s.metric_range_price30DMA/100) * self.cfg.stoploss / 100.0, 2)

        subject = "Buy Order Placed: " + self.symbol + \
            " " + c_subj + " " + str(self.account_id)
        message = c_message + "\n"
        message += "Price: " + str(lmt_price) + "\n"
        message += "Shares: " + str(self.size) + "\n"

        message += "Profit: $" + \
            str(round(self.size * (self.cfg.sharestosell / 100.0)
                * abs(lmt_price - take_profit_price), 2)) + "\n"
        message += "Profit %: " + \
            str(round(((take_profit_price - lmt_price)/lmt_price)
                * 100 * (self.cfg.sharestosell / 100.0), 2)) + "%\n"
        message += "Profit Take Price: $" + str(take_profit_price) + "\n"

        message += "Loss: $" + \
            str(round(self.size * (self.cfg.sharestosell / 100.0)
                * abs(lmt_price - stop_loss_price), 2)) + "\n"
        message += "Loss %: " + str(round(((lmt_price - stop_loss_price)/lmt_price)
                                    * 100 * (self.cfg.sharestosell / 100.0), 2)) + "%\n"
        message += "Stop Loss Price: $" + str(stop_loss_price) + "\n"

        message += "Shares to be sold: " + \
            str((self.size * (self.cfg.sharestosell / 100.0))) + "\n"
        if self.s.metric_vwap_pct != None:
            message += "VWAP PCT: " + str(round(self.s.metric_vwap_pct, 2)) + "\n"
        if algo_on and strategy_enabled:
            message += "Position Equity Amount: $" + \
                str(round(self.size * lmt_price, 2)) + "\n"
            #logger.error(subject + " " + message)
            self.s.send_alert(msg=message, subj=subject)

        if (not algo_on or not strategy_enabled) and ((self.symbol, condition) not in self.conditions_dates_cache or datetime.datetime.now(tz) - self.conditions_dates_cache[self.symbol, condition] > datetime.timedelta(minutes=60)):
            self.conditions_dates_cache[(self.symbol, condition)] = datetime.datetime.now(tz)
            self.write_condition_tracker(cond=condition)

        if algo_on and strategy_enabled:
            self.write_condition_tracker(cond=condition)

    def update_open_trades(self):
        self.trades = []
        for trade in self.ib.openTrades():
            if self.symbol in trade.contract.symbol and trade.order.account == self.account_id:
                self.trades.append(trade)

    def update_short(self, price, nominal_range, algo_on, strategy_enabled):
        nw = datetime.datetime.now(tz)
        self.update_open_trades()

        for trade in self.trades:
            if trade.order.account == self.account_id:
                return

        if self.condition4 and (nw-self.last_execution_date_c4).total_seconds() > (60*self.cfg.sameConditionTimeC4) and (nw-self.last_execution_date_symbol).total_seconds() > (60*self.cfg.sameSymbolTime):
            send_order_bool = True
            for trade in self.trades:
                if self.symbol in trade.order.orderRef and "cond4" in trade.order.orderRef:
                    send_order_bool = False
            if send_order_bool:
                if algo_on:
                    print(datetime.datetime.now(tz),
                          self.symbol, "Condition 4 is valid")
                #logger.error("Account ID: " + str(self.account_id) + " Symbol: " + self.symbol + " Condition 4 is valid")
                self.send_order_short(price, nominal_range, "cond4", algo_on, strategy_enabled)

        if self.condition5 and (nw-self.last_execution_date_c5).total_seconds() > (60*self.cfg.sameConditionTimeC5) and (nw-self.last_execution_date_symbol).total_seconds() > (60*self.cfg.sameSymbolTime):
            send_order_bool = True
            for trade in self.trades:
                if self.symbol in trade.order.orderRef and "cond5" in trade.order.orderRef:
                    send_order_bool = False
            if send_order_bool:
                if algo_on:
                    print(datetime.datetime.now(tz),
                          self.symbol, "Condition 5 is valid")
                #logger.error("Account ID: " + str(self.account_id) + " Symbol: " + self.symbol + " Condition 5 is valid")
                self.send_order_short(price, nominal_range, "cond5", algo_on, strategy_enabled)

    def update_outstanding_orders(self):
        cash = self.get_remaining_available_cash()
        if cash <= 0:
            for trade in self.ib.openTrades():
                if trade.order.account == self.account_id:
                    orderRef = trade.order.orderRef
                    if "Buy" in orderRef or "Short" in orderRef:
                        self.ib.cancelOrder(trade.order)
                        self.s.setTimeCancelOrder(trade.order.orderRef, self)

    def update(self, price, nominal_range, algo_on, strategy_enabled):
        nw = datetime.datetime.now(tz)
        self.update_open_trades()
        for trade in self.trades:
            if trade.order.account == self.account_id:
                return
        if self.condition1 and (nw-self.last_execution_date_c1).total_seconds() > (60*self.cfg.sameConditionTimeC1) and (nw-self.last_execution_date_symbol).total_seconds() > (60*self.cfg.sameSymbolTime):
            send_order_bool = True
            for trade in self.trades:
                if self.symbol in trade.order.orderRef and "cond1" in trade.order.orderRef:
                    send_order_bool = False
        
            if send_order_bool:
                if algo_on:
                    print(datetime.datetime.now(tz),
                          self.symbol, "Condition 1 is valid")
                #logger.error("Account ID: " + str(self.account_id) + " Symbol: " + self.symbol + " Condition 1 is valid")
                self.send_order(price, nominal_range, "cond1", algo_on, strategy_enabled)

        if self.condition2 and (nw-self.last_execution_date_c2).total_seconds() > (60*self.cfg.sameConditionTimeC2) and (nw-self.last_execution_date_symbol).total_seconds() > (60*self.cfg.sameSymbolTime):
            send_order_bool = True
            for trade in self.trades:
                if self.symbol in trade.order.orderRef and "cond2" in trade.order.orderRef:
                    send_order_bool = False
            if send_order_bool:
                if algo_on:
                    print(datetime.datetime.now(tz),
                          self.symbol, "Condition 2 is valid")
                #logger.error("Account ID: " + str(self.account_id) + " Symbol: " + self.symbol + " Condition 2 is valid")
                self.send_order(price, nominal_range, "cond2", algo_on, strategy_enabled)

        if self.condition3 and (nw-self.last_execution_date_c3).total_seconds() > (60*self.cfg.sameConditionTimeC3) and (nw-self.last_execution_date_symbol).total_seconds() > (60*self.cfg.sameSymbolTime):
            send_order_bool = True
            for trade in self.trades:
                if self.symbol in trade.order.orderRef and "cond3" in trade.order.orderRef:
                    send_order_bool = False
            if send_order_bool:
                if algo_on:
                    print(datetime.datetime.now(tz),
                          self.symbol, "Condition 3 is valid")
                #logger.error("Account ID: " + str(self.account_id) + " Symbol: " + self.symbol + " Condition 3 is valid")
                self.send_order(price, nominal_range, "cond3", algo_on, strategy_enabled)

        if algo_on:
            buy_cond3 = False
            sp_tp_cond3 = False
            trade_cond3 = None
            for trade in self.trades:
                if self.symbol in trade.order.orderRef and "cond3" in trade.order.orderRef and "Buy-" in trade.order.orderRef:
                    buy_cond3 = True
                    trade_cond3 = trade
                if self.symbol in trade.order.orderRef and "cond3" in trade.order.orderRef and ("TP-" in trade.order.orderRef or "SL-" in trade.order.orderRef):
                    sp_tp_cond3 = True

            if buy_cond3 and (not sp_tp_cond3) and (nw-self.last_execution_date_c3).total_seconds() > (60*30):
                if "eod" not in trade.order.orderRef:
                    self.ib.cancelOrder(trade.order)
                    nw = datetime.datetime.now(tz)
                    self.last_execution_date_c3 = nw


last_time_spread_sheet = datetime.datetime.now(tz)


class StrategyCfg():
    def load_data(self):
        global last_time_spread_sheet
        success = False
        while success is False:
            try:
                while (datetime.datetime.now(tz) - last_time_spread_sheet).seconds < 1:
                    pass
                last_time_spread_sheet = datetime.datetime.now(tz)
                result = self.sheet.values().get(spreadsheetId=self.sheet_id,
                                                range=SAMPLE_RANGE_NAME).execute()
                values = result.get('values', [])
                self.values = values
                self.param1 = float(values[0][1])
                self.param2 = float(values[1][1])
                self.param3 = float(values[2][1])
                self.param4 = float(values[3][1])
                self.param5 = float(values[4][1])
                self.c1 = float(values[5][1]) == 1
                self.c2 = float(values[6][1]) == 1
                self.c3 = float(values[7][1]) == 1
                self.c4 = float(values[8][1]) == 1
                self.c5 = float(values[9][1]) == 1
                self.profittakeC1 = float(values[10][1])
                self.profittakeC2 = float(values[11][1])
                self.profittakeC3 = float(values[12][1])
                self.profittakeC4 = float(values[13][1])
                self.profittakeC5 = float(values[14][1])
                self.stoploss = float(values[15][1])
                self.sharestosell = float(values[16][1])
                self.offsetpct = float(values[17][1])
                self.sameSymbolTime = float(values[18][1])
                self.sameConditionTimeC1 = float(values[19][1])
                self.sameConditionTimeC2 = float(values[20][1])
                self.sameConditionTimeC3 = float(values[21][1])
                self.sameConditionTimeC4 = float(values[22][1])
                self.sameConditionTimeC5 = float(values[23][1])
                self.pauseAlgo = float(values[24][1])
                self.automaticBuyC1 = float(values[25][1]) == 1
                self.automaticBuyC2 = float(values[26][1]) == 1
                self.automaticBuyC3 = float(values[27][1]) == 1
                self.automaticBuyC4 = float(values[28][1]) == 1
                self.automaticBuyC5 = float(values[29][1]) == 1
                self.automaticSellC1 = float(values[30][1]) == 1
                self.automaticSellC2 = float(values[31][1]) == 1
                self.automaticSellC3 = float(values[32][1]) == 1
                self.automaticSellC4 = float(values[33][1]) == 1
                self.automaticSellC5 = float(values[34][1]) == 1
                self.StopLossUpdate = float(values[35][1])
                self.stopLossXC1 = float(values[36][1])
                self.stopLossYC1 = float(values[37][1])
                self.stopLossXC2 = float(values[38][1])
                self.stopLossYC2 = float(values[39][1])
                self.stopLossXC3 = float(values[40][1])
                self.stopLossYC3 = float(values[41][1])
                self.stopLossXC4 = float(values[42][1])
                self.stopLossYC4 = float(values[43][1])
                self.stopLossXC5 = float(values[44][1])
                self.stopLossYC5 = float(values[45][1])
                self.alertPCT1 = float(values[46][1])
                self.alertMin1 = float(values[47][1])
                self.alertPCT2 = float(values[48][1])
                self.alertMin2 = float(values[49][1])
                self.alertPriceVwapDiff = float(values[50][1])
                self.maxCapitalPct = float(values[51][1])
                self.vwap_pct = float(values[52][1])
                self.rally_x_min_pct = float(values[53][1])
                self.rally_x_max_pct = float(values[54][1])
                self.rally_y_pct = float(values[55][1])
                self.allow_actions = float(values[56][1]) == 1
                self.action1_time = float(values[57][1])
                self.action2_time = float(values[58][1])
                self.algo_off_before = values[59][1]
                self.algo_off_after = values[60][1]
                self.max_daily_pnl = float(values[61][1])
                self.sl_update_exceptions = (values[62][1]).split(",")
                self.eod_exceptions = (values[63][1]).split(",")
                self.no_data_update_minutes = int(values[64][1])
                self.rally_x_rally_y_time_constraint = int(values[65][1])
                self.threshold = float(values[66][1])
                self.order_cancel_margin = float(values[67][1])
                self.vwap_margin = float(values[68][1])
                self.rangemultiple_threshold = float(values[69][1])
                self.liquidity_threshold = float(values[70][1])
                self.gap_threshold = float(values[71][1])
                self.sharpmovement_threshold = float(values[72][1])
                self.sharpmovement_minutes = int(values[73][1])
                success = True
            
            except HttpError as err:
                print(err)
                self.ib.sleep(10)

    def __init__(self, ib):
        self.ib = ib
        config = configparser.ConfigParser()
        config.read(p + '/cfg.ini')
        self.sheet_id = config.get("General", "Sheet_ID")

        self.creds = None
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file(
                'token.json', SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        service = build('sheets', 'v4', credentials=self.creds)
        self.sheet = service.spreadsheets()
        self.load_data()


class Symbol():
    def __init__(self, ib, symbol, email, cfg, algo, s, app):
        self.last_update_tick = datetime.datetime.now(tz)
        self.app = app
        self.metric_algo = algo
        self.df_15secs = None
        self.ib = ib
        self.cfg = cfg
        self.symbol = symbol
        self.strategy = []
        self.create_strategy(cfg)
        self.stock = Stock(symbol, 'SMART', 'USD')
        self.stock = self.ib.qualifyContracts(self.stock)[0]
        self.s = s

        self.email = email
        self.data_fetch_success = True
        self.fetch_data()
        self.initialize()
        self.save_data()
        self.hasNewBar = True
        self.updated = False
        self.ib.sleep(1)
        self.actual_p1 = self.cfg.param1
        self.actual_p2 = self.cfg.param2
        self.last_update_price_time = datetime.datetime.now(tz)
        
        self.last_update_price = 0
        self.send_email_msg = True

    def set_algo(self, algo):
        self.metric_algo = algo

    def get_vwap(self):
        if self.df_15secs_numpy.shape[0] >= 2:
            temp = np.add(
                self.df_15secs_numpy[:-1, LOW], self.df_15secs_numpy[:-1, HIGH])
            if self.df_15secs_numpy[:-1, VOLUME].sum() == 0:
                vwap4 = 0
            else:
                vwap4 = (np.multiply(
                    self.df_15secs_numpy[:-1, VOLUME], temp/2).sum() / self.df_15secs_numpy[:-1, VOLUME].sum())
            return vwap4
        else:
            return 0

    def create_strategy(self, cfg):
        for i in range(len(self.cfg.values)):
            if "Account" in self.cfg.values[i][0] or "Accound" in self.cfg.values[i][0]:
                account_id = self.cfg.values[i][1]
                cash_pct = float(self.cfg.values[i+1][1])
                self.strategy.append(
                    Strategy(self, self.ib, cfg, self.symbol, cash_pct, account_id))

    def update_stop_loss(self):
        if self.symbol in self.cfg.sl_update_exceptions:
            return
        if self.metric_algo != '1' and self.metric_algo != '1.0' and self.metric_algo != 1.0:
            return
        if self.cfg.StopLossUpdate:
            tmp = ' '.join(self.cfg.sl_update_exceptions)
            for trade in self.ib.openTrades():
                orderRef = trade.order.orderRef
                if len(orderRef.split("-")) == 4:
                    cond = orderRef.split("-")[1]
                    symbol = orderRef.split("-")[2]
                    otype = orderRef.split("-")[0]
                    stop_loss_x = 0
                    stop_loss_y = 0
                    if cond == "cond1":
                        stop_loss_x = self.cfg.stopLossXC1 * \
                            (self.cfg.profittakeC1/100) * \
                            (self.metric_range_price30DMA/100)
                        stop_loss_y = self.cfg.stopLossYC1 * \
                            (self.cfg.profittakeC1/100) * \
                            (self.metric_range_price30DMA/100)
                    elif cond == "cond2":
                        stop_loss_x = self.cfg.stopLossXC2 * \
                            (self.cfg.profittakeC2/100) * \
                            (self.metric_range_price30DMA/100)
                        stop_loss_y = self.cfg.stopLossYC2 * \
                            (self.cfg.profittakeC2/100) * \
                            (self.metric_range_price30DMA/100)
                    elif cond == "cond3":
                        stop_loss_x = self.cfg.stopLossXC3 * \
                            (self.cfg.profittakeC3/100) * \
                            (self.metric_range_price30DMA/100)
                        stop_loss_y = self.cfg.stopLossYC3 * \
                            (self.cfg.profittakeC3/100) * \
                            (self.metric_range_price30DMA/100)
                    elif cond == "cond4":
                        stop_loss_x = self.cfg.stopLossXC4 * \
                            (self.cfg.profittakeC4/100) * \
                            (self.metric_range_price30DMA/100)
                        stop_loss_y = self.cfg.stopLossYC4 * \
                            (self.cfg.profittakeC4/100) * \
                            (self.metric_range_price30DMA/100)
                    else:
                        stop_loss_x = self.cfg.stopLossXC5 * \
                            (self.cfg.profittakeC5/100) * \
                            (self.metric_range_price30DMA/100)
                        stop_loss_y = self.cfg.stopLossYC5 * \
                            (self.cfg.profittakeC5/100) * \
                            (self.metric_range_price30DMA/100)

                    if "orderStatus" in dir(trade) and "OrderStatus" in dir(order):
                        if otype == "SL" and trade.orderStatus.status not in order.OrderStatus.DoneStates:
                            if symbol == self.symbol:
                                avg_price = 0
                                positions = self.ib.positions(
                                    account=trade.order.account)
                                for position in positions:
                                    if position.contract.symbol == symbol:
                                        avg_price = float(position.avgCost)

                                if cond == "cond1" or cond == "cond2" or cond == "cond3":
                                    pr_inc = (
                                        self.df_15secs.high[-1] - avg_price) * 100.0 / avg_price
                                    if pr_inc >= stop_loss_y and round(trade.order.auxPrice, 2) != round((1 + stop_loss_x/100) * avg_price, 2):
                                        trade.order.auxPrice = round(
                                            (1 + stop_loss_x/100) * avg_price, 2)
                                        self.ib.placeOrder(
                                            trade.contract, trade.order)
                                else:
                                    pr_inc = (
                                        self.df_15secs.low[-1] - avg_price) * 100.0 / avg_price
                                    if pr_inc <= -stop_loss_y and round(trade.order.auxPrice, 2) != round((1 - stop_loss_x/100) * avg_price, 2):
                                        trade.order.auxPrice = round(
                                            (1 - stop_loss_x/100) * avg_price, 2)
                                        self.ib.placeOrder(
                                            trade.contract, trade.order)

    def rally_condition(self):
        # filter 15 secs df from lowest
        nw = datetime.datetime.now(tz)
        last_day_date = None
        if nw.day == self.df_15secs_numpy[-1, -1].day:
            last_day_date = self.df_15secs_numpy[-1, -1]
        else:
            last_day_date = self.df_daily_numpy[-1, -1]
        filtered = self.df_15secs_numpy[[x.time() >= datetime.time(9, 30, tzinfo=tz) and x.time() <= datetime.time(15, 59, tzinfo=tz)
                                         and x.day == last_day_date.day for x in self.df_15secs_numpy[:, -1]], :]

        arg_min = np.argmin(filtered[:, LOW], 0)
        filtered = filtered[arg_min:, :]

        # measure lowest to highest
        highest = np.max(filtered[:, HIGH])
        lowest = np.min(filtered[:, LOW])
        lowest_date = filtered[0, -1]

        rally_x = ((highest - lowest) * 100.0 / lowest) / \
            self.metric_range_price
        rally_x_condition = (rally_x >= (self.cfg.rally_x_min_pct/100.0)
                             ) and (rally_x <= (self.cfg.rally_x_max_pct/100.0))

        logger.error(f"Symbol: {self.symbol}, Function: rally_condition, Lowest: {lowest}, Highest: {highest}, Rally X: {rally_x}, Rally X Condition: {rally_x_condition}")

        # measure highest to last
        arg_max = np.argmax(filtered[:, HIGH])
        filtered = filtered[arg_max:, :]
        last_low = filtered[-1, LOW]
        rally_y = abs((highest - last_low) * 100.0 / highest) / \
            self.metric_range_price
        rally_y_condition = rally_y >= (self.cfg.rally_y_pct/100.0)
        last_low_date = filtered[-1, -1]

        logger.error(f"Symbol: {self.symbol}, Function: rally_condition, Last Low: {last_low}, Rally Y: {rally_y}, Rally Y Condition: {rally_y_condition}")

        delta = last_low_date - lowest_date
        minutes = delta.total_seconds() / 60
        time_constraint = True

        if self.metric_range_multiplier > self.cfg.threshold:
            if minutes < self.cfg.rally_x_rally_y_time_constraint:
                time_constraint = False

        logger.error(f"Symbol: {self.symbol}, Function: rally_condition, Time Delta: {delta}, Minutes: {minutes}, Time Constraint: {time_constraint}")

        return (rally_x_condition and rally_y_condition and time_constraint), (rally_x > (self.cfg.rally_x_max_pct/100.0))

    def rally_cond_short(self):
        # filter 15 secs df from highest
        nw = datetime.datetime.now(tz)
        last_day_date = None
        if nw.day == self.df_15secs_numpy[-1, -1].day:
            last_day_date = self.df_15secs_numpy[-1, -1]
        else:
            last_day_date = self.df_daily_numpy[-1, -1]
        filtered = self.df_15secs_numpy[[x.time() >= datetime.time(9, 30, tzinfo=tz) and x.time() <= datetime.time(15, 59, tzinfo=tz)
                                         and x.day == last_day_date.day for x in self.df_15secs_numpy[:, -1]], :]
        arg_max = np.argmax(filtered[:, HIGH], 0)
        filtered = filtered[arg_max:, :]

        # measure highest to lowest
        highest = np.max(filtered[:, HIGH])
        lowest = np.min(filtered[:, LOW])
        highest_date = filtered[0, -1]

        rally_x = abs((lowest - highest) * 100.0 / highest) / \
            self.metric_range_price
        rally_x_condition = (rally_x >= (self.cfg.rally_x_min_pct/100.0)
                             ) and (rally_x <= (self.cfg.rally_x_max_pct/100.0))

        logger.error(f"Symbol: {self.symbol}, Function: rally_cond_short, Highest: {highest}, Lowest: {lowest}, Rally X: {rally_x}, Rally X Condition: {rally_x_condition}")

        # measure lowest to highest
        arg_min = np.argmin(filtered[:, LOW])
        filtered = filtered[arg_min:, :]
        last_high = filtered[-1, HIGH]
        last_high_date = filtered[-1, -1]

        rally_y = abs((last_high - lowest) * 100.0 / lowest) / \
            self.metric_range_price
        rally_y_condition = rally_y >= (self.cfg.rally_y_pct/100.0)

        logger.error(f"Symbol: {self.symbol}, Function: rally_cond_short, Last High: {last_high}, Rally Y: {rally_y}, Rally Y Condition: {rally_y_condition}")

        delta = last_high_date - highest_date
        minutes = delta.total_seconds() / 60

        time_constraint = True

        if self.metric_range_multiplier > self.cfg.threshold:
            if minutes < self.cfg.rally_x_rally_y_time_constraint:
                time_constraint = False

        logger.error(f"Symbol: {self.symbol}, Function: rally_cond_short, Time Delta: {delta}, Minutes: {minutes}, Time Constraint: {time_constraint}")

        return (rally_x_condition and rally_y_condition and time_constraint), (rally_x > (self.cfg.rally_x_max_pct/100.0))

    def pre_conidtion_state(self, strategy):
        # if open trade or time difference less than same conidtion time return false
        # else return True
        nw = datetime.datetime.now(tz)
        pre_cond1 = (nw-strategy.last_execution_date_c1).total_seconds() > (60 *
                                                                            strategy.cfg.sameConditionTimeC1)
        pre_cond2 = (nw-strategy.last_execution_date_c2).total_seconds() > (60 *
                                                                            strategy.cfg.sameConditionTimeC2)
        pre_cond3 = (nw-strategy.last_execution_date_c3).total_seconds() > (60 *
                                                                            strategy.cfg.sameConditionTimeC3)
        pre_cond4 = (nw-strategy.last_execution_date_c4).total_seconds() > (60 *
                                                                            strategy.cfg.sameConditionTimeC4)
        pre_cond5 = (nw-strategy.last_execution_date_c5).total_seconds() > (60 *
                                                                            strategy.cfg.sameConditionTimeC5)

        strategy.update_open_trades()
        for trade in strategy.trades:
            if "cond1" in trade.order.orderRef:
                pre_cond1 = False
            if "cond2" in trade.order.orderRef:
                pre_cond2 = False
            if "cond3" in trade.order.orderRef:
                pre_cond3 = False
            if "cond4" in trade.order.orderRef:
                pre_cond1 = False
            if "cond5" in trade.order.orderRef:
                pre_cond1 = False
        return pre_cond1, pre_cond2, pre_cond3, pre_cond4, pre_cond5

    def conditions(self, strategy, mdp):
        condition1 = False
        condition2 = False
        condition3 = False
        condition4 = False
        condition5 = False

        rally_cond = False
        rally_cond_short = False

        pre_cond1, pre_cond2, pre_cond3, pre_cond4, pre_cond5 = self.pre_conidtion_state(
            strategy)
        now = datetime.datetime.now(tz)

        logger.error(f"{self.symbol}: Pre-conditions - c1:{pre_cond1}, c2:{pre_cond2}, c3:{pre_cond3}, c4:{pre_cond4}, c5:{pre_cond5}")

        if pre_cond1:
            if not strategy.c1:
                strategy.c1 = self.metric_range_percfromopen <= (
                    -1.0 * self.metric_range_price30DMA * self.actual_p1 / 100.0)
                logger.error(f"{self.symbol}: Condition 1 check - metric_range_percfromopen: {self.metric_range_percfromopen}, metric_range_price30DMA: {self.metric_range_price30DMA}, actual_p1: {self.actual_p1}, result: {strategy.c1}")
            else:
                vwap_condition12 = self.metric_vwap_price < 0 and abs(self.metric_vwap_price) >= (
                    self.cfg.vwap_pct * self.metric_range_price7DMA/100.0)
                rally_cond, reset = self.rally_condition()
                logger.error(f"{self.symbol}: Condition 1 VWAP check - metric_vwap_price: {self.metric_vwap_price}, vwap_pct: {self.cfg.vwap_pct}, metric_range_price7DMA: {self.metric_range_price7DMA}, vwap_condition12: {vwap_condition12}, rally_cond: {rally_cond}, reset: {reset}")
                if reset:
                    strategy.c1 = False
        else:
            strategy.c1 = False

        if pre_cond2:
            if not strategy.c2:
                d = self.df_daily.index[-1*l(self.df_15secs, 1)]
                df_15secs = self.df_15secs.loc[datetime.datetime(
                    year=d.year, month=d.month, day=d.day, hour=9, minute=30, second=00, tzinfo=tz):]
                strategy.c2 = (df_15secs["low"].iloc[-2] < df_15secs["low"].iloc[:-2].min()
                               ) and self.metric_range_price >= ((self.actual_p2 / 100.0) * self.metric_range_price30DMA)
                logger.error(f"{self.symbol}: Condition 2 check - df_15secs low[-2]: {df_15secs['low'].iloc[-2]}, df_15secs low min: {df_15secs['low'].iloc[:-2].min()}, metric_range_price: {self.metric_range_price}, actual_p2: {self.actual_p2}, metric_range_price30DMA: {self.metric_range_price30DMA}, result: {strategy.c2}")
            else:
                vwap_condition12 = self.metric_vwap_price < 0 and abs(self.metric_vwap_price) >= (
                    self.cfg.vwap_pct * self.metric_range_price7DMA/100.0)
                rally_cond, reset = self.rally_condition()
                logger.error(f"{self.symbol}: Condition 2 VWAP check - metric_vwap_price: {self.metric_vwap_price}, vwap_pct: {self.cfg.vwap_pct}, metric_range_price7DMA: {self.metric_range_price7DMA}, vwap_condition12: {vwap_condition12}, rally_cond: {rally_cond}, reset: {reset}")
                if reset:
                    strategy.c2 = False
        else:
            strategy.c2 = False

        if pre_cond4:
            if not strategy.c4:
                strategy.c4 = self.metric_range_percfromopen >= (
                    1.0 * self.metric_range_price30DMA * self.actual_p1 / 100.0)
                logger.error(f"{self.symbol}: Condition 4 check - metric_range_percfromopen: {self.metric_range_percfromopen}, metric_range_price30DMA: {self.metric_range_price30DMA}, actual_p1: {self.actual_p1}, result: {strategy.c4}")
            else:
                vwap_condition45 = self.metric_vwap_price > 0 and abs(self.metric_vwap_price) >= (
                    self.cfg.vwap_pct * self.metric_range_price7DMA/100.0)
                rally_cond_short, reset = self.rally_cond_short()
                logger.error(f"{self.symbol}: Condition 4 VWAP check - metric_vwap_price: {self.metric_vwap_price}, vwap_pct: {self.cfg.vwap_pct}, metric_range_price7DMA: {self.metric_range_price7DMA}, vwap_condition45: {vwap_condition45}, rally_cond_short: {rally_cond_short}, reset: {reset}")
                if reset:
                    strategy.c4 = False
        else:
            strategy.c4 = False

        if pre_cond5:
            if not strategy.c5:
                d = self.df_daily.index[-1*l(self.df_15secs, 1)]
                df_15secs = self.df_15secs.loc[datetime.datetime(
                    year=d.year, month=d.month, day=d.day, hour=9, minute=30, second=00, tzinfo=tz):]
                strategy.c5 = (df_15secs["high"].iloc[-2] > df_15secs["high"].iloc[:-2].max()
                               ) and self.metric_range_price >= ((self.actual_p2 / 100.0) * self.metric_range_price30DMA) 
                logger.error(f"{self.symbol}: Condition 5 check - df_15secs high[-2]: {df_15secs['high'].iloc[-2]}, df_15secs high max: {df_15secs['high'].iloc[:-2].max()}, metric_range_price: {self.metric_range_price}, actual_p2: {self.actual_p2}, metric_range_price30DMA: {self.metric_range_price30DMA}, result: {strategy.c5}")
            else:
                vwap_condition45 = self.metric_vwap_price > 0 and abs(self.metric_vwap_price) >= (
                    self.cfg.vwap_pct * self.metric_range_price7DMA/100.0)
                rally_cond_short, reset = self.rally_cond_short()
                logger.error(f"{self.symbol}: Condition 5 VWAP check - metric_vwap_price: {self.metric_vwap_price}, vwap_pct: {self.cfg.vwap_pct}, metric_range_price7DMA: {self.metric_range_price7DMA}, vwap_condition45: {vwap_condition45}, rally_cond_short: {rally_cond_short}, reset: {reset}")
                if reset:
                    strategy.c5 = False
        else:
            strategy.c5 = False

        condition1 = strategy.c1 and rally_cond and pre_cond1 and vwap_condition12
        condition2 = strategy.c2 and rally_cond and pre_cond2 and vwap_condition12
        condition3 = mdp / self.metric_range_price30DMA <= -1 * (strategy.cfg.param3/100.0) and pre_cond3
        condition4 = strategy.c4 and rally_cond_short and pre_cond4 and vwap_condition45
        condition5 = strategy.c5 and rally_cond_short and pre_cond5 and vwap_condition45

        logger.error(f"{self.symbol}: Final conditions - c1:{condition1}, c2:{condition2}, c3:{condition3}, c4:{condition4}, c5:{condition5}")
        logger.error(f"{self.symbol}: Condition 3 details - mdp: {mdp}, metric_range_price30DMA: {self.metric_range_price30DMA}, param3: {strategy.cfg.param3}")

        return condition1, condition2, condition3, condition4, condition5

    def setTimeCancelOrder(self, ref, strategy):
        nw = datetime.datetime.now(tz)
        if "cond1" in ref:
            strategy.last_execution_date_c1 = nw
        if "cond2" in ref:
            strategy.last_execution_date_c2 = nw
        if "cond3" in ref:
            strategy.last_execution_date_c3 = nw
        if "cond4" in ref:
            strategy.last_execution_date_c4 = nw
        if "cond5" in ref:
            strategy.last_execution_date_c5 = nw
        strategy.last_execution_date_symbol = nw

    def cancel_long(self, strategy):
        d = self.df_daily.index[-1*l(self.df_15secs, 1)]
        df_15secs = self.df_15secs.loc[datetime.datetime(
            year=d.year, month=d.month, day=d.day, hour=9, minute=30, second=00, tzinfo=tz):]
        if (df_15secs["low"].iloc[-2] < df_15secs["low"].iloc[:-2].min()) and abs(df_15secs["low"].iloc[-2] - df_15secs["low"].iloc[:-2].min()) > self.cfg.order_cancel_margin:
            for trade in self.ib.openTrades():
                if self.symbol in trade.order.orderRef and "Buy-" in trade.order.orderRef:
                    self.ib.cancelOrder(trade.order)
                    self.setTimeCancelOrder(trade.order.orderRef, strategy)

    def cancel_short(self, strategy):
        d = self.df_daily.index[-1*l(self.df_15secs, 1)]
        df_15secs = self.df_15secs.loc[datetime.datetime(
            year=d.year, month=d.month, day=d.day, hour=9, minute=30, second=00, tzinfo=tz):]
        if (df_15secs["high"].iloc[-2] > df_15secs["high"].iloc[:-2].max()) and abs(df_15secs["high"].iloc[-2] - df_15secs["high"].iloc[:-2].max()) > self.cfg.order_cancel_margin:
            for trade in self.ib.openTrades():
                if self.symbol in trade.order.orderRef and "Short" in trade.order.orderRef:
                    self.ib.cancelOrder(trade.order)
                    self.setTimeCancelOrder(trade.order.orderRef, strategy)

    def is_algo_on(self):
        algo_enabled = not (self.metric_algo != '1' and self.metric_algo !=
                            '1.0' and self.metric_algo != 1.0) and self.cfg.pauseAlgo == 0
        return algo_enabled

    def update_strategy(self, price, strategy, mdp, strategy_enabled):
        if self.df_15secs.shape[0] > 2 and self.after_market_open() and self.before_market_close():
            algo_on = self.is_algo_on() and strategy_enabled
            try:
                nomial_range = (self.daily_high - self.daily_low)
            except:
                return
            condition1, condition2, condition3, condition4, condition5 = self.conditions(
                strategy, mdp)

            if condition1 and self.cfg.c1:
                strategy.c1 = False
                strategy.set_conditions(True, False, False, False, False)
                strategy.update(price, nomial_range, self.is_algo_on(), strategy_enabled )
            if condition2 and self.cfg.c2:
                strategy.c2 = False
                strategy.set_conditions(False, True, False, False, False)
                strategy.update(price, nomial_range, self.is_algo_on(), strategy_enabled )
            if condition3 and self.cfg.c3:
                strategy.set_conditions(False, False, True, False, False)
                strategy.update(price, nomial_range, self.is_algo_on(), strategy_enabled )
            if condition4 and self.cfg.c4:
                strategy.c4 = False
                strategy.set_conditions(False, False, False, True, False)
                strategy.update_short(price, nomial_range, self.is_algo_on(), strategy_enabled)
            if condition5 and self.cfg.c5:
                strategy.c5 = False
                strategy.set_conditions(False, False, False, False, True)
                strategy.update_short(price, nomial_range, self.is_algo_on(), strategy_enabled)

            self.update_stop_loss()

            if algo_on:
                self.cancel_long(strategy)
                self.cancel_short(strategy)
                strategy.update_outstanding_orders()

    def save_data(self):
        d["weeks"] = self.df_weekly
        d["minutes"] = self.df_minutes
        d["days"] = self.df_daily
        d["days2"] = self.df_daily2
        foldername = "data/" + str(datetime.datetime.now(tz).year) + "-" + str(
            datetime.datetime.now(tz).month) + "-" + str(datetime.datetime.now(tz).day)
        filename = self.symbol
        try:
            os.makedirs(p + "/" + foldername)
        except OSError as e:
            pass
        save_obj(d, foldername + "/" + filename)

    def fetch_data(self):
        if not self.get_15secs_bars():
            self.data_fetch_success = False
        else:
            self.data_fetch_success = True

        filename = "data/" + str(datetime.datetime.now(tz).year) + "-" + str(datetime.datetime.now(tz).month) + \
            "-" + str(datetime.datetime.now(tz).day) + \
            "/" + self.symbol + ".pkl"

        if os.path.isfile(p + "/" + filename):
            d = load_obj(filename)
            self.df_daily = d["days"]
            self.df_daily2 = d["days2"]
            self.df_weekly = d["weeks"]
            self.df_minutes = d["minutes"]
        else:
            if self.s >= 49:
                self.cancel()
            self.get_daily_bars()
            self.get_minutes_bars(35)
            self.get_weekly_bars()
            if self.s >= 49:
                self.get_15secs_bars()
            if not self.data_fetch_success:
                nw = datetime.datetime.now(tz)
                last = datetime.datetime(
                    year=nw.year, month=nw.month, day=nw.day, tzinfo=tz)
                self.df_daily.loc[last] = self.df_daily.iloc[-1].copy(
                    deep=True)
        self.df_minutes["datetime"] = self.df_minutes.index
        self.df_minutes_numpy = self.df_minutes.to_numpy()

        self.df_daily["datetime"] = self.df_daily.index
        self.df_daily_numpy = self.df_daily.to_numpy()

        self.df_weekly["datetime"] = self.df_weekly.index
        self.df_weekly_numpy = self.df_weekly.to_numpy()

    def initialize(self):
        self.price = None
        self.metric_range_price = None
        self.metric_range_priceperc = None
        self.metric_range_priceperc30D = None
        self.metric_range_priceperc52Week = None
        self.metric_range_rel52week = None
        self.metric_range_percfromopen = None
        self.metrtic_range_oneperc = None
        self.metric_range_price7DMA = None
        self.metric_range_price30DMA = None
        self.metric_range_daylower = None
        self.metric_range_daymiddle = None
        self.metric_range_dayhigh = None
        self.metric_market_open_range_7DMA = None
        self.metric_market_open_range_30DMA = None
        self.metric_market_open_change_7DMA = None
        self.metric_market_open_change_30DMA = None
        self.metric_50DMA = None
        self.metric_100DMA = None
        self.metric_PercAbove30DMA = None
        self.metric_volCurrentTimePerMinuteVsvolCurrentTimePerMinute30DMA = None
        self.metric_Vol15Secsvs30DMA = None
        self.metric_volume_buy_pct_day = None
        self.metric_volume_buy_pct_week = None
        self.metric_volume_buy_pct_month = None
        self.metric_volume_buy_pct_week_avg = None
        self.metric_volume_buy_pct_month_avg = None
        self.metric_Vol7DMA = None
        self.metric_Vol30DMA = None
        self.metric_vol_chg_pct_day = None
        self.metric_vol_chg_pct_week = None
        self.metric_vol_chg_pct_month = None
        self.metric_pricechange_day = None
        self.metric_pricechange_7days = None
        self.metric_pricechange_30days = None
        self.metric_gap_7DMA = None
        self.metric_gap_30DMA = None
        self.vol15sec = None
        self.volCurrentDay = None
        self.vol30DMACurrentTimePerMinute = [1] * 721
        self.metric_Vol15Secsvs30DMA = None
        self.metric_volCurrentTimePerMinuteVsvolCurrentTimePerMinute30DMA = None
        self.metric_PercAbove30DMA = None
        self.metric_Vol7DMA = None
        self.metric_Vol30DMA = None
        self.metric_7DChange_7DMARange = None
        self.metric_30Change_30DMARange = None
        self.alerts_date = [datetime.datetime(2000, 1, 1)] * 11
        self.price = 0
        self.metric_7dchange7drange = None
        self.metric_30dchange30drange = None
        self.metric_vwap = None
        self.metric_vwap_price = None
        self.metric_range_multiplier = None
        self.metric_7dma_range_multiplier = None
        self.metric_liquidity = None
        self.metric_vwap_pct = None 
        self.metric_1d_gap = None 
        self.stopped = False
        nw = datetime.datetime.now(tz)
        self.update_upto_yesterday()
        self.average30DVolUpToTime()
        self.averagenetbuy()
        self.update_gap_range()
        self.update_open_change_range()
        self.update_range_change()
        self.update_range_multiple()
        self.update_cache()

        
    
    def update_cache(self):
        self.df_15secs['datetime'] = self.df_15secs.index
        self.df_15secs_numpy = self.df_15secs.to_numpy()
        # self.filtered_dfminutes_1_cache = self.filtered_dfminutes_cache(1)
        # self.filtered_dfminutes_7_cache = self.filtered_dfminutes_cache(7)
        # self.filtered_dfminutes_30_cache = self.filtered_dfminutes_cache(30)


    def update_range_multiple(self):
        first_index = 1
        try:
            if self.df_15secs.index[-1].day == self.df_daily.index[-1].day:
                first_index = 2
        except:
            pass
        res = []
        for i in range(first_index, first_index+8):
            high, low = self.get_day_high_low(i)
            current_day_range = high - low
            ranges = []
            for j in range(i+1, i+1+30):
                high, low = self.get_day_high_low(j)
                ranges.append(high - low)
            res.append(current_day_range / np.mean(ranges))
        self.metric_7dma_range_multiplier = np.mean(res)

    def update_vwap(self):
        self.metric_vwap = self.get_vwap()

    def update_range_change(self):
        first_index = 1
        try:
            if self.df_15secs.index[-1].day == self.df_daily2.index[-1].day:
                first_index = 2
        except:
            pass

        # compute ranges array
        ranges = []
        for i in range(first_index, 62):
            r = (self.df_daily2["high"].iloc[-i] - self.df_daily2["low"].iloc[-i]
                 ) * 100 / self.df_daily2["open"].iloc[-i]
            ranges.append(r)

        # caclualte the change
        self.metric_7dchange7drange = (
            np.mean(ranges[:7]) - np.mean(ranges[7:14])) * 100 / np.mean(ranges[7:14])
        self.metric_30dchange30drange = (
            np.mean(ranges[:30]) - np.mean(ranges[30:])) * 100 / np.mean(ranges[30:])

    def update_open_change_range(self):
        pass

    def update_gap_range(self):
        start_index = 1
        end_index = 31
        if self.after_market_open():
            start_index += 1
            end_index += 1
        ranges = []
        for i in range(start_index, end_index):
            high, low = self.df_daily2.high[-1*l(self.df_daily2, i)], self.df_daily2.low[-1*l(self.df_daily2, i)]
            open, close = self.df_daily2.open[-1*l(self.df_daily2, i)], self.df_daily2.close[-1*l(self.df_daily2, i)]
            r = (high - low) * 100 / open
            ranges.append(r)
        self.metric_range_price7DMA = np.mean(ranges[:7])
        self.metric_range_price30DMA = np.mean(ranges[:30])

        gaps = []
        for i in range(start_index, end_index):
            open, _ = self.get_day_close_open(i)
            _, close = self.get_day_close_open(i+1)
            g = (open - close) * 100.0 / close
            gaps.append(g)
        self.metric_gap_7DMA = np.mean(gaps[:7])
        self.metric_gap_30DMA = np.mean(gaps[:])

    def get_day_open_15(self, n):
        d = self.df_daily.index[-1*l(self.df_daily, n)]
        if datetime.datetime(year=d.year, month=d.month, day=d.day, hour=9, minute=30, tzinfo=tz) in self.df_minutes.index and datetime.datetime(year=d.year, month=d.month, day=d.day, hour=9, minute=44, tzinfo=tz) in self.df_minutes.index:
            open = self.df_minutes.loc[datetime.datetime(
                year=d.year, month=d.month, day=d.day, hour=9, minute=30, tzinfo=tz)]["open"]
            close = self.df_minutes.loc[datetime.datetime(
                year=d.year, month=d.month, day=d.day, hour=9, minute=44, tzinfo=tz)]["close"]
        else:
            open, close = self.get_day_open_15(n-1)
        return open, close

    def get_day_high_low_15(self, n):
        d = self.df_daily.index[-1*l(self.df_daily, n)]
        if datetime.datetime(year=d.year, month=d.month, day=d.day, hour=9, minute=30, tzinfo=tz) in self.df_minutes.index and datetime.datetime(year=d.year, month=d.month, day=d.day, hour=9, minute=44, tzinfo=tz) in self.df_minutes.index:
            high = self.df_minutes.loc[datetime.datetime(year=d.year, month=d.month, day=d.day, hour=9, minute=30, tzinfo=tz):datetime.datetime(
                year=d.year, month=d.month, day=d.day, hour=9, minute=44, tzinfo=tz)]["high"].max()
            low = self.df_minutes.loc[datetime.datetime(year=d.year, month=d.month, day=d.day, hour=9, minute=30, tzinfo=tz):datetime.datetime(
                year=d.year, month=d.month, day=d.day, hour=9, minute=44, tzinfo=tz)]["low"].min()
        else:
            high, low = self.get_day_high_low_15(n-1)
        return high, low

    def get_day_close_open(self, n):
        open = self.df_daily.open[-1*l(self.df_daily, n)]
        close = self.df_daily.close[-1*l(self.df_daily, n)]
        return open, close

    def get_day_high_low(self, n):
        high = self.df_daily.high[-1*l(self.df_daily, n)]
        low = self.df_daily.low[-1*l(self.df_daily, n)]
        return high, low

    def averagenetbuy(self):
        self.avgnetbuy = []
        for i in range(1, 31):
            self.avgnetbuy.append(self.daily_net_volume(i))

    def update_upto_yesterday(self):
        self.upto_yest_high = -10
        self.upto_yest_low = 99999999

        nw = datetime.datetime.now(tz)
        for i in range(1, 10):
            if self.df_daily.index[-1*l(self.df_daily, i)].day != nw.day:
                self.upto_yest_high = max(
                    self.upto_yest_high, self.df_daily["high"].iloc[-1*l(self.df_daily, i)])
                self.upto_yest_low = min(
                    self.upto_yest_low, self.df_daily["low"].iloc[-1*l(self.df_daily, i)])

    def average30DVolUpToTime(self):
        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=4, minute=00, second=0, microsecond=0, tzinfo=tz)
        todayMarketClose = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=16, minute=00, second=0, microsecond=0, tzinfo=tz)
        dateIterator = todayMarketOpen + datetime.timedelta(minutes=0)
        df_minutes = self.df_minutes.copy(deep=True)
        df_minutes = df_minutes.reset_index()
        historicalMinutesSinceOpen = df_minutes["date"].copy(deep=True)
        historicalMinutesSinceOpen = historicalMinutesSinceOpen.apply(lambda dt: (
            dt - datetime.datetime(year=dt.year, month=dt.month, day=dt.day, hour=4, minute=00, tzinfo=tz)).total_seconds()/60.0)
        df_var = self.df_daily.index[-1].tz_localize("America/New_York")
        df_var_2 = self.df_daily.index[-1 *
                                       l(self.df_daily, 31)].tz_localize("America/New_York")
        daysInRange = df_minutes["date"].copy(deep=True).apply(
            lambda dt: dt < df_var and dt >= df_var_2)
        while dateIterator <= todayMarketClose:
            minutesSinceOpen = int(
                (dateIterator - todayMarketOpen).total_seconds()/60.0)
            cond = daysInRange & (historicalMinutesSinceOpen >= 0) & (
                historicalMinutesSinceOpen <= minutesSinceOpen)
            filtered = df_minutes[cond].copy(deep=True)
            self.vol30DMACurrentTimePerMinute[minutesSinceOpen] = filtered["volume"].mean(
            ) * 100.0
            dateIterator += datetime.timedelta(minutes=1)

    def onSeconds(self, bars, hasNewBar):
        def convert_to_15_second_bar(bars):
            
            time = bars[0].time.astimezone(tz)

            open_price = bars[0].open_
            high_price = max(bar.high for bar in bars)
            low_price = min(bar.low for bar in bars)
            close_price = bars[-1].close

            volume =  sum(bar.volume for bar in bars)

            new_bar = BarData(
                date=time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
            return new_bar
        if len(bars) >= 3 and (bars[-1].time.second + 5) % 15 == 0:
            bar = convert_to_15_second_bar(bars[-3:])
            nw = datetime.datetime.now(tz)
            nw2 = datetime.datetime.now(tz)
            late_bar = False
            if (datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=nw.hour, minute=nw.minute, second=nw.second, tzinfo=tz) - bar.date).total_seconds() >= 30:
                #log_string = "Late New Bar: " + self.symbol + " " + \
                #    pd.to_datetime(self.df_15secs.index[-1]).strftime(
                #        "%m/%d/%Y, %H:%M:%S") + " " + str(self.df_15secs["open"].iloc[-1])
                #logger.error(log_string)
                late_bar = True
                
            bar = pd.DataFrame([bar.dict()])
            bar['date'] = pd.to_datetime(bar['date'])
            bar = bar.set_index('date')
            bar["datetime"] = bar.index
            if self.df_15secs.empty or self.df_15secs['datetime'].iloc[-1] < bar['datetime'].iloc[-1]:
                self.df_15secs = pd.concat([self.df_15secs, bar], axis=0)    
                self.df_15secs = self.df_15secs.loc[datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=0, tzinfo=tz):]

            self.hasNewBar = not late_bar
            end = datetime.datetime.now(tz)
            log_string = "New Bar: " + self.symbol + " " + pd.to_datetime(self.df_15secs.index[-1]).strftime(
                "%m/%d/%Y, %H:%M:%S") + " " + str(self.df_15secs["open"].iloc[-1])
            #logger.error(log_string)

    def get_daily_bars(self):
        historical_data_daily = self.ib.reqHistoricalData(
            self.stock, '', barSizeSetting='1 day', durationStr='105 D', whatToShow='TRADES', useRTH=False, keepUpToDate=False)
        self.df_daily = util.df(historical_data_daily)
        self.df_daily['date'] = pd.to_datetime(self.df_daily['date'])
        self.df_daily = self.df_daily.set_index('date')
        self.df_daily['datetime'] = self.df_daily.index
        self.df_daily_numpy = self.df_daily.to_numpy()

        historical_data_daily = self.ib.reqHistoricalData(
            self.stock, '', barSizeSetting='1 day', durationStr='105 D', whatToShow='TRADES', useRTH=True, keepUpToDate=False)
        self.df_daily2 = util.df(historical_data_daily)
        self.df_daily2['date'] = pd.to_datetime(self.df_daily2['date'])
        self.df_daily2 = self.df_daily2.set_index('date')
        self.df_daily2['datetime'] = self.df_daily2.index
        self.df_daily_numpy2 = self.df_daily2.to_numpy()

    def get_weekly_bars(self):
        dt = ''
        barsList = []
        while True:
            bars = self.ib.reqHistoricalData(
                self.stock,
                endDateTime=dt,
                durationStr='1 M',
                barSizeSetting='1 week',
                whatToShow='TRADES',
                useRTH=False,
                keepUpToDate=False,
                formatDate=1)
            if not bars or len(barsList) > 13:
                break
            barsList.append(bars)
            dt = bars[0].date

        allBars = [b for bars in reversed(barsList) for b in bars]
        self.df_weekly = util.df(allBars)
        self.df_weekly['date'] = pd.to_datetime(self.df_weekly['date'])
        self.df_weekly = self.df_weekly.set_index('date')

        self.df_weekly['datetime'] = self.df_weekly.index
        self.df_weekly_numpy = self.df_weekly.to_numpy()

    def get_minutes_bars(self, days):
        dt = ''
        barsList = []
        while len(barsList) < (days/8.0):
            if len(barsList) > (days/8.0):
                break
            bars = self.ib.reqHistoricalData(
                self.stock,
                endDateTime=dt,
                durationStr='8 D',
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=False,
                keepUpToDate=False,
                formatDate=1)
            if not bars or len(barsList) > (days/8.0):
                break
            barsList.append(bars)
            dt = bars[0].date

        allBars = [b for bars in reversed(barsList) for b in bars]
        df_minutes = util.df(allBars)

        historicalMinutesSinceOpen = df_minutes["date"].copy(
            deep=True).apply(lambda dt: dt)
        historicalMinutesSinceOpen = historicalMinutesSinceOpen.apply(lambda dt: (
            dt - datetime.datetime(year=dt.year, month=dt.month, day=dt.day, hour=16, minute=00, tzinfo=tz)).total_seconds()/60.0)
        cond = historicalMinutesSinceOpen < 0
        self.df_minutes = df_minutes[cond]
        self.df_minutes['date'] = pd.to_datetime(self.df_minutes['date'])
        self.df_minutes = self.df_minutes.set_index('date')

        self.df_minutes['datetime'] = self.df_minutes.index

    def on_tick(self, tick, *_):
        nw = datetime.datetime.now(tz)
        if (nw - self.last_update_tick).seconds > 1:
            self.last_update_tick = nw
            if not math.isnan(tick.vwap) and not math.isnan(tick.last) and tick.vwap != 0 and tick.last != 0:
                self.metric_vwap = tick.vwap
                self.metric_vwap_price = (tick.last - self.metric_vwap) * 100.0 / tick.last

    def get_15secs_bars(self):
        self.historical_data_15secs = self.ib.reqHistoricalData(
            self.stock, '', barSizeSetting='15 secs', durationStr='1 D', whatToShow='TRADES', useRTH=False)
        
        df_15secs = util.df(self.historical_data_15secs)
            
        nw = datetime.datetime.now(tz)
        df_15secs['date'] = pd.to_datetime(df_15secs['date'])
        df_15secs = df_15secs.set_index('date')

        try:
            self.df_15secs = df_15secs.loc[datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=0, tzinfo=tz):datetime.datetime(
                year=nw.year, month=nw.month, day=nw.day, hour=15, minute=59, second=59, tzinfo=tz)]
        except:
            self.df_15secs = df_15secs
        
        self.df_15secs['datetime'] = self.df_15secs.index
        
        self.historical_data_15secs = self.ib.reqRealTimeBars(self.stock, 5, whatToShow='TRADES', useRTH=False)
        self.historical_data_15secs.updateEvent += self.onSeconds
        
        market_data = self.ib.reqMktData(self.stock, '233')  # 233 is the generic tick type for VWAP
        market_data.updateEvent += self.on_tick
        return True

    def cancel(self):
        self.ib.cancelHistoricalData(self.historical_data_15secs)

    def daily_net_volume(self, n):
        df_minutes = self.df_minutes.copy(deep=True)
        df_minutes = df_minutes.reset_index()
        historicalMinutesSinceOpen = df_minutes["date"].copy(
            deep=True).apply(lambda dt: dt)
        d = self.df_daily.index[-1*l(self.df_daily, n)]
        diff = historicalMinutesSinceOpen.apply(
            lambda dt: dt.day == d.day and dt.month == d.month)
        cond = diff
        df_minutes = df_minutes[cond].copy(deep=True)
        diff = df_minutes["close"].iloc[1:].values - \
            df_minutes["close"].iloc[:-1].values
        buy_volume = df_minutes.iloc[1:, :][diff > 0]["volume"].sum()
        sell_volume = df_minutes.iloc[1:, :][diff < 0]["volume"].sum()
        total_volume = df_minutes.iloc[1:, :][diff != 0]["volume"].sum()
        if total_volume != 0:
            avg_vol = round((buy_volume-sell_volume)*100/total_volume, 2)
        else:
            avg_vol = 0
        return avg_vol

    def handle_msg(self, queue_alerts):
        while not queue_alerts.empty():
            global msg_dates
            msg, secs = queue_alerts.get()
            if msg in msg_dates.keys():
                d = msg_dates[msg]
                if (datetime.datetime.now(tz) - d).total_seconds() > 60 * secs:
                    msg_dates[msg] = datetime.datetime.now(tz)
                    self.send_alert(msg)
            else:
                msg_dates[msg] = datetime.datetime.now(tz)
                self.send_alert(msg)

    def check_alerts(self):
        a = self.cfg.alertPCT1 / 100.0
        b = self.cfg.alertMin1
        c = self.cfg.alertPCT2 / 100.0
        d = self.cfg.alertMin2

        queue_alerts = Queue(maxsize=1000)
        down_1800, index_down_1800 = self.max_down_perc_opt(d*60)
        down_600, index_down_600 = self.max_down_perc_opt(b*60)
        up_1800, index_up_1800 = self.max_up_perc_opt(d*60)
        up_600, index_up_600 = self.max_up_perc_opt(b*60)
        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=4, minute=00, second=0, tzinfo=tz)
        now = datetime.datetime(year=nw.year, month=nw.month, day=nw.day,
                                hour=nw.hour, minute=nw.minute, second=nw.second, tzinfo=tz)
        minutesSinceOpen = int((now - todayMarketOpen).total_seconds()/60.0)
        if minutesSinceOpen < 0 or minutesSinceOpen > 720:
            return

        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=9, minute=30, second=0, tzinfo=tz)
        now = datetime.datetime(year=nw.year, month=nw.month, day=nw.day,
                                hour=nw.hour, minute=nw.minute, second=nw.second, tzinfo=tz)
        afterMarketOpen = ((now - todayMarketOpen).total_seconds() > 30)

        if not afterMarketOpen:
            return

        if self.metric_range_percfromopen == None:
            return

        # update_gap_metrics

        open, _ = self.get_day_close_open(1)
        _, close = self.get_day_close_open(2)
        dail_gap = (open - close) * 100.0 / close  # marketopen

        if self.metric_range_percfromopen / self.metric_range_price30DMA >= 0.75:
            msg = self.symbol + r" Up 75% of 30DMA from the open price"
            #queue_alerts.put((msg, 720))

        if self.metric_range_percfromopen / self.metric_range_price30DMA <= -0.75:
            msg = self.symbol + r" Down 75% of 30DMA from the open price"
            #queue_alerts.put((msg, 720))

        if self.metric_range_percfromopen / self.metric_range_price30DMA >= 1.2:
            msg = self.symbol + r" Up 120% of 30DMA from the open price"
            queue_alerts.put((msg, 720))

        if self.metric_range_percfromopen / self.metric_range_price30DMA <= -1.2:
            msg = self.symbol + r" Down 120% of 30DMA from the open price"
            queue_alerts.put((msg, 720))

        if up_600/self.metric_range_price30DMA >= a and down_600/self.metric_range_price30DMA <= -a:
            if index_up_600 > index_down_600:
                msg = self.symbol + r" Up " + \
                    str(a*100) + r"% of 30DMA within " + str(b) + r" minutes"
                queue_alerts.put((msg, 5))
            else:
                msg = self.symbol + r" Down " + \
                    str(a*100) + r"% of 30DMA within " + str(b) + r" minutes"
                queue_alerts.put((msg, 5))
        elif up_600/self.metric_range_price30DMA >= a:
            msg = self.symbol + r" Up " + \
                str(a*100) + r"% of 30DMA within " + str(b) + r" minutes"
            queue_alerts.put((msg, 5))

        elif down_600/self.metric_range_price30DMA <= -a:
            msg = self.symbol + r" Down " + \
                str(a*100) + r"% of 30DMA within " + str(b) + r" minutes"
            queue_alerts.put((msg, 5))

        if up_1800/self.metric_range_price30DMA >= c and down_1800/self.metric_range_price30DMA <= -c:
            if index_up_1800 > index_down_1800:
                msg = self.symbol + r" Up " + \
                    str(c*100) + r"% of 30DMA within " + str(d) + r" minutes"
                queue_alerts.put((msg, 10))
            else:
                msg = self.symbol + r" Down " + \
                    str(c*100) + r"% of 30DMA within " + str(d) + r" minutes"
                queue_alerts.put((msg, 10))
        elif up_1800/self.metric_range_price30DMA >= c:
            msg = self.symbol + r" Up " + \
                str(c*100) + r"% of 30DMA within " + str(d) + r" minutes"
            queue_alerts.put((msg, 10))

        elif down_1800/self.metric_range_price30DMA <= -c:
            msg = self.symbol + r" Down " + \
                str(c*100) + r"% of 30DMA within " + str(d) + r" minutes"
            queue_alerts.put((msg, 10))

        if self.metric_range_price > self.metric_range_price30DMA:
            msg = self.symbol + r" Day Range is greater than 30 DMA Range"
            queue_alerts.put((msg, 720))

        if dail_gap > 5 and afterMarketOpen:
            msg = self.symbol + r" Gap is greater than 5%"
            queue_alerts.put((msg, 720))
        if dail_gap < -5 and afterMarketOpen:
            msg = self.symbol + r" Gap is less than -5%"
            queue_alerts.put((msg, 720))

        price_vwap_range_ref = (
            self.cfg.alertPriceVwapDiff / 100.0) * self.metric_range_price7DMA

        if self.metric_vwap_price != None:
            if abs(self.metric_vwap_price) >= price_vwap_range_ref:
                if self.metric_vwap_price >= 0:
                    msg = self.symbol + r" Price Above Vwap Threshold"
                    queue_alerts.put((msg, 720))
                else:
                    msg = self.symbol + r" Price Below Vwap Threshold"
                    queue_alerts.put((msg, 720))

        self.handle_msg(queue_alerts)

    def filtered_dfminutes_cache(self, n):
        cache = {}
        index = n
        if self.after_market_open(): index+=1
        d1 = self.df_daily_numpy[-1*l(self.df_daily_numpy, index), -1]
        curr_time = datetime.datetime(year=d1.year, month=d1.month, day=d1.day, hour=00, minute=00, tzinfo=tz).time()
        while curr_time <= datetime.datetime(year=d1.year, month=d1.month, day=d1.day, hour=15, minute=59, tzinfo=tz).time():
            curr_time = (datetime.datetime(year=2000, month=1, day=1, hour=curr_time.hour, minute=curr_time.minute, tzinfo=tz) + datetime.timedelta(minutes=1)).time()
            cache[curr_time] = self.df_minutes_numpy[(self.df_minutes_numpy[:, -1] >= datetime.datetime(year=d1.year, month=d1.month, day=d1.day, hour=00, minute=00, tzinfo=tz)) & (
            self.df_minutes_numpy[:, -1] <= datetime.datetime(year=d1.year, month=d1.month, day=d1.day, hour=curr_time.hour, minute=curr_time.minute, tzinfo=tz)), :]
        return cache
    
    def from_cache_1(self):
        d = self.df_15secs_numpy[-1, -1]
        time_index = datetime.datetime(year=d.year, month=d.month, day=d.day, hour=d.hour, minute=d.minute, tzinfo=tz).time()
        return self.filtered_dfminutes_1_cache[time_index]

    def from_cache_7(self):
        d = self.df_15secs_numpy[-1, -1]
        time_index = datetime.datetime(year=d.year, month=d.month, day=d.day, hour=d.hour, minute=d.minute, tzinfo=tz).time()
        return self.filtered_dfminutes_7_cache[time_index]
    
    def from_cache_30(self):
        d = self.df_15secs_numpy[-1, -1]
        time_index = datetime.datetime(year=d.year, month=d.month, day=d.day, hour=d.hour, minute=d.minute, tzinfo=tz).time()
        return self.filtered_dfminutes_30_cache[time_index]

    def filtered_dfminutes(self, n):
        d1 = self.df_daily_numpy[-1*l(self.df_daily_numpy, n), -1]
        d2 = self.df_15secs_numpy[-1, -1]
        df_minutes_temp = self.df_minutes_numpy[(self.df_minutes_numpy[:, -1] >= datetime.datetime(year=d1.year, month=d1.month, day=d1.day, hour=00, minute=00, tzinfo=tz)) & (
            self.df_minutes_numpy[:, -1] <= datetime.datetime(year=d1.year, month=d1.month, day=d1.day, hour=d2.hour, minute=d2.minute, second=d2.second, tzinfo=tz)), :]
        return df_minutes_temp

    def parallel(self, metrics_db):
        nw_ref = datetime.datetime.now()
        if self.df_15secs_numpy.shape[0] < 2:
            return

        # construct daily
        ######################################
        nw = datetime.datetime.now(tz)
        last_day_date = None
        try:
            (self.df_15secs_numpy[-1, -1].day)
        except:
            print("Error", symbol)

        if nw.day == self.df_15secs_numpy[-1, -1].day:
            last_day_date = self.df_15secs_numpy[-1, -1]
        else:
            last_day_date = self.df_daily_numpy[-1, -1]

        filtered = self.df_15secs_numpy[[
            x.day == last_day_date.day for x in self.df_15secs_numpy[:, -1]], :]
        filtered2 = self.df_15secs_numpy[[x.time() >= datetime.time(9, 30, tzinfo=tz) and x.time() <= datetime.time(15, 59, tzinfo=tz)
                                          and x.day == last_day_date.day for x in self.df_15secs_numpy[:, -1]], :]

        self.daily_volume = filtered[:, VOLUME].sum()
        self.daily_close = filtered[-1, CLOSE]

        self.daily_high2 = filtered[:, HIGH].max()
        self.daily_low2 = filtered[:, LOW].min()
        self.daily_open2 = filtered[0, OPEN]

        is_marketopen = True
        if filtered2.shape[0] == 0:
            is_marketopen = False
        else:
            self.daily_high = filtered2[:, HIGH].max()
            self.daily_low = filtered2[:, LOW].min()
            self.daily_open = filtered2[0, OPEN]
        ################################### ###
        # Update Up To Yesterday
        ######################################
        upto_yest_high = -10
        upto_yest_low = 99999999

        nw = datetime.datetime.now(tz)
        for i in range(1, 10):
            if self.df_daily_numpy[-1*l(self.df_daily_numpy, i), -1].day != nw.day:
                upto_yest_high = max(
                    upto_yest_high, self.df_daily_numpy[-1*l(self.df_daily_numpy, i), HIGH])
                upto_yest_low = min(
                    upto_yest_low, self.df_daily_numpy[-1*l(self.df_daily_numpy, i), LOW])
        ######################################
        # Update update_volume_metrics
        ######################################
        self.metric_Vol30DMA = self.df_daily_numpy[-1 *
                                                   l(self.df_daily_numpy, 31):-1, VOLUME].mean() * 100
        self.metric_Vol7DMA = self.df_daily_numpy[-1 *
                                                  l(self.df_daily_numpy, 8):-1, VOLUME].mean() * 100

        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=4, minute=00, second=0, tzinfo=tz)
        now = datetime.datetime(year=nw.year, month=nw.month, day=nw.day,
                                hour=nw.hour, minute=nw.minute, second=nw.second, tzinfo=tz)
        minutesSinceOpen = int((now - todayMarketOpen).total_seconds()/60.0)
        self.metric_PercAbove30DMA = None

        if minutesSinceOpen >= 0:
            projection_term = (720 / min(max(minutesSinceOpen, 1), 720))
            projection_term = max(min(projection_term, 720), 1)
            self.metric_PercAbove30DMA = (self.daily_volume * projection_term - (
                self.metric_Vol30DMA/100.0)) * 100 / (self.metric_Vol30DMA/100.0)

        self.metric_volCurrentTimePerMinuteVsvolCurrentTimePerMinute30DMA = None
        minutesSinceOpen = min(
            len(self.vol30DMACurrentTimePerMinute)-1, minutesSinceOpen)
        if minutesSinceOpen < len(self.vol30DMACurrentTimePerMinute) and minutesSinceOpen >= 0 and self.vol30DMACurrentTimePerMinute[minutesSinceOpen] > 0:
            self.metric_volCurrentTimePerMinuteVsvolCurrentTimePerMinute30DMA = (
                self.daily_volume * 100.0 / min(max(minutesSinceOpen, 1), 720)) / self.vol30DMACurrentTimePerMinute[minutesSinceOpen]

        ######################################
        # update_pricerange_metrics
        ######################################
        self.price = self.daily_close
        if is_marketopen:
            price_range = (self.daily_high - self.daily_low) * \
                100.0 / self.daily_open
            self.metric_range_price = price_range  # marketopen
        else:
            self.metric_range_price = 0

        max_size = -1 * self.df_weekly_numpy[:, HIGH].shape[0]
        if is_marketopen and self.daily_close != 0:
            self.metric_range_rel52week = (max(self.df_weekly_numpy[max(-1-52, max_size):-1, HIGH].max(
            ), upto_yest_high) - self.daily_close) * 100.0 / self.daily_close

        if is_marketopen and (self.daily_high - self.daily_low) != 0:
            self.metric_range_priceperc = (
                self.daily_close - self.daily_low) * 100.0 / (self.daily_high - self.daily_low)  # marketopen
        else:
            self.metric_range_priceperc = 0  # marketopen

        temp = self.df_daily_numpy[-1*l(self.df_daily_numpy, 30):, LOW].min()
        self.metric_range_priceperc30D = (self.daily_close - min(temp, self.daily_low2)) * 100.0 / \
            (max(self.df_daily_numpy[-1*l(self.df_daily_numpy, 30):,
             HIGH].max(), self.daily_high2) - min(temp, self.daily_low2))
        wlow = min(self.daily_low2,
                   self.df_weekly_numpy[max(-52, max_size):, LOW].min())
        whigh = max(self.daily_high2,
                    self.df_weekly_numpy[max(-52, max_size):, HIGH].max())
        self.metric_range_priceperc52Week = (
            self.daily_close - wlow) * 100.0 / (whigh - wlow)
        self.metrtic_range_oneperc = 0.01 * self.daily_close
        if is_marketopen:
            self.metric_range_daylower = 0.25 * \
                (self.daily_high - self.daily_low) + \
                self.daily_low  # marketopen
            self.metric_range_daymiddle = 0.5 * \
                (self.daily_high - self.daily_low) + \
                self.daily_low  # marketopen
            self.metric_range_dayhigh = 0.75 * \
                (self.daily_high - self.daily_low) + \
                self.daily_low  # marketopen
            self.metric_range_percfromopen = (
                self.daily_close - self.daily_open) * 100 / self.daily_open  # marketopen
        else:
            self.metric_range_daylower = 0
            self.metric_range_daymiddle = 0
            self.metric_range_dayhigh = 0
            self.metric_range_percfromopen = 0
        ######################################
        ######################################
        # update_pricechange_metrics
        index = 0
        nw = datetime.datetime.now(tz)
        t1 = self.df_daily_numpy[-1*l(self.df_daily_numpy, (2-index)), CLOSE]
        t2 = self.df_daily_numpy[-1*l(self.df_daily_numpy, (1+7-index)), CLOSE]
        t3 = self.df_daily_numpy[-1 *
                                 l(self.df_daily_numpy, (1+30-index)), CLOSE]
        self.metric_pricechange_day = (self.daily_close - t1) * 100 / t1
        self.metric_pricechange_7days = (self.daily_close - t2) * 100 / t2
        self.metric_pricechange_30days = (self.daily_close - t3) * 100 / t3
        self.metric_50DMA = self.df_daily_numpy[-1 *
                                                l(self.df_daily_numpy, 51):-1, CLOSE].mean()
        self.metric_100DMA = self.df_daily_numpy[-1 *
                                                 l(self.df_daily_numpy, 100):-1, CLOSE].mean()
        ######################################

        # Update Raneg Multiple
        if is_marketopen:
            self.metric_range_multiplier = self.metric_range_price / self.metric_range_price30DMA

        # update liquidity
        SECONDS_PER_TRADING_DAY = 23400
        self.metric_liquidity = self.metric_Vol7DMA / SECONDS_PER_TRADING_DAY * self.price

        # Range Multiple Threshold to turn off Algo 
        if is_marketopen:
            if self.metric_range_multiplier > self.cfg.rangemultiple_threshold:
                self.set_algo(False)

        # The Vwap Pct Column 
        if is_marketopen and self.metric_vwap_price is not None:
            self.metric_vwap_pct = abs(self.metric_vwap_price) * 100.0 / self.metric_range_price7DMA

        if is_marketopen:
            if self.metric_liquidity/1e6 > self.cfg.liquidity_threshold and (self.metric_algo == 1 or self.metric_algo == "1"):
                self.set_algo(True)
            else:
                self.set_algo(False)

        # update 1 day gap 
        if is_marketopen:
            today_open = self.daily_open 
            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
            yesterday = yesterday.date()
            yesterday_close = self.df_daily2[self.df_daily2.index <= str(yesterday)].iloc[-1]['close']
            self.metric_1d_gap = (today_open - yesterday_close) * 100.0 / yesterday_close
            self.metric_1d_gap = round(self.metric_1d_gap, 2)
            if abs(self.metric_1d_gap) > self.metric_range_price30DMA*self.cfg.gap_threshold/100.0:
                self.set_algo(False)

        # sharp movement calculations 
        if is_marketopen:
            last_n_rows = self.df_15secs.tail(4 * self.cfg.sharpmovement_minutes)
            lowest_low = last_n_rows['low'].min()
            highest_high = last_n_rows['high'].max()
            change_percentage = abs(highest_high - lowest_low) / lowest_low * 100
            #logger.error("Sharp Movement: " +  str(self.symbol) + " " + str(change_percentage) + " " + str(self.metric_range_price30DMA) + " " + str(self.cfg.sharpmovement_threshold))
            if (change_percentage/self.metric_range_price30DMA) > (self.cfg.sharpmovement_threshold/100.0):
                #logger.error("Turn Algo Off")
                self.set_algo(False)

        # cancel orders if algo is off
        if self.metric_algo == 0:
            for trade in self.ib.openTrades():
                if trade.contract.symbol == self.symbol:
                    if "cond1" in trade.order.orderRef or "cond2" in trade.order.orderRef or "cond3" in trade.order.orderRef or "cond4" in trade.order.orderRef or "cond5" in trade.order.orderRef:
                        position_open = False
                        for position in self.ib.positions():
                            if position.contract.symbol == self.symbol and position.position != 0 and position.account == trade.order.account:
                                position_open = True 
                        if not position_open:
                            self.ib.cancelOrder(trade.order)
 
        # Wrting to DB
        data = [self.symbol, self.metric_algo, self.price, self.metric_range_multiplier, self.metric_range_price,  self.metric_range_price30DMA,  self.metric_vwap_price, self.metric_vwap_pct, self.metric_range_priceperc,  self.metric_range_price7DMA, self.metric_liquidity, self.metric_7dma_range_multiplier, self.metric_vwap, self.metric_1d_gap, self.metric_range_percfromopen, self.metric_volCurrentTimePerMinuteVsvolCurrentTimePerMinute30DMA, self.metric_range_priceperc30D, self.metric_range_priceperc52Week, self.metric_range_rel52week, self.metrtic_range_oneperc, self.metric_7dchange7drange, self.metric_30dchange30drange, self.metric_range_daylower, self.metric_range_daymiddle, self.metric_range_dayhigh, self.metric_market_open_range_7DMA,
                self.metric_market_open_range_30DMA, self.metric_market_open_change_7DMA, self.metric_market_open_change_30DMA, self.metric_50DMA, self.metric_100DMA, self.metric_PercAbove30DMA, self.metric_Vol15Secsvs30DMA, self.metric_volume_buy_pct_day, self.metric_volume_buy_pct_week, self.metric_volume_buy_pct_month, self.metric_volume_buy_pct_week_avg, self.metric_volume_buy_pct_month_avg, self.metric_Vol7DMA, self.metric_Vol30DMA, self.metric_vol_chg_pct_day, self.metric_vol_chg_pct_week, self.metric_vol_chg_pct_month, self.metric_pricechange_day, self.metric_pricechange_7days, self.metric_pricechange_30days, self.metric_gap_7DMA, self.metric_gap_30DMA]
        
        for i in range(2, len(data)):
            if data[i] == None or math.isnan(data[i]):
                data[i] = 0
            if i == 26:
                data[i] = round(data[i], 2)
            else:
                data[i] = round(data[i], 2)

        if filtered2.shape[0] != 0:
            self.check_alerts()
        end_time = datetime.datetime.now(tz)
        return data

    def update(self, metrics_db, strategy_enabled):
        data = None
        start_time = datetime.datetime.now(tz)
        if self.hasNewBar and self.data_fetch_success and self.before_market_close():
            self.df_15secs['datetime'] = self.df_15secs.index
            self.df_15secs_numpy = self.df_15secs.to_numpy()
            data = self.parallel(metrics_db)

            if self.df_15secs.shape[0] >= 2:
                mdp, _ = self.max_down_perc_opt(1800)
                if self.price != 0:
                    for strategy in self.strategy:
                        # and strategy_enabled[strategy.account_id]:
                        if self.price != 0:
                            self.update_strategy(
                                self.price, strategy, mdp, strategy_enabled[strategy.account_id])

            self.hasNewBar = False
        if not self.data_fetch_success:
            # print("fetch data")
            self.data_fetch_success = self.get_15secs_bars()
        return data

    def max_up_perc_opt(self, max_secs):
        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=9, minute=30, second=0, tzinfo=tz)
        first_valid_index = -1
        for i in range(self.df_15secs_numpy.shape[0]):
            diff_secs = (pd.to_datetime(self.df_15secs_numpy[-1, -1]) - pd.to_datetime(
                self.df_15secs_numpy[-1-i, -1])).total_seconds()
            if diff_secs <= max_secs and pd.to_datetime(self.df_15secs_numpy[-1-i, -1]) >= todayMarketOpen:
                first_valid_index = self.df_15secs_numpy.shape[0] - i
            else:
                break
        if first_valid_index == -1:
            return 0, 0
        max_up = 0
        index = 0
        for i in range(first_valid_index+1, self.df_15secs_numpy.shape[0]):
            diff_perc = (self.df_15secs_numpy[i, HIGH] - self.df_15secs_numpy[first_valid_index:i, LOW].min(
            )) * 100 / self.df_15secs_numpy[first_valid_index:i, LOW].min()
            if diff_perc > max_up:
                index = i
            max_up = max(max_up, diff_perc)
        return max_up, index

    def max_down_perc_opt(self, max_secs):
        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=9, minute=30, second=0, tzinfo=tz)
        first_valid_index = -1
        for i in range(self.df_15secs_numpy.shape[0]):
            diff_secs = (pd.to_datetime(self.df_15secs_numpy[-1, -1]) - pd.to_datetime(
                self.df_15secs_numpy[-1-i, -1])).total_seconds()
            if diff_secs <= max_secs and pd.to_datetime(self.df_15secs_numpy[-1-i, -1]) >= todayMarketOpen:
                first_valid_index = self.df_15secs_numpy.shape[0] - i
            else:
                break
        if first_valid_index == -1:
            return 0, 0
        max_down = 9999
        index = 0
        for i in range(first_valid_index+1, self.df_15secs_numpy.shape[0]):
            diff_perc = (self.df_15secs_numpy[i, LOW] - self.df_15secs_numpy[first_valid_index:i, HIGH].max(
            )) * 100 / self.df_15secs_numpy[first_valid_index:i, HIGH].max()
            if diff_perc < max_down:
                index = i
            max_down = min(max_down, diff_perc)
        return max_down, index

    def after_market_open(self):
        nw = datetime.datetime.now(tz)
        todayMarketOpen = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=9, minute=30, second=0, tzinfo=tz)
        now = datetime.datetime(year=nw.year, month=nw.month, day=nw.day,
                                hour=nw.hour, minute=nw.minute, second=nw.second, tzinfo=tz)
        return ((now - todayMarketOpen).total_seconds() > 30)

    def before_market_close(self):
        nw = datetime.datetime.now(tz)
        todayMarketClose = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=15, minute=59, second=0, tzinfo=tz)
        now = datetime.datetime(year=nw.year, month=nw.month, day=nw.day,
                                hour=nw.hour, minute=nw.minute, second=nw.second, tzinfo=tz)
        return ((now - todayMarketClose).total_seconds() < 0)


    def bmc(self):
        nw = datetime.datetime.now(tz)
        todayMarketClose = datetime.datetime(
            year=nw.year, month=nw.month, day=nw.day, hour=15, minute=59, second=59, tzinfo=tz)
        now = datetime.datetime(year=nw.year, month=nw.month, day=nw.day,
                                hour=nw.hour, minute=nw.minute, second=nw.second)
        return ((now - todayMarketClose).total_seconds() < 0)

    def send_alert(self, msg, subj=""):
        if subj == "":
            subj = msg
        client_alert.send(msg+"&&&"+subj)


class IbApp():
    def __init__(self):
        self.daily_pnls_dollar = {}
        self.daily_pnls_percent = {}
        self.disable_target_pnl_reached = []
        
        # Clear old Data
        if sys.platform == "linux" or sys.platform == "linux2":
            self.clearFolder()
        self.last_update_time = datetime.datetime.now()
        self.last_reload_time = datetime.datetime(2000, 1, 1, tzinfo=tz)
        self.ib = IB()
        self.start_day = datetime.datetime.now(tz).day
        self.symbols = []
        self.last_update_meta = datetime.datetime(
            year=2000, month=1, day=1, tzinfo=tz)
        self.last_cfg_update_time = 0
        try:
            os.remove(p + "/c.dat")
        except OSError:
            pass

        self.create_data_db()

        self.cfg = StrategyCfg(self.ib)
        self.initialize_meta()

        self.closed = False
        self.closed_notification = False

        self.ib.setTimeout(1000)
        self.ib.connect(self.address, self.port, self.client_id)
        self.ib.execDetailsEvent += self.execDetails
        self.ib.orderStatusEvent += self.orderStatusChange
        self.last_trail_update = datetime.datetime.now(tz)
        self.target_pnl_reached = {}
        self.accounts_target_pnl_blacklist = []
        self.subscribeToPNL()
        self.update_symbols_data()
        
    def subscribeToPNL(self):
        for i in range(len(self.cfg.values)):
            if "Account" in self.cfg.values[i][0] or "Accound" in self.cfg.values[i][0]:
                account_id = self.cfg.values[i][1]
                self.ib.reqPnL(account_id, "")

    def clearFolder(self):
        for folder in os.listdir("./data"):
            today = str(datetime.date.today())
            folder_path = "./data/"+folder
            try:
                today_date = list(map(int, today.split("-")))
                folder_date = list(map(int, folder.split("-")))
                if today_date != folder_date:
                    try:
                        shutil.rmtree(folder_path)
                    except:
                        continue
            except:
                continue

    def orderStatusChange(self, trade):
        if self.cfg.pauseAlgo == 1:
            return

        if trade.orderStatus.status == "Cancelled" or trade.orderStatus.status == "Filled":
            for open_trade in self.ib.openTrades():
                if open_trade.order.orderRef == trade.order.orderRef and open_trade.order.account == trade.order.account and open_trade.order.orderRef != "eod" and open_trade.order.orderRef != "targetprofit":
                    self.ib.cancelOrder(open_trade.order)


    def update_strategy_timeexecution(self, trade):
        for s in self.symbols:
            for strategy in s.strategy:
                if strategy.account_id == trade.order.account and strategy.symbol == trade.contract.symbol:
                    s.setTimeCancelOrder(trade.order.orderRef , strategy)

    def execDetails(self, trade, fill):
        symbol = fill.contract.symbol
        fill_price = fill.execution.price
        side = fill.execution.side
        size = fill.execution.shares
        avg_price = fill.execution.avgPrice

        for s in self.symbols:
            for strategy in s.strategy:
                if strategy.account_id == trade.order.account:
                    order_ref = trade.order.orderRef
                    # update last execution time
                    if "cond1" in order_ref:
                        strategy.last_execution_date_c1 = datetime.datetime.now(tz)
                    if "cond2" in order_ref:
                        strategy.last_execution_date_c2 = datetime.datetime.now(tz)
                    if "cond3" in order_ref:
                        strategy.last_execution_date_c3 = datetime.datetime.now(tz)
                    if "cond4" in order_ref:
                        strategy.last_execution_date_c4 = datetime.datetime.now(tz)
                    if "cond5" in order_ref:
                        strategy.last_execution_date_c5 = datetime.datetime.now(tz)
                    strategy.last_execution_date_symbol = datetime.datetime.now(tz)
        
        if self.cfg.pauseAlgo == 1 or "eod" in trade.order.orderRef or "targetprofit" in trade.order.orderRef:
            return

        for s in self.symbols:
            if s.symbol == symbol:
                if "Buy" in trade.order.orderRef or "Short" in trade.order.orderRef:
                    for strategy in s.strategy:
                        if strategy.account_id == trade.order.account:
                            positions = self.ib.positions(
                                account=trade.order.account)

                            for position in positions:
                                if position.contract.symbol == symbol:
                                    avg_price = position.avgCost

                            if "cond4" in trade.order.orderRef or "cond5" in trade.order.orderRef:
                                strategy.send_sl_tp_short(
                                    avg_price, size, trade.order.orderRef)
                            else:
                                strategy.send_sl_tp(
                                    avg_price, size, trade.order.orderRef)
                            shares_to_sell = int(
                                abs(fill.execution.cumQty) * (strategy.cfg.sharestosell/100))

                            if trade.order.totalQuantity == abs(fill.execution.cumQty):
                                strategy.trade_start_time = datetime.datetime.now(
                                    tz)
                                strategy.trade_start_time_actionx = False
                                strategy.trade_start_time_actiony = False
                                strategy.avgp = avg_price

                                cond = trade.order.orderRef.split("-")[1]
                                take_profit_price = strategy.tp
                                stop_loss_price = strategy.sl
                                c_subj = ""
                                c_message = ""
                                profit = strategy.cfg.profittakeC1
                                if cond == "cond1":
                                    c_subj = "C1"
                                    c_message = "Condition 1"
                                    profit = strategy.cfg.profittakeC1
                                if cond == "cond2":
                                    c_subj = "C2"
                                    c_message = "Condition 2"
                                    profit = strategy.cfg.profittakeC2
                                if cond == "cond3":
                                    c_subj = "C3"
                                    c_message = "Condition 3"
                                    profit = strategy.cfg.profittakeC3
                                if cond == "cond4":
                                    c_subj = "C4"
                                    c_message = "Condition 4"
                                    profit = strategy.cfg.profittakeC4
                                if cond == "cond5":
                                    c_subj = "C5"
                                    c_message = "Condition 5"
                                    profit = strategy.cfg.profittakeC5

                                position_equity_amount = abs(
                                    round(fill.execution.cumQty * avg_price, 2))
                                profit_dollar = round(
                                    shares_to_sell * abs(avg_price - take_profit_price), 2)
                                loss_dollar = round(
                                    shares_to_sell * abs(avg_price - stop_loss_price), 2)
                                profit_pct = round(
                                    (profit_dollar * 100 / position_equity_amount), 2)
                                loss_pct = round(
                                    (loss_dollar * 100 / position_equity_amount), 2)

                                # Send Notification Message
                                subject = "Buy Order Filled: " + strategy.symbol + \
                                    " " + c_subj + " " + \
                                    str(strategy.account_id)
                                if cond == "cond4" or cond == "cond5":
                                    subject = "Sell Order Filled: " + strategy.symbol + \
                                        " " + c_subj + " " + \
                                        str(strategy.account_id)
                                message = c_message + "\n"
                                message += "Price: " + \
                                    str(round(avg_price, 2)) + "\n"
                                message += "Shares: " + \
                                    str(abs(fill.execution.cumQty)) + "\n"
                                message += "Profit: $" + \
                                    str(profit_dollar) + "\n"
                                message += "Profit %: " + \
                                    str(profit_pct) + "%\n"
                                message += "Profit Take Price: $" + \
                                    str(take_profit_price) + "\n"
                                message += "Loss: $" + str(loss_dollar) + "\n"
                                message += "Loss %: " + str(loss_pct) + "%\n"
                                message += "Stop Loss Price: $" + \
                                    str(stop_loss_price) + "\n"
                                message += "Shares to be sold: " + \
                                    str(shares_to_sell) + "\n"
                                message += "Position Equity Amount: $" + \
                                    str(position_equity_amount) + "\n"
                                message += "VWAP PCT: " + str(int(strategy.s.metric_vwap_pct)) + "\n"
                                if trade.order.orderRef != "targetprofit":
                                    strategy.s.send_alert(
                                        msg=message, subj=subject)
                                #logger.error(subject + " " + message)

                else:
                    for strategy in s.strategy:
                        if strategy.account_id == trade.order.account:
                            if abs(strategy.qty) == abs(fill.execution.cumQty):
                                strategy.trade_start_time = None
                                subject = ""
                                order_ref = trade.order.orderRef
                                

                                if "TP" in order_ref.split("-")[0]:
                                    subject = "Profit Take Filled: " + \
                                        strategy.symbol + " " + \
                                        str(strategy.account_id)
                                if "SL" in order_ref.split("-")[0]:
                                    subject = "Stop Loss Filled: " + \
                                        strategy.symbol + " " + \
                                        str(strategy.account_id)

                                message = "Price: $" + \
                                    str(round(avg_price, 2)) + "\n"
                                message += "Shares Closed: " + \
                                    str(fill.execution.cumQty) + "\n"

                                pnl = round(
                                    abs(fill.execution.cumQty * avg_price - fill.execution.cumQty * strategy.avgp), 2)
                                pct = round(
                                    pnl * 100.0 / (fill.execution.cumQty * strategy.avgp), 2)

                                if "TP" in order_ref.split("-")[0]:
                                    message += "Profit: $" + str(pnl) + "\n"
                                    message += "Profit %: " + str(pct) + "%\n"
                                if "SL" in order_ref.split("-")[0]:
                                    message += "Loss: $" + str(pnl) + "\n"
                                    message += "Loss %: " + str(pct) + "%\n"
                                if trade.order.orderRef != "targetprofit":
                                    strategy.s.send_alert(
                                        msg=message, subj=subject)
                                #logger.error(subject + " " + message)

    def stop(self):
        if os.path.isfile(p + "/c.dat"):
            os.remove(p + "/c.dat")
            client_alert.send("stop")
            return True
        else:
            return False

    def initialize_meta(self):
        time.sleep(5)
        while not self.stop():
            if os.path.isfile(p + "/meta.db"):
                self.conn_meta = sqlite3.connect(p + '/meta.db')
                self.cur_meta = self.conn_meta.cursor()
                self.cur_meta.execute("SELECT * FROM METADATA")
                row = self.cur_meta.fetchall()[0]
                self.address = row[0]
                self.port = row[1]
                self.client_id = row[2]
                self.email = row[3]
                self.symbols_string = row[4].split(",")
                return
            else:
                time.sleep(1)
        sys.exit(0)

    def reload_cfg(self):
        nw = datetime.datetime.now(tz)
        if (nw - self.last_reload_time).seconds < 2:
            return
        self.cfg.load_data()
        for symbol in self.symbols:
            symbol.cfg = self.cfg
            for strategy in symbol.strategy:
                strategy.cfg = self.cfg

        for i in range(len(self.cfg.values)):
            if "Account" in self.cfg.values[i][0] or "Accound" in self.cfg.values[i][0]:
                account_id = self.cfg.values[i][1]
                cash_pct = float(self.cfg.values[i+1][1])
                for symbol in self.symbols:
                    for strategy in symbol.strategy:
                        if account_id == strategy.account_id:
                            strategy.cash_pct = cash_pct
        self.last_reload_time = datetime.datetime.now(tz)

    def update_meta(self):
        if (datetime.datetime.now(tz) - self.last_update_meta).total_seconds() < 1:
            return
        try:
            self.cur_meta.execute("SELECT * FROM METADATA")
        except:
            return
        row = self.cur_meta.fetchall()[0]
        self.address = row[0]
        self.port = row[1]
        self.client_id = row[2]
        self.email = row[3]
        self.symbols_string = row[4].split(",")
        self.algo = row[5].split(",")

        try:
            if self.email != "":
                client_alert.send("email:"+str(self.email))
        except:
            print("Error update mail")

        try:
            self.reload_cfg()
        except:
            pass

        for i, elem in enumerate(self.symbols_string):
            elemIsNew = True
            for symbol in self.symbols:
                if elem == symbol.symbol:
                    elemIsNew = False
            if elemIsNew:
                self.add_symbol(elem, self.algo[i])

        self.delete_symbols()

        self.last_update_meta = datetime.datetime.now(tz)

    def delete_symbols(self):
        for i, symbol in enumerate(self.symbols):
            if symbol.symbol not in self.symbols_string:
                print("delete", symbol.symbol)
                self.symbols[i].cancel()
                del self.symbols[i]
                self.delete_symbols()

    def add_symbol(self, symbol, algo):
        print("IB: Add", symbol)
        try:
            self.symbols.append(
                Symbol(self.ib, symbol, self.email, self.cfg, algo, len(self.symbols), self))
        except Exception as e:
            logger.error(f"Error adding symbol {symbol}: {str(e)}")
            self.ib.sleep(1)

    def update_trail(self):
        nw = datetime.datetime.now(tz)
        if self.closed or self.cfg.pauseAlgo == 1 or (nw-self.last_trail_update).total_seconds() < 15:
            return
        for trade in self.ib.openTrades():
            if "Buy" in trade.order.orderRef:
                for symbol in self.symbols:
                    for strategy in symbol.strategy:
                        if "orderStatus" in dir(trade):
                            if strategy.account_id == trade.order.account and symbol.symbol == trade.contract.symbol and trade.orderStatus.status != "PreSubmitted":
                                condRef = trade.order.orderRef.split("-")[1]
                                symbolRef = trade.order.orderRef.split("-")[2]
                                nominal_range = symbol.daily_high - symbol.daily_low
                                if (condRef == "cond1" or condRef == "cond2") and strategy.cond12_price != None:
                                    if symbol.price < strategy.cond12_price:
                                        strategy.cond12_price = symbol.price
                                        trade.order.auxPrice = round(
                                            (self.cfg.param4 / 100) * nominal_range, 2)
                                        trade.order.trailStopPrice = round(
                                            symbol.price + (self.cfg.param4 / 100) * nominal_range, 2)
                                        trade.order.lmtPriceOffset = round(
                                            (self.cfg.offsetpct/100.0 * trade.order.trailStopPrice), 2)
                                        self.ib.placeOrder(
                                            trade.contract, trade.order)
                                        self.last_trail_update = datetime.datetime.now(
                                            tz)
                                elif condRef == "cond3" and strategy.cond3_price != None:
                                    if symbol.price < strategy.cond3_price:
                                        strategy.cond3_price = symbol.price
                                        trade.order.trailStopPrice = round(
                                            symbol.price + (self.cfg.param5 / 100) * symbol.price, 2)
                                        trade.order.auxPrice = round(
                                            (self.cfg.param5 / 100) * symbol.price, 2)
                                        trade.order.lmtPriceOffset = round(
                                            (self.cfg.offsetpct/100.0 * trade.order.trailStopPrice), 2)
                                        self.ib.placeOrder(
                                            trade.contract, trade.order)
                                        self.last_trail_update = datetime.datetime.now(
                                            tz)

    def close_all_positions(self):
        if self.closed or self.cfg.pauseAlgo == 1:
            return
        nw = datetime.datetime.now(tz)

        if datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=nw.hour, minute=nw.minute, second=nw.second, microsecond=0, tzinfo=tz) >= datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=15, minute=59, second=00, microsecond=0, tzinfo=tz) and datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=nw.hour, minute=nw.minute, second=nw.second, microsecond=0, tzinfo=tz) <= datetime.datetime(year=nw.year, month=nw.month, day=nw.day, hour=15, minute=59, second=59, microsecond=0, tzinfo=tz):
            # Cancel Related Orders
            for trade in self.ib.openTrades():
                if trade.order.orderRef != "eod":
                    for symbol in self.symbols:
                        for strategy in symbol.strategy:
                            if strategy.account_id == trade.order.account and symbol.symbol == trade.contract.symbol and trade.contract.symbol not in self.cfg.eod_exceptions:
                                self.ib.cancelOrder(trade.order)

            if len(self.ib.positions()) > 0:
                for position in self.ib.positions():
                    for symbol in self.symbols:
                        for strategy in symbol.strategy:
                            if strategy.account_id == position.account and symbol.symbol == position.contract.symbol and position.contract.symbol not in self.cfg.eod_exceptions:
                                contract = None
                                if symbol == "ES" or symbol == "NQ":
                                    contract = Contract(
                                        symbol=position.contract.symbol, secType='CONTFUT', exchange='GLOBEX', currency='USD', includeExpired=True)
                                else:
                                    contract = Stock(
                                        position.contract.symbol, 'SMART', 'USD')
                                contract = self.ib.qualifyContracts(contract)[
                                    0]
                                order = None
                                if position.position > 0:
                                    order = MarketOrder(
                                        'SELL', position.position)
                                else:
                                    order = MarketOrder(
                                        'BUY', abs(position.position))
                                order.account = position.account
                                order.orderRef = "eod"
                                self.ib.placeOrder(contract, order)

                                last_price = float(
                                    symbol.df_15secs["close"][-1])
                                size = abs(float(position.position))
                                avgCost = float(position.avgCost)
                                pnl = 0
                                if position.position > 0:
                                    pnl = size * (last_price - avgCost)
                                else:
                                    pnl = size * (avgCost - last_price)
                                subject = "Position Closed: " + \
                                    str(symbol.symbol) + " " + \
                                    str(order.account)
                                message = "Price: " + \
                                    str(round(last_price, 2)) + "\n"
                                if position.position > 0:
                                    message += "Shares Sold: " + \
                                        str(size) + "\n"
                                else:
                                    message += "Shares Bought: " + \
                                        str(size) + "\n"
                                if pnl > 0:
                                    message += "Profit: $" + \
                                        str(round(pnl, 2)) + "\n"
                                    message += "Profit %: " + \
                                        str(round(abs(pnl)*100 /
                                            (avgCost*size), 2)) + "%\n"
                                else:
                                    message += "Loss: $" + \
                                        str(abs(round(pnl, 2))) + "\n"
                                    message += "Loss %: " + \
                                        str(round(abs(pnl)*100 /
                                            (avgCost*size), 2)) + "%\n"
                                symbol.send_alert(message, subject)
                                #logger.error(subject + " " + message)
            self.closed = True

    def update_cfg(self):
        self.reload_cfg()

    def create_data_db(self):
        try:
            os.remove(p + "/data.db")
        except OSError:
            pass

        self.metrics_db = sqlite3.connect(
            p+'/data.db', check_same_thread=False)

        self.metrics_db.execute('''CREATE TABLE DATA
                (Symbol TEXT PRIMARY KEY,
                a TEXT,
                b TEXT,
                c TEXT,
                d TEXT,
                e TEXT,
                f TEXT,
                g TEXT,
                h TEXT,
                i TEXT,
                j TEXT,
                k TEXT,
                l TEXT,
                m TEXT,
                n TEXT,
                o TEXT,
                p TEXT,
                q TEXT,
                r TEXT,
                s TEXT,
                t TEXT,
                u TEXT,
                v Text,
                w TEXT, 
                x TEXT,
                y TEXT,
                z TEXT, 
                aa TEXT,
                bb TEXT,
                cc TEXT,
                dd TEXT,
                ee TEXT,
                ff TEXT,
                hh TEXT,
                gg TEXT,
                ii TEXT,
                jj TEXT,
                kk TEXT,
                ll TEXT,
                mm TEXT, nn TEXT, oo TEXT, qq TEXT, rr TEXT, ss TEXT, tt TEXT, uu TEXT, abcde TEXT, abc TEXT) ;''')
        self.metrics_db.commit()

    def reset(self):
        nw = datetime.datetime.now(tz)
        if self.start_day != nw.day:
            self.start_day = nw.day
            for symbol in self.symbols:
                symbol.cancel()
            self.symbols = []
            self.closed = False
            self.closed_notification = False

    def update_trade_time_actions(self):
        try:
            if self.cfg.allow_actions:
                for trade in self.ib.openTrades():
                    for symbol in self.symbols:
                        for strategy in symbol.strategy:
                            if symbol.df_15secs.shape[0] > 2 and symbol.after_market_open() and symbol.before_market_close():
                                if strategy.account_id == trade.order.account and symbol.symbol == trade.contract.symbol:
                                    last_price = symbol.df_15secs_numpy[-1, CLOSE]
                                    strategy.trade_time_action(last_price)
        except:
            pass

    def get_daily_pnl(self, account):
        pnL = self.ib.pnl(account, "")
        try:
            if np.isnan(pnL[0].dailyPnL):
                return 0
            else:
                return float(pnL[0].dailyPnL)
        except:
            return 0

    def get_is_strategy_enabled_dict(self):
        strategy_enabled = {}
        accounts_values = self.ib.accountSummary()
        nw = datetime.datetime.now(tz)
        algo_off_before_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_before.split(":")[0]), int(self.cfg.algo_off_before.split(":")[1]), tzinfo=tz)
        algo_off_after_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_after.split(":")[0]), int(self.cfg.algo_off_after.split(":")[1]), tzinfo=tz)
        strategy_enabled_time_condition = nw >= algo_off_before_time and nw <= algo_off_after_time
        current_account = ""
        for account_value in accounts_values:
            if account_value.tag == "NetLiquidation":
                current_account = account_value.account
                if "DF" in current_account:
                    continue
                net_liq = float(account_value.value)
                if current_account not in self.target_pnl_reached.keys():
                    daily_pnl = self.get_daily_pnl(current_account)
                    self.daily_pnls_dollar[current_account] = round(daily_pnl, 2)
                    self.daily_pnls_percent[current_account] = round(daily_pnl * 100/net_liq, 2)
                    strategy_enabled[current_account] = strategy_enabled_time_condition and daily_pnl * \
                        100/net_liq < self.cfg.max_daily_pnl
                    self.target_pnl_reached[current_account] = daily_pnl * \
                        100/net_liq >= self.cfg.max_daily_pnl
                    #logger.error(str(current_account) + " daily_pnl(1): " + str(daily_pnl) + " " + str(strategy_enabled[current_account]) + " " + str(self.target_pnl_reached[current_account]) + " " + str(self.cfg.max_daily_pnl) + " " + str(net_liq))
                else:
                    if self.target_pnl_reached[current_account] == False:
                        daily_pnl = self.get_daily_pnl(current_account)
                        self.daily_pnls_dollar[current_account] = round(daily_pnl, 2)
                        self.daily_pnls_percent[current_account] = round(daily_pnl * 100/net_liq, 2)
                        strategy_enabled[current_account] = strategy_enabled_time_condition and daily_pnl * \
                            100/net_liq < self.cfg.max_daily_pnl
                        self.target_pnl_reached[current_account] = daily_pnl * \
                            100/net_liq >= self.cfg.max_daily_pnl
                        #logger.error(str(current_account) + " daily_pnl(2): " + str(daily_pnl) + " " + str(strategy_enabled[current_account]) + " " + str(self.target_pnl_reached[current_account]) + " " + str(self.cfg.max_daily_pnl) + " " + str(net_liq))
                    else:
                        strategy_enabled[current_account] = False
        return strategy_enabled
    
    def handle_open_orders_positions_after_algo_off(self, strategy_enabled):
        nw = datetime.datetime.now()
        if (nw - self.last_update_time).seconds < 1:
            return 
        #logger.error("handle_open_orders_positions_after_algo_off")
        self.last_update_time = nw 
        nw = datetime.datetime.now(tz)
        algo_off_before_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_before.split(":")[0]), int(self.cfg.algo_off_before.split(":")[1]), tzinfo=tz)
        algo_off_after_time = datetime.datetime(nw.year, nw.month, nw.day, int(
            self.cfg.algo_off_after.split(":")[0]), int(self.cfg.algo_off_after.split(":")[1]), tzinfo=tz)
        strategy_enabled_time_condition = nw >= algo_off_before_time and nw <= algo_off_after_time
        for account, enabled in strategy_enabled.items():
            if enabled == False:
                for trade in self.ib.openTrades():
                    if trade.order.account == account and "-TP" not in trade.order.orderRef and "TP-" not in trade.order.orderRef and "-SL" not in trade.order.orderRef and "SL-" not in trade.order.orderRef and "eod" not in trade.order.orderRef and "targetprofit" not in trade.order.orderRef:
                        if strategy_enabled_time_condition and account in self.disable_target_pnl_reached:
                            continue
                        self.ib.cancelOrder(trade.order)
                        self.update_strategy_timeexecution(trade)
                        self.ib.sleep(0.1)
            self.ib.sleep(0.2)
            if account in self.target_pnl_reached:
                if self.target_pnl_reached[account]:
                    # Check if account is in blacklist
                    if account in self.accounts_target_pnl_blacklist:
                        continue
                    self.accounts_target_pnl_blacklist.append(account)
                    if strategy_enabled_time_condition and account in self.disable_target_pnl_reached:
                            continue
                    #logger.error("Target PnL Reached "  + str(account))
                    for trade in self.ib.openTrades():
                        if trade.order.account == account and "eod" not in trade.order.orderRef and "targetprofit" not in trade.order.orderRef:
                            #logger.error(" cancelling order 11")
                            self.ib.cancelOrder(trade.order)
                            self.update_strategy_timeexecution(trade)

                    self.ib.sleep(3)
      
                    email_alert = ""
                    email_alert += f"Profit/Loss percentage: {self.daily_pnls_percent[account]}%\n"
                    email_alert += f"PnL: ${self.daily_pnls_dollar[account]}\n"
                    send_alert(email_alert, f"TARGET PROFIT REACHED {account}")
                    if len(self.ib.positions()) > 0:
                        for position in self.ib.positions():
                            if position.account == account:
                                logger.error(f"closing: {position.contract.symbol} {position.position}")
                                if position.position > 0:
                                    order = MarketOrder('SELL', position.position)
                                else:
                                    order = MarketOrder('BUY', abs(position.position))
                                order.account = position.account
                                order.orderRef = "targetprofit"
                                contract = Stock(
                                    position.contract.symbol, 'SMART', 'USD')
                                contract = self.ib.qualifyContracts(contract)[0]
                                self.ib.placeOrder(contract, order)
                                price = 0
                                for symbol in self.symbols:
                                    if symbol.symbol == position.contract.symbol:
                                        price = symbol.df_15secs_numpy[-1, CLOSE]
                                pnl = round(price * position.position - position.avgCost * position.position, 2)
                                pnl_pct = round(pnl * 100 / abs(position.avgCost * position.position), 2)
                                email_alert = (f"closing: {position.contract.symbol}\nShares: {position.position}\nPrice: {price}\nPnL: ${pnl}\nProfit/Loss percentage: {pnl_pct}%\n")
                                send_alert(email_alert, f"{contract.symbol} Position Closed, PnL Target Hit {account}")

    def no_data_update(self):
        index = 0
        strategy_enabled = self.get_is_strategy_enabled_dict()
        for symbol in self.symbols:
            data = symbol.update(self.metrics_db, strategy_enabled)

            index += 1
            if data != None:
                if data[2] != symbol.last_update_price and index == 1 and symbol.after_market_open() and symbol.before_market_close():
                    symbol.last_update_price = data[2]
                    symbol.last_update_price_time = datetime.datetime.now(tz)
                    symbol.send_email_msg = False

                try:
                    self.metrics_db.execute(
                        "INSERT INTO DATA (a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,aa,bb,cc,dd,ee,ff,hh,gg,ii,jj,kk,ll,mm,nn,oo,qq,rr,ss,tt,uu,abcde,abc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", data)
                except:
                    pass


    def global_vwap_reset(self):
        open_trades = self.ib.openTrades()
        for symbol in self.symbols:
            for strategy in symbol.strategy:
                strategy.vwap_reset(symbol.metric_vwap_price, symbol.metric_range_price7DMA, open_trades)


    def update_symbols_data(self):

        while not self.stop():
            current_time = datetime.datetime.now(tz)
            if current_time.hour >= 16 or current_time.hour <= 0:
                self.ib.sleep(60)
                continue
            self.no_data_update()
            self.update_meta()
            self.close_all_positions()
            self.update_trail()
            self.update_trade_time_actions()
            strategy_enabled = self.get_is_strategy_enabled_dict()
            self.handle_open_orders_positions_after_algo_off(strategy_enabled)
            self.global_vwap_reset()

            try:
                zac_sheet_data = zac_sheet.get_data()
                for i, elem in enumerate(self.symbols_string):
                    for symbol in self.symbols:
                        if elem == symbol.symbol:
                            if zac_sheet_data != None:
                                if symbol.symbol in zac_sheet_data:
                                    symbol.set_algo(zac_sheet_data[symbol.symbol])
                            break
            except:
                pass
            try:
                self.metrics_db.commit()
            except:
                pass
            self.ib.sleep(0.2)

def is_weekday():
    today = datetime.datetime.today().weekday()
    return today < 5

def start():
    try:
        print("Start")
        while not is_weekday():
            time.sleep(5)
        app = IbApp()
    except Exception as ex:
        print(ex)
        global client_alert
        config = configparser.ConfigParser()
        config.read(p + '/cfg.ini')
        trace = []
        tb = ex.__traceback__
        while tb is not None:
            trace.append({
                "filename": tb.tb_frame.f_code.co_filename,
                "name": tb.tb_frame.f_code.co_name,
                "lineno": tb.tb_lineno
            })
            tb = tb.tb_next
        print(str({
            'type': type(ex).__name__,
            'message': str(ex),
            'trace': trace
        }))
        logger.error(str({
            'type': type(ex).__name__,
            'message': str(ex),
            'trace': trace
        }))
        client_alert.send(str(ex) + " &&& System Error")
        time.sleep(10)
        restart_program()


if __name__ == "__main__":
    start()