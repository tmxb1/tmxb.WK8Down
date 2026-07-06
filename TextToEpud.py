import os
import re
from ebooklib import epub
import sys

def create_epub_from_project(project_dir, output_epub='测试.epub', book_title=None, author='Unknown'):
    """
    将指定目录下的章节txt、封面、图片打包为epub
    目录结构：
        project_dir/
            cover.jpg          (可选)
            images/            (可选)
                img1.jpg
                img2.png
            1 章名.txt
            2 章名.txt
            ...
    章节文本中可以使用 {{image:文件名}} 嵌入图片
    """
    if not os.path.isdir(project_dir):
        raise ValueError(f"目录不存在: {project_dir}")

    # 书籍元数据
    book_title = book_title or os.path.basename(os.path.abspath(project_dir))
    book = epub.EpubBook()
    book.set_identifier(os.urandom(16).hex())
    book.set_title(book_title)
    book.set_language('zh')
    book.add_author(author)

    # --- 封面 ---
    cover_path = os.path.join(project_dir, 'cover.jpg')
    if os.path.isfile(cover_path):
        with open(cover_path, 'rb') as f:
            book.set_cover("cover.jpg", f.read())

    # --- CSS 样式 ---
    style = '''
    body {
        font-family: "Songti SC", "Noto Serif CJK SC", serif;
        line-height: 1.8;
        padding: 1em;
    }
    h1 {
        text-align: center;
        font-size: 1.8em;
        margin-bottom: 1.5em;
    }
    p {
        text-indent: 2em;
        margin: 0.5em 0;
    }
    img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 1em auto;
    }
    '''
    css_item = epub.EpubItem(
        uid="style", file_name="style/default.css",
        media_type="text/css", content=style
    )
    book.add_item(css_item)

    # --- 加载图片资源 ---
    images_dir = os.path.join(project_dir, 'images')
    image_items = {}  # 文件名 -> EpubItem
    if os.path.isdir(images_dir):
        for fname in os.listdir(images_dir):
            fpath = os.path.join(images_dir, fname)
            if not os.path.isfile(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                continue
            media_type = f'image/{ext[1:]}'
            if ext == '.jpg':
                media_type = 'image/jpeg'
            with open(fpath, 'rb') as f:
                img_content = f.read()
            img_item = epub.EpubImage(
                uid=f'img_{fname}',
                file_name=f'images/{fname}',
                media_type=media_type,
                content=img_content
            )
            book.add_item(img_item)
            image_items[fname] = img_item

    # --- 处理章节文件 ---
    chapters = []
    toc_links = []

    # 获取所有txt并按文件名中的数字排序
    txt_files = [f for f in os.listdir(project_dir) if f.endswith('.txt')]

    def sort_key(name):
        m = re.match(r'^(\d+)\s+.*\.txt$', name)
        return int(m.group(1)) if m else float('inf')

    txt_files.sort(key=sort_key)

    for txt_file in txt_files:
        file_path = os.path.join(project_dir, txt_file)

        # 提取章名 (去掉编号和 .txt)
        m = re.match(r'^\d+\s+(.*)\.txt$', txt_file)
        chapter_title = m.group(1) if m else os.path.splitext(txt_file)[0]

        # 读取文本内容
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        # 替换图片占位符 {{image:文件名}}
        def replace_image(match):
            fname = match.group(1).strip()
            if fname in image_items:
                return f'<img src="images/{fname}" alt="{fname}"/>'
            else:
                return f'[图片不存在: {fname}]'

        processed_text = re.sub(r'\[\[img:(.*?)\]\]', replace_image, raw_text)

        # 将文本转为HTML段落 (空行自动分段)
        paragraphs = []
        for line in processed_text.splitlines():
            line = line.strip()
            if line:
                paragraphs.append(f'<p>{line}</p>')
        body_html = '\n'.join(paragraphs)

        # 创建章节
        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chap_{txt_file[:-4]}.xhtml',
            lang='zh'
        )
        chapter.content = f'''<html>
<head><link rel="stylesheet" type="text/css" href="style/default.css"/></head>
<body>
<h1>{chapter_title}</h1>
{body_html}
</body>
</html>'''
        chapter.add_item(css_item)
        book.add_item(chapter)
        chapters.append(chapter)
        toc_links.append(epub.Link(f'chap_{txt_file[:-4]}.xhtml', chapter_title, f'chap_{txt_file[:-4]}'))

    # 导航文件（必须）
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 设置目录和阅读顺序
    book.toc = toc_links
    book.spine = ['nav'] + chapters

    # 生成 EPUB
    epub.write_epub(output_epub, book, {})
    print(f"✅ EPUB 已生成: {output_epub}")

if __name__ == '__main__':

    project = sys.argv[1] if len(sys.argv) > 1 else 'content/第三卷'
    out = sys.argv[2] if len(sys.argv) > 2 else 'book.epub'
    create_epub_from_project(project, out)