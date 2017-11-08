import requests
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
from urllib.parse import urlparse


def check_links(url):
    only_a_tags = SoupStrainer("a")
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    links = BeautifulSoup(r.content, "lxml", parse_only=only_a_tags)
    urls = [(a.text, a.get('href')) for a in links.find_all("a", href=True) if a.get('href')[:4] == "http"]
    return check_status_code(urls)


def check_status_code(urls):
    '''
    source code taken from: https://www.webucator.com/blog/2016/05/checking-your-sitemap-for-broken-links-with-python/
    :param urls: list of tuples containing names and urls to check [( name,url)]
    :return: list of quintuple: [(status code,  url,text of url,error evaluation)]
    '''
    results = []
    for i, (name, url) in enumerate(urls, 1):
        try:
            r = requests.get(url)
            if r.history:
                result = (r.status_code, "".join(name.split()), url, 'No error. Redirect to ' + r.url)
            elif r.status_code == 200:
                result = (r.status_code, "".join(name.split()), url, 'No error. No redirect.')
            else:
                result = (r.status_code, "".join(name.split()), url, 'Error?')
        except Exception as e:
            result = (0, "".join(name.split()), url, e)

        results.append(result)
    # Sort by status
    results.sort(key=lambda result: (result[0]))
    return results


def extract_hp(url):
    hp = ""
    content = get_soup(url)
    if content.find(text="Website"):
        for span in content.find_all("span"):
            if span.text == "Website":
                span = span.find_next_sibling()
                hp = span.a["href"]
                break
    return hp


def get_soup(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "lxml")
    return soup


if __name__ == '__main__':
    soup = get_soup('http://www.supsi.ch/idsia_en/institute/people/staff.html')
    content = soup.find("div", attrs={"id": "contentArea"})
    to_scan = [(link.text, link["href"]) for link in content.find_all("a")]
    # to_scan = to_scan[1:3]
    report = []
    for id, hp in to_scan:
        if str(hp).find("scheda-collaboratore") >= 0:
            hp = extract_hp(hp)
            if hp == '':
                report.append((id, 'no web page', '', '', ''))
                print('{} : no web page '.format(id))
                continue
        # does it resolves hp?
        chk = check_status_code([(id, hp)])
        if chk[0][0] not in [200, 403]:
            report.append((id, chk[0][0], chk[0][1], chk[0][2], chk[0][3]))
            print('ERROR:', chk)
            continue
        print('{} : {}'.format(id, hp))
        report.append((id, hp, '', '', ''))
        results = check_links(hp)
        for result in results:
            if result[0] != 200:
                report.append(('',
                               result[0] if result[0] != 0 else 'unknown',
                               result[1], result[2], result[3]))
                print('\t{}'.format(result))
    import pandas as pd

    df = pd.DataFrame(report,
                      columns=['Surname', 'home page and http errors', 'link text cleaned', 'link', 'error explained'])
    df.to_csv("check_hpgs.csv", sep=";", index=False)
