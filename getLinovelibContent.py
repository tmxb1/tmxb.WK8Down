import shutil

import requests
from bs4 import BeautifulSoup,NavigableString
import re
import time
import os
from urllib.parse import urlparse, unquote, urljoin

cookies = {
    'Hm_lvt_ef8d5b3eafdfe7d1bbf72e3f450ad2ed': '1780384172',
    'HMACCOUNT': 'B9DEB56BE24A1DD1',
    'cf_clearance': 'f_cxtiMkLQ1HfSwKOys4MP_ECJQUMeYrt_uSrd_8Its-1780384174-1.2.1.1-VQOKu84.JALYnLKsdq10T9x9lVhrjqvAnw4A8UfD9r8AZg9y_8mY.5Dvn9QIW8oB_xDgTXpXmevlZXhlPKqj1msEh7MSmOFSpc2KcCNGb7rugR73_OdKPrKO5HXYP6OQ8SjQm7AwZ9xRUKK_JmfQ6n2FHtCF9joIGPWixcsObTcJCl8i1Lsz9AWsNbqtjFzw48g_lWxyBm5.g.KaTnjE3GC5jlJNFs0TlDWxuViW_j_JyDRFYZOclKPhv5YHJxhB7vQEDyn0hW0D1Z5x0.6rPFDhZu7jwXeYF8TthdsblUxO6oVJiZ0aMH2xrCECEypAYwqFP6_Et4Uv7cbwQ0fzMg',
    'jieqiRecentRead': '3080.319838.0.1.1780384195.0',
    'Hm_lpvt_ef8d5b3eafdfe7d1bbf72e3f450ad2ed': '1780384194',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9',
    'cache-control': 'max-age=0',
    # 'cookie': 'Hm_lvt_ef8d5b3eafdfe7d1bbf72e3f450ad2ed=1780384172; HMACCOUNT=B9DEB56BE24A1DD1; cf_clearance=f_cxtiMkLQ1HfSwKOys4MP_ECJQUMeYrt_uSrd_8Its-1780384174-1.2.1.1-VQOKu84.JALYnLKsdq10T9x9lVhrjqvAnw4A8UfD9r8AZg9y_8mY.5Dvn9QIW8oB_xDgTXpXmevlZXhlPKqj1msEh7MSmOFSpc2KcCNGb7rugR73_OdKPrKO5HXYP6OQ8SjQm7AwZ9xRUKK_JmfQ6n2FHtCF9joIGPWixcsObTcJCl8i1Lsz9AWsNbqtjFzw48g_lWxyBm5.g.KaTnjE3GC5jlJNFs0TlDWxuViW_j_JyDRFYZOclKPhv5YHJxhB7vQEDyn0hW0D1Z5x0.6rPFDhZu7jwXeYF8TthdsblUxO6oVJiZ0aMH2xrCECEypAYwqFP6_Et4Uv7cbwQ0fzMg; jieqiRecentRead=3080.319838.0.1.1780384195.0; Hm_lpvt_ef8d5b3eafdfe7d1bbf72e3f450ad2ed=1780384194',
    'if-modified-since': 'Sat, 09 May 2026 18:06:16 GMT',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}

