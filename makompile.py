#    _____          __                        .__.__          
#   /     \ _____  |  | ______   _____ ______ |__|  |   ____  
#  /  \ /  \\__  \ |  |/ /  _ \ /     \\____ \|  |  | _/ __ \ 
# /    Y    \/ __ \|    <  <_> )  Y Y  \  |_> >  |  |_\  ___/ 
# \____|__  (____  /__|_ \____/|__|_|  /   __/|__|____/\___  >
#         \/     \/     \/           \/|__|                \/ 
# A static website / personal wiki generator based on txt files.
# 24L25

from typing import List, Dict, Any
from enum import Enum
import re
import sys
from pathlib import Path
from datetime import datetime


DOCS_DIRECTORY = "docs"
RESULT_DIRECTORY = "web"


class SCSET(Enum):  # "Section Compilation Settings"
    NO_TITLES = 1
    NO_LISTS = 2
    LIST_DEPTH = 3
    NO_PARAGRAPH = 4
    NO_RESTORE_CODE = 5


def error(message: str):
    print("+------------------+")
    print("| Makompile Error! |")
    print("+------------------+")
    print("Makompile couldn't compile <CURRENT FILE>. The error was:")
    print(message)
    sys.exit(1)


def make_link(text: str, destination: str) -> str:
    if destination.lower().strip() in document_names:
        if text == destination:
            text = text.upper()
        destination = translate_page_name(Path(destination.lower().strip()))
        return f"<a href=\"{destination}\">{text}</a>"
    return f"<a href=\"{destination}\" target=_blank>{text}</a>"


