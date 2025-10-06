from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests, uuid, os, random
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

# In-memory user & wallet database (for demo)
users = {}
wallets = {}

# ---------- HOME ----------
@app.route('/')
def index():
    return render_template('index.html')

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if email in users:
            flash('Email already registered. Try logging in.')
            return redirect(url_for('login'))

        users[email] = {'username': username, 'email': email, 'password': password}
        wallets[email] = {'balance': 0, 'data': 500}

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.get(email)
        if user and check_password_hash(user['password'], password):
            session['user'] = email
            flash(f"Welcome back, {user['username']}!")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')
            return redirect(url_for('login'))
    return render_template('login.html')

# ---------- RESET PASSWORD ----------
@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        email = request.form['email']
        if email not in users:
            flash("Email not found.")
            return redirect(url_for('reset'))
        flash("Password reset link sent to your email (simulation).")
        return redirect(url_for('login'))
    return render_template('reset.html')

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access your dashboard.')
        return redirect(url_for('login'))

    email = session['user']
    wallet = wallets[email]

    if 'account_number' not in session:
        session['account_number'] = random.randint(1000000000, 9999999999)
        session['bank_name'] = random.choice(["GTBank", "Access Bank", "UBA", "Opay", "Moniepoint"])

    return render_template(
        'dashboard.html',
        wallet=wallet,
        account_number=session['account_number'],
        bank_name=session['bank_name']
    )

# ---------- FUND WALLET ----------
@app.route('/fund', methods=['GET', 'POST'])
def fund_wallet():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    email = session['user']

    if request.method == 'POST':
        pay_email = email
        amount = int(request.form['amount']) * 100

        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "email": pay_email,
            "amount": amount,
            "reference": str(uuid.uuid4()),
            "callback_url": url_for('fund_callback', _external=True)
        }

        response = requests.post('https://api.paystack.co/transaction/initialize', json=data, headers=headers)
        res_data = response.json()

        if res_data.get('status'):
            return redirect(res_data['data']['authorization_url'])
        else:
            flash("Payment initialization failed. Try again.")
            return redirect(url_for('fund_wallet'))

    account_number = session.get('account_number', random.randint(1000000000, 9999999999))
    bank_name = session.get('bank_name', "Opay")
    return render_template('fund.html', account_number=account_number, bank_name=bank_name)

# ---------- CALLBACK ----------
@app.route('/fund/callback')
def fund_callback():
    email = session.get('user')
    if not email:
        return redirect(url_for('login'))

    reference = request.args.get('reference')
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    res_data = response.json()

    if res_data.get('status') and res_data['data']['status'] == 'success':
        wallets[email]['balance'] += res_data['data']['amount'] / 100
        flash("Wallet funded successfully!")
        return redirect(url_for('dashboard'))
    else:
        flash("Payment verification failed.")
        return redirect(url_for('fund_wallet'))

# ---------- AIRTIME ----------
@app.route('/airtime', methods=['GET', 'POST'])
def airtime():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    email = session['user']
    wallet = wallets[email]

    if request.method == 'POST':
        amount = int(request.form['amount'])
        if wallet['balance'] >= amount:
            wallet['balance'] -= amount
            flash(f"Airtime of ₦{amount} purchased successfully!")
        else:
            flash("Insufficient balance. Please fund your wallet.")
    return render_template('airtime.html')

# ---------- DATA ----------
@app.route('/data', methods=['GET', 'POST'])
def data():
    if 'user' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    email = session['user']
    wallet = wallets[email]

    if request.method == 'POST':
        network = request.form['network']
        phone = request.form['phone']
        plan = request.form['plan']
        pin = request.form['pin']

        # For demo purposes, assume each plan costs a fixed price
        plan_prices = {
            '500MB': 200,
            '1GB': 300,
            '2GB': 500,
            '3GB': 700,
            '5GB': 1200,
            '1.5GB': 500
        }
        amount = plan_prices.get(plan, 300)

        if wallet['balance'] >= amount:
            wallet['balance'] -= amount
            flash(f"✅ {network} {plan} data purchased successfully for {phone}!")
        else:
            flash("❌ Insufficient balance. Please fund your wallet.")

        return redirect(url_for('data'))

    return render_template('data.html')
# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
