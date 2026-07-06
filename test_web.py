# test_login.py
import re
import time
import tkinter.font as tkFont
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync  # 引入 stealth 插件
import tkinter as tk
from PIL import Image, ImageTk
import os,sys
import urllib.request
from io import BytesIO
import shutil
import random
import getLinovelibContent
import TextToEpud
from tkinter import messagebox, filedialog


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("wenku8 小说浏览器")
        self.root.geometry("900x700")
        self.current_display_data = None

        # ---------- 登录界面 ----------
        self.login_frame = tk.Frame(root)
        self.login_frame.pack(fill="both", expand=True)

        tk.Label(self.login_frame, text="文库8账号", font=("微软雅黑", 12)).pack(pady=(80, 5))
        self.username_entry = tk.Entry(self.login_frame, font=("微软雅黑", 10), width=25)
        self.username_entry.pack(pady=5)

        tk.Label(self.login_frame, text="密码", font=("微软雅黑", 12)).pack(pady=(15, 5))
        self.password_entry = tk.Entry(self.login_frame, show="*", font=("微软雅黑", 10), width=25)
        self.password_entry.pack(pady=5)

        login_btn = tk.Button(self.login_frame, text="登录", command=self.do_login,
                              font=("微软雅黑", 10), bg="#4CAF50", fg="white")
        login_btn.pack(pady=30)

        # 浏览器相关对象
        self.browser = None
        self.context = None
        self.page = None          # 主页面（用于登录后保持会话）
        self.playwright = None

        # 搜索/详情页面管理
        self.search_frame = None
        self.search_entry = None
        self.image_display_frame = None
        self.search_page = None           # 当前搜索结果页面
        self.current_detail_page = None   # 详情页
        self.current_catalog_page = None  # 目录页

    def truncate_text(self, text, font, max_width, max_lines=2, ellipsis='……'):
        """将文本截断至最多 max_lines 行"""
        lines = [[]]
        for char in text:
            test_line = ''.join(lines[-1]) + char
            if font.measure(test_line) > max_width and lines[-1]:
                lines.append([char])
            else:
                lines[-1].append(char)
            if len(lines) > max_lines:
                break
        if len(lines) <= max_lines:
            return text
        result_lines = lines[:max_lines]
        while result_lines[-1]:
            last_line_str = ''.join(result_lines[-1])
            if font.measure(last_line_str + ellipsis) <= max_width:
                break
            result_lines[-1].pop()
        truncated = ''.join([''.join(line) for line in result_lines]) + ellipsis
        return truncated

    def do_login(self):
        """点击登录按钮：使用 Playwright 登录，成功后切换到搜索界面"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("错误", "请输入账号和密码")
            return

        tip = tk.Label(self.login_frame, text="正在登录，请稍候...", font=("微软雅黑", 9), fg="blue")
        tip.pack(pady=(0, 20))
        self.root.update()

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True, slow_mo=50, args=["--no-sandbox"])
            self.context = self.browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
            self.page = self.context.new_page()
            stealth_sync(self.page)

            self.page.goto("https://www.wenku8.net/login.php")
            self.page.click("input[name='submit']")
            self.page.wait_for_timeout(2000)

            # 登录验证：等待包含用户名的 strong 标签出现
            self.page.wait_for_selector(
                "strong:has-text('"+username+"')",
                timeout=30000,
                state="visible"
            )

            # 登录成功，销毁登录界面，创建搜索界面
            self.login_frame.destroy()
            self.create_search_interface()
        except Exception as e:
            tip.destroy()
            messagebox.showerror("登录失败", f"登录过程出错：{e}\n请检查网络、账号密码或网站是否可访问。")
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.browser = self.context = self.page = self.playwright = None

    def fetch_images_with_playwright(self, img_urls):
        """使用当前已启动的 playwright 实例下载图片"""
        images = []
        for url in img_urls:
            try:
                response = self.context.request.get(url)
                if response.ok:
                    img = Image.open(BytesIO(response.body()))
                    images.append(img)
                else:
                    print(f"图片加载失败 {url}: 状态码 {response.status}")
                    images.append(None)
                time.sleep(random.uniform(0.5, 1))
            except Exception as e:
                print(f"图片加载异常 {url}: {e}")
                images.append(None)
        return images

    def load_latest_books(self):
        """加载最新入库小说列表，作为搜索页默认显示"""
        self.clear_image_display()
        loading = tk.Label(self.image_display_frame, text="正在加载最新入库小说...", font=("微软雅黑", 10))
        loading.pack(pady=50)
        self.root.update()

        try:

            # 获取主页
            home_page = None
            if hasattr(self, 'page') and self.page and not self.page.is_closed():
                home_page = self.page
            else:
                if self.context.pages:
                    home_page = self.context.pages[0]
                else:
                    home_page = self.context.new_page()
                    stealth_sync(home_page)
                    home_page.goto("https://www.wenku8.net/login.php?do=login")
                    home_page.wait_for_load_state("networkidle")

            # 点击“最新入库”链接（当前页跳转）
            # 建议改用更健壮的选择器，例如：home_page.locator("a:has-text('最新入库')").click()
            home_page.locator('xpath=/html/body/div[3]/div/ul/li[5]/a').click()

            # 等待页面导航完成
            home_page.wait_for_load_state("networkidle", timeout=60000)  # 可适当增加超时

            # 更新当前操作页为 home_page（它已经是最新入库页面）
            self.search_page = home_page

            # 可选：额外等待某个列表元素出现，确保内容渲染完成
            # self.search_page.wait_for_selector(".novel-list", timeout=30000)

            # 解析结果
            titles, imgs, urls, authors, page, page_next_url = self.parse_search_results(self.search_page)

        except Exception as e:
            messagebox.showerror("错误", f"加载最新入库失败：{e}")
            self.show_empty_message("加载最新入库失败，请手动搜索")
            return
        finally:
            loading.destroy()

        if not titles:
            self.show_empty_message("暂无最新入库小说")
            return


        # 复用网格显示逻辑，支持翻页
        self.show_images_grid(titles, imgs, urls, authors, self.image_display_frame, page, page_next_url,"最新入库")

    def create_search_interface(self):
        """登录成功后创建搜索栏和显示区域"""
        self.search_frame = tk.Frame(self.root)
        self.search_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(self.search_frame, text="搜索小说:", font=("微软雅黑", 10)).pack(side="left")
        self.search_entry = tk.Entry(self.search_frame, width=35, font=("微软雅黑", 10))
        self.search_entry.pack(side="left", padx=8)
        search_btn = tk.Button(self.search_frame, text="搜索", command=self.on_search, bg="#2196F3", fg="white")
        search_btn.pack(side="left")

        self.image_display_frame = tk.Frame(self.root)
        self.image_display_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.clear_image_display()
        # 替换原来的空提示，默认显示最新入库小说
        self.load_latest_books()


    def clear_image_display(self):
        if self.image_display_frame:
            for widget in self.image_display_frame.winfo_children():
                widget.destroy()

    def show_empty_message(self, msg):
        label = tk.Label(self.image_display_frame, text=msg, font=("微软雅黑", 12), fg="gray")
        label.pack(pady=50)

    def on_search(self):
        """搜索按钮回调：使用主页搜索，释放旧搜索页面"""
        if self.search_page and not self.search_page.is_closed() and self.search_page != self.page:
            self.search_page.close()
        self.search_page = None  # 置空引用

        keyword = self.search_entry.get().strip()
        if not keyword:
            self.load_latest_books()
            return

        if not self.page or self.page.is_closed():
            messagebox.showerror("错误", "登录已失效，请重新启动程序并登录")
            return



        self.clear_image_display()
        loading = tk.Label(self.image_display_frame, text="正在搜索并加载图片，请稍候...", font=("微软雅黑", 10))
        loading.pack(pady=50)
        self.root.update()

        try:
            # 确保主页面回到首页
            self.page.goto("https://www.wenku8.net/")
            self.page.wait_for_load_state("networkidle")

            # 在首页搜索框中填入关键词并提交，捕获新标签页
            self.page.fill("input[name='searchkey']", keyword)
            with self.context.expect_page() as new_page_info:
                self.page.click("input[type='submit']")
            self.search_page = new_page_info.value
            self.search_page.wait_for_load_state("networkidle")

            # 解析搜索结果
            titles, imgs, urls, authors, page, page_next_url = self.parse_search_results(self.search_page)

        except Exception as e:
            messagebox.showerror("错误", f"搜索失败：{e}")
            self.show_empty_message("搜索出错，请重试")
            return
        finally:
            loading.destroy()

        if not titles:
            self.show_empty_message(f"未找到与「{keyword}」相关的小说")
            return

        # 显示图片网格
        self.show_images_grid(titles, imgs, urls, authors, self.image_display_frame, page, page_next_url)

    def parse_search_results(self, page):
        """从搜索结果页解析书籍列表或单本详情（页面不关闭）"""
        titles, imgs, urls, authors, page_info = [], [], [], [], []
        page_next_url = ''
        print("当前url：", page.url)

        if "book" in page.url:
            # 单本小说详情页
            xpath = "//*[contains(text(),'小说作者：')]"
            elem = page.locator(xpath).first
            full_text = elem.inner_text()
            author = full_text.split("小说作者：")[-1].strip()
            title_elem = page.locator('//*[@id="content"]/div[1]/table[1]/tbody/tr[1]/td/table/tbody/tr/td[1]/span/b')
            title = title_elem.inner_text().strip()
            img_elem = page.locator('//*[@id="content"]/div[1]/table[2]/tbody/tr/td[1]/img[1]')
            img = img_elem.get_attribute('src').strip()
            titles.append(title)
            imgs.append(img)
            urls.append(page.url)
            authors.append(author)
            page_info = []  # 单本时无分页
        else:
            # 列表页面
            pagestats = page.locator('//*[@id="pagestats"]').text_content().strip()
            page_now, page_last = pagestats.split('/')
            page_info = [page_now, page_last]
            if page_now == page_last:
                page_next_url = None
            else:
                page_next_url = page.locator('//*[@id="pagelink"]//a[contains(@class, "next")]').get_attribute(
                    'href').strip() if page.locator('//*[@id="pagelink"]//a[contains(@class, "next")]').count() > 0 else None

            divs = page.locator('//*[@id="content"]/table/tbody/tr/td/div')
            count = divs.count()
            for i in range(count):
                div = divs.nth(i)
                a_elem = div.locator('xpath=div[1]/a').first
                if a_elem.count() == 0:
                    continue
                title = a_elem.get_attribute('tiptitle')
                if title:
                    title = title.strip()
                else:
                    title = a_elem.inner_text().strip()
                href = a_elem.get_attribute('href')
                url = 'https://www.wenku8.net' + href.strip() if href else None

                img_elem = div.locator('xpath=div[1]/a/following-sibling::img').first
                if img_elem.count() == 0:
                    img_elem = div.locator('xpath=div[1]/a/img').first
                img_src = img_elem.get_attribute('src').strip() if img_elem.count() > 0 else None

                p_elem = div.locator('xpath=div[2]/p[1]').first
                author = None
                if p_elem.count() > 0:
                    text = p_elem.inner_text().strip()
                    if "作者:" in text:
                        after = text.split("作者:")[1]
                        author = after.split('/')[0].strip() if '/' in after else after.strip()
                    else:
                        author = text

                titles.append(title)
                imgs.append(img_src)
                urls.append(url)
                authors.append(author)

        return titles, imgs, urls, authors, page_info, page_next_url

    def show_images_grid(self, titles, imgs, urls, authors, parent_frame, page, page_next_url,top_title=""):
        """在父容器中创建带滚动条的图片网格"""
        self.current_display_data = (titles, imgs, urls, authors, page, page_next_url)
        self.clear_image_display()
        if top_title:
            tk.Label(parent_frame, text=top_title, font=("微软雅黑", 14, "bold")).pack(side='top', pady=(10, 5))
        canvas = tk.Canvas(parent_frame)
        scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        valid_items = [(i, url) for i, url in enumerate(imgs) if url]
        if not valid_items:
            tk.Label(scrollable_frame, text="无图片URL").pack()
            return

        loading_label = tk.Label(scrollable_frame, text="正在下载图片...", font=("微软雅黑", 10))
        loading_label.pack(pady=20)
        parent_frame.update_idletasks()

        try:
            pil_images = self.fetch_images_with_playwright([url for _, url in valid_items])
        except Exception as e:
            print("批量获取图片失败:", e)
            pil_images = []
        finally:
            loading_label.destroy()

        success_items = []
        for (idx, _), pil_img in zip(valid_items, pil_images):
            if pil_img is not None:
                success_items.append((pil_img, titles[idx], authors[idx], urls[idx]))

        if not success_items:
            tk.Label(scrollable_frame, text="所有图片加载失败", fg="red").pack()
            return

        cols = 5
        title_font = tkFont.Font(family="微软雅黑", size=10)
        rows_data = [success_items[i:i + cols] for i in range(0, len(success_items), cols)]

        for row_idx, row_items in enumerate(rows_data):
            row_display_titles = []
            row_lines_needed = []
            for _, title, _, _ in row_items:
                display_title = self.truncate_text(title, title_font, max_width=140, max_lines=2)
                row_display_titles.append(display_title)
                if title_font.measure(display_title) > 140:
                    lines = 2
                else:
                    lines = 1
                row_lines_needed.append(lines)

            max_lines_in_row = max(row_lines_needed) if row_lines_needed else 1

            for col_idx, (pil_img, title, author, book_url) in enumerate(row_items):
                display_title = row_display_titles[col_idx]

                cell_frame = tk.Frame(scrollable_frame, relief=tk.RIDGE, bd=2, padx=5, pady=5)
                cell_frame.grid(row=row_idx, column=col_idx, padx=8, pady=8, sticky="n")

                pil_img.thumbnail((150, 200))
                photo = ImageTk.PhotoImage(pil_img)
                img_label = tk.Label(cell_frame, image=photo)
                img_label.image = photo
                img_label.pack()
                img_label.bind("<Button-1>", lambda e, url=book_url: self.open_book_detail(url))

                title_label = tk.Label(
                    cell_frame,
                    text=display_title,
                    font=("微软雅黑", 10),
                    wraplength=140,
                    height=max_lines_in_row,
                    anchor='nw',
                    justify='left'
                )
                title_label.pack(pady=(5, 0), fill='x')
                title_label.bind("<Button-1>", lambda e, url=book_url: self.open_book_detail(url))

                author_label = tk.Label(cell_frame, text=author, font=("微软雅黑", 8), fg="gray", wraplength=140)
                author_label.pack()

        # 分页控件
        if len(page) == 2:
            pagination_frame = tk.Frame(scrollable_frame)
            pagination_frame.grid(row=len(rows_data), column=0, columnspan=cols, pady=10)

            current_page, max_page = page[0], page[1]
            tk.Label(pagination_frame, text=f"第 {current_page} 页 / 共 {max_page} 页",
                     font=("微软雅黑", 10)).pack(side="left", padx=10)

            if page_next_url and current_page < max_page:
                next_btn = tk.Button(
                    pagination_frame,
                    text="下一页 ▶",
                    command=self.go_to_next_page,
                    bg="#2196F3", fg="white", font=("微软雅黑", 9)
                )
                next_btn.pack(side="left", padx=5)
            else:
                tk.Label(pagination_frame, text="已是最后一页", fg="gray", font=("微软雅黑", 9)) \
                    .pack(side="left", padx=5)

        btn_frame = tk.Frame(scrollable_frame)
        btn_frame.grid(row=len(rows_data) + 1, column=0, sticky='w', pady=15)
        close_btn = tk.Button(btn_frame, text="关闭程序", command=self.root.destroy, bg="#f44336", fg="white")
        close_btn.pack()

    def go_to_next_page(self):
        """点击当前搜索页面的下一页按钮，刷新网格（模拟点击）"""
        if not self.search_page or self.search_page.is_closed():
            messagebox.showerror("错误", "搜索页面已失效")
            return

        # 找到下一页链接并点击
        next_link = self.search_page.locator('//*[@id="pagelink"]//a[contains(@class, "next")]')
        if next_link.count() == 0:
            messagebox.showinfo("提示", "没有下一页")
            return

        self.clear_image_display()
        loading = tk.Label(self.image_display_frame, text="正在加载下一页...", font=("微软雅黑", 10))
        loading.pack(pady=50)
        self.root.update()

        try:
            next_link.click()
            self.search_page.wait_for_load_state("networkidle")
            titles, imgs, urls, authors, page, page_next_url = self.parse_search_results(self.search_page)
        except Exception as e:
            messagebox.showerror("错误", f"翻页失败：{e}")
            return
        finally:
            loading.destroy()

        if not titles:
            self.show_empty_message("该页无结果")
            return

        self.show_images_grid(titles, imgs, urls, authors, self.image_display_frame,
                              page=page, page_next_url=page_next_url)

    def open_book_detail(self, book_url):
        """打开书籍详情页"""
        # 关闭之前的详情页和目录页
        if self.current_detail_page and not self.current_detail_page.is_closed():
            self.current_detail_page.close()
        if self.current_catalog_page and not self.current_catalog_page.is_closed():
            self.current_catalog_page.close()
        self.current_detail_page = None
        self.current_catalog_page = None

        self.clear_image_display()
        loading = tk.Label(self.image_display_frame, text="正在加载书籍详情...", font=("微软雅黑", 10))
        loading.pack(pady=50)
        self.root.update()

        detail_page = None
        try:
            detail_page = self.context.new_page()
            stealth_sync(detail_page)
            detail_page.goto(book_url)
            detail_page.wait_for_load_state("networkidle")

            detail_data, catalog_page = self.parse_book_detail(detail_page)
            # 保存页面对象，暂不关闭，返回时再释放
            self.current_detail_page = detail_page
            self.current_catalog_page = catalog_page
            # 防止 finally 中关闭详情页
            detail_page = None
        except Exception as e:
            messagebox.showerror("错误", f"获取书籍详情失败：{e}")
            self.show_empty_message("获取详情失败，请返回")
            return
        finally:
            loading.destroy()
            # 只关闭未保存的页面（异常时）
            if detail_page:
                detail_page.close()

        if detail_data:
            self.show_book_detail(detail_data)
        else:
            self.show_empty_message("未找到书籍信息")

    def open_as(self):
        if getattr(sys, 'frozen', False):
            # 打包后，exe 路径
            return os.path.dirname(sys.executable)
        else:
            # 开发时，脚本所在目录
            return os.path.dirname(os.path.abspath(__file__))

    def parse_book_detail(self, page):
        """解析书籍详情页，返回 (data, catalog_page)"""
        data = {}
        title_xpath = "//*[@id='content']/div[1]/table[1]/tbody/tr[1]/td/table/tbody/tr/td[1]/span/b"
        readurl_xpath = "//*[@id='content']/div[1]/div[4]/div/span[1]/fieldset/div/a"
        author_xpath = "//*[@id='content']/div[1]/table[1]/tbody/tr[2]/td[2]"
        intro_xpath = "//*[@id='content']/div[1]/table[2]/tbody/tr/td[2]/span[6]"
        img_xpath = "//*[@id='content']/div[1]/table[2]/tbody/tr/td[1]/img"

        try:
            title_elem = page.locator(f"xpath={title_xpath}").first
            a_elem = page.locator(readurl_xpath).first
            href = a_elem.get_attribute("href").strip()
            author_elem = page.locator(f"xpath={author_xpath}").first
            intro_elem = page.locator(f"xpath={intro_xpath}").first
            img = page.locator(img_xpath).first.get_attribute("src").strip()

            data['title'] = title_elem.inner_text().strip()
            data['author'] = author_elem.inner_text().strip()
            data['intro'] = intro_elem.inner_text().strip()
            data['cover_url'] = img
            data['href'] = href
        except Exception:
            data['title'] = "未知书名"
            data['author'] = "未知作者"
            data['intro'] = "暂无简介"
            data['cover_url'] = None
            data['href'] = None

        data['volumes'] = []
        catalog_page = None
        try:
            a_elem = page.locator(readurl_xpath).first
            a_elem.click()
            page.wait_for_load_state("networkidle")
            catalog_page = page  # 当前页已变为目录页

            rows = catalog_page.locator("tr")
            print("rows:",rows)
            row_count = rows.count()
            current_volume_name = None
            volume_a_list = []

            for i in range(row_count):
                tr_loc = rows.nth(i)
                vcss_td = tr_loc.locator("td.vcss")
                if vcss_td.count() > 0:
                    if current_volume_name is not None:
                        first_href = volume_a_list[0].get_attribute("href") if volume_a_list else None
                        one_href = catalog_page.url.rfind("/")
                        # 截取前面部分 + 拼接新内容
                        first_href = catalog_page.url[:one_href] + "/" + first_href
                        data['volumes'].append({
                            "volume_name": current_volume_name,
                            "url": first_href,
                            "a_total_count": len(volume_a_list)
                        })
                    current_volume_name = vcss_td.inner_text().strip()
                    volume_a_list = []
                    continue

                ccss_tds = tr_loc.locator("td.ccss")
                td_num = ccss_tds.count()
                for j in range(td_num):
                    td_loc = ccss_tds.nth(j)
                    a_tag = td_loc.locator("a").first
                    if a_tag.count() > 0:
                        volume_a_list.append(a_tag)

            if current_volume_name is not None:
                first_href = volume_a_list[0].get_attribute("href") if volume_a_list else None
                one_href = catalog_page.url.rfind("/")
                first_href = catalog_page.url[:one_href] + "/" + first_href
                data['volumes'].append({
                    "volume_name": current_volume_name,
                    "url": first_href,
                    "a_total_count": len(volume_a_list)
                })
        except Exception as e:
            print(f"获取卷列表失败: {e}")
            data['volumes'] = []
        # 注意：不关闭 catalog_page，由调用者管理
        print("data:",data)
        return data, catalog_page

    def show_book_detail(self, detail):
        """展示书籍详情界面"""
        self.clear_image_display()

        # 创建滚动区域
        canvas = tk.Canvas(self.image_display_frame)
        scrollbar = tk.Scrollbar(self.image_display_frame, orient="vertical", command=canvas.yview)
        detail_frame = tk.Frame(canvas)

        detail_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=detail_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ---------- 上部：左侧封面 + 右侧信息 ----------
        info_frame = tk.Frame(detail_frame)
        info_frame.pack(fill="x", padx=20, pady=10)

        # 左侧封面
        if detail.get('cover_url'):
            try:
                resp = self.context.request.get(detail['cover_url'])
                if resp.ok:
                    pil_img = Image.open(BytesIO(resp.body()))
                    pil_img.thumbnail((200, 260))
                    photo = ImageTk.PhotoImage(pil_img)
                    cover_label = tk.Label(info_frame, image=photo)
                    cover_label.image = photo
                    cover_label.pack(side="left", padx=(0, 15))
            except Exception as e:
                print("封面加载失败:", e)

        # 右侧信息区域
        right_frame = tk.Frame(info_frame)
        right_frame.pack(side="left", fill="both", expand=True)

        title_font = tkFont.Font(family="微软雅黑", size=16, weight="bold")
        title_width = title_font.measure("中" * 30)
        tk.Label(right_frame, text=detail.get('title', ''),
                 font=title_font, anchor='w', justify='left',
                 wraplength=title_width).pack(anchor='w', pady=(0, 5))
        tk.Label(right_frame, text=f"{detail.get('author', '')}",
                 font=("微软雅黑", 10), fg="gray", anchor='w', justify='left').pack(anchor='w', pady=(0, 10))

        intro_text = detail.get('intro', '')
        if intro_text:
            intro_label = tk.Label(right_frame, text=intro_text, font=("微软雅黑", 9),
                                   wraplength=500, justify='left', bg='#f5f5f5', padx=10, pady=10,
                                   anchor='w')
            intro_label.pack(anchor='w', fill='x', pady=(0, 10))

        # ---------- 卷列表（下方） ----------
        tk.Label(detail_frame, text="========== 卷列表 ==========",
                 font=("微软雅黑", 12)).pack(pady=(15, 5))

        volumes = detail.get('volumes', [])
        if not volumes:
            tk.Label(detail_frame, text="未找到卷信息", fg="gray").pack()
        else:
            for vol in volumes:
                vol_frame = tk.Frame(detail_frame)
                vol_frame.pack(fill='x', padx=50, pady=2)
                tk.Label(vol_frame, text=vol['volume_name'],
                         font=("微软雅黑", 10), anchor='w').pack(side='left', fill='x', expand=True)
                download_btn = tk.Button(vol_frame, text="下载",
                                         command=lambda v=vol: self.download_volume(v['url'], v['volume_name'],v["a_total_count"],detail.get('title', '')),
                                         bg="#4CAF50", fg="white", font=("微软雅黑", 9))
                download_btn.pack(side='right')

        # ---------- 返回按钮 ----------
        return_btn = tk.Button(detail_frame, text="← 返回搜索结果", command=self.return_to_search,
                               bg="#2196F3", fg="white", font=("微软雅黑", 10))
        return_btn.pack(pady=20)

        # self.clear_image_display()
        #
        # canvas = tk.Canvas(self.image_display_frame)
        # scrollbar = tk.Scrollbar(self.image_display_frame, orient="vertical", command=canvas.yview)
        # detail_frame = tk.Frame(canvas)
        #
        # detail_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # canvas.create_window((0, 0), window=detail_frame, anchor="nw")
        # canvas.configure(yscrollcommand=scrollbar.set)
        #
        # canvas.pack(side="left", fill="both", expand=True)
        # scrollbar.pack(side="right", fill="y")
        #
        # if detail.get('cover_url'):
        #     try:
        #         resp = self.context.request.get(detail['cover_url'])
        #         if resp.ok:
        #             pil_img = Image.open(BytesIO(resp.body()))
        #             pil_img.thumbnail((200, 260))
        #             photo = ImageTk.PhotoImage(pil_img)
        #             cover_label = tk.Label(detail_frame, image=photo)
        #             cover_label.image = photo
        #             cover_label.pack(pady=10)
        #     except Exception as e:
        #         print("封面加载失败:", e)
        #
        # tk.Label(detail_frame, text=detail.get('title', ''), font=("微软雅黑", 16, "bold")).pack(pady=(5, 0))
        # tk.Label(detail_frame, text=f"{detail.get('author', '')}", font=("微软雅黑", 10), fg="gray").pack()
        # intro_text = detail.get('intro', '')
        # intro_label = tk.Label(detail_frame, text=intro_text, font=("微软雅黑", 9),
        #                        wraplength=600, justify='left', bg='#f5f5f5', padx=10, pady=10)
        # intro_label.pack(pady=10, padx=20, fill='x')
        #
        # tk.Label(detail_frame, text="========== 卷列表 ==========", font=("微软雅黑", 12)).pack(pady=(15, 5))
        # volumes = detail.get('volumes', [])
        # if not volumes:
        #     tk.Label(detail_frame, text="未找到卷信息", fg="gray").pack()
        # else:
        #     for vol in volumes:
        #         vol_frame = tk.Frame(detail_frame)
        #         vol_frame.pack(fill='x', padx=50, pady=2)
        #         tk.Label(vol_frame, text=vol['volume_name'], font=("微软雅黑", 10), anchor='w').pack(side='left', fill='x', expand=True)
        #         download_btn = tk.Button(vol_frame, text="下载",
        #                                  command=lambda v=vol: self.download_volume(v['url'], v['volume_name']),
        #                                  bg="#4CAF50", fg="white", font=("微软雅黑", 9))
        #         download_btn.pack(side='right')
        #
        # return_btn = tk.Button(detail_frame, text="← 返回搜索结果", command=self.return_to_search,
        #                        bg="#2196F3", fg="white", font=("微软雅黑", 10))
        # return_btn.pack(pady=20)




    def download_volume(self, volume_url, volume_name,number,title):
        """下载指定卷的TXT文件  救了遇到痴汉的S级美少女才发现是邻座的青梅竹马"""
        print("volume_url:",volume_url) #https://www.wenku8.net/novel/2/2911/117437.htm
        print("volume_name:", volume_name) #第一卷
        print("number:", number) #38
        print("页面：",self.search_page)

        top = self.image_display_frame.winfo_toplevel()  # 获取根窗口
        popup = tk.Toplevel(top)
        popup.title("下载中")
        popup.geometry("300x100")
        popup.resizable(False, False)

        # 禁止通过关闭按钮退出
        popup.protocol("WM_DELETE_WINDOW", lambda: None)

        # 设置模态（置顶并锁定父窗口）
        popup.transient(top)
        popup.grab_set()

        # 居中显示（可选）
        popup.update_idletasks()
        x = top.winfo_x() + (top.winfo_width() - 300) // 2
        y = top.winfo_y() + (top.winfo_height() - 100) // 2
        popup.geometry(f"+{x}+{y}")

        # 提示文字
        tk.Label(
            popup,
            text=f"《{volume_name}》下载中...",
            font=("微软雅黑", 12)
        ).pack(expand=True)

        # 强制刷新界面，让弹窗立刻显示
        top.update()

        # ---------- 执行下载并保证弹窗关闭 ----------
        try:
            getLinovelibContent.get_content(volume_url, volume_name, number,title)
        finally:
            popup.grab_release()  # 解除模态
            popup.destroy()  # 关闭弹窗
        #转换成epud
        top = self.image_display_frame.winfo_toplevel()  # 获取根窗口
        popup = tk.Toplevel(top)
        popup.title("打包成EPUD中")
        popup.geometry("300x100")
        popup.resizable(False, False)

        # 禁止通过关闭按钮退出
        popup.protocol("WM_DELETE_WINDOW", lambda: None)

        # 设置模态（置顶并锁定父窗口）
        popup.transient(top)
        popup.grab_set()

        # 居中显示（可选）
        popup.update_idletasks()
        x = top.winfo_x() + (top.winfo_width() - 300) // 2
        y = top.winfo_y() + (top.winfo_height() - 100) // 2
        popup.geometry(f"+{x}+{y}")

        # 提示文字
        tk.Label(
            popup,
            text=f"《{volume_name}》打包中...",
            font=("微软雅黑", 12)
        ).pack(expand=True)

        # 强制刷新界面，让弹窗立刻显示
        top.update()

        # ---------- 执行下载并保证弹窗关闭 ----------
        try:
            input=title+"/"+volume_name
            output=title+"-"+volume_name+".epub"
            print("input",input,"\noutput:",output)
            TextToEpud.create_epub_from_project(input,output)
        finally:
            popup.grab_release()  # 解除模态
            popup.destroy()  # 关闭弹窗
        #将下载下来的进行打包成epud 完成
        self.open_as()
        #添加最新入库

    def return_to_search(self):
        """返回搜索结果界面，并释放详情/目录页"""
        # 关闭详情页和目录页
        if self.current_detail_page and not self.current_detail_page.is_closed():
            self.current_detail_page.close()
        if self.current_catalog_page and not self.current_catalog_page.is_closed():
            self.current_catalog_page.close()
        self.current_detail_page = None
        self.current_catalog_page = None

        if self.current_display_data:
            titles, imgs, urls, authors, page, page_next_url = self.current_display_data
            self.show_images_grid(titles, imgs, urls, authors, self.image_display_frame, page, page_next_url)
        else:
            self.clear_image_display()
            self.show_empty_message("没有搜索结果")

    def __del__(self):
        """析构时清理浏览器资源"""
        if hasattr(self, 'search_page') and self.search_page:
            try:
                self.search_page.close()
            except:
                pass
        if hasattr(self, 'current_detail_page') and self.current_detail_page:
            try:
                self.current_detail_page.close()
            except:
                pass
        if hasattr(self, 'current_catalog_page') and self.current_catalog_page:
            try:
                self.current_catalog_page.close()
            except:
                pass
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

def zb():
    if getattr(sys, 'frozen', False):
        browser_path = os.path.join(sys._MEIPASS, "playwright-browsers")
    else:
        browser_path = "playwright-browsers"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_path

if __name__ == "__main__":
    zb()
    root = tk.Tk()
    app = App(root)
    root.mainloop()




"""
未完成：
1.详细页面进行左右栏
2.主页新增今日更新
3.与下载进行联动
“”“

