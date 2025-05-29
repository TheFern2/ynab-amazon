import json
import os
from ynab import YNAB
from dotenv import load_dotenv, dotenv_values
import logging
from datetime import datetime

# Load environment variables from .env file
env_values = dotenv_values()

# Set up logging to both file and console
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a logger
    logger = logging.getLogger('ynab_amazon')
    logger.setLevel(logging.INFO)
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(message)s')
    console_formatter = logging.Formatter('%(message)s')
    
    # File handler (with timestamp in filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(f'logs/ynab_amazon_update_{timestamp}.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def load_json_file(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def find_matching_amazon_order(amazon_orders, ynab_amount):
    # Convert YNAB amount from milliunits to dollars
    ynab_dollars = ynab_amount / -1000  # Changed to handle negative amount properly
    
    # Find orders with matching total amount
    matching_orders = [
        order for order in amazon_orders 
        if abs(float(order['grand_total']) - ynab_dollars) < 0.01
    ]
    
    return matching_orders[0] if matching_orders else None

def create_subtransactions(items, estimated_tax=None, order_total=None, ynab_amount=None, coupon_savings=None, subscription_discount=None, shipping_total=None, free_shipping=None):
    subtransactions = []
    items_with_no_price = []
    subtotal = 0
    
    # Process items first
    for item in items:
        price = item.get('price')
        # Skip items with no price or price is 'None'
        if not price or price == 'None':
            items_with_no_price.append(item)
            continue
            
        # Get quantity, default to 1 if None or not specified
        quantity = item.get('quantity')
        if quantity is None or quantity == 'None':
            quantity = 1
            
        # Multiply price by quantity and convert to milliunits
        amount = int(round(float(price) * float(quantity) * -1000))
        subtotal += amount
        
        # Only add quantity to memo if it exists and is greater than 1
        if quantity and int(quantity) > 1:
            memo = f"{item['title'][:40]}... (Qty: {quantity})"
        else:
            memo = f"{item['title'][:40]}..."
        
        subtransactions.append({
            "amount": amount,
            "payee_name": "Amazon",
            "memo": memo
        })
    
    # Handle shipping costs
    if shipping_total and shipping_total != 'None' and float(shipping_total) != 0:
        shipping_amount = int(round(float(shipping_total) * -1000))  # Negative amount for cost
        
        # Only add shipping if there's a net shipping cost (shipping_total > free_shipping)
        net_shipping = float(shipping_total)
        if free_shipping and free_shipping != 'None':
            net_shipping += float(free_shipping)  # free_shipping is already negative
            
        if abs(net_shipping) > 0.01:  # If there's a meaningful net shipping cost
            subtotal += shipping_amount
            subtransactions.append({
                "amount": shipping_amount,
                "payee_name": "Amazon",
                "memo": "Shipping Cost"
            })
            
            # Add free shipping discount if it exists
            if free_shipping and free_shipping != 'None' and float(free_shipping) != 0:
                free_shipping_amount = int(round(float(free_shipping) * -1000))  # Keep as negative
                subtotal += free_shipping_amount
                subtransactions.append({
                    "amount": free_shipping_amount,
                    "payee_name": "Amazon",
                    "memo": "Free Shipping Discount"
                })
    
    # Add coupon savings if present (as negative amount)
    if coupon_savings and coupon_savings != 'None' and float(coupon_savings) != 0:
        savings_amount = int(round(float(coupon_savings) * -1000))  # Negative amount for savings
        subtotal += savings_amount
        subtransactions.append({
            "amount": savings_amount,
            "payee_name": "Amazon",
            "memo": "Coupon Savings"
        })

    # Add subscription discount if present (as negative amount)
    if subscription_discount and subscription_discount != 'None' and float(subscription_discount) != 0:
        discount_amount = int(round(float(subscription_discount) * -1000))  # Negative amount for discount
        subtotal += discount_amount
        subtransactions.append({
            "amount": discount_amount,
            "payee_name": "Amazon",
            "memo": "Subscription Discount"
        })
    
    # Add tax as a separate subtransaction if it exists
    if estimated_tax and estimated_tax != 'None':
        tax_amount = int(round(float(estimated_tax) * -1000))  # Round before converting to int
        subtotal += tax_amount
        subtransactions.append({
            "amount": tax_amount,
            "payee_name": "Amazon",
            "memo": "Sales Tax"
        })
    
    # If we have the YNAB amount, adjust the subtransactions to match it exactly
    if ynab_amount and subtransactions:
        difference = ynab_amount - subtotal
        if abs(difference) <= 10:  # If difference is 1 cent or less
            # Add the difference to the largest subtransaction to minimize rounding impact
            largest_sub = max(subtransactions, key=lambda x: abs(x['amount']))
            largest_sub['amount'] += difference
    
    return subtransactions, items_with_no_price