def compile_section(section: str, settings: Dict[SCSET, Any] = {}, code_match_replacements = []) -> str:
    #print("")
    #print("------")
    #print("Compiling:")
    #print(section)
    if not section:
        return ""

    # +-----------------------------+
    # | Title and subtitle sections |
    # +-----------------------------+
    if SCSET.NO_TITLES not in settings:
        # -- Title --
        if len(section) > 1 and section[0] == "#" and section[1] != "#":
            return "<h1>" + compile_section(
                section[1:].strip(),
                {
                    SCSET.NO_TITLES: True,
                    SCSET.NO_LISTS: True,
                    SCSET.NO_PARAGRAPH: True,
                }
            ) + "</h1>"

        # -- Subtitle --
        if len(section) > 2 and section[0:2] == "##" and section[2] != "#":
            return "<h2>" + compile_section(
                section[2:].strip(), 
                {
                    SCSET.NO_TITLES: True,
                    SCSET.NO_LISTS: True,
                    SCSET.NO_PARAGRAPH: True,
                }
            ) + "</h2>"

        # -- Subsubtitle --
        if len(section) > 3 and section[0:3] == "###" and section[3] != "#":
            return "<h3>" + compile_section(
                section[3:].strip(), 
                {
                    SCSET.NO_TITLES: True,
                    SCSET.NO_LISTS: True,
                    SCSET.NO_PARAGRAPH: True,
                }
            ) + "</h3>"

    # +------+
    # | Code |
    # +------+
    code_matches = re.findall(r'`.*?`', section)
    for code_match in code_matches:
        tag_contents = code_match[1:-1].strip()
        code_match_replacements.append(tag_contents)
        section = section.replace(code_match, f"<CODE:{len(code_match_replacements) - 1}>")

    # +-----------+
    # | Bold Text |
    # +-----------+
    code_matches = re.findall(r'\*\*.*?\*\*', section)
    for code_match in code_matches:
        tag_contents = code_match[2:-2].strip()
        section = section.replace(code_match, f"<b>{tag_contents}</b>")

    # +------------+
    # | Small Text |
    # +------------+
    code_matches = re.findall(r'_\*.*?\*_', section)
    for code_match in code_matches:
        tag_contents = code_match[2:-2].strip()
        section = section.replace(code_match, f"<small>{tag_contents}</small>")

    # +------------+
    # | List Items |
    # +------------+
    if SCSET.NO_LISTS not in settings:
        if section[0] == "*" or section[0] == "%":
            #print("FOUND A LIST IN THIS SECTION!")
            list_bullet = section[0]
            section_lines = section.split("\n")
            list_items = []
            for line in section_lines:
                if line[0] == list_bullet:
                    list_items.append(line)
                else:
                    list_items[-1] += f"\n{line}"
            #print("List items:", list_items)
            if list_bullet == "*":
                list_html = "<ul>"
            else:
                list_html = "<ol>"
            for list_item in list_items:
                content = list_item[1:].strip()
                content_lines = content.split("\n")
                #print("Content lines:", content_lines)
                list_html += "\n<li>"
                sublist_parts = [""]
                depth = 2 if SCSET.LIST_DEPTH not in settings else settings[SCSET.LIST_DEPTH] + 2
                #print("Depth:", depth)
                for content_line in content_lines:
                    if len(content_line) >= depth + 1 and content_line[0:depth+1] == f"{depth * ' '}{list_bullet}":
                        content_line = content_line[depth:]
                        sublist_parts.append(content_line)
                    else:
                        sublist_parts[-1] += f"\n{content_line}"
                #print("Sublist parts:", sublist_parts)
                for sublist_part in sublist_parts:
                    list_html += "\n" + compile_section(
                        sublist_part, 
                        {
                            SCSET.NO_TITLES: True,
                            SCSET.LIST_DEPTH: depth,
                            SCSET.NO_PARAGRAPH: True,
                            SCSET.NO_RESTORE_CODE: True,
                        }
                    )
                list_html += "\n</li>"
            if list_bullet == "*":
                list_html += "\n</ul>"
            else:
                list_html += "\n</ol>"
            return compile_section(
                list_html,
                {
                    SCSET.NO_TITLES: True,
                    SCSET.NO_LISTS: True,
                    SCSET.NO_PARAGRAPH: True,
                },
                code_match_replacements
            )

    # +--------+
    # | Images |
    # +--------+
    image_matches = re.findall(r'\[\[.*?\]\]', section)
    for image_match in image_matches:
        tag_contents = image_match[2:-2].strip()
        if not tag_contents:
            error(f"The image tag '{image_match}' is empty.")
        tokens = tag_contents.split("|")
        image_info = {
            "img": "",
            "alt": "",
            "link": "",
            "class": ""
        }
        for token in tokens:
            token = token.strip()
            parts = token.split(" ", 1)
            if len(parts) != 2:
                error(f"The image tag '{image_match}' has an invalid parameter: '{token}'.")
            command = parts[0].lower()
            if command in image_info:
                if image_info[command]:
                    error(f"The image tag '{image_match}' has duplicated too many '{command}' parameters.")
                else:
                    image_info[command] = parts[1]
        if not image_info["img"]:
            error(f"The image tag '{image_match}' is missing the image path.")
        html_image_tag = f"<img src=\"{image_info['img']}\""
        if image_info["alt"]:
            html_image_tag += f" alt=\"{image_info['alt']}\""
        if image_info["class"]:
            html_image_tag += f" class=\"{image_info['class']}\""
        html_image_tag += ">"
        if image_info["link"]:
            html_image_tag = make_link(html_image_tag, image_info["link"])
        section = section.replace(image_match, html_image_tag)

    # +-------+
    # | Links |
    # +-------+
    link_matches = re.findall(r'\[.*?\]', section)
    for link_match in link_matches:
        tag_contents = link_match[1:-1].strip()
        if not tag_contents:
            error(f"The link tag '{link_match}' is empty.")
        tokens = tag_contents.split("|")
        if len(tokens) > 2:
            error(f"The link tag '{link_match}' has has too many arguments.")
        if len(tokens) == 1:
            section = section.replace(link_match, make_link(tag_contents, tag_contents))
        else:
            text = tokens[0].strip()
            destination = tokens[1].strip()
            section = section.replace(link_match, make_link(text, destination))

    # +---------+
    # | Italics |
    # +---------+
    code_matches = re.findall(r'__.*?__', section)
    for code_match in code_matches:
        tag_contents = code_match[2:-2].strip()
        section = section.replace(code_match, f"<i>{tag_contents}</i>")

    # +-----------------------+
    # | Restore Code Sections |
    # +-----------------------+
    if SCSET.NO_RESTORE_CODE not in settings:
        for i in range(0, len(code_match_replacements)):
            section = section.replace(f"<CODE:{i}>", f"<code>{code_match_replacements[i]}</code>")

    if SCSET.NO_PARAGRAPH not in settings:
        section = f"<p>{section}</p>"

    return section


