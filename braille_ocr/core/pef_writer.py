"""
pef_writer.py
-------------
Converts a braille Unicode string into a Portable Embosser Format (PEF) file.

PEF is an XML-based format used by braille embossers and refreshable braille
displays.  The code handles RTF-command braille equivalents (\\tab, \\line,
\\par, \\page, \\sbkpage) and wraps the content in the correct PEF tags.
"""

import re

from braille_ocr.config import PEF_COLUMNS_PER_PAGE, PEF_LINES_PER_PAGE


# ── RTF-command → PEF-tag substitutions ──────────────────────────────────────
# Each tuple is (braille_pattern, pef_replacement).
# An empty braille cell is appended to every pattern so that no stray spaces
# are left behind (PEF tags don't support optional trailing spaces the way RTF
# commands do).
_RTF_TO_PEF = [
    ("⠸⠡⠞⠁⠃⠀",  "⠀⠀"),                                                    # \tab  → two spaces
    ("⠸⠡⠇⠔⠑⠀",  "</row>\n\t\t\t\t\t<row>"),                               # \line → row break
    ("⠸⠡⠏⠜⠀",   "</row>\n\t\t\t\t\t<row>⠀⠀"),                             # \par  → row break + indent
    ("⠸⠡⠏⠁⠛⠑⠀", "</row>\n\t\t\t\t</page>\n\t\t\t\t<page>\n\t\t\t\t\t<row>"),  # \page
    ("⠸⠡⠎⠃⠅⠏⠁⠛⠑⠀",
     "</row>\n\t\t\t\t</page>\n\t\t\t</section>\n\t\t\t<section>\n\t\t\t\t</page>\n\t\t\t\t\t<row>"),  # \sbkpage
]


def _apply_rtf_to_pef_substitutions(text: str) -> str:
    """Replace braille RTF-command sequences with their PEF tag equivalents."""
    for pattern, replacement in _RTF_TO_PEF:
        text = re.sub(re.escape(pattern), replacement, text)
    return text


def _wrap_into_rows(pef_string: str) -> str:
    """
    Split *pef_string* at empty braille cells and re-wrap the content into
    PEF rows of at most PEF_COLUMNS_PER_PAGE characters.
    """
    pef_rows = []
    current_row_length = 0

    non_empty_cells = re.split("⠀", pef_string)

    for segment in non_empty_cells:
        if "r" not in segment:
            # Pure braille — length is simply the character count.
            seg_len = len(segment)
        else:
            # Segment contains a PEF tag (all tags contain the letter 'r').
            # Count only the braille characters (exclude XML/tag characters).
            pattern = re.compile(r"[^ \n\t<>sectionrowpage/\\]")
            match = re.match(pattern, segment)
            seg_len = len(match.group(0)) if match else 0
            current_row_length = seg_len  # reset after a structural tag

        if current_row_length + seg_len < PEF_COLUMNS_PER_PAGE:
            pef_rows.append(segment + "⠀")
            current_row_length += seg_len + 1
        else:
            pef_rows.append(f"</row>\n\t\t\t\t\t<row>{segment}⠀")
            current_row_length = seg_len + 1

    return "".join(pef_rows)


def _insert_page_breaks(pef_string: str) -> str:
    """
    Walk the assembled row string and insert automatic page breaks every
    PEF_LINES_PER_PAGE rows (unless an explicit page break already exists).
    """
    page_tag_indices = [m.start() for m in re.finditer("</page>", pef_string)]
    row_tag_indices  = [m.start() for m in re.finditer("</row>",  pef_string)]

    row_count = 0
    for i in range(len(row_tag_indices) - 1, -1, -1):
        row_idx = row_tag_indices[i]

        # If we've passed the last explicit page break, reset the counter.
        if page_tag_indices and row_idx <= page_tag_indices[-1]:
            page_tag_indices.pop()
            row_count = 0
            continue

        if i > 0 and row_count < PEF_LINES_PER_PAGE - 1:
            row_count += 1
        elif i > 0 and row_count == PEF_LINES_PER_PAGE - 1:
            # Insert an automatic page break after this </row>.
            pef_string = (
                pef_string[: row_idx + 7]
                + "\t\t\t\t</page>\n\t\t\t\t<page>\n\t"
                + pef_string[row_idx + 8 :]
            )
            row_count = 0

    return pef_string


def _pef_document(content: str) -> str:
    """Wrap *content* in the full PEF XML envelope."""
    cols = PEF_COLUMNS_PER_PAGE
    rows = PEF_LINES_PER_PAGE
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<pef version="2008-1" xmlns="http://www.daisy.org/ns/2008/pef">\n'
        "\t<head>\n"
        '\t\t<meta xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        "\t\t\t<dc:format>application/x-pef+xml</dc:format>\n"
        "\t\t\t<dc:identifier>org.pef-format.00002</dc:identifier>\n"
        "\t\t</meta>\n"
        "\t</head>\n"
        "\t<body>\n"
        f'\t\t<volume cols="{cols}" rows="{rows}" rowgap="0" duplex="false">\n'
        "\t\t\t<section>\n"
        "\t\t\t\t<page>\n"
        "\t\t\t\t\t<row>⠀"
        + content
        + "</row>\n"
        "\t\t\t\t</page>\n"
        "\t\t\t</section>\n"
        "\t\t</volume>\n"
        "\t</body>\n"
        "</pef>"
    )


def write_pef(character_string: str, output_path: str, file_stem: str) -> None:
    """
    Convert *character_string* (raw braille Unicode) to a PEF file and write
    it to *output_path/<file_stem>.pef*.
    """
    pef_string = _apply_rtf_to_pef_substitutions(character_string)
    pef_string = _wrap_into_rows(pef_string)
    pef_string = _insert_page_breaks(pef_string)

    pef_path = f"{output_path}/{file_stem}.pef"
    with open(pef_path, "w", encoding="utf-8") as f:
        f.write(_pef_document(pef_string))
