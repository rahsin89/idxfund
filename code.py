# Periodic Index Fund Investment System
# A Python system to periodically invest in an index fund by tracking its composition
# Operating at weekly frequency

import pandas as pd
import yfinance as yf
import time
import schedule
import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("index_investor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IndexInvestor")

###########################################
# SECTION 1: DATA RETRIEVAL
###########################################

def get_index_composition(index_symbol):
    """
    Retrieves the composition of an index and its current weights.
    For some indices, you might need specialized data sources.
    
    Args:
        index_symbol: The symbol of the index (e.g., "^GSPC" for S&P 500)
        
    Returns:
        Dictionary with symbols and their weights in the index
    """
    # This is a simplified example - actual implementation depends on your data source
    if index_symbol == "^GSPC":  # S&P 500
        # In reality, you would need a data provider for accurate composition data
        # This is placeholder code
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        symbols = sp500['Symbol'].tolist()
        
        # Get market caps to approximate weights
        market_caps = {}
        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                market_caps[symbol] = stock.info.get('marketCap', 0)
            except:
                market_caps[symbol] = 0
        
        # Calculate weights
        total_mcap = sum(market_caps.values())
        weights = {symbol: market_caps[symbol]/total_mcap for symbol in market_caps}
        
        return {'symbols': symbols, 'weights': weights}
    else:
        raise ValueError(f"Index {index_symbol} not supported")

###########################################
# SECTION 2: PORTFOLIO MANAGEMENT
###########################################

class IndexPortfolio:
    """
    Class to track portfolio holdings, values, and weights.
    This is essential for determining what trades to make to match the index.
    """
    
    def __init__(self, initial_cash=0):
        self.cash = initial_cash
        self.holdings = {}  # symbol -> quantity
        self.prices = {}    # symbol -> current price
        
    def deposit(self, amount):
        """Add cash to the portfolio."""
        self.cash += amount
        
    def update_prices(self, symbols=None):
        """Update current market prices."""
        symbols = symbols or list(self.holdings.keys())
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                self.prices[symbol] = ticker.history(period='1d')['Close'].iloc[-1]
            except:
                print(f"Could not update price for {symbol}")
    
    def get_total_value(self):
        """Calculate total portfolio value."""
        holdings_value = sum(self.holdings.get(s, 0) * self.prices.get(s, 0) 
                            for s in self.holdings)
        return holdings_value + self.cash
    
    def get_current_weights(self):
        """Calculate current portfolio weights."""
        total = self.get_total_value()
        if total == 0:
            return {}
        
        weights = {}
        for symbol, quantity in self.holdings.items():
            if symbol in self.prices:
                weights[symbol] = (quantity * self.prices[symbol]) / total
        
        # Include cash weight
        weights['CASH'] = self.cash / total
        return weights

###########################################
# SECTION 3: ORDER GENERATION
###########################################

def generate_orders(portfolio, target_weights, min_order_value=10):
    """
    Generate buy/sell orders to rebalance the portfolio.
    
    Args:
        portfolio: The IndexPortfolio object
        target_weights: Dictionary of symbol -> target weight
        min_order_value: Minimum order value to avoid tiny orders
        
    Returns:
        List of (symbol, quantity, action) tuples
    """
    portfolio.update_prices(list(target_weights.keys()))
    total_value = portfolio.get_total_value()
    current_weights = portfolio.get_current_weights()
    
    orders = []
    available_cash = portfolio.cash
    
    # Calculate target value for each position
    for symbol, target_weight in target_weights.items():
        target_value = total_value * target_weight
        current_value = 0
        
        if symbol in portfolio.holdings and symbol in portfolio.prices:
            current_value = portfolio.holdings[symbol] * portfolio.prices[symbol]
        
        value_difference = target_value - current_value
        
        # Skip small adjustments
        if abs(value_difference) < min_order_value:
            continue
            
        # Calculate quantity based on current price
        if symbol in portfolio.prices and portfolio.prices[symbol] > 0:
            price = portfolio.prices[symbol]
            quantity = int(value_difference / price)  # Whole shares only
            
            if quantity > 0 and value_difference > 0:  # Buy
                order_value = quantity * price
                if order_value <= available_cash:
                    orders.append((symbol, quantity, "BUY"))
                    available_cash -= order_value
                    
            elif quantity < 0 and value_difference < 0:  # Sell
                orders.append((symbol, abs(quantity), "SELL"))
    
    return orders

###########################################
# SECTION 4: EXECUTION
###########################################

