import os
import asyncio
import threading
import requests
import time
import json
import re
import logging
import aiohttp
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta
from telegram.error import BadRequest
from fastapi import FastAPI
import uvicorn
import random

# Configure logging to focus on errors only
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8341377704:AAF8yfGc0jxBn0INh037g-O_YZMKfrtBnSk"
BASE_URL = "http://8.222.182.223:8081"

# File paths with Render.com compatibility
ACCOUNTS_FILE = "/tmp/accounts.json" if 'RENDER' in os.environ else "accounts.json"
USERS_FILE = "/tmp/users.json" if 'RENDER' in os.environ else "users.json" 
STATS_FILE = "/tmp/stats.json" if 'RENDER' in os.environ else "stats.json"
SUBSCRIPTIONS_FILE = "/tmp/subscriptions.json" if 'RENDER' in os.environ else "subscriptions.json"

ADMIN_ID = 5624278091
MAX_PER_ACCOUNT = 5

# Subscription plans
SUBSCRIPTION_PLANS = {
    "1": {"days": 1, "price": 30, "label": "1 দিন"},
    "3": {"days": 3, "price": 90, "label": "3 দিন"}, 
    "5": {"days": 5, "price": 150, "label": "5 দিন"},
    "7": {"days": 7, "price": 210, "label": "7 দিন"},
    "15": {"days": 15, "price": 450, "label": "15 দিন"},
    "30": {"days": 30, "price": 900, "label": "30 দিন"}
}

# Status map
status_map = {
    0: "⚠️ Check Failed",
    1: "✅ Registered", 
    2: "🔵 In Progress",
    3: "⚠️ Try Again Later",
    4: "🟢 Fresh Number",
    7: "🚫 Ban Number",
    5: "🟡 Pending Verification",
    6: "🔴 Blocked",
    8: "🟠 Limited",
    9: "🔶 Restricted", 
    10: "🟣 VIP Number",
    11: "⚫ Banned",
    12: "🟤 Temp Blocked",
    13: "💤 Inactive",
    14: "🌀 Processing",
    15: "📞 Call Required",
    -1: "❌ Token Expired",
    -2: "❌ API Error",
    -3: "❌ No Data Found",
    16: "🚫 Already Exists"
}

# FastAPI for /ping endpoint
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "🤖 Python Number Checker Bot is Running!"}

@app.get("/ping")
async def ping():
    return {"message": "Bot is alive!"}

# Enhanced keep-alive system
async def keep_alive_enhanced():
    """Enhanced keep-alive with multiple strategies"""
    keep_alive_urls = [
    "https://webck-9utn.onrender.com",
    "https://wslink.onrender.com/ping"
    ]
    
    while True:
        try:
            for url in keep_alive_urls:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=10) as response:
                            print(f"🔄 Keep-alive ping to {url}: Status {response.status}")
                            await asyncio.sleep(2)  # Small delay between pings
                except Exception as e:
                    print(f"⚠️ Keep-alive ping failed for {url}: {e}")
            
            # Wait for next ping cycle (5 minutes)
            await asyncio.sleep(5 * 60)
            
        except Exception as e:
            print(f"❌ Keep-alive system error: {e}")
            await asyncio.sleep(5 * 60)

async def random_ping():
    """Additional random pings to avoid pattern detection"""
    while True:
        try:
            random_time = random.randint(3 * 60, 8 * 60)  # 3-8 minutes
            await asyncio.sleep(random_time)
            
            async with aiohttp.ClientSession() as session:
                async with session.get("https://webck-9utn.onrender.com", timeout=10) as response:
                    print(f"🎲 Random ping sent: Status {response.status}")
                    
        except Exception as e:
            print(f"⚠️ Random ping failed: {e}")

async def immediate_ping():
    """Immediate ping on startup"""
    await asyncio.sleep(30)  # Wait 30 seconds after startup
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://webck-9utn.onrender.com", timeout=10) as response:
                print(f"🚀 Immediate startup ping: Status {response.status}")
    except Exception as e:
        print(f"⚠️ Immediate ping failed: {e}")

# Enhanced file operations with error handling
def load_accounts():
    try:
        # Try multiple possible file locations
        possible_paths = [
            ACCOUNTS_FILE,
            "accounts.json",
            "/tmp/accounts.json",
            "./accounts.json"
        ]
        
        for file_path in possible_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        print(f"✅ Loaded accounts from {file_path}: {len(data)} accounts")
                        return data
            except Exception as e:
                print(f"❌ Error loading from {file_path}: {e}")
                continue
        
        print("ℹ️ No accounts file found, starting fresh")
        return []
        
    except Exception as e:
        print(f"❌ Critical error loading accounts: {e}")
        return []

def save_accounts(accounts):
    try:
        # Try multiple possible file locations
        possible_paths = [
            ACCOUNTS_FILE,
            "accounts.json", 
            "/tmp/accounts.json"
        ]
        
        success = False
        for file_path in possible_paths:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(accounts, f, indent=4, ensure_ascii=False)
                print(f"✅ Saved {len(accounts)} accounts to {file_path}")
                success = True
                break
            except Exception as e:
                print(f"❌ Error saving to {file_path}: {e}")
                continue
        
        if not success:
            print("❌ Failed to save accounts to any location")
            
    except Exception as e:
        print(f"❌ Critical error saving accounts: {e}")

def load_users():
    try:
        possible_paths = [USERS_FILE, "users.json", "/tmp/users.json", "./users.json"]
        for file_path in possible_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Ensure we return a dictionary, not a list
                        if isinstance(data, dict):
                            return data
                        else:
                            print(f"⚠️ Users file contains {type(data)}, converting to dict")
                            return {}
            except Exception as e:
                print(f"❌ Error loading from {file_path}: {e}")
                continue
        return {}
    except Exception as e:
        print(f"❌ Error loading users: {e}")
        return {}

def save_users(users):
    try:
        possible_paths = [USERS_FILE, "users.json", "/tmp/users.json"]
        for file_path in possible_paths:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(users, f, indent=4, ensure_ascii=False)
                break
            except:
                continue
    except Exception as e:
        print(f"❌ Error saving users: {e}")

