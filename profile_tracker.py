from apscheduler.schedulers.background import BackgroundScheduler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import random

# Global scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def load_tracked_profiles():
    try:
        with open('tracked_profiles.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tracked_profiles": []}

def save_tracked_profiles(data):
    with open('tracked_profiles.json', 'w') as f:
        json.dump(data, f, indent=4)

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
def check_new_tweets(profile):
    print(f"Checking tweets for {profile['profile_url']}")
    driver = setup_driver()
    try:
        username = profile['profile_url'].split('/')[-1]
        profile_url = f"https://twitter.com/{username}"
        driver.get(profile_url)
        time.sleep(3)
        
        tweets = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
        )
        
        if tweets:
            latest_tweet = tweets[0]
            tweet_link = latest_tweet.find_element(By.CSS_SELECTOR, "a[href*='/status/']").get_attribute('href')
            tweet_id = tweet_link.split('/')[-1]
            
            if profile['last_tweet_id'] != tweet_id:
                print(f"Yeni tweet bulundu: {tweet_link}")
                profile['last_tweet_id'] = tweet_id
                data = load_tracked_profiles()
                for p in data['tracked_profiles']:
                    if p['profile_url'] == profile['profile_url']:
                        p['last_tweet_id'] = tweet_id
                save_tracked_profiles(data)
                
                process_new_tweet(tweet_link, profile['like_count'], profile['retweet_count'])
                
    except Exception as e:
        print(f"Tweet kontrol hatası: {str(e)}")
    finally:
        driver.quit()

def process_new_tweet(tweet_url, like_count, retweet_count):
    from main import process_account
    
    with open('accounts.json', 'r') as f:
        accounts = json.load(f)['accounts']
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        if like_count > 0:
            selected_accounts = random.sample(accounts, min(like_count, len(accounts)))
            for account in selected_accounts:
                executor.submit(process_account, account, tweet_url, 'like')
        
        if retweet_count > 0:
            selected_accounts = random.sample(accounts, min(retweet_count, len(accounts)))
            for account in selected_accounts:
                executor.submit(process_account, account, tweet_url, 'retweet')

def start_tracking(profile_data):
    job_id = f"check_{profile_data['profile_url']}"
    scheduler.add_job(
        check_new_tweets,
        'interval',
        minutes=profile_data['check_interval'],
        id=job_id,
        args=[profile_data]
    )

def stop_tracking(profile_url):
    job_id = f"check_{profile_url}"
    try:
        scheduler.remove_job(job_id)
    except:
        pass
