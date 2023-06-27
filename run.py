#!/usr/bin/env python3
import asyncio
import logging
import os

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from metaapi_cloud_sdk import MetaApi
from prettytable import PrettyTable
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, ConversationHandler, CallbackContext

from telethon import TelegramClient, events
from cleantext import clean

# Valeurs issues de my.telegram.org
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
PHONE = os.environ.get("PHONE")
PASSWORD = os.environ.get("PASSWORD")

NAME_CHANNEL_SOURCE = os.environ.get("NAME_CHANNEL_SOURCE") #Channel Test Python
BOT_CHANNEL_SOURCE = os.environ.get("BOT_CHANNEL_SOURCE") #Canal test CodeTGMT4

client = TelegramClient('Service', API_ID, API_HASH)

SYMBOLES = (
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
    'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
    'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAGUSD', 'XAUUSD', 'DAX40', 'DJ30', 'US30', 'ETHUSD', 'BTCUSD')
SYMBOLES_FXLIFT = (
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
    'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
    'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAGUSD', 'XAUUSD', 'GER40_U3', 'US30Cash', 'US30Cash', 'ETHUSD', 'BTCUSD')
MULTIPLIER = (
    '0,0001', '0,0001', '0,01', '0,0001', '0,0001', '0,0001', '0,01', '0,01', '0,0001', '0,0001', '0,0001', '0,0001',
    '0,01', '0,0001', '0,0001', '0,0001', '0,0001', '0,0001', '0,01', '0,0001', '0,0001', '0,0001', '0,0001', '0,01',
    '0,0001', '0,0001', '0,0001', '0,01', '0,01', '0,01', '1', '1', '1', '1', '1')
# ^ Sur une paire de devises à 5 décimales, un pip est de 0,0001
# | Sur une paire de devises à 3 décimales, un pip est de 0,01
# | Sur une paire de devises à 2 décimales, un pip est de 0,1

InfoTrade = {}
client.start(phone=PHONE,password=PASSWORD,code_callback=None)


