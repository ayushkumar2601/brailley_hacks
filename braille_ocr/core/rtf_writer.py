"""
rtf_writer.py
-------------
Writes the final Rich Text Format (RTF) document.

The RTF body is produced by transcription.transcribe_to_rtf(); this module
wraps it in the RTF envelope and saves it to disk.
"""

import os


def write_rtf(rtf_body: str, output_path: str, file_stem: str) -> None:
    """
    Wrap *rtf_body* in the RTF envelope and write to
    *output_path/<file_stem>.rtf*.
    """
    rtf_path = os.path.join(output_path, f"{file_stem}.rtf")
    header = r"{\rtf1 \ansi \deff0 {\fonttbl {\f0 Ubuntu;}}\f0 \fs24 "
    with open(rtf_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(rtf_body)
        f.write("}")
