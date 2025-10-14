from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1QbsKKgNsvIExFVK5FEhvaBi1WThw8MDVdFY9P3ey6L0'
SAMPLE_RANGE_NAME = 'A1:B300'

import configparser

p = os.path.dirname(os.path.realpath(__file__))


class StrategyCfg():
    def __init__(self):
        config = configparser.ConfigParser()
        config.read(p + '/cfg.ini') 
        self.sheet_id = config.get("General", "Sheet_ID")

        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        try:
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.sheet_id,
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
            self.sameConditionTimeC1 = float(values[18][1])
            self.sameConditionTimeC2 = float(values[19][1])
            self.sameConditionTimeC3 = float(values[20][1])
            self.sameConditionTimeC4 = float(values[21][1])
            self.sameConditionTimeC5 = float(values[22][1])
            self.pauseAlgo = float(values[23][1])
            self.automaticBuyC1 = float(values[24][1])
            self.automaticBuyC2 = float(values[25][1])
            self.automaticBuyC3 = float(values[26][1])
            self.automaticBuyC4 = float(values[27][1])
            self.automaticBuyC5 = float(values[28][1])
            self.automaticSellC1 = float(values[29][1])
            self.automaticSellC2 = float(values[30][1])
            self.automaticSellC3 = float(values[31][1])
            self.automaticSellC4 = float(values[32][1])
            self.automaticSellC5 = float(values[33][1])
            self.StopLossUpdate = float(values[34][1])
            self.stopLossXC1 = float(values[35][1])
            self.stopLossYC1 = float(values[36][1])
            self.stopLossXC2 = float(values[37][1])
            self.stopLossYC2 = float(values[38][1])
            self.stopLossXC3 = float(values[39][1])
            self.stopLossYC3 = float(values[40][1])
            self.stopLossXC4 = float(values[41][1])
            self.stopLossYC4 = float(values[42][1])
            self.stopLossXC5 = float(values[43][1])
            self.stopLossYC5 = float(values[44][1])
            self.alertPCT1 = float(values[45][1])
            self.alertMin1 = float(values[46][1])
            self.alertPCT2 = float(values[47][1])
            self.alertMin2 = float(values[48][1])
            self.alertPriceVwapDiff = float(values[49][1])
            self.maxCapitalPct = float(values[50][1])
            self.vwap_pct = float(values[51][1])
            self.rally_x_min_pct = float(values[52][1])
            self.rally_x_max_pct = float(values[53][1])
            self.rally_y_pct = float(values[54][1])
            self.eod_exceptions = (values[55][1]).split(",")
        except HttpError as err:
            print(err)  





        



def reload_cfg(self):
    print("reload cfg")
    self.cfg = StrategyCfg()
    for symbol in self.symbols:
        symbol.cfg = self.cfg
        for strategy in symbol.strategy:
            strategy.cfg = self.cfg


    config = configparser.ConfigParser()
    config.read(p + "/cfg.ini")

    for i in range(len(config.values)):
        if "Account" in config.values[i][0]:
            account_id = config.values[i][1]
            cash_pct = config.values[i+1][1]
            print(account_id, cash_pct)
            for symbol in self.symbols:
                for strategy in symbol.strategy:
                    if account_id == strategy.account_id:
                        strategy.cash_pct = cash_pct


if __name__ == '__main__':
    #main()
    reload_cfg()