@client.on(events.NewMessage(chats=NAME_CHANNEL_SOURCE))
async def message_handler(event):
    message = event.message.text
    message = clean(message, no_emoji=True,lower=False)
    message = message.splitlines()
    message = [line.rstrip() for line in message] # ['alerte', "j'achete le gold (xauusd) a 1936", 'stop loss : 1926', 'take profit 1 : 1945', 'take profit 2 : 2020']

    try:
        if message[0].split()[0].lower()[0:6] == 'alerte':
            # Détermine si c'est un BUY ou un SELL
            if "J'achete" in message[1][0:8]:
                InfoTrade['TypeOrdre'] = 'BUY'
            elif "Je vends" in message[1][0:8]:
                InfoTrade['TypeOrdre'] = 'SELL'
            else:
                return {}

            # Extrait le symbole du signal
            AnalyseSYMBOLES = message[1].split()
            for i in range(len(AnalyseSYMBOLES)):
                if '(' in AnalyseSYMBOLES[i]:
                    AnalyseSYMBOLES[i] = AnalyseSYMBOLES[i].removeprefix('(')
                    AnalyseSYMBOLES[i] = AnalyseSYMBOLES[i].removesuffix(')')
                else:
                    AnalyseSYMBOLES[i] = AnalyseSYMBOLES[i]
                if AnalyseSYMBOLES[i] in SYMBOLES:
                    SymbolesLOTS = AnalyseSYMBOLES[i]
                    indice = SYMBOLES.index(AnalyseSYMBOLES[i])
                    InfoTrade['Symbole'] = SYMBOLES_FXLIFT[indice]
                    InfoTrade['Multiplier'] = MULTIPLIER[indice]
                else:
                    continue

            # Extrait le SL du signal en ajoutant l'écart des marchées entres les brokers pour certains symboles
            if InfoTrade['Symbole'] == 'GER40_U3':
                InfoTrade['StopLoss'] = float(message[2].split(': ')[1].split(' ')[0]) + 140
            else:
                InfoTrade['StopLoss'] = message[2].split(': ')[1].split(' ')[0]

            # Extrait les TPs du signal en ajoutant l'écart des marchées entres les brokers pour certains symboles
            y = 0
            for j in range(len(message)):
                if message[j].split()[0] == 'Take':
                    y = y + 1
                    if y == 1:
                        if InfoTrade['Symbole'] == 'GER40_U3':
                            InfoTrade['TakeProfits'] = [float(message[j].split(': ')[1].split(' ')[0]) + 140]
                        else:
                            InfoTrade['TakeProfits'] = [message[j].split(': ')[1].split(' ')[0]]
                    else:
                        if InfoTrade['Symbole'] == 'GER40_U3':
                            InfoTrade['TakeProfits'].append(float(message[j].split(': ')[1].split(' ')[0]) + 140)
                        else:
                            InfoTrade['TakeProfits'].append(message[j].split(': ')[1].split(' ')[0])
                else:
                    continue

            # Attributions des lots fixes selon le symbole
            if SymbolesLOTS == 'ETHUSD':
                InfoTrade['Lots'] = 0.07
            elif SymbolesLOTS == 'BTCUSD':
                InfoTrade['Lots'] = 0.02
            elif SymbolesLOTS == 'XAUUSD':
                InfoTrade['Lots'] = 0.01
            elif SymbolesLOTS == 'DAX40' or SymbolesLOTS == 'DJ30' or SymbolesLOTS == 'US30':
                InfoTrade['Lots'] = 0.01
            # elif SYMBOLES = '':
            #     InfoTrade['Lots'] =
            else:
                InfoTrade['Lots'] = 0.02

            if len(InfoTrade['TakeProfits']) == 1:
                MessageSIGNAL = f"{InfoTrade['TypeOrdre']} {InfoTrade['Symbole']} \nEntry NOW\nLOTS {InfoTrade['Lots']}\nMultiplier {InfoTrade['Multiplier']}\nSL {InfoTrade['StopLoss']}\nTP {InfoTrade['TakeProfits'][0]}"
            elif len(InfoTrade['TakeProfits']) == 2:
                MessageSIGNAL = f"{InfoTrade['TypeOrdre']} {InfoTrade['Symbole']} \nEntry NOW\nLOTS {InfoTrade['Lots']}\nMultiplier {InfoTrade['Multiplier']}\nSL {InfoTrade['StopLoss']}\nTP {InfoTrade['TakeProfits'][0]}\nTP {InfoTrade['TakeProfits'][1]}"
            elif len(InfoTrade['TakeProfits']) >= 3:
                MessageSIGNAL = f"{InfoTrade['TypeOrdre']} {InfoTrade['Symbole']} \nEntry NOW\nLOTS {InfoTrade['Lots']}\nMultiplier {InfoTrade['Multiplier']}\nSL {InfoTrade['StopLoss']}\nTP {InfoTrade['TakeProfits'][0]}\nTP {InfoTrade['TakeProfits'][1]}\nTP {InfoTrade['TakeProfits'][2]}"

            print(MessageSIGNAL)

            await client.send_message(BOT_CHANNEL_SOURCE, '/trade')
            await client.send_message(BOT_CHANNEL_SOURCE, MessageSIGNAL)

    except Exception as error:
        Erreur =(f"There was an issue😕\n\nError Message:\n{error}")
        await client.send_message(BOT_CHANNEL_SOURCE, Erreur)

    return

client.run_until_disconnected()

# MetaAPI Credentials
API_KEY = os.environ.get("API_KEY")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")

# Telegram Credentials
TOKEN = os.environ.get("TOKEN")
TELEGRAM_USER = os.environ.get("TELEGRAM_USER")

# Heroku Credentials
APP_URL = os.environ.get("APP_URL")

# Port number for Telegram bot web hook
PORT = int(os.environ.get('PORT', '8443'))