class BrokerInterface:
    """
    Interface to connect with a broker for executing trades.
    In a real implementation, this would connect to your broker's API.
    """
    
    def __init__(self, api_key=None, api_secret=None, paper_trading=True):
        self.paper_trading = paper_trading
        self.api_key = api_key
        self.api_secret = api_secret
        
        # In a real implementation, you would connect to your broker's API
        # For example, with Alpaca:
        # if not paper_trading:
        #     self.api = tradeapi.REST(api_key, api_secret, base_url='https://api.alpaca.markets')
        # else:
        #     self.api = tradeapi.REST(api_key, api_secret, base_url='https://paper-api.alpaca.markets')
    
    def place_order(self, symbol, quantity, side):
        """Place an order with the broker."""
        if self.paper_trading:
            print(f"PAPER TRADING: {side} {quantity} shares of {symbol}")
            return True
        else:
            try:
                # This would use your broker's API
                # Example with Alpaca:
                # self.api.submit_order(
                #     symbol=symbol,
                #     qty=quantity,
                #     side=side.lower(),
                #     type='market',
                #     time_in_force='day'
                # )
                print(f"Order placed: {side} {quantity} shares of {symbol}")
                return True
            except Exception as e:
                print(f"Error placing order: {e}")
                return False
    
    def get_account_info(self):
        """Get account information from broker."""
        if self.paper_trading:
            return {"cash": 10000}  # Example
        else:
            # Would use broker API
            # return self.api.get_account()
            pass

###########################################
# SECTION 5: MAIN SYSTEM INTEGRATION
###########################################

class IndexInvestor:
    """
    Main class that integrates all components of the system.
    """
    
    def __init__(self, index_symbol, broker_interface, initial_cash=0):
        self.index_symbol = index_symbol
        self.broker = broker_interface
        self.portfolio = IndexPortfolio(initial_cash)
        self.latest_composition = None
        
    def update_index_composition(self):
        """Fetch latest index composition."""
        try:
            self.latest_composition = get_index_composition(self.index_symbol)
            logger.info(f"Updated index composition with {len(self.latest_composition['symbols'])} symbols")
            return True
        except Exception as e:
            logger.error(f"Failed to update index composition: {e}")
            return False
    
    def rebalance(self):
        """Rebalance portfolio to match index weights."""
        if not self.latest_composition:
            if not self.update_index_composition():
                logger.error("Cannot rebalance without index composition")
                return
        
        # Generate orders
        orders = generate_orders(self.portfolio, self.latest_composition['weights'])
        
        # Execute orders
        successful_orders = []
        for symbol, quantity, action in orders:
            if quantity > 0:  # Skip zero-quantity orders
                success = self.broker.place_order(symbol, quantity, action)
                if success:
                    successful_orders.append((symbol, quantity, action))
                    
                    # Update portfolio (in a real system, you'd confirm execution first)
                    if action == "BUY":
                        self.portfolio.holdings[symbol] = self.portfolio.holdings.get(symbol, 0) + quantity
                        self.portfolio.cash -= quantity * self.portfolio.prices[symbol]
                    else:  # SELL
                        self.portfolio.holdings[symbol] = self.portfolio.holdings.get(symbol, 0) - quantity
                        self.portfolio.cash += quantity * self.portfolio.prices[symbol]
        
        logger.info(f"Rebalancing complete. Executed {len(successful_orders)} orders.")
        
    def deposit_funds(self, amount):
        """Add funds to the portfolio."""
        self.portfolio.deposit(amount)
        logger.info(f"Deposited ${amount}. New cash balance: ${self.portfolio.cash}")
        
    def run_weekly(self, day_of_week=0, hour=9, minute=30):
        """
        Schedule weekly runs (0=Monday, 1=Tuesday, etc.)
        Default is Monday at 9:30 AM
        """
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = days[day_of_week]
        
        # Set up the schedule based on the day of week
        if day_of_week == 0:
            schedule.every().monday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        elif day_of_week == 1:
            schedule.every().tuesday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        elif day_of_week == 2:
            schedule.every().wednesday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        elif day_of_week == 3:
            schedule.every().thursday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        elif day_of_week == 4:
            schedule.every().friday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        elif day_of_week == 5:
            schedule.every().saturday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        elif day_of_week == 6:
            schedule.every().sunday.at(f"{hour:02d}:{minute:02d}").do(self.rebalance)
        
        logger.info(f"Scheduled weekly rebalancing for {day_name} at {hour:02d}:{minute:02d}")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

###########################################
# EXAMPLE USAGE
###########################################

if __name__ == "__main__":
    # Initialize with paper trading
    broker = BrokerInterface(paper_trading=True)
    
    # Create system for S&P 500 tracking
    system = IndexInvestor("^GSPC", broker, initial_cash=10000)
    
    # Initialize with current composition
    system.update_index_composition()
    
    # Run initial rebalance
    system.rebalance()
    
    # Start weekly schedule (Monday at 9:30 AM)
    system.run_weekly()