def handle_transaction_mismatch(update, matching_order, difference):
    """Handle a transaction amount mismatch by allowing user to add missing items or gift card amounts."""
    print(f"\nHandling mismatch for order: {matching_order['order_details_link']}")
    print(f"Current difference: ${abs(difference)/1000:.2f}")
    print("\nOptions:")
    print("1. Add missing item")
    print("2. Enter adjustment amount")
    print("3. Skip this transaction")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        item_name = input("Enter item name: ")
        item_price = float(input("Enter item price: "))
        quantity = input("Enter quantity (default 1): ").strip() or "1"
        
        # Convert price to milliunits and make negative
        amount = int(round(float(item_price) * float(quantity) * -1000))
        
        # Create memo with quantity if > 1
        if int(quantity) > 1:
            memo = f"{item_name[:40]}... (Qty: {quantity})"
        else:
            memo = f"{item_name[:40]}..."
            
        # Add new subtransaction
        update['subtransactions'].append({
            "amount": amount,
            "payee_name": "Amazon",
            "memo": memo
        })
        
        return True
        
    elif choice == "2":
        print("\nExamples of adjustments:")
        print("  -1.50  (for a gift card credit - shows negative in Amazon)")
        print("  +1.20  (for additional charges like tips)")
        print("  -5.00  (for a refund or discount - shows negative in Amazon)")
        print("  +2.75  (for additional tax or fees)")
        
        adjustment_input = input("\nEnter adjustment amount (- for credits/refunds, + for additional charges): ").strip()
        
        # Parse the adjustment amount
        try:
            if adjustment_input.startswith('+'):
                adjustment_amount = float(adjustment_input[1:])
            elif adjustment_input.startswith('-'):
                adjustment_amount = -float(adjustment_input[1:])
            else:
                adjustment_amount = float(adjustment_input)
        except ValueError:
            print("Invalid amount format. Please try again.")
            return False
        
        memo = input("Enter description for this adjustment: ").strip()
        if not memo:
            memo = "Manual Adjustment"
        
        # Convert to milliunits (YNAB uses milliunits)
        # For YNAB: negative amounts are expenses, positive adjustments reduce the total
        # So Amazon credits (negative) should become positive YNAB adjustments
        amount = int(round(adjustment_amount * -1000))
        
        # Add adjustment subtransaction
        update['subtransactions'].append({
            "amount": amount,
            "payee_name": "Amazon",
            "memo": memo
        })
        
        return True
        
    return False

def verify_transaction_amounts(updates_preview, matching_orders_map, logger):
    """Verify transaction amounts and handle mismatches."""
    has_mismatches = False
    fixed_transactions = []
    
    for i, update in enumerate(updates_preview):
        while True:  # Keep trying to fix the transaction until it matches or user skips
            sub_total = sum(sub['amount'] for sub in update['subtransactions'])
            difference = update['amount'] - sub_total
            
            if abs(difference) <= 1:  # Transaction matches
                if update not in fixed_transactions:
                    fixed_transactions.append(update)
                break
                
            has_mismatches = True
            matching_order = matching_orders_map[update['id']]
            
            logger.error(f"\nTransaction {i} amount mismatch:")
            logger.error(f"Order link: {matching_order['order_details_link']}")
            logger.error(f"Amazon order total: ${float(matching_order['grand_total']):.2f}")
            logger.error(f"Raw YNAB amount (milliunits): {update['amount']}")
            logger.error(f"Raw subtotal (milliunits): {sub_total}")
            logger.error(f"Transaction amount: ${update['amount']/-1000:.2f}")
            logger.error(f"Sum of subtransactions: ${sub_total/-1000:.2f}")
            logger.error("Subtransactions:")
            for sub in update['subtransactions']:
                logger.error(f"  - ${sub['amount']/-1000:.2f}: {sub['memo']}")
            logger.error(f"Difference: ${(update['amount'] - sub_total)/-1000:.2f}")
            
            if not handle_transaction_mismatch(update, matching_order, difference):
                break  # User chose to skip
            
    return has_mismatches, fixed_transactions

