import os
import re
import sys


# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from src.utils import clean_text


def test_normalize_whitespace():
    dirty = "Hello\n\n\tWorld\n\nGoodbye"
    clean = clean_text(dirty)
    assert clean == "Hello\n World\nGoodbye"


def test_remove_html_tags():
    dirty = "Some <b>bold</b> text"
    clean = clean_text(dirty)
    assert clean == "Some bold text"


def test_remove_markdown_tags():
    dirty = "This is a sample text with a <a href='https://www.example.com'>link</a> included."
    clean = clean_text(dirty)
    assert clean == "This is a sample text with a link included."


def test_replace_special_characters():
    dirty = "Text with &#160;&#160;special&#160; chars"
    clean = clean_text(dirty)
    assert clean == "Text with special chars"


def test_remove_table_tags():
    dirty = """
        <table>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
            </tr>
        </table>
        <p>Some text outside the table.</p>
        <table>
            <tr>
                <td>Cell A</td>
                <td>Cell B</td>
            </tr>
        </table>
    """
    clean = clean_text(dirty)
    assert clean == "\n \n Some text outside the table.\n \n "


def test_end_to_end():
    dirty = (
        "Hello <a href='https://www.example.com'>link</a>\n\n"
        "&#160;&#160;Goodbye<br>World"
    )
    clean = clean_text(dirty)
    assert clean == "Hello link\n Goodbye\nWorld"