def load_stats():
    try:
        possible_paths = [STATS_FILE, "stats.json", "/tmp/stats.json", "./stats.json"]
        for file_path in possible_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Ensure we return a dictionary
                        if isinstance(data, dict):
                            return data
                        else:
                            print(f"⚠️ Stats file contains {type(data)}, returning default")
                            return {
                                "total_checked": 0, 
                                "total_deleted": 0, 
                                "today_checked": 0, 
                                "today_deleted": 0,
                                "last_reset": datetime.now().isoformat()
                            }
            except:
                continue
        return {
            "total_checked": 0, 
            "total_deleted": 0, 
            "today_checked": 0, 
            "today_deleted": 0,
            "last_reset": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ Error loading stats: {e}")
        return {
            "total_checked": 0, 
            "total_deleted": 0, 
            "today_checked": 0, 
            "today_deleted": 0,
            "last_reset": datetime.now().isoformat()
        }

def save_stats(stats):
    try:
        possible_paths = [STATS_FILE, "stats.json", "/tmp/stats.json"]
        for file_path in possible_paths:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=4, ensure_ascii=False)
                break
            except:
                continue
    except Exception as e:
        print(f"❌ Error saving stats: {e}")

# Subscription file operations
def load_subscriptions():
    try:
        possible_paths = [SUBSCRIPTIONS_FILE, "subscriptions.json", "/tmp/subscriptions.json", "./subscriptions.json"]
        for file_path in possible_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        print(f"✅ Loaded subscriptions from {file_path}: {len(data)} users")
                        return data
            except Exception as e:
                print(f"❌ Error loading from {file_path}: {e}")
                continue
        return {}
    except Exception as e:
        print(f"❌ Error loading subscriptions: {e}")
        return {}

def save_subscriptions(subscriptions):
    try:
        possible_paths = [SUBSCRIPTIONS_FILE, "subscriptions.json", "/tmp/subscriptions.json"]
        for file_path in possible_paths:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(subscriptions, f, indent=4, ensure_ascii=False)
                break
            except:
                continue
    except Exception as e:
        print(f"❌ Error saving subscriptions: {e}")

# Subscription functions
def is_user_subscribed(user_id):
    if user_id == ADMIN_ID:
        return True
    
    subscriptions = load_subscriptions()
    user_sub = subscriptions.get(str(user_id), {})
    
    if not user_sub:
        return False
    
    end_date = datetime.fromisoformat(user_sub.get('end_date', '2000-01-01'))
    return datetime.now() < end_date

def get_user_subscription_info(user_id):
    subscriptions = load_subscriptions()
    user_sub = subscriptions.get(str(user_id), {})
    
    if not user_sub:
        return None
    
    end_date = datetime.fromisoformat(user_sub.get('end_date', '2000-01-01'))
    plan_days = user_sub.get('plan_days', 0)
    start_date = datetime.fromisoformat(user_sub.get('start_date', '2000-01-01'))
    
    time_remaining = end_date - datetime.now()
    remaining_days = time_remaining.days
    remaining_hours = time_remaining.seconds // 3600
    remaining_minutes = (time_remaining.seconds % 3600) // 60
    
    return {
        'active': datetime.now() < end_date,
        'end_date': end_date,
        'plan_days': plan_days,
        'start_date': start_date,
        'remaining_days': remaining_days,
        'remaining_hours': remaining_hours,
        'remaining_minutes': remaining_minutes,
        'total_remaining_hours': remaining_days * 24 + remaining_hours
    }