# def run():
#     with sync_playwright() as p:
#         # 1. 启动浏览器 (建议有头模式，用于调试)
#         browser = p.chromium.launch(headless=True, slow_mo=50)
#
#         # 2. 创建上下文 (可在此配置代理、视角等)
#         context = browser.new_context(
#             viewport={"width": 1920, "height": 1080},
#             locale="zh-CN"
#         )
#
#         # 3. 创建页面并立即启用隐身模式
#         page = context.new_page()
#         stealth_sync(page)  # 关键步骤：应用反检测策略
#
#         # 4. 访问登录页
#         page.goto("https://www.wenku8.net/login.php")
#
#         # 5. 等待并填入账号密码 (此处需根据实际页面元素调整选择器)
#         # 提示：使用 browser inspector 检查实际元素的 name 或 id
#
#         # 6. 点击登录按钮
#         page.click("input[name='submit']")
#
#         # 7. 等待登录完成（例如等待跳转或某个特定元素出现）
#         page.wait_for_url("https://www.wenku8.net/")  # 等待跳转到首页
#
#         # 8. 登录成功后可进行后续数据抓取，例如：
#         # content = page.content()
#         page.screenshot(path="1.png")
#         novel = input("请输入小说名称：")
#         page.fill("input[name='searchkey']",novel)
#         with context.expect_page() as new_page_info:
#             page.click("input[type='submit']")  # 触发新标签页
#
#         # 获取新页面对象
#         search_page = new_page_info.value
#
#         # 等待新页面加载完成（可选）
#         search_page.wait_for_load_state("networkidle")
#
#         # 现在可以在新页面上进行操作
#         print("新页面 URL:", search_page.url)
#         page.close()
#         search_page.screenshot(path="2.png")
#         authors, titles, imgs, urls='','','',''
#         # 判断什么类型：三种，具体小说页面，小说列表，空
#         if "book" in search_page.url:
#             xpath = "//*[contains(text(),'小说作者：')]"
#             elem = search_page.locator(xpath).first
#             full_text = elem.inner_text()
#             authors = full_text.split("小说作者：")[-1].strip()
#
#             xpath=search_page.locator('//*[@id="content"]/div[1]/table[1]/tbody/tr[1]/td/table/tbody/tr/td[1]/span/b')
#             elem = xpath.inner_text()
#             titles = elem.strip()
#
#             xpath = search_page.locator('//*[@id="content"]/div[1]/table[2]/tbody/tr/td[1]/img[1]')
#             elem = xpath.get_attribute('src')
#             imgs = elem.strip()
#
#             xpath = search_page.locator('//*[@id="content"]/div[1]/div[4]/div/span[1]/fieldset/div/a')
#             elem = xpath.get_attribute('href')
#             urls = 'https://www.wenku8.net'+elem.strip()
#             print('auther:' + authors + '\ntitle:' + titles+ '\nimg:' + imgs+ '\nurl:' + urls)
#         else:
#             divs = search_page.locator('//*[@id="content"]/table/tbody/tr/td/div')
#             count = divs.count()
#
#             titles = []
#             imgs = []
#             urls=[]
#             authors=[]
#             for i in range(count):
#                 div = divs.nth(i)
#
#                 # 获取标题（相对路径 div[2]/b/a）
#                 a_elem = div.locator('xpath=div[1]/a').first
#                 title = None
#                 url = None
#                 if a_elem.count() > 0:
#                     title = a_elem.get_attribute('tiptitle')
#                     title = title.strip() if title else None
#                     url = a_elem.get_attribute('href')
#                     url = url.strip() if url else None
#                 titles.append(title)
#                 urls.append('http://img.wenku8.com'+url)
#
#                 # 2. 获取 a 后面的 img 的 src（使用 following-sibling）
#                 img_elem = div.locator('xpath=div[1]/a/following-sibling::img').first
#                 # 若找不到，尝试 img 在 a 内部的情况（如 <a><img>...</a>）
#                 if img_elem.count() == 0:
#                     img_elem = div.locator('xpath=div[1]/a/img').first
#                 img_src = None
#                 if img_elem.count() > 0:
#                     img_src = img_elem.get_attribute('src')
#                     img_src = img_src.strip() if img_src else None
#                 imgs.append(img_src)
#
#                 p_elem = div.locator('xpath=div[2]/p[1]').first
#                 author = None
#                 if p_elem.count() > 0:
#                     text = p_elem.inner_text().strip()  # 例如 "作者:aaa/分类:bbb"
#                     # 提取 "作者:" 与 "/" 之间的内容
#                     if "作者:" in text:
#                         # 找到 "作者:" 之后的部分
#                         after_author = text.split("作者:")[1]
#                         # 取到第一个 '/' 之前的内容（若无 '/' 则取全部）
#                         if '/' in after_author:
#                             author = after_author.split('/')[0].strip()
#                         else:
#                             author = after_author.strip()
#                     else:
#                         # 备用逻辑：直接取整个文本（可根据需要调整）
#                         author = text
#                 authors.append(author)
#             #需要小说名、作者、书面、链接
#
#         print("登录成功！")
#         time.sleep(3)  # 调试时可短暂停留，观察浏览器状态
#         browser.close()
#         return titles, imgs, urls, authors
#
#
# def fetch_images_with_playwright(img_urls):
#     """
#     一次性使用 Playwright 获取多张图片，返回 PIL Image 列表
#     注：此函数会在主线程中同步下载，图片较多时可能短暂卡顿，但简单场景下足够使用
#     """
#     images = []
#     with sync_playwright() as p:
#         request_context = p.request.new_context(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#         )
#         for url in img_urls:
#             try:
#                 response = request_context.get(url)
#                 if response.ok:
#                     img = Image.open(BytesIO(response.body()))
#                     images.append(img)
#                 else:
#                     print(f"图片加载失败 {url}: 状态码 {response.status}")
#                     images.append(None)
#                 time.sleep(random.uniform(0.5, 1))
#             except Exception as e:
#                 print(f"图片加载异常 {url}: {e}")
#                 images.append(None)
#     return images
#
# def zzck(titles, imgs, urls, authors):
#     root = tk.Tk()
#     root.title("窗口示例")
#     root.geometry("900x700")  # 增大窗口高度，适应4行内容
#
#     # 添加滚动条，防止内容溢出
#     canvas = tk.Canvas(root)
#     scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
#     scrollable_frame = tk.Frame(canvas)
#
#     scrollable_frame.bind(
#         "<Configure>",
#         lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
#     )
#     canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
#     canvas.configure(yscrollcommand=scrollbar.set)
#
#     canvas.pack(side="left", fill="both", expand=True)
#     scrollbar.pack(side="right", fill="y")
#
#     # 收集需要获取的图片（非空URL）
#     valid_items = [(i, url) for i, url in enumerate(imgs) if url]
#     if not valid_items:
#         no_img_label = tk.Label(scrollable_frame, text="无图片")
#         no_img_label.pack()
#         button = tk.Button(root, text="关闭", command=root.destroy)
#         button.pack(pady=10)
#         root.mainloop()
#         return
#
#     # 批量获取图片
#     try:
#         pil_images = fetch_images_with_playwright([url for _, url in valid_items])
#     except Exception as e:
#         print("批量获取图片失败:", e)
#         pil_images = []
#
#     # 组装成功项：[(pil_img, title, author), ...]
#     success_items = []
#     for (idx, _), pil_img in zip(valid_items, pil_images):
#         if pil_img is not None:
#             success_items.append((pil_img, titles[idx], authors[idx]))
#
#     if not success_items:
#         no_img_label = tk.Label(scrollable_frame, text="所有图片加载失败")
#         no_img_label.pack()
#         button = tk.Button(root, text="关闭", command=root.destroy)
#         button.pack(pady=10)
#         root.mainloop()
#         return
#
#     # 网格布局参数
#     cols = 5
#     rows = (len(success_items) + cols - 1) // cols
#
#     for i, (pil_img, title, author) in enumerate(success_items):
#         row = i // cols
#         col = i % cols
#
#         # 每个单元格用一个 Frame 容纳
#         cell_frame = tk.Frame(scrollable_frame, relief=tk.RIDGE, bd=2, padx=5, pady=5)
#         cell_frame.grid(row=row, column=col, padx=8, pady=8, sticky="n")
#
#         # 图片（缩放至合适大小）
#         pil_img.thumbnail((150, 200))
#         photo = ImageTk.PhotoImage(pil_img)
#         img_label = tk.Label(cell_frame, image=photo)
#         img_label.image = photo  # 保持引用
#         img_label.pack()
#
#         # 标题（默认字体稍大）
#         title_label = tk.Label(cell_frame, text=title, font=("微软雅黑", 10), wraplength=140)
#         title_label.pack(pady=(5, 0))
#
#         # 作者（小字体）
#         author_label = tk.Label(cell_frame, text=author, font=("微软雅黑", 8), fg="gray", wraplength=140)
#         author_label.pack()
#
#     # 关闭按钮
#     button = tk.Button(root, text="关闭", command=root.destroy)
#     button.pack(pady=10)
#
#     root.mainloop()
#
#
# class App:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("图片浏览程序")
#         self.root.geometry("900x700")
#
#         # ---------- 1. 登录界面 ----------
#         self.login_frame = tk.Frame(root)
#         self.login_frame.pack(fill="both", expand=True)
#
#         tk.Label(self.login_frame, text="账号:", font=("微软雅黑", 12)).pack(pady=(80, 5))
#         self.username_entry = tk.Entry(self.login_frame, font=("微软雅黑", 10), width=25)
#         self.username_entry.pack(pady=5)
#
#         tk.Label(self.login_frame, text="密码:", font=("微软雅黑", 12)).pack(pady=(15, 5))
#         self.password_entry = tk.Entry(self.login_frame, show="*", font=("微软雅黑", 10), width=25)
#         self.password_entry.pack(pady=5)
#
#         login_btn = tk.Button(self.login_frame, text="登录", command=self.do_login, font=("微软雅黑", 10), bg="#4CAF50", fg="white")
#         login_btn.pack(pady=30)
#
#         # 后续会用到的控件占位
#         self.search_frame = None
#         self.search_entry = None
#         self.image_display_frame = None
#
#     def do_login(self):
#         """登录验证：任意非空账号密码即可通过"""
#         username = self.username_entry.get().strip()
#         password = self.password_entry.get()
#         if username and password:
#             # 登录成功，移除登录界面
#             self.login_frame.destroy()
#             self.create_search_interface()
#         else:
#             messagebox.showerror("错误", "请输入账号和密码")
#
#     def create_search_interface(self):
#         """登录后创建搜索区域（输入框 + 搜索按钮）"""
#         # 顶部搜索栏
#         self.search_frame = tk.Frame(self.root)
#         self.search_frame.pack(fill="x", padx=10, pady=10)
#
#         tk.Label(self.search_frame, text="搜索关键词:", font=("微软雅黑", 10)).pack(side="left")
#         self.search_entry = tk.Entry(self.search_frame, width=35, font=("微软雅黑", 10))
#         self.search_entry.pack(side="left", padx=8)
#         search_btn = tk.Button(self.search_frame, text="搜索", command=self.on_search, bg="#2196F3", fg="white")
#         search_btn.pack(side="left")
#
#         # 下方区域：用于动态显示图片网格
#         self.image_display_frame = tk.Frame(self.root)
#         self.image_display_frame.pack(fill="both", expand=True, padx=5, pady=5)
#
#         # 初始提示
#         self.clear_image_display()
#         self.show_empty_message("点击「搜索」按钮查看图片")
#
#     def clear_image_display(self):
#         """清空图片显示区域的所有子控件"""
#         if self.image_display_frame:
#             for widget in self.image_display_frame.winfo_children():
#                 widget.destroy()
#
#     def show_empty_message(self, msg):
#         """在图片区域显示提示文字"""
#         label = tk.Label(self.image_display_frame, text=msg, font=("微软雅黑", 12), fg="gray")
#         label.pack(pady=50)
#
#     def on_search(self):
#         """搜索按钮回调：根据关键词过滤本地模拟数据，并展示图片网格"""
#         keyword = self.search_entry.get().strip()
#
#         # ---------- 模拟本地图书数据（可根据实际需求替换为网络请求）----------
#         all_books = [
#             {
#                 "title": "把喜欢的女生收作女仆后，她居然在我的房间里偷偷地搞些什么",
#                 "img": "http://img.wenku8.com/image/4/4116/4116s.jpg",
#                 "url": "http://img.wenku8.com/image/4/4116/4116s.jpg",
#                 "author": "把喜欢的女生收作女仆后"
#             },
#             {
#                 "title": "成功回避死亡结局的美少女游戏女主们似乎读到了我的【日记本】，并道了我的秘密",
#                 "img": "http://img.wenku8.com/image/4/4282/4282s.jpg",
#                 "url": "http://img.wenku8.com/image/4/4282/4282s.jpg",
#                 "author": "成功回避死亡结局的美少女游戏女主们似乎读到了我的【日记本】"
#             },
#             # 可在此添加更多示例数据
#         ]
#         # 根据标题进行模糊匹配（不区分大小写）
#         if keyword:
#             filtered = [book for book in all_books if keyword.lower() in book["title"].lower()]
#         else:
#             filtered = all_books
#
#         if not filtered:
#             self.clear_image_display()
#             self.show_empty_message(f"未找到包含「{keyword}」的图片")
#             return
#
#         # 提取四个列表，供展示函数使用
#         titles = [book["title"] for book in filtered]
#         imgs = [book["img"] for book in filtered]
#         urls = [book["url"] for book in filtered]
#         authors = [book["author"] for book in filtered]
#
#         self.show_images_grid(titles, imgs, urls, authors, self.image_display_frame)
#
#     def show_images_grid(self, titles, imgs, urls, authors, parent_frame):
#         """
#         在指定的父容器中显示图片网格（带滚动条）
#         包含：加载提示 → 批量获取图片 → 网格布局
#         """
#         # 清空旧内容
#         self.clear_image_display()
#
#         # 创建滚动区域（Canvas + Scrollbar）
#         canvas = tk.Canvas(parent_frame)
#         scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
#         scrollable_frame = tk.Frame(canvas)
#
#         scrollable_frame.bind(
#             "<Configure>",
#             lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
#         )
#         canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
#         canvas.configure(yscrollcommand=scrollbar.set)
#
#         canvas.pack(side="left", fill="both", expand=True)
#         scrollbar.pack(side="right", fill="y")
#
#         # 收集有效的图片URL
#         valid_items = [(i, url) for i, url in enumerate(imgs) if url]
#         if not valid_items:
#             tk.Label(scrollable_frame, text="无图片URL").pack()
#             return
#
#         # 显示加载提示，并强制刷新界面
#         loading_label = tk.Label(scrollable_frame, text="正在加载图片，请稍候...", font=("微软雅黑", 10))
#         loading_label.pack(pady=20)
#         parent_frame.update_idletasks()
#
#         # 批量下载图片（同步，可能短暂阻塞，但数据量小时影响不大）
#         try:
#             pil_images = fetch_images_with_playwright([url for _, url in valid_items])
#         except Exception as e:
#             print("批量获取图片失败:", e)
#             pil_images = []
#         finally:
#             loading_label.destroy()
#
#         # 组装下载成功的图片及对应的标题、作者
#         success_items = []
#         for (idx, _), pil_img in zip(valid_items, pil_images):
#             if pil_img is not None:
#                 success_items.append((pil_img, titles[idx], authors[idx]))
#
#         if not success_items:
#             tk.Label(scrollable_frame, text="所有图片加载失败", fg="red").pack()
#             return
#
#         # 网格布局参数
#         cols = 5
#         rows = (len(success_items) + cols - 1) // cols
#
#         for i, (pil_img, title, author) in enumerate(success_items):
#             row = i // cols
#             col = i % cols
#
#             # 每个单元格用独立 Frame 包裹
#             cell_frame = tk.Frame(scrollable_frame, relief=tk.RIDGE, bd=2, padx=5, pady=5)
#             cell_frame.grid(row=row, column=col, padx=8, pady=8, sticky="n")
#
#             # 缩略图
#             pil_img.thumbnail((150, 200))
#             photo = ImageTk.PhotoImage(pil_img)
#             img_label = tk.Label(cell_frame, image=photo)
#             img_label.image = photo  # 保持引用
#             img_label.pack()
#
#             # 标题
#             title_label = tk.Label(cell_frame, text=title, font=("微软雅黑", 10), wraplength=140)
#             title_label.pack(pady=(5, 0))
#
#             # 作者
#             author_label = tk.Label(cell_frame, text=author, font=("微软雅黑", 8), fg="gray", wraplength=140)
#             author_label.pack()
#
#         # 在网格下方添加一个关闭程序按钮
#         btn_frame = tk.Frame(scrollable_frame)
#         btn_frame.grid(row=rows, column=0, columnspan=cols, pady=15)
#         close_btn = tk.Button(btn_frame, text="关闭程序", command=self.root.destroy, bg="#f44336", fg="white")
#         close_btn.pack()
#
#
# if __name__ == "__main__":
#     root = tk.Tk()
#     app = App(root)
#     root.mainloop()
#     # title,img,url,author=run()
#     # print("Titles:", title)
#     # print("imgs:", img)
#     # print("urls:", url)
#     # print("authors:", author)
#     img=['http://img.wenku8.com/image/4/4116/4116s.jpg','http://img.wenku8.com/image/4/4282/4282s.jpg']
#     title= ['把喜欢的女生收作女仆后，她居然在我的房间里偷偷地搞些什么',
#             '成功回避死亡结局的美少女游戏女主们似乎读到了我的【日记本】，并道了我的秘密']
#     url=['http://img.wenku8.com/image/4/4116/4116s.jpg','http://img.wenku8.com/image/4/4282/4282s.jpg']
#     author=['把喜欢的女生收作女仆后',
#             '成功回避死亡结局的美少女游戏女主们似乎读到了我的【日记本】']
#     zzck(title,img,url,author)