# cookies = {
#     'Hm_lvt_ef8d5b3eafdfe7d1bbf72e3f450ad2ed': '1780384172',
#     'HMACCOUNT': 'B9DEB56BE24A1DD1',
#     'user_tz': 'Asia%2FShanghai',
#     'FCOEC': '%5B%5B%5B28%2C%22%5B%5B%5B%5B1%2Cnull%2C%5B1780495656%2C88091000%5D%2C10%5D%5D%5D%2C%5Bnull%2C0%2C%5B1780409256%2C88091000%5D%2C0%5D%5D%22%5D%5D%5D',
#     '__gads': 'ID=654176b12ab6efb8:T=1780409243:RT=1780409979:S=ALNI_Ma2Sr_fgIlUoiLL7VxG4ncymfBU5A',
#     '__gpi': 'UID=0000144326212880:T=1780409243:RT=1780409979:S=ALNI_MZm4FBxjVIZ8ds64gaH9RotmJl9nQ',
#     '__eoi': 'ID=14098aeef3e82e81:T=1780409243:RT=1780409979:S=AA-Afja5D4S2zUKSy3Kf2HRuzTbn',
#     'FCCDCF': '%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%22ffebc9af-5749-4c2c-9427-37931eddb66f%5C%22%2C%5B1780409244%2C352000000%5D%5D%22%5D%5D%5D',
#     'FCNEC': '%5B%5B%22AKsRol9GFenuMbH8NMfigfZ5j9OZpKm8WbV36xDoODckFRFS7cnVSbNO0gmPh_IUY8O3NpQ-i9x0TDSlUzEcSF9Vkg-MHCU3gkKaIhoU2pE3Q0pgitEVzwkKj1pVEWauCe-NDWCJLOW3jjHUs9mMu55rol_UD7PSwQ%3D%3D%22%5D%2Cnull%2C%5B%5B21%2C%22%5B%5B%5B%5B5%2C1%2C%5B0%5D%5D%2C%5B1780409245%2C491102000%5D%2C%5B1209600%5D%5D%5D%5D%22%5D%5D%5D',
#     'jieqiRecentRead': '3095.309465.0.1.1780409303.0-3080.319838.0.1.1780414482.0',
#     'Hm_lpvt_ef8d5b3eafdfe7d1bbf72e3f450ad2ed': '1780414484',
#     'cf_clearance': 'xT.pqTL.z_mCxyp7DRLlRqhc42ujqHoQWhCtqyXHVSw-1780414484-1.2.1.1-EWA5pQxw88IOJna3XSsPYBeLvbH.Oh5K36ALqOe9yh0nwP4F.4Wd_sITOdjBbSVON7erZUV7nE7Y4tHHNR44GZf.kJpuWbk2kwkZazoiRVdEx9_nHHNetugHtrlsvFOU3XvcRvuav4cKJZjm9Vuml5Gr4JvO2GbrUiLopQh8._juScoOkNim98bZ7e_vtHRkOgX034p3_BfHK77OyvWhMTBdqHrfQqVz7nK5En2DBuP6cASbmecYx2KtWVxCQ4lxV.zzNGZ87JPNPPbkxzgpHZ01YQ0t794XwYVx0tOSZmJqN5gH0pR772KenTnS962Pwp7scnrUoRIZ2aAreIU.7w',
# }

picture_headers = {
    'sec-ch-ua-platform': '"Windows"',
    'Referer': 'https://www.linovelib.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
}



def extract_content(node, img_save_dir, page_url, base_dir, has_cover):
    if node is None:
        return ""
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name == "div":
            class_list = child.get("class", [])
            if "divimage" in class_list:
                img_tag = child.find("img")
                if img_tag:
                    img_src = img_tag.get("data-src") or img_tag.get("src", "")
                    if img_src:
                        # 补全相对路径为绝对URL
                        img_src = urljoin(page_url, img_src)
                        # 下载图片，传入封面目录与标记
                        download_image(img_src, img_save_dir, page_url, base_dir, has_cover)
                        img_name = os.path.basename(urlparse(img_src).path)
                        img_name = unquote(img_name) if img_name else "image.jpg"
                        parts.append(f"[[img:{img_name}]]")
                continue
        elif child.name == "br":
            parts.append("\n")
            continue
        else:
            parts.append(extract_content(child, img_save_dir, page_url, base_dir, has_cover))
    return "".join(parts)


