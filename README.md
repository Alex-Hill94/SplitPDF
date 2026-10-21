# SplitPDF

A small Python utility for extracting a page range from a PDF. It includes both a command-line interface and a macOS-friendly drag-and-drop GUI.

## Requirements

- Python 3.11 or newer
- `pypdf`
- `tkinterdnd2`
- Tkinter, including the native Tk runtime

Install the Python packages with:

```bash
python3 -m pip install -r requirements.txt
```

On macOS with Homebrew Python, install Tkinter with:

```bash
brew install python-tk@3.11
```

## Command line

Extract an inclusive, 1-based page range:

```bash
python3 split_pdf.py example.pdf -pages 16-20
```

The default output is `example_pages_16-20.pdf`. Use `-o` to choose a different output path:

```bash
python3 split_pdf.py example.pdf -pages 16-20 -o extracted.pdf
```

## GUI

Launch the drag-and-drop interface with:

```bash
python3 split_pdf.py --gui
```

You can also run `python3 split_pdf.py` with no arguments. Drag a PDF into the window, enter a page range such as `2-3`, and click **Split selected PDF**.

## Installing the command globally on macOS

If you want to call the script as `split_pdf` from any directory:

```bash
chmod +x split_pdf.py
ln -s "$(pwd)/split_pdf.py" /opt/homebrew/bin/split_pdf
```

Then use either:

```bash
split_pdf example.pdf -pages 16-20
split_pdf --gui
```
