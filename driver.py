import requests
from bs4 import BeautifulSoup, Comment
import re
import html.entities
import json as JSON


def safe_html(html):
    if not html:
        return None

    # remove these tags, complete with contents.
    blacklist = ["script", "style"]

    whitelist = [
        "div", "span", "p", "br", "pre",
        "table", "tbody", "thead", "tr", "td", "a",
        "blockquote", 
        "ul", "li", "ol",
        "b", "em", "i", "strong", "u", "font"
    ]

    # BeautifulSoup is catching out-of-order and unclosed tags, so markup
    # can't leak out of comments and break the rest of the page.
    soup = BeautifulSoup(html, 'lxml')
    soup.findAll('a')

    # now strip HTML we don't like.
    for tag in soup.findAll():
        if tag.name.lower() in blacklist:
            # blacklisted tags are removed in their entirety
            tag.extract()
        elif tag.name.lower() in whitelist:
            # tag is allowed. Make sure all the attributes are allowed.
            tag.attrs = [(a[0], safe_css(a[0], a[1])) for a in tag.attrs if _attr_name_whitelisted(a[0])]
        else:
            # not a whitelisted tag. I'd like to remove it from the tree
            # and replace it with its children. But that's hard. It's much
            # easier to just replace it with an empty span tag.
            tag.name = "span"
            tag.attrs = []

    # scripts can be executed from comments in some cases
    comments = soup.findAll(text=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()

    clean_html = str(soup)

    if clean_html == ", -":
        return None

    return clean_html


def _attr_name_whitelisted(attr_name):
    return attr_name.lower() in ["href", "style", "color", "size", "bgcolor", "border"]


def safe_css(attr, css):
    if attr == "style":
        return re.sub("(width|height):[^;]+;", "", css)
    return css


def plaintext(input):
    """Converts HTML to plaintext, preserving whitespace."""

    # from http://effbot.org/zone/re-sub.htm#unescape-html
    def _unescape(text):
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return chr(int(text[3:-1], 16))
                    else:
                        return chr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = chr(html.entities.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)

    input = safe_html(input) # basic sanitation first
    text = "".join(BeautifulSoup("<body>%s</body>" % input, features="lxml").body(text=True))
    text = text.replace("xml version='1.0' encoding='%SOUP-ENCODING%'", "") # strip BS meta-data
    return _unescape(text)


def main():
    document = {}
    url = 'https://www.tweentribune.com/article/tween56/how-centuries-old-dice-reveal-changing-attitudes-about-fate/'
    request = requests.get(url)
    dirty_html = request.text
    clean_html = safe_html(dirty_html)
    pure_text = plaintext(clean_html)
    document['document'] = pure_text.replace('\n', ' ')
    print(JSON.dumps(document))


if __name__ == "__main__":
    main()
