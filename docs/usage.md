# YNAB Amazon Integration - Usage Guide

This guide explains how to use the YNAB Amazon integration scripts to enhance your YNAB transactions with detailed Amazon order information.

## Prerequisites

Before using the scripts, you need to:

1. Copy `sample.env` to `.env` and fill in your credentials:
   ```
   AMAZON_EMAIL=your_amazon_email@example.com
   AMAZON_PASSWORD=your_amazon_password
   AMAZON_OTP=your_otp_code_if_required
   YNAB_API_KEY=your_ynab_api_key
   YNAB_BUDGET_ID=your_ynab_budget_id
   YNAB_ACCOUNT_ID=your_ynab_account_id
   ```

2. Install the required dependencies (preferably in a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```

## Step 1: Retrieve Amazon Orders and YNAB Transactions

Run the `get_data.py` script to fetch your Amazon order history and YNAB transactions, by default will get current year and ynab 30 days previous transactions from the current day:

```bash
cd src/
python get_data.py
```

If you'd like to get more or other years:
```bash
python get_data.py --amazon-year 2024 --ynab-date 2024-04-10
```

You can also specify a different payee name to filter YNAB transactions (defaults to "Amazon"):
```bash
python get_data.py --payee-name "Target"
python get_data.py --amazon-year 2024 --ynab-date 2024-04-10 --payee-name "Walmart"
```

This script will:
1. Log into your Amazon account using credentials from your `.env` file (Make sure to add OTP if you have MFA enabled)
2. Fetch your Amazon order history
3. Save the order data to `amazon_orders.json`
4. Connect to YNAB using your API key
5. Retrieve all YNAB transactions with "Amazon" as the payee
6. Save these transactions to `ynab_amazon_transactions.json`

## Step 2: Update YNAB Transactions with Detailed Amazon Order Information

After retrieving the data, run the `update_ynab.py` script to match Amazon orders with YNAB transactions and update them with detailed line items:

```bash
cd src/
python update_ynab.py
```

This script will:
1. Load the previously saved JSON files
2. Match YNAB transactions with Amazon orders based on the total amount
3. Create detailed subtransactions for each item in the matched Amazon orders
4. Redistribute the "Sales Tax" line item across other items if necessary
5. Preview the updates before applying them
6. After your confirmation, update the transactions in YNAB

If you'd like to keep "Sales Tax" as a separate line item:
```bash
python update_ynab.py --preserve-sales-tax-line
```

### Handling Mismatches

If there are discrepancies between the YNAB transaction amounts and the Amazon order totals, the script will prompt you to:
1. Add missing items
2. Add adjustments (gift cards, tips, refunds, etc.)
3. Skip the transaction

#### Option 1: Add Missing Items
Use this when you have items that weren't captured in the Amazon order data but were part of the transaction.

#### Option 2: Add Adjustments
This flexible option allows you to add various types of adjustments to match the transaction total. The script will show examples before prompting for input:

**Examples of adjustments:**
- `-1.50` for a gift card credit (shows negative in Amazon)
- `+1.20` for additional charges like tips
- `-5.00` for a refund or discount (shows negative in Amazon)
- `+2.75` for additional tax or fees

When you select option 2, you'll be prompted to:
1. Enter the adjustment amount (use `-` for credits/refunds that show negative in Amazon, `+` for additional charges)
2. Enter a custom description for the adjustment (e.g., "Gift Card Applied", "Delivery Tip", "Refund", etc.)

If you don't provide a description, it will default to "Manual Adjustment".

This interactive process helps ensure that the subtransactions correctly match the total transaction amount.

## Logs

The update script creates detailed logs in the `logs` directory with timestamps for each run. These logs include information about:
- Transactions matched and updated
- Any mismatches or issues encountered
- Items that had no price information and need manual review

## Troubleshooting

### Amazon Login Issues
- Ensure your Amazon credentials are correct in the `.env` file
- If you use 2FA, enter the OTP code in the `.env` file when prompted
- For persistent login issues, try logging in manually on Amazon's website first

### YNAB API Issues
- Verify your YNAB API key is valid and has not expired
- Ensure you have the correct budget ID and account ID

### Transaction Matching Issues
- If transactions aren't matching, verify that the amounts in YNAB exactly match your Amazon order totals
- Some Amazon orders may be split into multiple shipments or charges, which can complicate matching 