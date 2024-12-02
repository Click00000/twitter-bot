# PARÇA 1
import os
from flask import Flask, render_template, request, redirect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from concurrent.futures import ThreadPoolExecutor
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import random
from profile_tracker import load_tracked_profiles, save_tracked_profiles

template_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(template_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

def get_active_accounts():
    with open('accounts.json', 'r') as f:
        accounts = json.load(f)
    return len(accounts['accounts'])

def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'})
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver
# PARÇA 2
def twitter_login(driver, username, password):
    try:
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(4)
        
        username_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
        )
        username_input.clear()
        username_input.send_keys(username)
        time.sleep(1)
        username_input.send_keys(Keys.ENTER)
        print(f"✅ {username} için kullanıcı adı girildi ve ENTER tuşuna basıldı")
        time.sleep(2)
        
        password_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
        )
        password_input.send_keys(password)
        time.sleep(1)
        password_input.send_keys(Keys.ENTER)
        print(f"✅ {username} için şifre girildi ve ENTER tuşuna basıldı")
        time.sleep(4)
        
        try:
            WebDriverWait(driver, 15).until(
                lambda x: "home" in x.current_url
            )
            print(f"✅ {username} için giriş başarılı!")
            return True
        except:
            print(f"❌ {username} için giriş başarısız - Ana sayfa yüklenemedi")
            return False
            
    except Exception as e:
        print(f"❌ Login hatası ({username}): {str(e)}")
        return False

def like_tweet(driver, tweet_url):
    try:
        driver.get(tweet_url)
        time.sleep(3)
        like_button = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='like']"))
        )
        driver.execute_script("arguments[0].click();", like_button)
        time.sleep(1)
        print("Like işlemi başarılı")
        return True
    except Exception as e:
        print(f"Like hatası: {str(e)}")
        return False

def retweet(driver, tweet_url):
    try:
        driver.get(tweet_url)
        time.sleep(3)
        retweet_button = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='retweet']"))
        )
        driver.execute_script("arguments[0].click();", retweet_button)
        time.sleep(1)
        retweet_confirm = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='retweetConfirm']"))
        )
        driver.execute_script("arguments[0].click();", retweet_confirm)
        time.sleep(1)
        print("Retweet işlemi başarılı")
        return True
    except Exception as e:
        print(f"Retweet hatası: {str(e)}")
        return False
# PARÇA 3
def process_account(account, url, action_type):
    driver = setup_driver()
    try:
        if twitter_login(driver, account['username'], account['password']):
            if action_type == 'like':
                return like_tweet(driver, url)
            elif action_type == 'retweet':
                return retweet(driver, url)
    finally:
        driver.quit()

@app.route('/')
def home():
    active_accounts = get_active_accounts()
    tracked_profiles = load_tracked_profiles()['tracked_profiles']
    return render_template('index.html', 
                         active_accounts=active_accounts,
                         tracked_profiles=tracked_profiles)

@app.route('/process_engagement', methods=['POST'])
def process_engagement():
    tweet_url = request.form['tweet_url']
    like_count = int(request.form['like_count'])
    retweet_count = int(request.form['retweet_count'])
    
    with open('accounts.json', 'r') as f:
        accounts = json.load(f)['accounts']
    
    success_likes = 0
    success_retweets = 0
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        if like_count > 0:
            selected_for_like = random.sample(accounts, min(like_count, len(accounts)))
            like_futures = [executor.submit(process_account, account, tweet_url, 'like') 
                          for account in selected_for_like]
            success_likes = sum(1 for future in like_futures if future.result())
            
        if retweet_count > 0:
            selected_for_retweet = random.sample(accounts, min(retweet_count, len(accounts)))
            retweet_futures = [executor.submit(process_account, account, tweet_url, 'retweet') 
                             for account in selected_for_retweet]
            success_retweets = sum(1 for future in retweet_futures if future.result())
    
    return f"Etkileşim işlemi tamamlandı! {success_likes} like, {success_retweets} retweet başarılı."

@app.route('/add_profile', methods=['POST'])
def add_profile():
    from profile_tracker import start_tracking
    
    profile_data = {
        "profile_url": request.form['profile_url'],
        "like_count": int(request.form['like_count']),
        "retweet_count": int(request.form['retweet_count']),
        "check_interval": int(request.form['check_interval']),
        "last_tweet_id": None,
        "is_active": True
    }
    
    data = load_tracked_profiles()
    data['tracked_profiles'].append(profile_data)
    save_tracked_profiles(data)
    start_tracking(profile_data)
    
    return redirect('/')

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    from profile_tracker import stop_tracking
    
    profile_url = request.form['profile_url']
    data = load_tracked_profiles()
    stop_tracking(profile_url)
    
    data['tracked_profiles'] = [p for p in data['tracked_profiles'] 
                              if p['profile_url'] != profile_url]
    save_tracked_profiles(data)
    
    return redirect('/')

@app.route('/toggle_profile', methods=['POST'])
def toggle_profile():
    from profile_tracker import start_tracking, stop_tracking
    
    profile_url = request.form['profile_url']
    data = load_tracked_profiles()
    
    for profile in data['tracked_profiles']:
        if profile['profile_url'] == profile_url:
            profile['is_active'] = not profile['is_active']
            
            if profile['is_active']:
                start_tracking(profile)
            else:
                stop_tracking(profile_url)
            break
    
    save_tracked_profiles(data)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