# Async login
async def login_api_async(username, password):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"account": username, "password": password, "identity": "Member"}
            async with session.post(f"{BASE_URL}/user/login", json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "data" in data and "token" in data["data"]:
                        print(f"✅ Login successful for {username}")
                        return data["data"]["token"]
                print(f"❌ Login failed: {username} - Status: {response.status}")
                return None
    except Exception as e:
        print(f"❌ Login error for {username}: {e}")
        return None

# Normalize phone - Improved to extract multiple numbers WITH ORDER PRESERVED
def extract_phone_numbers(text):
    # Find all sequences of digits that could be phone numbers
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\d{10}\b'
    matches = re.findall(phone_pattern, text)
    
    normalized_numbers = []
    seen_numbers = set()  # Track duplicates while preserving order
    
    for match in matches:
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', match)
        
        # Handle country code if present
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        
        if len(digits) == 10 and digits not in seen_numbers:
            normalized_numbers.append(digits)
            seen_numbers.add(digits)
    
    return normalized_numbers  # Return in original order without duplicates
    
async def add_number_async(session, token, cc, phone, retry_count=2):
    for attempt in range(retry_count):
        try:
            headers = {"Admin-Token": token}
            add_url = f"{BASE_URL}/z-number-base/addNum?cc={cc}&phoneNum={phone}&smsStatus=2"
            async with session.post(add_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    print(f"✅ Number {phone} added successfully")
                    return True
                elif response.status == 401:
                    print(f"❌ Token expired during add for {phone}, attempt {attempt + 1}")
                    continue
                elif response.status in (400, 409):
                    print(f"❌ Number {phone} already exists or invalid, status {response.status}")
                    return False
                else:
                    print(f"❌ Add failed for {phone} with status {response.status}")
        except Exception as e:
            print(f"❌ Add number error for {phone} (attempt {attempt + 1}): {e}")
    return False

# Status checking
async def get_status_async(session, token, phone):
    try:
        headers = {"Admin-Token": token}
        status_url = f"{BASE_URL}/z-number-base/getAullNum?page=1&pageSize=15&phoneNum={phone}"
        async with session.get(status_url, headers=headers, timeout=10) as response:
            if response.status == 401:
                print(f"❌ Token expired for {phone}")
                return -1, "❌ Token Expired", None
            
            try:
                res = await response.json()
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error for {phone}: {e}")
                return -2, "❌ API Error", None
            
            if res.get('code') == 28004:
                print(f"❌ Login required for {phone}")
                return -1, "❌ Token Expired", None
            
            if res.get('msg') and any(keyword in res.get('msg').lower() for keyword in ["already exists", "cannot register", "number exists"]):
                print(f"❌ Number {phone} already exists or cannot register")
                return 16, "🚫 Already Exists", None
            if res.get('code') in (400, 409):
                print(f"❌ Number {phone} already exists, code {res.get('code')}")
                return 16, "🚫 Already Exists", None
            
            if (res and "data" in res and "records" in res["data"] and 
                res["data"]["records"] and len(res["data"]["records"]) > 0):
                record = res["data"]["records"][0]
                status_code = record.get("registrationStatus")
                record_id = record.get("id")
                status_name = status_map.get(status_code, f"🔸 Status {status_code}")
                return status_code, status_name, record_id
            
            return None, "🔵 Checking...", None
    except Exception as e:
        print(f"❌ Status error for {phone}: {e}")
        return -2, "🔄 Refresh Server", None

# Async delete
async def delete_single_number_async(session, token, record_id, username):
    try:
        headers = {"Admin-Token": token}
        delete_url = f"{BASE_URL}/z-number-base/deleteNum/{record_id}"
        async with session.delete(delete_url, headers=headers, timeout=10) as response:
            if response.status == 200:
                return True
            else:
                print(f"❌ Delete failed for {record_id}: Status {response.status}")
                return False
    except Exception as e:
        print(f"❌ Delete error for {record_id}: {e}")
        return False

# Account Manager
class AccountManager:
    def __init__(self):
        print("🔄 Initializing Account Manager...")
        self.accounts = load_accounts()
        print(f"📊 Loaded {len(self.accounts)} accounts from storage")
        self.valid_tokens = {}
        self.token_usage = {}
        self.account_passwords = {acc["username"]: acc["password"] for acc in self.accounts}
        
    async def initialize(self):
        print("🔄 Starting account validation...")
        active_count = await self.validate_all_tokens()
        print(f"✅ Account initialization complete: {active_count} active accounts")
        return active_count
        
    async def login_all_accounts(self):
        print("🔄 Logging in all accounts...")
        tasks = [self.login_single_account(account) for account in self.accounts]
        results = await asyncio.gather(*tasks)
        successful_logins = sum(1 for result in results if result)
        save_accounts(self.accounts)
        self.valid_tokens = {}
        self.token_usage = {}
        for account in self.accounts:
            if account.get("token"):
                self.valid_tokens[account["username"]] = account["token"]
                self.token_usage[account["username"]] = 0
        print(f"✅ Login completed: {successful_logins} successful, {len(self.accounts) - successful_logins} failed")
        return successful_logins
    
    async def login_single_account(self, account):
        token = await login_api_async(account["username"], account["password"])
        if token:
            account["token"] = token
            account["last_login"] = datetime.now().isoformat()
            return True
        return False
    
    async def logout_all_accounts(self):
        for account in self.accounts:
            account["token"] = None
            if "last_login" in account:
                del account["last_login"]
        self.valid_tokens = {}
        self.token_usage = {}
        save_accounts(self.accounts)
        print("✅ All accounts logged out")
        return True
    
    async def validate_all_tokens(self):
        async def no_token_task():
            return False, None
        tasks = [self.validate_single_token(account) if account.get("token") else no_token_task() for account in self.accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.valid_tokens = {}
        self.token_usage = {}
        valid_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Exception in token validation for account {self.accounts[i]['username']}: {result}")
                continue
            is_valid, token = result
            if is_valid and token:
                username = self.accounts[i]["username"]
                self.valid_tokens[username] = token
                self.token_usage[username] = 0
                self.accounts[i]["token"] = token
                valid_count += 1
        save_accounts(self.accounts)
        print(f"✅ Token validation: {valid_count} valid tokens")
        return valid_count
    
    async def validate_single_token(self, account):
        if not account.get("token"):
            new_token = await login_api_async(account["username"], account["password"])
            if new_token:
                account["token"] = new_token
                return True, new_token
            return False, None
        try:
            async with aiohttp.ClientSession() as session:
                status_code, _, _ = await get_status_async(session, account["token"], "0000000000")
                if status_code is not None and status_code != -1:
                    return True, account["token"]
            new_token = await login_api_async(account["username"], account["password"])
            if new_token:
                account["token"] = new_token
                return True, new_token
            return False, None
        except Exception as e:
            print(f"❌ Token validation error for {account['username']}: {e}")
            return False, None
    
    def get_next_available_token(self):
        if not self.valid_tokens:
            print("❌ No valid tokens available")
            return None
        available_accounts = [(username, token, self.token_usage.get(username, 0)) 
                            for username, token in self.valid_tokens.items() 
                            if self.token_usage.get(username, 0) < MAX_PER_ACCOUNT]
        if not available_accounts:
            print("❌ All accounts are at maximum usage")
            return None
        best_username, best_token, _ = min(available_accounts, key=lambda x: x[2])
        self.token_usage[best_username] += 1
        print(f"✅ Using token from {best_username}, usage: {self.token_usage[best_username]}/{MAX_PER_ACCOUNT}")
        return best_token, best_username
    
    def release_token(self, username):
        if username in self.token_usage:
            self.token_usage[username] = max(0, self.token_usage[username] - 1)
            print(f"✅ Released token from {username}, usage: {self.token_usage[username]}/{MAX_PER_ACCOUNT}")
    
    def get_active_count(self):
        return len(self.valid_tokens)
    
    def get_remaining_checks(self):
        total_slots = len(self.valid_tokens) * MAX_PER_ACCOUNT
        used_slots = sum(self.token_usage.values())
        remaining = max(0, total_slots - used_slots)
        print(f"📊 Remaining checks: {remaining} (Active: {len(self.valid_tokens)}, Used: {used_slots})")
        return remaining
    
    def get_accounts_status(self):
        return {
            "total": len(self.accounts),
            "active": len(self.valid_tokens),
            "inactive": len(self.accounts) - len(self.valid_tokens),
            "usage": dict(self.token_usage)
        }

# Global account manager
account_manager = AccountManager()

# Subscription functions
async def show_subscription_plans(update: Update, context: CallbackContext, message_id=None):
    keyboard = []
    row = []
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        button = InlineKeyboardButton(
            f"{plan['label']} - {plan['price']}৳", 
            callback_data=f"plan_{plan_id}"
        )
        row.append(button)
        
        # 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:  # Add remaining buttons if any
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "📋 **Select a subscription plan**\n\n"
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        message += f"{plan['label']}\t{plan['price']}৳\n"
    
    if message_id:
        # Edit existing message
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ Error editing message: {e}")
    else:
        # Send new message
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_payment_info(update: Update, context: CallbackContext, plan_id):
    query = update.callback_query
    await query.answer()
    
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    
    if plan:
        message = (
            "আপনি নিচের যেকোনো পদ্ধতিতে পেমেন্ট করতে পারেন:\n\n"
            "💰 Payment:\n"
            "bKash/nagad: 01861887876\n"
            f"Amount: {plan['price']}৳ ({plan['label']})\n"
            f"Reference: {plan_id}day\n"
            "admin: @Notfound_errorx \n\n"
            "পেমেন্টের পর স্ক্রিনশট দিয়ে কনফার্ম করুন।"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_{plan_id}"),
                InlineKeyboardButton("🔙 Back to Plans", callback_data="back_to_plans")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message, 
            reply_markup=reply_markup,
            parse_mode='none'
        )

async def handle_payment_confirmation(update: Update, context: CallbackContext, plan_id):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    
    if plan:
        # Send confirmation message to admin
        keyboard = [
            [
                InlineKeyboardButton("✅ Allow Access", callback_data=f"admin_allow_{user_id}_{plan_id}"),
                InlineKeyboardButton("❌ Deny Access", callback_data=f"admin_deny_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        user_info = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
        
        admin_message = (
            f"🆕 **New Subscription Request**\n\n"
            f"👤 User: {user_info}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📦 Plan: {plan['label']}\n"
            f"💰 Amount: {plan['price']}৳\n\n"
            f"Confirm payment and activate subscription?"
        )
        
        try:
            await context.bot.send_message(
                ADMIN_ID,
                admin_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Notify user
            await query.edit_message_text(
                "✅ **Payment confirmation sent to admin!**\n\n"
                "Admin will activate your subscription soon.\n"
                "You will be notified when it's activated.",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ Error sending admin message: {e}")
            await query.edit_message_text(
                "❌ Error sending confirmation. Please try again later.",
                parse_mode='Markdown'
            )

async def subscription_management(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
        
    subscriptions = load_subscriptions()
    
    if not subscriptions:
        await update.message.reply_text("❌ No active subscriptions!")
        return
    
    message = "📅 **Subscription Management**\n\n"
    
    for user_id, sub_data in subscriptions.items():
        end_date = datetime.fromisoformat(sub_data['end_date'])
        time_remaining = end_date - datetime.now()
        remaining_days = time_remaining.days
        remaining_hours = time_remaining.seconds // 3600
        remaining_minutes = (time_remaining.seconds % 3600) // 60
        
        status = "✅ Active" if remaining_days >= 0 else "❌ Expired"
        
        message += f"👤 User ID: `{user_id}`\n"
        message += f"📅 Plan: {sub_data['plan_days']} days\n"
        message += f"⏰ End: {end_date.strftime('%Y-%m-%d %H:%M')}\n"
        message += f"📊 Status: {status}\n"
        message += f"⏱️ Remaining: {remaining_days}d {remaining_hours}h {remaining_minutes}m\n"
        message += "───\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Subscription", callback_data="admin_add_sub")],
        [InlineKeyboardButton("✏️ Edit Subscription", callback_data="admin_edit_sub")],
        [InlineKeyboardButton("🗑️ Remove Subscription", callback_data="admin_remove_sub")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh_subs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def add_subscription(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: `/addsub user_id days`", parse_mode='Markdown')
        return
        
    try:
        user_id = context.args[0]
        days = int(context.args[1])
        
        subscriptions = load_subscriptions()
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        subscriptions[user_id] = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'plan_days': days,
            'added_by': update.effective_user.id,
            'added_at': datetime.now().isoformat()
        }
        
        save_subscriptions(subscriptions)
        
        await update.message.reply_text(
            f"✅ Subscription added for user `{user_id}`\n"
            f"📅 {days} days\n"
            f"⏰ Valid until: {end_date.strftime('%Y-%m-%d %H:%M')}",
            parse_mode='Markdown'
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                user_id,
                f"🎉 **Your subscription has been activated!**\n\n"
                f"📅 Duration: {days} days\n"
                f"⏰ Valid until: {end_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Use /start to access the bot."
            )
        except Exception as e:
            print(f"❌ Could not notify user {user_id}: {e}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def remove_subscription(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if not context.args:
        await update.message.reply_text("❌ Usage: `/removesub user_id`", parse_mode='Markdown')
        return
        
    try:
        user_id = context.args[0]
        
        subscriptions = load_subscriptions()
        
        if user_id in subscriptions:
            del subscriptions[user_id]
            save_subscriptions(subscriptions)
            
            await update.message.reply_text(
                f"✅ Subscription removed for user `{user_id}`",
                parse_mode='Markdown'
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    user_id,
                    "❌ **Your subscription has been removed!**\n\n"
                    "You no longer have access to the bot.\n"
                    "Please purchase a new subscription to continue."
                )
            except Exception as e:
                print(f"❌ Could not notify user {user_id}: {e}")
        else:
            await update.message.reply_text(
                f"❌ No subscription found for user `{user_id}`",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_subscription_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('plan_'):
        plan_id = data.split('_')[1]
        await show_payment_info(update, context, plan_id)
    
    elif data.startswith('confirm_'):
        plan_id = data.split('_')[1]
        await handle_payment_confirmation(update, context, plan_id)
    
    elif data == "back_to_plans":
        await show_subscription_plans(update, context, query.message.message_id)
    
    elif data.startswith('admin_allow_'):
        # Format: admin_allow_userId_planId
        parts = data.split('_')
        user_id = parts[2]
        plan_id = parts[3]
        
        plan = SUBSCRIPTION_PLANS.get(plan_id)
        
        if plan:
            subscriptions = load_subscriptions()
            start_date = datetime.now()
            end_date = start_date + timedelta(days=plan['days'])
            
            subscriptions[user_id] = {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'plan_days': plan['days'],
                'added_by': query.from_user.id,
                'added_at': datetime.now().isoformat()
            }
            
            save_subscriptions(subscriptions)
            
            # Notify admin
            await query.edit_message_text(
                f"✅ Subscription activated for user `{user_id}`\n"
                f"📅 Plan: {plan['label']}\n"
                f"⏰ Valid until: {end_date.strftime('%Y-%m-%d %H:%M')}",
                parse_mode='Markdown'
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    user_id,
                    f"🎉 **Your subscription has been activated!**\n\n"
                    f"📅 Plan: {plan['label']}\n"
                    f"⏰ Valid until: {end_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"You can now use the bot. Send /start to begin!"
                )
            except Exception as e:
                print(f"❌ Could not notify user {user_id}: {e}")
    
    elif data.startswith('admin_deny_'):
        user_id = data.split('_')[2]
        
        # Notify admin
        await query.edit_message_text(
            f"❌ Subscription request denied for user `{user_id}`",
            parse_mode='Markdown'
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                user_id,
                "❌ **Your subscription request was denied!**\n\n"
                "Please contact admin for more information."
            )
        except Exception as e:
            print(f"❌ Could not notify user {user_id}: {e}")
    
    elif data == "admin_add_sub":
        await query.edit_message_text(
            "👤 User ID এবং দিন সংখ্যা পাঠান এই ফরম্যাটে:\n"
            "`/addsub user_id days`\n\n"
            "যেমন: `/addsub 123456789 30`",
            parse_mode='Markdown'
        )
    
    elif data == "admin_remove_sub":
        await query.edit_message_text(
            "👤 User ID পাঠান এই ফরম্যাটে:\n"
            "`/removesub user_id`\n\n"
            "যেমন: `/removesub 123456789`",
            parse_mode='Markdown'
        )
    
    elif data == "admin_refresh_subs":
        await subscription_management(update, context)

# Track status
async def track_status_optimized(context: CallbackContext):
    data = context.job.data
    phone = data['phone']
    token = data['token']
    username = data['username']
    checks = data['checks']
    last_status = data.get('last_status', '🔵 Processing...')
    serial_number = data.get('serial_number')
    
    try:
        async with aiohttp.ClientSession() as session:
            status_code, status_name, record_id = await get_status_async(session, token, phone)
        
        prefix = f"{serial_number}. " if serial_number else ""
        
        if status_code == -1:
            account_manager.release_token(username)
            error_text = f"{prefix}`{phone}` ❌ Token Error (Auto-Retry)"
            try:
                await context.bot.edit_message_text(
                    chat_id=data['chat_id'], 
                    message_id=data['message_id'],
                    text=error_text,
                    parse_mode='Markdown'
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    print(f"❌ Message update failed for {phone}: {e}")
            return
        
        if status_name != last_status:
            new_text = f"{prefix}`{phone}` {status_name}"
            try:
                await context.bot.edit_message_text(
                    chat_id=data['chat_id'], 
                    message_id=data['message_id'],
                    text=new_text,
                    parse_mode='Markdown'
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    print(f"❌ Message update failed for {phone}: {e}")
        
        final_states = [0, 1, 4, 7, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        if status_code in final_states:
            account_manager.release_token(username)
            deleted_count = await delete_number_from_all_accounts_optimized(phone)
            final_text = f"{prefix}`{phone}` {status_name}"
            try:
                await context.bot.edit_message_text(
                    chat_id=data['chat_id'], 
                    message_id=data['message_id'],
                    text=final_text,
                    parse_mode='Markdown'
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    print(f"❌ Final message update failed for {phone}: {e}")
            return
        
        if checks >= 6:
            account_manager.release_token(username)
            deleted_count = await delete_number_from_all_accounts_optimized(phone)
            timeout_text = f"{prefix}`{phone}` 🟡 Try leter "
            try:
                await context.bot.edit_message_text(
                    chat_id=data['chat_id'], 
                    message_id=data['message_id'],
                    text=timeout_text,
                    parse_mode='Markdown'
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    print(f"❌ Timeout message update failed for {phone}: {e}")
            return
        
        if context.job_queue:
            context.job_queue.run_once(
                track_status_optimized, 
                1,
                data={
                    **data, 
                    'checks': checks + 1, 
                    'last_status': status_name
                }
            )
        else:
            print("❌ JobQueue not available, cannot schedule status check")
    except Exception as e:
        print(f"❌ Tracking error for {phone}: {e}")
        account_manager.release_token(username)

# Bulk delete
async def delete_number_from_all_accounts_optimized(phone):
    accounts = load_accounts()
    deleted_count = 0
    async with aiohttp.ClientSession() as session:
        tasks = []
        for account in accounts:
            if account.get("token"):
                tasks.append(delete_if_exists(session, account["token"], phone, account['username']))
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if result is True:
                    deleted_count += 1
        stats = load_stats()
        stats["total_deleted"] += deleted_count
        stats["today_deleted"] += deleted_count
        save_stats(stats)
        print(f"✅ Deleted {phone} from {deleted_count} accounts")
        return deleted_count

async def delete_if_exists(session, token, phone, username):
    try:
        status_code, _, record_id = await get_status_async(session, token, phone)
        if record_id:
            return await delete_single_number_async(session, token, record_id, username)
        return True
    except Exception as e:
        print(f"❌ Delete check error for {phone} in {username}: {e}")
        return False

# Daily stats reset
async def reset_daily_stats(context: CallbackContext):
    stats = load_stats()
    stats["today_checked"] = 0
    stats["today_deleted"] = 0
    stats["last_reset"] = datetime.now().isoformat()
    save_stats(stats)
    print("✅ Daily stats reset")

# Subscription expiry check
async def check_subscription_expiry(context: CallbackContext):
    """Check for expiring subscriptions and send notifications"""
    subscriptions = load_subscriptions()
    now = datetime.now()
    
    for user_id, sub_data in subscriptions.items():
        end_date = datetime.fromisoformat(sub_data['end_date'])
        time_remaining = end_date - now
        remaining_hours = time_remaining.total_seconds() / 3600
        
        # Notify when 1 hour remaining
        if 0 < remaining_hours <= 1:
            try:
                await context.bot.send_message(
                    int(user_id),
                    "⚠️ **Subscription Expiring Soon!**\n\n"
                    "Your subscription will expire in 1 hour.\n"
                    "Please renew to continue using the bot.\n\n"
                    "Use /start to view subscription plans."
                )
            except Exception as e:
                print(f"❌ Could not send expiry notification to {user_id}: {e}")
        
        
# Bot command handlers
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        keyboard = [
            [KeyboardButton("➕ অ্যাকাউন্ট যোগ"), KeyboardButton("📋 অ্যাকাউন্ট লিস্ট")],
            [KeyboardButton("🚀 Refresh Server"), KeyboardButton("🚪 ওয়ান-ক্লিক লগআউট")],
            [KeyboardButton("📊 Statistics"), KeyboardButton("👥 User Management")],
            [KeyboardButton("📅 Subscription Management"), KeyboardButton("🔄 রিস্টার্ট বট")],
            [KeyboardButton("❓ সাহায্য")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        accounts_status = account_manager.get_accounts_status()
        active = accounts_status["active"]
        remaining = account_manager.get_remaining_checks()
        await update.message.reply_text(
            f"🔥 **নম্বর চেকার বট** 👑\n\n"
            f"📱 **Total Server:** {accounts_status['total']}\n"
            f"✅ **Active Accounts:** {active}\n"
            f"⚡ **Remaining Checks:** {remaining}\n\n"
            f"📱 **নম্বর পাঠান** যেকোনো format এ",
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
        return
        
    # Check subscription for regular users
    if not is_user_subscribed(user_id):
        await show_subscription_plans(update, context)
        return
        
    # Regular users with active subscription - তাদেরও কিছু menu options থাকবে
    keyboard = [
        [KeyboardButton("🚀 Refresh Server"),
        KeyboardButton("📊 Statistics")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    accounts_status = account_manager.get_accounts_status()
    active = account_manager.get_active_count()
    remaining = account_manager.get_remaining_checks()
    sub_info = get_user_subscription_info(user_id)
    
    await update.message.reply_text(
        f"🔥 WA Number Checker\n\n"
        f"📱 **Active Server:** {active}\n"
        f"✅ **Remaining checks:** {remaining}\n"
        f"📅 **Your Subscription:** {sub_info['remaining_days']}d {sub_info['remaining_hours']}h {sub_info['remaining_minutes']}m remaining\n\n"
        f"📱 **নম্বর পাঠান** যেকোনো format এ",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_stats(update: Update, context: CallbackContext) -> None:
    if not is_user_subscribed(update.effective_user.id):
        await show_subscription_plans(update, context)
        return
    
    user_id = update.effective_user.id
    stats = load_stats()
    accounts_status = account_manager.get_accounts_status()
    
    # User এর subscription info নিন
    sub_info = get_user_subscription_info(user_id)
    
    # Admin এবং regular user এর জন্য আলাদা message
    if user_id == ADMIN_ID:
        message = (
            f"📊 **Statistics Dashboard** 👑\n\n"
            f"🔢 **Total Checked:** {stats['total_checked']}\n"
            f"🗑️ **Total Deleted:** {stats['total_deleted']}\n"
            f"📅 **Today Checked:** {stats['today_checked']}\n"
            f"🗑️ **Today Deleted:** {stats['today_deleted']}\n\n"
            f"📱 **Account Status:**\n"
            f"• Total: {accounts_status['total']}\n"
            f"• Active: {accounts_status['active']}\n"
            f"• Inactive: {accounts_status['inactive']}\n"
            f"• Current Usage: {sum(accounts_status['usage'].values())}/{accounts_status['active'] * MAX_PER_ACCOUNT}\n\n"
            f"⚡ **Remaining Checks:** {account_manager.get_remaining_checks()}"
        )
    else:
        # Regular user এর জন্য subscription status সহ message
        if sub_info and sub_info['active']:
            subscription_status = (
                f"📅 **Subscription Status:** ✅ Active\n"
                f"⏰ **Remaining Time:** {sub_info['remaining_days']}d {sub_info['remaining_hours']}h {sub_info['remaining_minutes']}m\n"
                f"📆 **Valid Until:** {sub_info['end_date'].strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            subscription_status = "📅 **Subscription Status:** ❌ Inactive"
        
        message = (
            f"📊 **Statistics Dashboard**\n\n"
            f"🔢 **Total Checked:** {stats['total_checked']}\n"
            
            f"📅 **Today Checked:** {stats['today_checked']}\n\n"
           
            f"{subscription_status}\n\n"
            f"📱 **Server Status:**\n"
            f"• Active Servers: {accounts_status['active']}\n"
            f"• Available Checks: {account_manager.get_remaining_checks()}"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def admin_users(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    users = load_users()
    
    # Ensure users is a dictionary
    if not isinstance(users, dict):
        users = {}
        
    if not users:
        await update.message.reply_text("❌ No users in database!")
        return
    keyboard = []
    for user_id, user_data in users.items():
        if int(user_id) == ADMIN_ID:
            continue
        status = "✅" if user_data["approved"] else "⏳" if user_data["pending"] else "❌"
        button_text = f"{status} {user_data['username']}"
        if user_data["pending"]:
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"user_{user_id}"),
                InlineKeyboardButton("✅ Allow", callback_data=f"allow_{user_id}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"deny_{user_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"user_{user_id}"),
                InlineKeyboardButton("🔄 Toggle", callback_data=f"toggle_{user_id}")
            ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "👥 **User Management**\n\n"
    msg += "✅ - Approved\n⏳ - Pending\n❌ - Denied\n\n"
    msg += "Click buttons to manage users:"
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_approval(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Only admin can use these buttons!")
        return
    data = query.data
    user_id = int(data.split('_')[1])
    users = load_users()
    
    # Ensure users is a dictionary
    if not isinstance(users, dict):
        users = {}
        
    if data.startswith('allow_'):
        users[str(user_id)]["approved"] = True
        users[str(user_id)]["pending"] = False
        save_users(users)
        await query.edit_message_text(
            f"✅ User {users[str(user_id)]['username']} has been approved!"
        )
        await context.bot.send_message(
            user_id,
            "✅ Your access has been approved by admin! Use /start to begin."
        )
    elif data.startswith('deny_'):
        users[str(user_id)]["approved"] = False
        users[str(user_id)]["pending"] = False
        save_users(users)
        await query.edit_message_text(
            f"❌ User {users[str(user_id)]['username']} has been denied!"
        )
        await context.bot.send_message(
            user_id,
            "❌ Your access request has been denied by admin."
        )

async def handle_user_management(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Only admin can use these buttons!")
        return
    data = query.data
    if data.startswith('user_'):
        user_id = data.split('_')[1]
        users = load_users()
        
        # Ensure users is a dictionary
        if not isinstance(users, dict):
            users = {}
            
        user_data = users.get(user_id, {})
        status = "✅ Approved" if user_data.get("approved") else "⏳ Pending" if user_data.get("pending") else "❌ Denied"
        await query.edit_message_text(
            f"👤 **User Details**\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"📛 Name: {user_data.get('username', 'N/A')}\n"
            f"📊 Status: {status}",
            parse_mode='Markdown'
        )
    elif data.startswith('toggle_'):
        user_id = data.split('_')[1]
        users = load_users()
        
        # Ensure users is a dictionary
        if not isinstance(users, dict):
            users = {}
            
        if user_id in users:
            users[user_id]["approved"] = not users[user_id]["approved"]
            users[user_id]["pending"] = False
            save_users(users)
            status = "✅ Approved" if users[user_id]["approved"] else "❌ Denied"
            await query.edit_message_text(
                f"🔄 User {users[user_id]['username']} status changed to: {status}"
            )

async def add_account(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    await update.message.reply_text("👤 `username:password` পাঠান\nযেমন: `HasanCA:HasanCA`", parse_mode='Markdown')

async def list_accounts(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("❌ কোনো অ্যাকাউন্ট নেই!")
        return
    accounts_status = account_manager.get_accounts_status()
    msg = "📋 **অ্যাকাউন্ট লিস্ট:**\n\n"
    for i, acc in enumerate(accounts, 1):
        status = "✅ লগইন" if acc['username'] in account_manager.valid_tokens else "❌ লগআউট"
        usage = accounts_status['usage'].get(acc['username'], 0)
        msg += f"{i}. `{acc['username']}` - {status} (Usage: {usage}/{MAX_PER_ACCOUNT})\n"
    msg += f"\n**সারাংশ:**\n"
    msg += f"• মোট অ্যাকাউন্ট: {accounts_status['total']}\n"
    msg += f"• এক্টিভ: {accounts_status['active']}\n"
    msg += f"• ইনএক্টিভ: {accounts_status['inactive']}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def one_click_login(update: Update, context: CallbackContext) -> None:
    # Admin এবং subscribed users উভয়ই access পাবে
    if update.effective_user.id != ADMIN_ID and not is_user_subscribed(update.effective_user.id):
        await update.message.reply_text("❌ Subscription required! Please purchase a subscription to use this feature.")
        return
        
    processing_msg = await update.message.reply_text("🔄 Proccessing...")
    successful_logins = await account_manager.login_all_accounts()
    accounts_status = account_manager.get_accounts_status()
    await processing_msg.edit_text(
        f"✅ Server Refresh Successfull\n\n"
        f"📊 Result:\n"
        f"• Success: {successful_logins}\n"
        f"• Failed: {len(account_manager.accounts) - successful_logins}\n"
        f"• Total active: {accounts_status['active']}\n\n"
        f"⚡ Available Checks: {account_manager.get_remaining_checks()}"
    )

async def one_click_logout(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    processing_msg = await update.message.reply_text("🔄 সব অ্যাকাউন্ট লগআউট করা হচ্ছে...")
    await account_manager.logout_all_accounts()
    await processing_msg.edit_text(
        "✅ **সব অ্যাকাউন্ট সফলভাবে লগআউট করা হয়েছে!**\n\n"
        "আপনি আবার লগইন করতে চাইলে \"🚀 Refresh Server\" বাটন ব্যবহার করুন।"
    )

async def restart_bot(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    await update.message.reply_text("🔄 বট রিস্টার্ট করা হচ্ছে...")
    await account_manager.initialize()
    accounts_status = account_manager.get_accounts_status()
    await update.message.reply_text(
        f"✅ **বট সফলভাবে রিস্টার্ট হয়েছে!**\n\n"
        f"📊 **কারেন্ট স্ট্যাটাস:**\n"
        f"• এক্টিভ অ্যাকাউন্ট: {accounts_status['active']}\n"
        f"• Available Checks: {account_manager.get_remaining_checks()}\n"
        f"• মোট অ্যাকাউন্ট: {accounts_status['total']}"
    )

async def logout_account(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    if not context.args:
        await update.message.reply_text("🚪 `/logout username`")
        return
    username = context.args[0]
    accounts = load_accounts()
    for acc in accounts:
        if acc["username"] == username:
            acc["token"] = None
            if username in account_manager.valid_tokens:
                del account_manager.valid_tokens[username]
            if username in account_manager.token_usage:
                del account_manager.token_usage[username]
            save_accounts(accounts)
            await update.message.reply_text(f"✅ `{username}` লগআউট!")
            return
    await update.message.reply_text("❌ অ্যাকাউন্ট পাওয়া যায়নি!")



# Async number adding with serial number
async def async_add_number_optimized(token, phone, msg, username, serial_number=None):
    try:
        async with aiohttp.ClientSession() as session:
            added = await add_number_async(session, token, 11, phone)
            prefix = f"{serial_number}. " if serial_number else ""
            if added:
                await msg.edit_text(f"{prefix}`{phone}` 🔵 In Progress", parse_mode='Markdown')
            else:
                status_code, status_name, record_id = await get_status_async(session, token, phone)
                if status_code == 16:
                    await msg.edit_text(f"{prefix}`{phone}` 🚫 Already Exists", parse_mode='Markdown')
                    account_manager.release_token(username)
                    return
                await msg.edit_text(f"{prefix}`{phone}` ❌ Add Failed", parse_mode='Markdown')
                account_manager.release_token(username)
    except Exception as e:
        print(f"❌ Add error for {phone}: {e}")
        prefix = f"{serial_number}. " if serial_number else ""
        await msg.edit_text(f"{prefix}`{phone}` ❌ Add Failed", parse_mode='Markdown')
        account_manager.release_token(username)

# Process multiple numbers from a single message
async def process_multiple_numbers(update: Update, context: CallbackContext, text: str):
    """Process multiple phone numbers from a single message"""
    numbers = extract_phone_numbers(text)
    
    if not numbers:
        await update.message.reply_text("❌ কোনো ভ্যালিড নম্বর পাওয়া যায়নি!")
        return
    
    # Start processing immediately without any notification message - JUST LIKE BEFORE
    for index, phone in enumerate(numbers, 1):
        if account_manager.get_remaining_checks() <= 0:
            # Only notify if all accounts are full
            await update.message.reply_text(f"❌ All accounts full! Max {account_manager.get_active_count() * MAX_PER_ACCOUNT}")
            break
            
        token_data = account_manager.get_next_available_token()
        if not token_data:
            # Only notify if no accounts available
            await update.message.reply_text("❌ No available accounts! Please login first.")
            break
            
        token, username = token_data
        stats = load_stats()
        stats["total_checked"] += 1
        stats["today_checked"] += 1
        save_stats(stats)
        
        # Only change: add serial number to the message
        msg = await update.message.reply_text(f"{index}. `{phone}` 🔵 Processing...", parse_mode='Markdown')
        asyncio.create_task(async_add_number_optimized(token, phone, msg, username, index))
        
        if context.job_queue:
            context.job_queue.run_once(
                track_status_optimized, 
                2,
                data={
                    'chat_id': update.message.chat_id,
                    'message_id': msg.message_id,
                    'phone': phone,
                    'token': token,
                    'username': username,
                    'checks': 0,
                    'last_status': '🔵 Processing...',
                    'serial_number': index
                }
            )
            
async def handle_message_optimized(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # Admin এবং subscribed users উভয়ই access পাবে
    if user_id != ADMIN_ID and not is_user_subscribed(user_id):
        await show_subscription_plans(update, context)
        return
    
    text = update.message.text.strip()
    
    # Handle menu buttons (admin এবং subscribed users উভয়ের জন্য)
    if user_id == ADMIN_ID or is_user_subscribed(user_id):
        if text == "🚀 Refresh Server":
            await one_click_login(update, context)
            return
        if text == "📊 Statistics":
            await show_stats(update, context)
            return
        
    
    # Handle menu buttons (শুধু admin এর জন্য)
    if user_id == ADMIN_ID:
        if text == "👥 User Management":
            await admin_users(update, context)
            return
        if text == "📅 Subscription Management":
            await subscription_management(update, context)
            return
        if text == "🚪 ওয়ান-ক্লিক লগআউট":
            await one_click_logout(update, context)
            return
        if text == "🔄 রিস্টার্ট বট":
            await restart_bot(update, context)
            return
        if text == "➕ অ্যাকাউন্ট যোগ":
            await add_account(update, context)
            return
        if text == "📋 অ্যাকাউন্ট লিস্ট":
            await list_accounts(update, context)
            return
    
    # Handle account addition (username:password) - only for admin
    if ':' in text and len(text.split(':')) == 2:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only command!")
            return
        username, password = text.split(':')
        token = await login_api_async(username, password)
        if token:
            accounts = load_accounts()
            account_exists = False
            for acc in accounts:
                if acc["username"] == username:
                    acc["password"] = password
                    acc["token"] = token
                    account_exists = True
                    break
            if not account_exists:
                accounts.append({"username": username, "password": password, "token": token})
            save_accounts(accounts)
            await account_manager.initialize()
            await update.message.reply_text(f"✅ `{username}` যোগ! Total: {len(accounts)}")
        else:
            await update.message.reply_text("❌ লগইন ফেইল! ইউজারনেম/পাসওয়ার্ড চেক করুন।")
        return
    
    # Handle phone numbers (single or multiple)
    numbers = extract_phone_numbers(text)
    if numbers:
        if len(numbers) == 1:
            # Single number processing
            phone = numbers[0]
            if account_manager.get_remaining_checks() <= 0:
                await update.message.reply_text(f"❌ All accounts full! Max {account_manager.get_active_count() * MAX_PER_ACCOUNT}")
                return
            token_data = account_manager.get_next_available_token()
            if not token_data:
                await update.message.reply_text("❌ No available accounts! Please login first.")
                return
            token, username = token_data
            stats = load_stats()
            stats["total_checked"] += 1
            stats["today_checked"] += 1
            save_stats(stats)
            msg = await update.message.reply_text(f"`{phone}` 🔵 Processing...", parse_mode='Markdown')
            asyncio.create_task(async_add_number_optimized(token, phone, msg, username))
            if context.job_queue:
                context.job_queue.run_once(
                    track_status_optimized, 
                    2,
                    data={
                        'chat_id': update.message.chat_id,
                        'message_id': msg.message_id,
                        'phone': phone,
                        'token': token,
                        'username': username,
                        'checks': 0,
                        'last_status': '🔵 Processing...'
                    }
                )
        else:
            # Multiple numbers processing with serial numbers
            await process_multiple_numbers(update, context, text)
        return
    
    # If no numbers found and not a command
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("❓ নম্বর পাঠান বা মেনু ব্যবহার করুন!")
    else:
        # Subscribed users কেও menu options remind করবে
        await update.message.reply_text("❓ নম্বর পাঠান বা মেনু বাটন ব্যবহার করুন!")

# Run FastAPI server
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=10000)

def main():
    # Start FastAPI server in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    print("🌐 FastAPI server started on port 10000")
    
    # Initialize bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def initialize_bot():
        await account_manager.initialize()
        
        # Start enhanced keep-alive system
        asyncio.create_task(keep_alive_enhanced())
        asyncio.create_task(random_ping()) 
        asyncio.create_task(immediate_ping())
        
        print("🤖 Bot initialized successfully with enhanced keep-alive!")
    
    loop.run_until_complete(initialize_bot())
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add all handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("logout", logout_account))
    application.add_handler(CommandHandler("admin_users", admin_users))
    application.add_handler(CommandHandler("restart", restart_bot))
    application.add_handler(CommandHandler("addsub", add_subscription))
    application.add_handler(CommandHandler("removesub", remove_subscription))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_optimized))
    application.add_handler(CallbackQueryHandler(handle_approval, pattern=r"^(allow|deny)_"))
    application.add_handler(CallbackQueryHandler(handle_user_management, pattern=r"^(user|toggle)_"))
    application.add_handler(CallbackQueryHandler(handle_subscription_callback, pattern=r"^(plan_|confirm_|admin_|back_to_plans)"))
    
    if application.job_queue:
        application.job_queue.run_repeating(reset_daily_stats, interval=86400, first=0)
        application.job_queue.run_repeating(check_subscription_expiry, interval=1800, first=0)  # Check every 30 minutes
    else:
        print("❌ JobQueue not available, daily stats reset not scheduled")
    
    print("🚀 Bot starting polling with 24/7 keep-alive...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
