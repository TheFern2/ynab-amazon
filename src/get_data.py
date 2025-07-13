from amazonorders.session import AmazonSession, IODefault
from amazonorders.orders import AmazonOrders
import os
from dotenv import load_dotenv, dotenv_values
from ynab import YNAB
import json
from datetime import datetime
import argparse
from datetime import timedelta

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fetch Amazon orders and YNAB transactions')
parser.add_argument('--amazon-year', type=int, default=datetime.now().year, help='Year to fetch Amazon orders for')
parser.add_argument('--ynab-date', type=str, default=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), help='Date for YNAB transactions in ISO format (YYYY-MM-DD)')
parser.add_argument('--payee-name', type=str, default='Amazon', help='Payee name to filter YNAB transactions (default: Amazon)')
args = parser.parse_args()

# Load environment variables from .env file
env_values = dotenv_values()

class OtpIO(IODefault):
    def prompt(self, msg, type=None, **kwargs):
        if 'OTP' in msg or 'code' in msg:
            otp = get_otp_somehow()  # Your logic here
            return otp
        return super().prompt(msg, type=type, **kwargs)

def get_otp_somehow():
    return env_values.get("AMAZON_OTP")

# Amazon orders
amazon_session = AmazonSession(env_values.get("AMAZON_EMAIL"),
                               env_values.get("AMAZON_PASSWORD"),
                               io=OtpIO())

amazon_session.login()

print(f"Fetching Amazon orders for year {args.amazon_year}...")
amazon_orders = AmazonOrders(amazon_session)
orders = amazon_orders.get_order_history(year=args.amazon_year, full_details=True)

# Store Amazon orders in a list
amazon_orders_list = []
for order in orders:
    print(f"{order.order_placed_date} {order.order_number} - {order.grand_total} {order.order_details_link}")
    
    # Handle items information
    items_data = []
    if hasattr(order, 'items') and order.items:
        # print(f"{order.items}")
        print(f"{order.order_number}")
        for item in order.items:
            print(f"{item}")
            item_data = {}
            # Extract available item attributes
            if hasattr(item, 'title'):
                item_data['title'] = item.title
            if hasattr(item, 'price'):
                item_data['price'] = str(item.price)
            if hasattr(item, 'quantity'):
                item_data['quantity'] = item.quantity
            items_data.append(item_data)
    amazon_orders_list.append({
        "date": str(order.order_placed_date),
        "order_number": order.order_number,
        "grand_total": order.grand_total,
        "order_details_link": order.order_details_link,
        "estimated_tax": order.estimated_tax,
        "coupon_savings": order.coupon_savings,
        "subscription_discount": order.subscription_discount,
        "shipping_total": order.shipping_total,
        "free_shipping": order.free_shipping,
        "refund_total": order.refund_total,
        "reward_points": order.reward_points,
        "promotion_applied": order.promotion_applied,
        "multibuy_discount": order.multibuy_discount,
        "amazon_discount": order.amazon_discount,
        "gift_card": order.gift_card,
        "gift_wrap": order.gift_wrap,        
        "items": items_data
    })

# Save Amazon orders to file
with open('amazon_orders.json', 'w') as f:
    json.dump(amazon_orders_list, f, indent=2)

# Get transactions Amazon payee from ynab

# Initialize YNAB client with API key from .env
ynab_client = YNAB(env_values.get("YNAB_API_KEY"))

# Use provided date or fallback to today
if args.ynab_date:
    ynab_date = datetime.strptime(args.ynab_date, '%Y-%m-%d').date()
else:
    ynab_date = datetime.today().date()

print(f"Fetching YNAB transactions from {ynab_date}...")
# Get transactions using budget ID from .env
transactions = ynab_client.get_transactions(env_values.get("YNAB_BUDGET_ID"), ynab_date)

# Filter and store Amazon transactions
amazon_transactions = []
if 'data' in transactions and 'transactions' in transactions['data']:
    for transaction in transactions['data']['transactions']:
        if transaction.get('payee_name', '').lower().startswith(args.payee_name.lower()):
            amazon_transactions.append(transaction)
            print(f"Date: {transaction['date']}, Amount: ${abs(transaction['amount'])/1000:.2f}, Payee: {transaction['payee_name']}")

print(f"Found {len(amazon_transactions)} Amazon transactions.")

# Save YNAB Amazon transactions to file
with open('ynab_amazon_transactions.json', 'w') as f:
    json.dump(amazon_transactions, f, indent=2)
