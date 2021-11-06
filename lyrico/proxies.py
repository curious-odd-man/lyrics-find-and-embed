import random
from time import sleep

import requests
from lxml.html import fromstring

proxies = set()


def reset_proxies():
    print("Resetting proxies")
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies.clear()
    for i in parser.xpath('//tbody/tr')[:100]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            # Grabbing IP and corresponding PORT
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)


def get_with_proxies(url, params, headers):
    sleep(5)
    return requests.get(url, params=params, headers=headers)
    # success = False
    # actual_proxies = list(proxies)
    # random.shuffle(actual_proxies)
    # while not success:
    #     if len(actual_proxies) == 0:
    #         print('waiting proxies to change...')
    #         sleep(10 * 60)
    #         reset_proxies()
    #     proxy = actual_proxies[0]
    #     del actual_proxies[0]
    #     try:
    #         print(".", end='')
    #         return requests.get(url, params=params, headers=headers, proxies={"http": proxy, "https": proxy})
    #     except (ConnectionError, TimeoutError) as e:
    #         print("failed proxy: " + str(e))
    #

if __name__ == '__main__':
    reset_proxies()
    print(proxies)