def download_image(url, save_dir, page_url='', base_dir='', has_cover=None):
    """下载图片到 save_dir，第一张自动复制为卷封面"""
    if has_cover is None:
        has_cover = [False]
    try:
        parsed = urlparse(url)
        filename = unquote(os.path.basename(parsed.path))
        if not filename or '.' not in filename:
            filename = f"image_{abs(hash(url))}.jpg"
        safe_name = "".join(c for c in filename if c not in r'\/:*?"<>|')
        if not safe_name:
            safe_name = "untitled.jpg"

        filepath = os.path.join(save_dir, safe_name)
        if os.path.exists(filepath):
            return

        img_headers = picture_headers.copy()
        if page_url:
            img_headers['Referer'] = page_url

        resp = requests.get(url, headers=img_headers, cookies=cookies, timeout=10)
        print(f"下载图片 {url} -> 状态码 {resp.status_code}")
        resp.raise_for_status()

        # 校验返回内容是否为图片，避免保存损坏文件
        content_type = resp.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            print(f"警告：返回内容非图片，跳过保存。Content-Type: {content_type}")
            return

        with open(filepath, 'wb') as f:
            f.write(resp.content)
        print(f"图片已保存: {filepath}")

        # 核心逻辑：第一张成功下载的图片复制为卷封面
        if not has_cover[0] and base_dir:
            ext = os.path.splitext(filepath)[1]  # 保留原扩展名
            cover_path = os.path.join(base_dir, f"cover{ext}")
            shutil.copy2(filepath, cover_path)
            print(f"已生成封面文件: {cover_path}")
            has_cover[0] = True  # 标记已生成，后续不再复制
        time.sleep(5)
    except Exception as e:
        print(f"图片下载失败 {url}: {e}")


def get_content(url, volume_name, number,bookName):
    print("进入get_content函数")
    result = 0
    TextIndex = 1
    cover = True
    # 标记是否已生成封面，用列表实现可变传参
    has_cover = [False]

    while True:
        print("进入get_content函数中的循环中")
        try:
            base_dir = os.path.join(bookName, volume_name)
            img_dir = os.path.join(base_dir, "images")
            # 提前创建目录，避免下载图片时路径不存在
            os.makedirs(img_dir, exist_ok=True)
            response = requests.get(url, cookies=cookies, headers=headers)
            response.encoding = 'gb18030'
            soup = BeautifulSoup(response.text, 'html5lib')

            title = soup.find('div', id="title").text.strip()
            if " " in title:
                volume_part, title_part = title.split(maxsplit=1)
            else:
                volume_part = volume_name
                title_part = title

            content = soup.find('div', id="content")
            # 传入封面目录与封面标记
            print(content, img_dir, url, base_dir, has_cover)
            content_text = extract_content(content, img_dir, url, base_dir, has_cover).strip()
            print("extract_content函数后")
            text = f"{title}\n\n{content_text}"
            print("开始爬取 " + title + ' ' + title_part)

            with open(os.path.join(base_dir, f"{TextIndex} {title_part}.txt"), 'a', encoding='utf-8') as f:
                f.write(text)
                print("本次需要爬取", number, "当前", TextIndex, "对比", str(TextIndex) == str(number))
                if str(TextIndex) == str(number):
                    cover = False
                else:
                    TextIndex += 1
            print("爬取完毕 " + title + ' ' + title_part)

            script = soup.find('script', string=re.compile('next_page'))
            if script:
                txt = script.string
                match = re.search(r'var next_page = "([^"]+)"', txt)
                print(match.group(1))
                url = url.rsplit('/', 1)[0] + '/' + match.group(1)

            if not cover:
                print(volume_name, "全部下载完毕")
                break
            time.sleep(25)
        except Exception as e:
            print("报错：",e)
            result = e
            break
    if result == 0:
        return True
    else:
        return result


if __name__ == '__main__':
    volume_url = "https://www.wenku8.net/novel/3/3683/154003.htm"
    volume_name = "第一卷"
    number = 11
    title="联谊去凑人数的我，把不知为何没人追的前人气偶像国宝级美少女带回家了。"
    result = get_content(volume_url, volume_name, number,title)
# 第九卷 第32话 最后的桐岛（2）
# pip install pytest-playwright
# playwright install chrome