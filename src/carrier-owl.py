import chromedriver_binary   # これは必ず入れる
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time
import yaml
import datetime
import numpy as np
import textwrap
from bs4 import BeautifulSoup
import requests
from fastprogress import progress_bar
import slackweb
import warnings
import urllib.parse
import random

slack_conf = {
    'channel': '#arxiv_stream',
    # 'channel': '#bot-test',
    'icon_emoji': ':uniguri_kun6:',
    'username': 'carrier_owl',
}

# setting
warnings.filterwarnings('ignore')


def get_articles_info(subject):
    weekday_dict = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
                  4: 'Fri', 5: 'Sat', 6: 'Sun'}
    url = f'https://arxiv.org/list/{subject}/pastweek?show=100000'
    response = requests.get(url)
    html = response.text
    year = datetime.date.today().year

    # いつの論文データを取得するか
    bs = BeautifulSoup(html)
    h3 = bs.find_all('h3')
    wd = weekday_dict[datetime.datetime.today().weekday()]
    day = datetime.datetime.today().day
    today = f'{wd}, {day}'

    # 今日、新しい論文が出てるかどうか(土日とか休みみたい)
    if today in h3[0].text:
        idx = 2
    else:
        idx = 1
    articles_html = html.split(f'{year}</h3>')[idx]   # <--------- 要注意

    # 論文それぞれのurlを取得
    bs = BeautifulSoup(articles_html)
    id_list = bs.find_all(class_='list-identifier')
    return id_list


def search_keywords(id_):
    a = id_.find('a')
    _url = a.get('href')
    url = 'https://arxiv.org'+_url

    response = requests.get(url)
    html = response.text

    bs = BeautifulSoup(html)
    title = bs.find('meta', attrs={'property': 'og:title'})['content']
    abstract = bs.find(
        'meta',
        attrs={'property': 'og:description'})['content']

    title_trans = get_translated_text('ja', 'en', title)
    abstract = abstract.replace('\n', '')
    abstract_trans = get_translated_text('ja', 'en', abstract)
    abstract_trans = textwrap.wrap(abstract_trans, 40)  # 40行で改行
    abstract_trans = '\n'.join(abstract_trans)

    results = [url, title_trans, abstract_trans]

    return results


def send2slack(results, slack):
    url = results[0]
    title = results[1]
    abstract = results[2]

    text_slack = f'''url: {url}
title: {title}
abstract:
\t {abstract}'''
    slack.notify(text=text_slack, **slack_conf)


def get_translated_text(from_lang, to_lang, from_text):
    '''
    https://qiita.com/fujino-fpu/items/e94d4ff9e7a5784b2987
    '''

    sleep_time = 1

    # urlencode
    from_text = urllib.parse.quote(from_text)

    # url作成
    url = 'https://www.deepl.com/translator#' + from_lang + '/' + to_lang + '/' + from_text

    # ヘッドレスモードでブラウザを起動
    options = Options()
    options.add_argument('--headless')

    # ブラウザーを起動
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    driver.implicitly_wait(10)  # 見つからないときは、10秒まで待つ

    for i in range(30):
        # 指定時間待つ
        time.sleep(sleep_time)
        html = driver.page_source
        to_text = get_text_from_page_source(html)

        try_count = i + 1
        if to_text:
            wait_time = sleep_time * try_count
            # アクセス修了
            break

    # ブラウザ停止
    driver.quit()
    return to_text


def get_text_from_page_source(html):
    soup = BeautifulSoup(html, features='lxml')
    target_elem = soup.find(class_="lmt__translations_as_text__text_btn")
    text = target_elem.text
    return text


def get_config():
    file_abs_path = os.path.abspath(__file__)
    file_dir = os.path.dirname(file_abs_path)
    config_path = f'{file_dir}/../config.yaml'
    with open(config_path, 'r') as yml:
        config = yaml.load(yml)
    return config


def main():
    config = get_config()
    slack = slackweb.Slack(url=config['slack_id'])
    subject = random.choice(config['subject'])
    id_list = get_articles_info(subject)
    id_ = random.choice(id_list)
    results = search_keywords(id_)
    send2slack(results, slack)


if __name__ == "__main__":
    main()
