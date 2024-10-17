import os
import stripe
import threading
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from contextlib import contextmanager
import logging
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
endpoint_secret = os.getenv('STRIPE_PAYMENT_WEBHOOK_SECRET')
DJ_BOT_PRODUCT_ID = 'prod_R2mETUJ7RTWF4t'

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Define SQLAlchemy models for users table
class User(Base):
    __tablename__ = 'users'
    discord_id = Column(String(50), primary_key=True)
    active_subscription = Column(Boolean, default=False)
    email = Column(String(255), nullable=True)
    subscription_start_date = Column(DateTime(timezone=True), nullable=True)

Base.metadata.create_all(engine)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Error during session scope: {e}")
        raise
    finally:
        session.close()

# Logging setup
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    logging.info(f"Received webhook: {payload}")
    logging.info(f"Signature header: {sig_header}")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        logging.error(f"Error verifying webhook: {e}")
        return jsonify({'error': 'Webhook verification failed'}), 400

    thread = threading.Thread(target=process_event, args=(event,))
    thread.start()

    return jsonify({'status': 'success'}), 200

def process_event(event):
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_checkout_session(session)
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            handle_subscription_update(subscription)
    except Exception as e:
        logging.error(f"Error processing event: {e}")

def handle_checkout_session(session):
    logging.info("Processing checkout.session.completed")
    customer_email = session['customer_details'].get('email')
    
    # Retrieve custom field for discord_id
    custom_fields = session.get('custom_fields', [])
    discord_id = next(
        (field['text']['value'] for field in custom_fields if field['key'] == 'discorduseridnotyourusername'),
        None
    )
    subscription_id = session.get('subscription')

    if not discord_id:
        logging.error("No Discord ID found in custom fields.")
        return

    try:
        line_items = stripe.checkout.Session.list_line_items(session['id'])
        product_id = line_items['data'][0]['price']['product']
        
        if product_id == DJ_BOT_PRODUCT_ID:
            with session_scope() as db_session:
                user = db_session.query(User).filter_by(discord_id=discord_id).first()
                if not user:
                    user = User(
                        discord_id=discord_id,
                        active_subscription=True,
                        email=customer_email,
                        subscription_start_date=datetime.now(timezone.utc)
                    )
                    db_session.add(user)
                else:
                    user.active_subscription = True
                    user.subscription_start_date = datetime.now(timezone.utc)
                logging.info(f"User {discord_id} subscription updated.")
    except Exception as e:
        logging.error(f"Error handling checkout session: {e}")

def handle_subscription_update(subscription):
    logging.info("Processing customer.subscription.updated")
    discord_id = subscription['metadata'].get('discorduseridnotyourusername')
    product_id = subscription['items']['data'][0]['price']['product']
    status = subscription['status']

    if product_id != DJ_BOT_PRODUCT_ID:
        return

    with session_scope() as db_session:
        user = db_session.query(User).filter_by(discord_id=discord_id).first()
        if user:
            user.active_subscription = status == 'active'
            if user.active_subscription:
                user.subscription_start_date = datetime.now(timezone.utc)
            logging.info(f"User {discord_id} status updated to {user.active_subscription}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5440)