def turn_file_into_sections(file_contents: str) -> List[str]:
    sections = []
    # +--------------------------+
    # | Split file into sections |
    # +--------------------------+
    code_mode = False
    current_section = ""
    file_contents += "\n\n"
    lines = file_contents.split("\n")
    for line in lines:
        if not code_mode:
            if line.strip() == "":  # Empty Line
                if current_section:
                    sections.append(current_section)
                    current_section = ""
            elif line.strip() == "```":
                if current_section:
                    sections.append(current_section)
                current_section = "<pre>"
                code_mode = True
            else:
                current_section += line + "\n"
        else:
            if line.strip() == "```":
                if current_section:
                    current_section += "</pre>"
                    sections.append(current_section)
                current_section = ""
                code_mode = False
            else:
                if current_section:
                    current_section += "\n"
                current_section += line

    # +-------------------+
    # | Sanitize Sections |
    # +-------------------+
    for i in range(0, len(sections)):
        sections[i] = sections[i].strip()
    return sections


def save_page(filename_stem, title, page_html, previous_doc, next_doc, page_number="", link_home=False):
    now = datetime.now()
    compiled_date = now.strftime("%a %b %d %H:%M:%S %z %Y")
    home_link = ""
    if link_home:
        home_link = "[<a href=\"index.html\">Home</a>]"
    page_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <style>
    {css}
    </style>
    <body>

    <div id="header-div">
        <span id="page-number">{page_number}</span>
        <span>{home_link}
        [<a href=sitemap.html>Index</a>]
        [<a href="{previous_doc}">←</a>]
        [<a href="{next_doc}">→</a>]
    </div>

    <hr>
    {page_html}

    <hr>

    <div id="footer">
        Page compiled using <a href="https://github.com/lartu/makompile" target=_blank>Makompile</a> on <i>{compiled_date}</i>.
    </div>
    </body>
    </html>
    """
    Path(RESULT_DIRECTORY).mkdir(parents=True, exist_ok=True)
    with open(Path(RESULT_DIRECTORY) / translate_page_name(Path(filename_stem)), "w") as f:
        f.write(page_html)


def translate_page_name(filename):
    if str(filename) == "home":
        return "index.html"
    return filename.with_suffix(".html")


if __name__ == "__main__":
    try:
        with open('styles.css', 'r') as f:
            css = f.read()
    except FileNotFoundError:
        error("CSS file 'styles.css' not found.")

    docs_path = Path(DOCS_DIRECTORY)
    if not docs_path.exists() or not docs_path.is_dir():
        error(f"Documents directory at '{DOCS_DIRECTORY}' not found.")

    files = docs_path.glob("*.txt")
    files = sorted(files)
    document_names = []
    for file in files:
        document_names.append(file.stem.lower())
    document_titles = {}

    if not files:
        error(f"Documents directory at '{DOCS_DIRECTORY}' doesn't contain any .txt files.")

    has_home = "home" in document_names

    if "index" in document_names:
        error(f"You cannot have a file called 'index.txt' in your '{DOCS_DIRECTORY}' documents directory.")
    
    for i in range(0, len(files)):
        file = files[i]
        page_html = ""
        title = ""
        filename = Path(file)
        if str(filename) != str(filename).lower():
            error(f"The filename '{file}' is not in lowercase.")
        with open(filename) as f:
            sections = turn_file_into_sections(f.read())
            for section in sections:
                if section[0:5] == "<pre>":
                    section_html = section
                else:
                    section_html = compile_section(section)
                if section_html[0:4] == "<h1>":
                    title = section_html[4:-5]
                page_html += "\n" + section_html
        if not title:
            title = str(file.stem).title()
        document_titles[filename] = title
        previous_doc = "sitemap.html"
        if i > 0:
            previous_doc = translate_page_name(Path(files[i - 1].stem))
        next_doc = "sitemap.html"
        if i < len(files) - 1:
            next_doc = translate_page_name(Path(files[i + 1].stem))
        save_page(filename.stem, title, page_html, previous_doc, next_doc, f"{i + 1} / {len(files)}", has_home)

    # Create index
    page_html = "<h1>Index</h1>\n<ol>"
    for file in files:
        page_path = translate_page_name(Path(file.stem))
        page_title = document_titles[file]
        if file.stem == "home":
            page_title += " <i><small>(Homepage)</small></i>"
        page_html += f"\n<li><a href=\"{page_path}\">{page_title}</a></li>"
    page_html += "\n</ol>"
    previous_doc = translate_page_name(Path(files[- 1].stem))
    next_doc = translate_page_name(Path(files[0].stem))
    save_page("sitemap", "Index", page_html, previous_doc, next_doc, "Index", has_home)

        