def main():
    # Set up logging
    logger = setup_logging()
    
    logger.info("Starting YNAB Amazon transaction update process")
    
    # Load data from JSON files
    amazon_orders = load_json_file('amazon_orders.json')
    ynab_transactions = load_json_file('ynab_amazon_transactions.json')
    
    logger.info(f"Loaded {len(amazon_orders)} Amazon orders and {len(ynab_transactions)} YNAB transactions")
    
    # Initialize YNAB client
    ynab_client = YNAB(env_values.get("YNAB_API_KEY"))
    
    # Store updates to preview
    updates_preview = []
    # Store items with no price for later review
    orders_with_no_price_items = {}
    # Store matching orders for verification
    matching_orders_map = {}
    
    # Process each YNAB transaction
    for txn in ynab_transactions:
        # Skip transactions that already have subtransactions (already processed)
        if txn.get('subtransactions') and len(txn['subtransactions']) > 0:
            logger.info(f"Skipping transaction {txn['id']} - already has {len(txn['subtransactions'])} subtransactions")
            continue
            
        # Skip transactions that already have Amazon order links in memo (already processed)
        memo = txn.get('memo', '') or ''
        if 'amazon.com/gp/your-account/order-details' in memo:
            logger.info(f"Skipping transaction {txn['id']} - already has Amazon order link in memo")
            continue
            
        matching_order = find_matching_amazon_order(amazon_orders, txn['amount'])
        
        if matching_order:
            update = {
                "account_id": txn['account_id'],
                "id": txn['id'],
                "amount": txn['amount']  # Add the original transaction amount
            }
            
            # Create memo based on number of items
            base_memo = txn.get('memo', '') or ''
            if len(matching_order['items']) == 1:
                item_title = matching_order['items'][0]['title'][:40]
                update['memo'] = f"{base_memo} {item_title} - {matching_order['order_details_link']}"
            else:
                update['memo'] = f"{base_memo} {matching_order['order_details_link']}"
            
            # Store matching order for verification
            matching_orders_map[update['id']] = matching_order
            
            # Add subtransactions and track items with no price
            update['subtransactions'], no_price_items = create_subtransactions(
                matching_order['items'], 
                matching_order.get('estimated_tax'),
                matching_order.get('grand_total'),
                txn['amount'],  # Pass YNAB amount for exact matching
                matching_order.get('coupon_savings'),
                matching_order.get('subscription_discount'),
                matching_order.get('shipping_total'),
                matching_order.get('free_shipping')
            )
            if no_price_items:
                orders_with_no_price_items[matching_order['order_details_link']] = no_price_items
            
            update['num_items'] = len(matching_order['items'])  # Store number of items for preview
            
            updates_preview.append(update)
    
    logger.info(f"Found {len(updates_preview)} matching transactions to update")
    
    # Sort updates by number of items (descending) to show multi-item transactions first
    updates_preview.sort(key=lambda x: x['num_items'], reverse=True)
    
    # Preview the first 10 updates and check amounts
    logger.info("\nPreview of updates (first 10 transactions, prioritizing multi-item orders):")
    for i, update in enumerate(updates_preview[:10], 1):
        logger.info(f"\nTransaction {i} ({update['num_items']} items):")
        logger.info(f"Memo: {update['memo']}")
        logger.info(f"Original transaction amount: ${abs(update['amount'])/1000:.2f}")
        logger.info("Subtransactions:")
        total_amount = 0
        for sub in update['subtransactions']:
            amount = abs(sub['amount'])/1000
            total_amount += amount
            logger.info(f"  - ${amount:.2f}: {sub['memo']}")
        logger.info(f"Sum of subtransactions: ${total_amount:.2f}")
    
    # Verify all transactions before sending
    logger.info("\nVerifying all transaction amounts...")
    has_mismatches, fixed_transactions = verify_transaction_amounts(updates_preview, matching_orders_map, logger)
    
    if has_mismatches and not fixed_transactions:
        logger.error("\n❌ Found amount mismatches that could not be fixed. Please review and try again.")
        return
    
    # Ask for confirmation
    response = input("\nDo you want to proceed with these updates? (y/n): ")
    
    if response.lower() == 'y':
        logger.info("Starting YNAB updates...")
        try:
            # Update transactions in batches
            payload = {'transactions': updates_preview}
            budget_id = env_values.get("YNAB_BUDGET_ID")
            logger.info(f"Using YNAB Budget ID: {budget_id}")
            status_code, response = ynab_client.patch_transactions(budget_id, payload)
            
            # Check if the update was successful
            if status_code == 200 and response.get('data'):
                logger.info("Updates completed successfully!")
                
                # Show items with no price for manual review
                if orders_with_no_price_items:
                    logger.info("\nThe following items had no price and need manual review:")
                    for order_link, items in orders_with_no_price_items.items():
                        logger.info(f"\nOrder: {order_link}")
                        for item in items:
                            quantity = item.get('quantity', 1)
                            logger.info(f"- {item['title'][:80]}... (Qty: {quantity})")
            else:
                logger.error(f"Failed to update transactions. Status: {status_code}")
                logger.error(f"Response: {response}")
        except Exception as e:
            logger.error(f"Error updating transactions: {str(e)}")
    else:
        logger.info("Updates cancelled.")

if __name__ == "__main__":
    main() 