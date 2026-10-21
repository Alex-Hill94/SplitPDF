#!/opt/homebrew/bin/python3.11
"""Split a PDF from the command line or with a small drag-and-drop GUI."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def get_pdf_classes():
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError(
            "The 'pypdf' package is required. Install it with: python3 -m pip install pypdf"
        ) from exc
    return PdfReader, PdfWriter


def parse_page_range(value: str) -> tuple[int, int]:
    """Parse an inclusive page range such as ``16-20`` or ``16``."""
    match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", value)
    if not match:
        raise argparse.ArgumentTypeError(
            "page range must look like START-END (for example, 16-20)"
        )

    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start < 1 or end < start:
        raise argparse.ArgumentTypeError(
            "page range must start at 1 and END must be greater than or equal to START"
        )
    return start, end


def build_output_path(input_path: Path, start: int, end: int) -> Path:
    suffix = f"_pages_{start}" if start == end else f"_pages_{start}-{end}"
    return input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")


def pdf_page_count(input_path: Path) -> int:
    PdfReader, _ = get_pdf_classes()
    return len(PdfReader(str(input_path)).pages)


def split_pdf(input_path: Path, page_range: tuple[int, int], output_path: Path) -> None:
    PdfReader, PdfWriter = get_pdf_classes()

    if not input_path.is_file():
        raise FileNotFoundError(f"input PDF not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise ValueError(f"input file must have a .pdf extension: {input_path}")

    start, end = page_range
    reader = PdfReader(str(input_path))
    page_count = len(reader.pages)
    if end > page_count:
        raise ValueError(
            f"requested pages {start}-{end}, but {input_path.name} has only {page_count} page(s)"
        )
    if output_path.resolve() == input_path.resolve():
        raise ValueError("output file must be different from the input file")

    writer = PdfWriter()
    for page_number in range(start - 1, end):
        writer.add_page(reader.pages[page_number])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)


def run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        from tkinterdnd2 import DND_FILES, TkinterDnD
    except ImportError:
        print(
            "The GUI requires tkinterdnd2. Install it with: "
            "python3 -m pip install tkinterdnd2",
            file=sys.stderr,
        )
        return 1

    class SplitPdfApp:
        def __init__(self, root: TkinterDnD.Tk) -> None:
            self.root = root
            self.root.title("Split PDF")
            self.root.geometry("620x470")
            self.files: list[Path] = []
            self.page_count: int | None = None

            main = ttk.Frame(root, padding=18)
            main.pack(fill="both", expand=True)
            ttk.Label(main, text="Split PDF", font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
            ttk.Label(
                main,
                text="Drag one or more PDFs into the box below, then choose the pages to keep.",
            ).pack(anchor="w", pady=(3, 14))

            self.drop_area = tk.Label(
                main,
                text="Drop PDF files here\n\nor click to choose files",
                height=5,
                relief="groove",
                bd=2,
                bg="#f4f4f4",
                fg="#333333",
            )
            self.drop_area.pack(fill="x")
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind("<<Drop>>", self.on_drop)
            self.drop_area.bind("<Button-1>", self.choose_files)

            list_frame = ttk.Frame(main)
            list_frame.pack(fill="both", expand=True, pady=(12, 10))
            ttk.Label(list_frame, text="PDFs:").pack(anchor="w")
            self.file_list = tk.Listbox(list_frame, height=5, exportselection=False)
            self.file_list.pack(side="left", fill="both", expand=True)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
            scrollbar.pack(side="right", fill="y")
            self.file_list.configure(yscrollcommand=scrollbar.set)
            self.file_list.bind("<<ListboxSelect>>", self.on_file_selected)

            controls = ttk.Frame(main)
            controls.pack(fill="x", pady=(0, 12))
            ttk.Label(controls, text="Pages to keep:").pack(side="left")
            self.pages_entry = ttk.Entry(controls, width=13)
            self.pages_entry.insert(0, "1-1")
            self.pages_entry.pack(side="left", padx=(8, 10))
            self.page_info = ttk.Label(controls, text="No PDF selected")
            self.page_info.pack(side="left")

            buttons = ttk.Frame(main)
            buttons.pack(fill="x")
            ttk.Button(buttons, text="Remove selected", command=self.remove_selected).pack(side="left")
            ttk.Button(buttons, text="Split selected PDF", command=self.split_selected).pack(side="right")

        def choose_files(self, _event=None) -> None:
            paths = filedialog.askopenfilenames(
                title="Choose PDF files", filetypes=[("PDF files", "*.pdf"), ("All files", "*")]
            )
            self.add_files([Path(path) for path in paths])

        def on_drop(self, event) -> None:
            self.add_files([Path(path) for path in self.root.tk.splitlist(event.data)])

        def add_files(self, paths: list[Path]) -> None:
            for path in paths:
                if path.is_file() and path.suffix.lower() == ".pdf" and path not in self.files:
                    self.files.append(path)
                    self.file_list.insert(tk.END, str(path))
            if self.files and not self.file_list.curselection():
                self.file_list.selection_set(0)
                self.on_file_selected()

        def on_file_selected(self, _event=None) -> None:
            selection = self.file_list.curselection()
            if not selection:
                return
            path = self.files[selection[0]]
            try:
                self.page_count = pdf_page_count(path)
                self.pages_entry.delete(0, tk.END)
                self.pages_entry.insert(0, f"1-{self.page_count}")
                self.page_info.configure(text=f"{self.page_count} page(s)")
            except Exception as exc:
                self.page_count = None
                self.page_info.configure(text="Could not read PDF")
                messagebox.showerror("Could not read PDF", str(exc))

        def remove_selected(self) -> None:
            selection = self.file_list.curselection()
            if not selection:
                return
            index = selection[0]
            self.file_list.delete(index)
            self.files.pop(index)
            if self.files:
                new_index = min(index, len(self.files) - 1)
                self.file_list.selection_set(new_index)
                self.on_file_selected()
            else:
                self.page_count = None
                self.page_info.configure(text="No PDF selected")

        def split_selected(self) -> None:
            selection = self.file_list.curselection()
            if not selection:
                messagebox.showwarning("No PDF selected", "Drag in a PDF or choose one first.")
                return
            try:
                page_range = parse_page_range(self.pages_entry.get())
            except argparse.ArgumentTypeError as exc:
                messagebox.showerror("Invalid page range", str(exc))
                return

            input_path = self.files[selection[0]]
            output_path = build_output_path(input_path, *page_range)
            try:
                split_pdf(input_path, page_range, output_path)
            except Exception as exc:
                messagebox.showerror("Could not split PDF", str(exc))
                return
            messagebox.showinfo("PDF split", f"Created:\n{output_path}")

    root = TkinterDnD.Tk()
    SplitPdfApp(root)
    root.mainloop()
    return 0


def main() -> int:
    if len(sys.argv) == 1:
        return run_gui()

    parser = argparse.ArgumentParser(
        description="Extract an inclusive range of pages from a PDF, or launch the GUI."
    )
    parser.add_argument("input_pdf", nargs="?", type=Path, help="path to the input PDF")
    parser.add_argument(
        "-pages",
        type=parse_page_range,
        metavar="START-END",
        help="inclusive page range, using 1-based page numbers (for example: 16-20)",
    )
    parser.add_argument("-o", "--output", type=Path, help="output PDF path")
    parser.add_argument("--gui", action="store_true", help="launch the drag-and-drop GUI")
    args = parser.parse_args()

    if args.gui:
        return run_gui()
    if args.input_pdf is None or args.pages is None:
        parser.error("the command-line mode requires INPUT_PDF and -pages START-END")

    output_path = args.output or build_output_path(args.input_pdf, *args.pages)
    try:
        split_pdf(args.input_pdf, args.pages, output_path)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