# Enables logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# possibles states for conversation handler
CALCULATE, TRADE, DECISION = range(3)


# Helper Functions
def ParseSignal(signal: str) -> dict:
    """Starts process of parsing signal and entering trade on MetaTrader account.

    Arguments:
        signal: trading signal

    Returns:
        a dictionary that contains trade signal information
    """

    # converts message to list of strings for parsing
    signal = signal.splitlines()
    signal = [line.rstrip() for line in signal]

    trade = {}

    # determines the order type of the trade
    if('Sell'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Sell'
        
    elif('Buy'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Buy'
    
    # returns an empty dictionary if an invalid order type was given
    else:
        return {}

    # extracts symbol from trade signal
    trade['Symbol'] = (signal[0].split())[-1].upper()
    
    # checks wheter or not to convert entry to float because of market exectution option ("NOW")
    if(trade['OrderType'] == 'Buy' or trade['OrderType'] == 'Sell'):
        trade['Entry'] = (signal[1].split())[-1]
    else:
        trade['Entry'] = float((signal[1].split())[-1])
    
    trade['StopLoss'] = float((signal[4].split())[-1])
    trade['TP'] = [float((signal[5].split())[-1])]
    
    # checks if there's a fourth line and parses it for TP2
    if(len(signal) > 6):
        trade['TP'].append(float(signal[6].split()[-1]))
        
    if(len(signal) > 7):
        trade['TP'].append(float(signal[7].split()[-1]))
        
    trade['PositionSize'] = float((signal[2].split())[-1])
    trade['Multiplier'] = float((signal[3].split())[-1])
    
    logger.info(trade['OrderType'])
    logger.info(trade['Symbol'])
    logger.info(trade['Entry'])
    logger.info(trade['Multiplier'])
    logger.info(trade['PositionSize'])
    logger.info(trade['StopLoss'])
    logger.info(trade['TP'])
    
    return trade
    

def GetTradeInformation(update: Update, trade: dict, balance: float) -> None:
    """Calculates information from given trade including stop loss and take profit in pips, posiition size, and potential loss/profit.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
    """

    # calculates the stop loss in pips
    stopLossPips = abs(round((trade['StopLoss'] - trade['Entry']) / trade['Multiplier']))

    # calculates the take profit(s) in pips
    takeProfitPips = []
    for takeProfit in trade['TP']:
        takeProfitPips.append(abs(round((takeProfit - trade['Entry']) / trade['Multiplier'])))
        
    # creates table with trade information
    table = CreateTable(trade, balance, stopLossPips, takeProfitPips)
    
    # sends user trade information and calcualted risk
    update.effective_message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)

    return
    

def CreateTable(trade: dict, balance: float, stopLossPips: int, takeProfitPips: int) -> PrettyTable:
    """Creates PrettyTable object to display trade information to user.

    Arguments:
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
        stopLossPips: the difference in pips from stop loss price to entry price

    Returns:
        a Pretty Table object that contains trade information
    """

    # creates prettytable object
    table = PrettyTable()
    
    potentialLoss = round((trade['PositionSize'] * 10) * stopLossPips * len(takeProfitPips), 2)
    risk = round(((potentialLoss * 100) / balance))
    
    table.title = "Trade Information"
    table.field_names = ["Key", "Value"]
    table.align["Key"] = "l"  
    table.align["Value"] = "l" 
    table.add_row([trade["OrderType"] , trade["Symbol"]])
    table.add_row(['Entry\n', trade['Entry']])
    
    table.add_row(['Position Size', trade['PositionSize']])
    table.add_row(['Risk', '{:,.0f} %'.format(risk)])
    table.add_row(['Multiplier', trade['Multiplier']])
    
    table.add_row(['\nStop Loss', '\n{} pips'.format(stopLossPips)])
    
    for count, takeProfit in enumerate(takeProfitPips):
        table.add_row([f'TP {count + 1}', f'{takeProfit} pips'])
    
    table.add_row(['\nCurrent Balance', '\n$ {:,.2f}'.format(balance)])

    # total potential profit from trade
    totalProfit = 0
    
    for count, takeProfit in enumerate(takeProfitPips):
        profit = round((trade['PositionSize'] * 10 * (1 / len(takeProfitPips))) * takeProfit, 2)
        table.add_row([f'TP {count + 1} Profit', '$ {:,.2f}'.format(profit)])
        
        # sums potential profit from each take profit target
        totalProfit += profit

    table.add_row(['\nTotal Profit', '\n$ {:,.2f}'.format(totalProfit)])
    table.add_row(['Potential Loss', '$ {:,.2f}'.format(potentialLoss)])
    
    return table
    

async def ConnectMetaTrader(update: Update, trade: dict, enterTrade: bool):
    """Attempts connection to MetaAPI and MetaTrader to place trade.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information

    Returns:
        A coroutine that confirms that the connection to MetaAPI/MetaTrader and trade placement were successful
    """

    # creates connection to MetaAPI
    api = MetaApi(API_KEY)
    
    try:
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        initial_state = account.state
        deployed_states = ['DEPLOYING', 'DEPLOYED']

        if initial_state not in deployed_states:
            #  wait until account is deployed and connected to broker
            logger.info('Deploying account')
            await account.deploy()

        logger.info('Waiting for API server to connect to broker ...')
        await account.wait_connected()

        # connect to MetaApi API
        connection = account.get_rpc_connection()
        await connection.connect()

        # wait until terminal state synchronized to the local state
        logger.info('Waiting for SDK to synchronize to terminal state ...')
        await connection.wait_synchronized()

        # obtains account information from MetaTrader server
        account_information = await connection.get_account_information()

        update.effective_message.reply_text("Successfully connected to MetaTrader!\nCalculating trade risk ... 🤔")

        # checks if the order is a market execution to get the current price of symbol
        if(trade['Entry'] == 'NOW'):
            price = await connection.get_symbol_price(symbol=trade['Symbol'])

            # uses bid price if the order type is a buy
            if(trade['OrderType'] == 'Buy'):
                trade['Entry'] = float(price['bid'])

            # uses ask price if the order type is a sell
            if(trade['OrderType'] == 'Sell'):
                trade['Entry'] = float(price['ask'])

        # produces a table with trade information
        GetTradeInformation(update, trade, account_information['balance'])
            
        # checks if the user has indicated to enter trade
        if(enterTrade == True):

            # enters trade on to MetaTrader account
            update.effective_message.reply_text("Entering trade on MetaTrader Account ... 👨🏾‍💻")

            try:
                # executes buy market execution order
                if(trade['OrderType'] == 'Buy'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_buy_order(trade['Symbol'], trade['PositionSize'], trade['StopLoss'], takeProfit)

                # executes sell market execution order
                elif(trade['OrderType'] == 'Sell'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_sell_order(trade['Symbol'], trade['PositionSize'], trade['StopLoss'], takeProfit)
             
                # sends success message to user
                update.effective_message.reply_text("Trade entered successfully! 💰")
                
                # prints success message to console
                logger.info('\nTrade entered successfully!')
                logger.info('Result Code: {}\n'.format(result['stringCode']))
            
            except Exception as error:
                logger.info(f"\nTrade failed with error: {error}\n")
                update.effective_message.reply_text(f"There was an issue 😕\n\nError Message:\n{error}")
    
    except Exception as error:
        logger.error(f'Error: {error}')
        update.effective_message.reply_text(f"There was an issue with the connection 😕\n\nError Message:\n{error}")
    
    return


# Handler Functions
def PlaceTrade(update: Update, context: CallbackContext) -> int:
    """Parses trade and places on MetaTrader account.   
    
    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    # checks if the trade has already been parsed or not
    if(context.user_data['trade'] == None):

        try: 
            # parses signal from Telegram message
            trade = ParseSignal(update.effective_message.text)
            
            # checks if there was an issue with parsing the trade
            if(not(trade)):
                raise Exception('Invalid Trade')

            # sets the user context trade equal to the parsed trade
            context.user_data['trade'] = trade
            update.effective_message.reply_text("Trade Successfully Parsed! 🥳\nConnecting to MetaTrader ... \n(May take a while) ⏰")
        
        except Exception as error:
            logger.error(f'Error: {error}')
            errorMessage = f"There was an error parsing this trade 😕\n\nError: {error}\n\nPlease re-enter trade with this format:\n\nBUY/SELL SYMBOL\nEntry \nLOTS \nMultiplier \nSL \nTP \n(TP) \n(TP) \n\nOr use the /cancel to command to cancel this action."
            update.effective_message.reply_text(errorMessage)

            # returns to TRADE state to reattempt trade parsing
            return TRADE
    
    # attempts connection to MetaTrader and places trade
    asyncio.run(ConnectMetaTrader(update, context.user_data['trade'], True))
    
    # removes trade from user context data
    context.user_data['trade'] = None

    return ConversationHandler.END
    

def CalculateTrade(update: Update, context: CallbackContext) -> int:
    """Parses trade and places on MetaTrader account.   
    
    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    # checks if the trade has already been parsed or not
    if(context.user_data['trade'] == None):

        try: 
            # parses signal from Telegram message
            trade = ParseSignal(update.effective_message.text)
            
            # checks if there was an issue with parsing the trade
            if(not(trade)):
                raise Exception('Invalid Trade')

            # sets the user context trade equal to the parsed trade
            context.user_data['trade'] = trade
            update.effective_message.reply_text("Trade Successfully Parsed! 🥳\nConnecting to MetaTrader ... (May take a while) ⏰")
        
        except Exception as error:
            logger.error(f'Error: {error}')
            errorMessage = f"There was an error parsing this trade 😕\n\nError: {error}\n\nPlease re-enter trade with this format:\n\nBUY/SELL SYMBOL\nEntry \nLOTS \nMultiplier \nSL \nTP \n\nOr use the /cancel to command to cancel this action."
            update.effective_message.reply_text(errorMessage)

            # returns to CALCULATE to reattempt trade parsing
            return CALCULATE
    
    # attempts connection to MetaTrader and calculates trade information
    asyncio.run(ConnectMetaTrader(update, context.user_data['trade'], False))

    # asks if user if they would like to enter or decline trade
    update.effective_message.reply_text("Souhaitez-vous envoyer cette transaction ? Pour l'envoyer, sélectionnez : /yes\nPour annuler, sélectionnez : /no")

    return DECISION
    

def unknown_command(update: Update, context: CallbackContext) -> None:
    """Checks if the user is authorized to use this bot or shares to use /help command for instructions.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if(not(update.effective_message.chat.username == TELEGRAM_USER)):
        update.effective_message.reply_text("Vous n'êtes pas autorisé à utiliser ce robot ! 🙅🏽‍♂️")
        return

    update.effective_message.reply_text("Commande inconnue. Utilisez /trade pour placer une transaction ou /calculate pour obtenir des informations sur une transaction. Vous pouvez également utiliser la commande /help pour consulter les instructions relatives à ce robot.")

    return


# Command Handlers
def welcome(update: Update, context: CallbackContext) -> None:
    """Sends welcome message to user.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    welcome_message = "Bienvenue sur le bot Telegram de FX Signal Copier ! 💻💸\nVous pouvez utiliser ce bot pour entrer dans les transactions directement à partir de Telegram et obtenir un aperçu détaillé de votre ratio risque-récompense avec le profit, la perte. Vous êtes en mesure de modifier des paramètres spécifiques tels que les symboles autorisés, le facteur de risque, et plus encore à partir de votre script Python personnalisé et des variables d'environnement.\nUtilisez la commande /help pour afficher des instructions et des exemples de transactions."
    
    # sends messages to user
    update.effective_message.reply_text(welcome_message)

    return
    

def help(update: Update, context: CallbackContext) -> None:
    """Sends a help message when the command /help is issued

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    # help_message = "Ce robot est utilisé pour entrer automatiquement des transactions sur votre compte MetaTrader directement à partir de Telegram. Pour commencer, assurez-vous que vous êtes autorisé à utiliser ce robot en ajustant votre script Python ou vos variables d'environnement.\nAprès une longue période d'absence du robot, assurez-vous de saisir à nouveau la commande start pour redémarrer la connexion à votre compte MetaTrader."
    commands = "Liste des commandes:\n/start : affiche le message de bienvenue\n/help : affiche la liste des commandes et des exemples de transactions\n/trade : prend en charge la transaction saisie par l'utilisateur pour l'analyser et la placer\n/calculate : calcule les informations de transaction pour une transaction saisie par l'utilisateur."
    trade_example = "Example Trades 💴:\n\n"
    market_execution_example = "Market Execution:\nBUY GBPUSD\nEntry NOW\nLOTS 0.01\nMultiplier 1\nSL 1.14336\nTP 1.28930\nTP 1.29845\nTP 1.29999\n\n"
    
    # sends messages to user
    # update.effective_message.reply_text(help_message)
    update.effective_message.reply_text(commands)
    update.effective_message.reply_text(trade_example + market_execution_example)

    return
    

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation.   
    
    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    update.effective_message.reply_text("La commande a été annulée.")

    # removes trade from user context data
    context.user_data['trade'] = None

    return ConversationHandler.END
    

def error(update: Update, context: CallbackContext) -> None:
    """Logs Errors caused by updates.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    logger.warning('Update "%s" caused error "%s"', update, context.error)

    return
    

def Trade_Command(update: Update, context: CallbackContext) -> int:
    """Asks user to enter the trade they would like to place.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if(not(update.effective_message.chat.username == TELEGRAM_USER)):
        update.effective_message.reply_text("Vous n'êtes pas autorisé à utiliser ce robot ! 🙅🏽‍♂️")
        return ConversationHandler.END
    
    # initializes the user's trade as empty prior to input and parsing
    context.user_data['trade'] = None
    
    # asks user to enter the trade
    update.effective_message.reply_text("Veuillez saisir le trade que vous souhaitez effectuer.")

    return TRADE
    

def Calculation_Command(update: Update, context: CallbackContext) -> int:
    """Asks user to enter the trade they would like to calculate trade information for.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if(not(update.effective_message.chat.username == TELEGRAM_USER)):
        update.effective_message.reply_text("Vous n'êtes pas autorisé à utiliser ce robot ! 🙅🏽‍♂️")
        return ConversationHandler.END

    # initializes the user's trade as empty prior to input and parsing
    context.user_data['trade'] = None

    # asks user to enter the trade
    update.effective_message.reply_text("Veuillez saisir le trade que vous souhaitez calculer.")

    return CALCULATE


def main() -> None:
    """Runs the Telegram bot."""

    updater = Updater(TOKEN, use_context=True)

    # get the dispatcher to register handlers
    dp = updater.dispatcher

    # message handler
    dp.add_handler(CommandHandler("start", welcome))

    # help command handler
    dp.add_handler(CommandHandler("help", help))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("trade", Trade_Command), CommandHandler("calculate", Calculation_Command)],
        states={
            TRADE: [MessageHandler(Filters.text & ~Filters.command, PlaceTrade)],
            CALCULATE: [MessageHandler(Filters.text & ~Filters.command, CalculateTrade)],
            DECISION: [CommandHandler("yes", PlaceTrade), CommandHandler("no", cancel)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # conversation handler for entering trade or calculating trade information
    dp.add_handler(conv_handler)

    # message handler for all messages that are not included in conversation handler
    dp.add_handler(MessageHandler(Filters.text, unknown_command))

    # log all errors
    dp.add_error_handler(error)
    
    # listens for incoming updates from Telegram
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=APP_URL + TOKEN)
    updater.idle()

    return


if __name__ == '__main__':
    main()
