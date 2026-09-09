import pandas as pd
import shutil
import glob
import subprocess
import warnings
import nctoolkit as nc

nc.session_info["stamp"] = nc.session_info["stamp"] + "_ecoval_output_"
import copy
from oceanval.matchall import matchup
import dill

from oceanval.session import session_info
from oceanval.utils import restrict_r_to_conda
restrict_r_to_conda()
import webbrowser
from oceanval.chunkers import add_chunks
import os
import re
import html
import nbformat
import base64
import io
from oceanval.fvcom import fvcom_preprocess
import importlib

from oceanval.parsers import Validator, definitions#, summaries


def reset():
    # add docstring
    """
    Reset the matchup definitions to their default state.
    This function resets the matchup definitions used in oceanval to their default state.
    """
    # reset session_info["short_title"] to empty dict
    session_info["short_title"] = dict()
    definitions.reset()

notebook_dict = dict()
add_point_comparison = definitions.add_point_comparison
add_gridded_comparison = definitions.add_gridded_comparison


def _jupyter_book_major_version():
    try:
        return int(_version("jupyter-book").split(".", 1)[0])
    except Exception:
        return 1


def _build_book(book_dir, validation_links=None):
    if _jupyter_book_major_version() >= 2:
        notebooks = glob.glob(os.path.join(book_dir, "notebooks", "*.ipynb"))
        notebooks.sort(
            key=lambda notebook: ("summary" in os.path.basename(notebook), notebook)
        )
        output_dir = os.path.join(book_dir, "_build", "html")
        if notebooks:
            subprocess.run(
                [
                    "jupyter",
                    "nbconvert",
                    "--to",
                    "notebook",
                    "--execute",
                    "--inplace",
                    "--allow-errors",
                    "--ExecutePreprocessor.timeout=500",
                    *notebooks,
                ],
                check=True,
            )
            _remove_diagnostic_outputs(notebooks)
            os.makedirs(os.path.join(output_dir, "notebooks"), exist_ok=True)
            subprocess.run(
                [
                    "jupyter",
                    "nbconvert",
                    "--to",
                    "html",
                    "--no-input",
                    "--output-dir",
                    os.path.join(output_dir, "notebooks"),
                    *notebooks,
                ],
                check=True,
            )
        os.makedirs(output_dir, exist_ok=True)
        # keep the logo alongside index.html so the two share a directory
        shutil.copyfile(
            os.path.join(book_dir, "pml_logo.jpg"), os.path.join(output_dir, "pml_logo.jpg")
        )
        _write_offline_report_pages(output_dir, notebooks, validation_links=validation_links)
    else:
        subprocess.run(["jupyter-book", "build", book_dir], check=True)


def _remove_diagnostic_outputs(notebooks):
    for notebook_path in notebooks:
        notebook = nbformat.read(notebook_path, as_version=4)
        kept_cells = []
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cleaned_outputs = []
                for output in cell.outputs:
                    if output.output_type == "stream":
                        continue
                    elif output.output_type in {"display_data", "update_display_data"}:
                        data = getattr(output, "data", {}) or {}
                        if data and set(data) != {"text/plain"}:
                            cleaned_outputs.append(output)
                    elif output.output_type == "error" and output.ename == "RInterpreterError":
                        cleaned_outputs.append(output)
                    elif output.output_type == "execute_result" and set(output.data) != {"text/plain"}:
                        cleaned_outputs.append(output)
                cell.outputs = cleaned_outputs
            kept_cells.append(cell)
        notebook.cells = kept_cells
        nbformat.write(notebook, notebook_path)


def _offline_report_sections(output_dir, notebooks):
    notebooks_by_stem = {
        os.path.splitext(os.path.basename(notebook))[0]: notebook
        for notebook in notebooks
    }
    toc_path = os.path.normpath(os.path.join(output_dir, "..", "..", "_toc.yml"))
    sections = []
    section = None
    if os.path.exists(toc_path):
        with open(toc_path, "r") as toc:
            for line in toc:
                if line.startswith("- caption: "):
                    section = [line.removeprefix("- caption: ").strip(), []]
                    sections.append(section)
                elif section is not None and "file: notebooks/" in line:
                    stem = os.path.splitext(line.split("file: notebooks/", 1)[1].strip())[0]
                    if stem in notebooks_by_stem:
                        section[1].append(notebooks_by_stem.pop(stem))

    if notebooks_by_stem:
        sections.append(("Validation Results", sorted(notebooks_by_stem.values())))
    return sections


def _offline_report_title(notebook_path):
    notebook = nbformat.read(notebook_path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type != "markdown":
            continue
        for line in cell.source.splitlines():
            if line.startswith("# "):
                return line.removeprefix("# ").strip()
    stem = os.path.splitext(os.path.basename(notebook_path))[0]
    return re.sub(r"^\d+_", "", stem).replace("_", " ").title()


def _offline_report_navigation(
    output_dir, notebooks, logo_path, notebook_prefix, index_path, pdf_href, validation_links=None
):
    sections = []
    for title, section_notebooks in _offline_report_sections(output_dir, notebooks):
        items = []
        for notebook in section_notebooks:
            stem = os.path.splitext(os.path.basename(notebook))[0]
            label = _offline_report_title(notebook)
            items.append(
                f'<li><a href="{notebook_prefix}{html.escape(stem)}.html">'
                f"{html.escape(label)}</a></li>"
            )
        if items:
            sections.append(f"<section><h2>{html.escape(title)}</h2><ul>{''.join(items)}</ul></section>")

    validation_block = ""
    if validation_links:
        links = "".join(
            f'<a class="oceanval-validation-link" href="{html.escape(href)}">{html.escape(label)}</a>'
            for label, href in validation_links
        )
        validation_block = (
            '<div class="oceanval-validation-links">'
            '<h2 class="oceanval-validation-heading">Reports</h2>'
            f"{links}</div>"
        )

    return (
        "<aside class=\"oceanval-sidebar\">"
        f"<div class=\"oceanval-nav-sections\">{''.join(sections)}</div>"
        f"{validation_block}"
        f"<a href=\"{index_path}\" class=\"oceanval-brand-link\">"
        "<div class=\"oceanval-brand-block\">"
        "<div class=\"oceanval-brand-text\">OceanVal by</div>"
        f"<div class=\"oceanval-logo-box\"><img class=\"oceanval-logo\" src=\"{logo_path}\" "
        "alt=\"Plymouth Marine Laboratory\"></div>"
        "</div></a>"
        f'<a href="{pdf_href}" class="oceanval-viewpdf-btn">View all as pdf</a>'
        "</aside>"
    )


def _offline_report_style():
    return (
        "<style>body{margin:0;color:#203047;background:#fff;font-family:Georgia,'Times New Roman',serif}"
        ".oceanval-sidebar{position:fixed!important;top:0;bottom:auto;left:0;width:300px;height:100vh;"
        "max-height:100vh;overflow:hidden;background:#0f7c7c;border-right:1px solid #0a5f5f;padding:28px 24px;"
        "z-index:10;color:#fff;display:flex;flex-direction:column;box-sizing:border-box}"
        ".oceanval-nav-sections{flex:1 1 auto;overflow-y:auto;min-height:0;padding-bottom:16px}.oceanval-brand-link{display:block;flex:0 0 auto;padding-top:12px;text-decoration:none}"
        ".oceanval-brand-block{background:#0f7c7c;border:2px solid #fff;border-radius:8px;padding:12px;box-sizing:border-box}"
        ".oceanval-brand-text{color:#fff;font-family:Arial,sans-serif;font-size:14px;font-weight:700;margin:0 0 10px}"
        ".oceanval-logo-box{background:#0f7c7c;border:1px solid rgba(255,255,255,0.9);border-radius:5px;padding:8px}"
        ".oceanval-logo{display:block;width:100%;max-width:100%;background:#0f7c7c}"
        ".oceanval-viewpdf-btn{display:block;flex:0 0 auto;margin-top:12px;background:#fff;"
        "border-radius:6px;padding:10px 12px;font-family:Arial,sans-serif;font-size:13px;font-weight:700;"
        "text-align:center;text-decoration:none;box-sizing:border-box}"
        ".oceanval-viewpdf-btn:hover{background:rgba(255,255,255,0.85)}"
        ".oceanval-validation-links{flex:0 0 auto;border-top:1px solid rgba(255,255,255,0.4);"
        "margin-top:12px;padding-top:12px;display:flex;flex-direction:column;gap:8px}"
        ".oceanval-validation-heading{margin:0 0 4px!important}"
        ".oceanval-validation-link{display:block;background:#fff;color:#0f7c7c;border-radius:6px;"
        "padding:10px 12px;font-family:Arial,sans-serif;font-size:13px;font-weight:700;"
        "text-align:center;text-decoration:none;box-sizing:border-box}"
        ".oceanval-validation-link:hover{background:rgba(255,255,255,0.85)}"
        ".oceanval-sidebar h2{font-family:Arial,sans-serif;font-size:14px;font-weight:700;letter-spacing:0;"
        "margin:25px 0 10px;text-transform:uppercase;color:#fff}.oceanval-sidebar ul{list-style:none;"
        "margin:0;padding:0}.oceanval-sidebar li{margin:0}.oceanval-sidebar a{color:#fff;text-decoration:none}"
        ".oceanval-sidebar li a{display:block;border-left:3px solid transparent;padding:8px 9px;"
        "font-family:Arial,sans-serif;font-size:14px;line-height:1.35}.oceanval-sidebar li a:hover"
        "{background:rgba(255,255,255,0.16);border-left-color:#fff}"
        ".oceanval-sidebar a.oceanval-viewpdf-btn{color:#0f7c7c}"
        ".oceanval-sidebar a.oceanval-validation-link{color:#0f7c7c}"
        ".jp-Notebook{margin-left:340px!important;margin-right:300px!important;font-size:1.15rem}"
        ".jp-Notebook p,.jp-Notebook li,.jp-Notebook dd{margin-top:0;margin-bottom:0.9em}"
        ".jp-Notebook table{margin-left:auto!important;margin-right:auto!important}"
        ".jp-Notebook img,.jp-Notebook figure{display:block;margin-left:auto;margin-right:auto}"
        ".jp-Notebook figcaption{text-align:center}"
        ".oceanval-index{max-width:calc(100% - 600px);margin-left:300px;margin-right:300px;padding:70px 72px;box-sizing:border-box}.oceanval-index h1{font-size:42px;"
        "font-weight:600;line-height:1.1;margin:0 0 28px;color:#24364d}.oceanval-index p{font-size:18px;"
        "line-height:1.65;margin:14px 0}.oceanval-index a{color:#086eb6}.oceanval-actions{display:flex;"
        "gap:12px;margin-top:32px}.oceanval-actions a{border:1px solid #0879c1;padding:11px 16px;"
        "font-family:Arial,sans-serif;font-size:14px;font-weight:600;text-decoration:none}.oceanval-actions a:hover"
        "{background:#0879c1;color:#fff}"
        ".oceanval-download-btn{position:fixed;top:24px;right:24px;z-index:20;width:220px;box-sizing:border-box;"
        "background:#0f7c7c;color:#fff;border:1px solid #0a5f5f;border-radius:6px;padding:10px 14px;"
        "font-family:Arial,sans-serif;font-size:13px;font-weight:700;cursor:pointer;text-align:center;"
        "text-decoration:none;display:block}"
        ".oceanval-download-btn:hover{background:#0a5f5f}"
        "@media(max-width:720px){.oceanval-sidebar{position:static!important;width:auto;height:auto;max-height:none;padding:20px;overflow:visible}.oceanval-nav-sections{overflow:visible;padding-bottom:0}.oceanval-logo"
        "{margin-bottom:0}.oceanval-brand-link{padding-top:16px}.jp-Notebook{margin-left:auto!important;margin-right:0!important}.oceanval-index"
        "{max-width:none;margin-left:0;margin-right:0;padding:38px 24px}.oceanval-index h1{font-size:32px}.oceanval-actions{flex-direction:column;"
        "align-items:flex-start}.oceanval-download-btn{position:static;width:auto;margin:16px 0 0 20px}}</style>"
    )


def _offline_report_sidebar_script():
    return (
        "<script>(function(){function restore(){var nav=document.querySelector("
        "'.oceanval-nav-sections');if(!nav){return;}var key='oceanval-sidebar-scroll';"
        "var saved=sessionStorage.getItem(key);if(saved!==null){nav.scrollTop=Number(saved);}"
        "nav.addEventListener('scroll',function(){sessionStorage.setItem(key,nav.scrollTop);});}"
        "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',restore);}"
        "else{restore();}})();</script>"
    )


def _offline_report_pdf_style():
    return (
        "<style>@page{size:A4;margin:18mm 16mm}"
        "body{font-family:Georgia,'Times New Roman',serif;color:#203047;"
        "margin:0;line-height:1.55;font-size:12.5pt}"
        "h1{font-size:20pt;margin:0 0 12pt}h2{font-size:15pt;margin:18pt 0 8pt}"
        "h3{font-size:12.5pt;margin:14pt 0 6pt}"
        "p{margin:0 0 8pt}"
        "img{max-width:100%;display:block;margin:8pt auto}"
        "table{border-collapse:collapse;width:100%;margin:10pt auto;"
        "page-break-inside:avoid;break-inside:avoid}"
        "tr,td,th{page-break-inside:avoid;break-inside:avoid}"
        "td,th{border:1px solid #ccc;padding:5px 8px;font-size:9.5pt}"
        "pre{white-space:pre-wrap;word-break:break-word;font-size:9.5pt}"
        ".oceanval-math-inline{height:1.2em;vertical-align:middle}"
        ".oceanval-math-display{display:block;max-width:100%;margin:10pt auto}"
        ".headerlink,.anchor-link{display:none}</style>"
    )


def _render_latex_for_pdf(body_content):
    patterns = [
        (r'<span class="math inline">\\\((.*?)\\\)</span>', False),
        (r'<div class="math">\\\[(.*?)\\\]</div>', True),
        (r'\\\[(.*?)\\\]', True),
        (r'\\\((.*?)\\\)', False),
        (r'\$\$(.*?)\$\$', True),
        (r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', False),
    ]
    if not any(re.search(pattern, body_content, flags=re.S) for pattern, _ in patterns):
        return body_content

    from matplotlib.mathtext import math_to_image

    def replace_math(match, display):
        expression = match.group(1).strip()
        buffer = io.BytesIO()
        try:
            math_to_image(
                f"${expression}$",
                buffer,
                dpi=200,
                format="svg",
                color="#203047",
            )
        except Exception:
            return match.group(0)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        class_name = "oceanval-math-display" if display else "oceanval-math-inline"
        return f'<img class="{class_name}" src="data:image/svg+xml;base64,{encoded}" alt="{html.escape(expression)}">'

    for pattern, display in patterns:
        body_content = re.sub(
            pattern,
            lambda match, display=display: replace_math(match, display),
            body_content,
            flags=re.S,
        )
    return body_content


def _combined_report_pdf_source(output_dir, notebooks, notebook_bodies, pdf_style):
    # concatenates each page's PDF body in the same order as the sidebar navigation
    parts = []
    first = True
    for _, section_notebooks in _offline_report_sections(output_dir, notebooks):
        for notebook in section_notebooks:
            body = notebook_bodies.get(notebook)
            if body is None:
                continue
            break_style = "" if first else "page-break-before:always;break-before:page;"
            parts.append(f'<section style="{break_style}">{body}</section>')
            first = False
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>OceanVal validation report</title>{pdf_style}</head><body>"
        f"{''.join(parts)}</body></html>"
    )


def _render_offline_report_pdfs(pages):
    # pages: iterable of (html_string, pdf_path, base_url) tuples
    try:
        from weasyprint import HTML
    except ImportError:
        warnings.warn(
            "weasyprint is not installed, so PDF downloads were not generated. "
            "Install it with 'pip install weasyprint'."
        )
        return
    for html_string, pdf_path, base_url in pages:
        try:
            HTML(string=html_string, base_url=base_url).write_pdf(pdf_path)
        except Exception as error:
            warnings.warn(
                f"Could not generate the PDF download for {os.path.basename(pdf_path)} ({error})."
            )


def _write_offline_report_pages(output_dir, notebooks, validation_links=None):
    validation_links = validation_links or []
    index_validation_links = [
        (label, os.path.relpath(target, output_dir)) for label, target in validation_links
    ]
    page_validation_links = [
        (label, os.path.relpath(target, os.path.join(output_dir, "notebooks")))
        for label, target in validation_links
    ]
    style = _offline_report_style()
    pdf_style = _offline_report_pdf_style()
    index_navigation = _offline_report_navigation(
        output_dir, notebooks, "pml_logo.jpg", "notebooks/", "index.html", "oceanval_report.pdf",
        validation_links=index_validation_links,
    )
    page_navigation = _offline_report_navigation(
        output_dir, notebooks, "../pml_logo.jpg", "", "../index.html", "../oceanval_report.pdf",
        validation_links=page_validation_links,
    )
    with open(os.path.join(output_dir, "index.html"), "w") as index:
        index.write(
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>OceanVal validation report</title>{style}{_offline_report_sidebar_script()}</head><body>{index_navigation}"
            "<main class=\"oceanval-index\"><h1>An ocean model validation using oceanval</h1>"
            "<p>Simulations were validated using the Python package <strong>oceanval</strong>.</p>"
            "<p>The report navigation contains validation metrics, domain summaries, and results for each variable.</p>"
            "<p><strong>oceanval</strong> is developed by Robert Wilson at "
            "<a href=\"https://www.pml.ac.uk/\">Plymouth Marine Laboratory</a>, who can be contacted at "
            "<a href=\"mailto:rwi@pml.ac.uk\">rwi@pml.ac.uk</a>.</p>"
            "<div class=\"oceanval-actions\"><a href=\"https://github.com/pmlmodelling/oceanval\">Installation</a>"
            "<a href=\"https://oceanval.readthedocs.io/\">Documentation</a></div>"
            "</main></body></html>"
        )

    pdf_jobs = []
    page_updates = []
    notebook_bodies = {}
    for notebook in notebooks:
        stem = os.path.splitext(os.path.basename(notebook))[0]
        page = os.path.join(output_dir, "notebooks", f"{stem}.html")
        with open(page, "r") as report_page:
            raw_html = report_page.read()

        title_match = re.search(r"<title>(.*?)</title>", raw_html, re.S)
        title = title_match.group(1).strip() if title_match else stem
        body_match = re.search(r"<body[^>]*>(.*)</body>", raw_html, re.S)
        body_content = body_match.group(1) if body_match else raw_html
        # strip heading anchor links (e.g. the clickable "¶") from the PDF export
        body_content = re.sub(
            r'<a[^>]*class="[^"]*(?:headerlink|anchor-link)[^"]*"[^>]*>.*?</a>',
            "",
            body_content,
            flags=re.S,
        )
        body_content = _render_latex_for_pdf(body_content)
        notebook_bodies[notebook] = body_content
        pdf_source = (
            f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(title)}</title>{pdf_style}</head><body>{body_content}</body></html>"
        )
        pdf_path = os.path.join(output_dir, "notebooks", f"{stem}.pdf")
        pdf_jobs.append((pdf_source, pdf_path, os.path.dirname(page)))

        download_link = (
            f'<a class="oceanval-download-btn" href="{stem}.pdf" download>View page as pdf</a>'
        )
        page_html = re.sub(
            r"(<body[^>]*>)",
            lambda match: f"{match.group(1)}{page_navigation}{download_link}",
            raw_html,
            count=1,
        )
        page_html = page_html.replace(
            "</head>", f"{style}{_offline_report_sidebar_script()}</head>", 1
        )
        page_updates.append((page, page_html))

    if notebook_bodies:
        combined_source = _combined_report_pdf_source(
            output_dir, notebooks, notebook_bodies, pdf_style
        )
        combined_path = os.path.join(output_dir, "oceanval_report.pdf")
        pdf_jobs.append((combined_source, combined_path, output_dir))

    _render_offline_report_pdfs(pdf_jobs)

    for page, page_html in page_updates:
        with open(page, "w") as report_page:
            report_page.write(page_html)


def fix_toc(concise=True, data_dir=None, out_dir=None):
    short_titles = dill.load(
        open(f"{data_dir}/oceanval_matchups/short_titles.pkl", "rb")
    )
    paths = glob.glob(f"{out_dir}/oceanval_report/notebooks/*.ipynb")
    variables = dill.load(
        open(f"{data_dir}/oceanval_matchups/variables_matched.pkl", "rb")
    )
    variables.sort()

    vv_dict = dict()
    for vv in variables:
        vv_paths = [os.path.basename(x) for x in paths if f"_{vv}.ip" in x]
        if len(vv_paths) > 0:
            vv_dict[vv] = vv_paths
    # get summary docs
    ss_paths = [os.path.basename(x) for x in paths if "summary" in x]

    out = f"{out_dir}/oceanval_report/_toc.yml"
    myst_out = f"{out_dir}/oceanval_report/myst.yml"

    # write line by line to out
    i_chapter = 1
    with open(out, "w") as f, open(myst_out, "w") as myst:
        # "format: jb-book"
        x = f.write("format: jb-book\n")
        x = f.write("root: intro\n")
        x = f.write("parts:\n")

        myst.write("version: 1\n")
        myst.write("project:\n")
        myst.write("  title: OceanVal validation report\n")
        myst.write("  toc:\n")
        myst.write("    - file: intro.md\n")

        x = f.write(f"- caption: Summaries\n")
        x = f.write("  chapters:\n")

        myst.write("    - title: Summaries\n")
        myst.write("      children:\n")

        x = f.write(f"  - file: notebooks/001_methods.ipynb\n")
        myst.write("        - file: notebooks/001_methods.ipynb\n")

        # open notebook and replace book_chapter with i_chapter

        # open notebook and replace book_chapter with i_chapter
        with open(
            f"{out_dir}/oceanval_report/notebooks/001_methods.ipynb", "r"
        ) as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("book_chapter", str(i_chapter))
        filedata = filedata.replace("info_text", "Validation metrics summary")

        with open(
            f"{out_dir}/oceanval_report/notebooks/001_methods.ipynb", "w"
        ) as file:
            file.write(filedata)
        i_chapter += 1
        for ff in ss_paths:
            x = f.write(f"  - file: notebooks/{ff}\n")
            myst.write(f"        - file: notebooks/{ff}\n")
            # open notebook and replace book_chapter with i_chapter
            with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "r") as file:
                filedata = file.read()

            filedata = filedata.replace("book_chapter", str(i_chapter))

            # Replace the target string
            # Write the file out again
            with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "w") as file:
                file.write(filedata)
            i_chapter += 1

        # loop over variables in each vv_dict
        # value is the file in the chapter section
        # key is the variable name, so is the section
        for vv in vv_dict.keys():
            # capitalize if not ph
            vv_out = short_titles[vv]

            x = f.write(f"- caption: {vv_out}\n")
            x = f.write("  chapters:\n")
            myst.write(f"    - title: {vv_out}\n")
            myst.write("      children:\n")
            for ff in vv_dict[vv]:
                x = f.write(f"  - file: notebooks/{ff}\n")
                myst.write(f"        - file: notebooks/{ff}\n")

                # open notebook and replace book_chapter with i_chapter
                with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "r") as file:
                    filedata = file.read()

                # Replace the target string
                filedata = filedata.replace("book_chapter", str(i_chapter))

                # Write the file out again

                with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "w") as file:
                    file.write(filedata)
                i_chapter += 1

        myst.write("site:\n")
        myst.write("  template: book-theme\n")
        myst.write("  options:\n")
        myst.write("    logo: pml_logo.jpg\n")
        myst.write("    folders: true\n")



def validate(
    lon_lim=None,
    lat_lim=None,
    concise=True,
    fixed_scale=False,
    region=None,
    data_dir=".",
    out_dir=".",
    test=False
):
    # docstring
    """
    Run the model evaluation for all of the available datasets, and generate a validation report.

    Parameters
    ----------
    lon_lim : list or None
        The longitude limits for the validation. Default is None
    lat_lim : list or None
        The latitude limits for the validation. Default is None
    fixed_scale : bool
        Whether to use a fixed scale for the seasonal plots. Default is False. If True, the minimum and maximum values are capped to cover the 2nd and 98th percentiles of both model and observations.
    region : str or None
        The region being validated. Must be either "nwes" (northwest European Shelf) or "global". Default is None.
    test : bool
        Default is False. Ignore, unless you are testing oceanval.

    Returns
    -------
    None
    """

    # if lon_lim  is not None, make sure it's a list
    if lon_lim is not None:
        if isinstance(lon_lim, list) == False:
            raise ValueError("lon_lim must be a list")
        else:
            if len(lon_lim) != 2:
                raise ValueError("lon_lim must be a list of length 2")
    if lat_lim is not None:
        if isinstance(lat_lim, list) == False:
            raise ValueError("lat_lim must be a list")
        else:
            if len(lat_lim) != 2:
                raise ValueError("lat_lim must be a list of length 2")

    # concise must be boolean
    if isinstance(concise, bool) == False:
        raise ValueError("concise must be a boolean")

    # checked fixed_scale is bool
    if isinstance(fixed_scale, bool) == False:
        raise ValueError("fixed_scale must be a boolean")

    # convert data_dir to absolute path
    data_dir = os.path.expanduser(data_dir)
    data_dir = os.path.abspath(data_dir)
    if region is not None and region not in ["nwes", "global"]:
        raise ValueError("region must be either 'nwes' or 'global'")
    # ensure proper handling of ~
    out_dir = os.path.expanduser(out_dir)
    out_dir = os.path.abspath(out_dir)

    book_dir = os.path.join(out_dir, "oceanval_report")
    # if it doesn't exist, create it
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    

    path_df = []

    fast_plot = False

    empty = True

    # book directory is book, book1, book2, book10 etc.

    # create a new name if one already exists
    i = 0

    if os.path.exists(book_dir):
        shutil.rmtree(book_dir)



    # remove the results directory
    x_path = "oceanval_results"
    if os.path.exists(x_path):
        if x_path == "oceanval_results":
            shutil.rmtree(x_path)

    if empty:
        from shutil import copyfile

        if not os.path.exists(book_dir):
            os.mkdir(book_dir)
        if not os.path.exists(f"{book_dir}/notebooks"):
            os.mkdir(f"{book_dir}/notebooks")


        data_path = importlib.resources.files(__name__).joinpath(
            "data/001_methods.ipynb"
        )
        if not os.path.exists(f"{book_dir}/notebooks/001_methods.ipynb"):
            copyfile(data_path, f"{book_dir}/notebooks/001_methods.ipynb")
        # open this file and replace model_name with model

        data_path = importlib.resources.files(__name__).joinpath("data/_toc.yml")

        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        data_path = importlib.resources.files(__name__).joinpath("data/intro.md")
        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        data_path = importlib.resources.files(__name__).joinpath(
            "data/requirements.txt"
        )
        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        data_path = importlib.resources.files(__name__).joinpath("data/intro.md")
        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        # copy config

        data_path = importlib.resources.files(__name__).joinpath("data/_config.yml")
        out = f"{book_dir}/" + os.path.basename(data_path)

        with open(data_path, "r") as file:
            filedata = file.read()

        # Write the file out again
        with open(out, "w") as file:
            file.write(filedata)

        # copyfile(data_path, out)

        # copy the custom stylesheet used to theme the built report
        static_src = importlib.resources.files(__name__).joinpath("data/_static")
        static_out = f"{book_dir}/_static"
        if not os.path.exists(static_out):
            os.makedirs(static_out)
        copyfile(f"{static_src}/custom.css", f"{static_out}/custom.css")

        path_df = []

        # loop through the point matchups and generate notebooks

        point_paths = glob.glob(f"{data_dir}/oceanval_matchups/point/**/**/**/**.csv")
        point_paths = [x for x in point_paths if "unit" not in os.path.basename(x)]
        # loop through the paths
        for pp in point_paths:
            ff_def = pp.replace(".csv", "_definitions.pkl")
            definitions = dill.load(open(ff_def, "rb"))
            vv = os.path.basename(pp).split("_")[2].replace(".csv", "")
            source = os.path.basename(pp).split("_")[0]
            variable = vv
            layer = os.path.basename(pp).split("_")[1].replace(".csv", "")
            Variable = definitions[variable].short_name

            vv_file = pp
            vv_file_find = pp.replace("../../", "")

            if os.path.exists(vv_file_find):
                if (
                    len(
                        glob.glob(
                            f"{book_dir}/notebooks/*point_{layer}_{variable}.ipynb"
                        )
                    )
                    == 0
                ):
                    file1 = importlib.resources.files(__name__).joinpath(
                        "data/point_template.ipynb"
                    )
                    with open(file1, "r") as file:
                        filedata = file.read()

                    if layer in ["all", "surface"]:
                        filedata = filedata.replace(
                            "chunk_point_surface", "chunk_point"
                        )
                    else:
                        filedata = filedata.replace("chunk_point_surface", "")
                    if layer in ["bottom", "all"]:
                        if vv.lower() not in ["pco2"]:
                            filedata = filedata.replace(
                                "chunk_point_bottom", "chunk_point"
                            )
                        else:
                            filedata = filedata.replace("chunk_point_bottom", "")
                    else:
                        filedata = filedata.replace("chunk_point_bottom", "")

                    # Replace the target string
                    out = f"{book_dir}/notebooks/{source}_{layer}_{variable}.ipynb"
                    filedata = filedata.replace("point_variable", variable)
                    n_levels = definitions[variable].n_levels
                    if layer != "all":
                        if n_levels > 1:
                            filedata = filedata.replace(
                                "Validation of point_layer", f"Validation of {layer}"
                            )
                        else:
                            filedata = filedata.replace(
                                "Validation of point_layer", f"Validation of "
                            )
                    else:
                        filedata = filedata.replace(
                            "Validation of point_layer", f"Validation of "
                        )

                    filedata = filedata.replace("point_layer", layer)
                    filedata = filedata.replace("point_obs_source", source)
                    filedata = filedata.replace("template_title", Variable)
                    filedata = filedata.replace("data_dir_value", data_dir)
                    filedata = filedata.replace("out_dir_value", out_dir)

                    # Write the file out again
                    with open(out, "w") as file:
                        file.write(filedata)

                    path_df.append(
                        pd.DataFrame(
                            {
                                "variable": [variable],
                                "path": out,
                            }
                        )
                    )

        # Loop through the gridded matchups and generate notebooks
        # identify gridded variables in matched data
        gridded_paths = glob.glob(f"{data_dir}/oceanval_matchups/gridded/**/**.nc")

        if len(gridded_paths) > 0:
            for vv in [
                os.path.basename(x).split("_")[1].replace(".nc", "")
                for x in gridded_paths
            ]:
                for source in [
                    os.path.basename(x).split("_")[0]
                    for x in glob.glob(
                        f"{data_dir}/oceanval_matchups/gridded/**/**_{vv}_**.nc"
                    )
                ]:

                    variable = vv
                    if not os.path.exists(
                        f"{book_dir}/notebooks/{source}_{variable}.ipynb"
                    ):
                        ff_def = glob.glob(
                            f"{data_dir}/oceanval_matchups/gridded/{variable}/{source}_*definitions*.pkl"
                        )[0]
                        definitions = dill.load(open(ff_def, "rb"))
                        Variable = definitions[variable].short_name
                        ff_nc = glob.glob(
                            f"{data_dir}/oceanval_matchups/gridded/{variable}/{source}_*surface*.nc"
                        )[0]
                        ds = nc.open_data(ff_nc, checks=False)
                        try:
                            n_months = len(ds.months)
                        except:
                            n_months = 12
                        seasonal = n_months >= 12

                        file1 = importlib.resources.files(__name__).joinpath(
                            "data/gridded_template.ipynb"
                        )
                        if (
                            len(
                                glob.glob(
                                    f"{book_dir}/notebooks/*{source}_{variable}.ipynb"
                                )
                            )
                            == 0
                        ):
                            with open(file1, "r") as file:
                                filedata = file.read()

                            # Replace the target string
                            filedata = filedata.replace("template_variable", variable)
                            filedata = filedata.replace("template_title", Variable)
                            filedata = filedata.replace("data_dir_value", data_dir)
                            filedata = filedata.replace("source_name", source)
                            if region == "nwes":
                                filedata = filedata.replace("zonal_height", "6000")
                            else:
                                filedata = filedata.replace("zonal_height", "2000")
                            # make every letter a capital
                            source_capital = source.upper()
                            filedata = filedata.replace("source_title", source_capital)
                            if seasonal is False:
                                filedata = filedata.replace("chunk_seasonal", "")
                            if region is not None:
                                filedata = filedata.replace("sub_regions_value", str(region))

                            # Write the file out again
                            with open(
                                f"{book_dir}/notebooks/{source}_{variable}.ipynb", "w"
                            ) as file:
                                file.write(filedata)

                            variable = vv
                            path_df.append(
                                pd.DataFrame(
                                    {
                                        "variable": [variable],
                                        "path": [
                                            f"{book_dir}/notebooks/{source}_{variable}.ipynb"
                                        ],
                                    }
                                )
                            )

        # need to start by figuring out whether anything has already been run...

        i = 0

        for ff in [
            x for x in glob.glob("{book_dir}/notebooks/*.ipynb") if "info" not in x
        ]:
            try:
                i_ff = int(os.path.basename(ff).split("_")[0])
                if i_ff > i:
                    i = i_ff
            except:
                pass

        i_orig = i

        if len(path_df) > 0:
            path_df = pd.concat(path_df)
            path_df = path_df.sort_values("variable").reset_index(drop=True)

        for i in range(len(path_df)):
            file1 = path_df.path.values[i]
            # pad i with zeros using zfill
            i_pad = str(i + 1).zfill(3)
            new_file = (
                os.path.dirname(file1) + "/" + i_pad + "_" + os.path.basename(file1)
            )
            os.rename(file1, new_file)

        # copy the summary.ipynb notebook and add i_pad to the name

        i = i + 2
        i_pad = str(i).zfill(3)

        file1 = importlib.resources.files(__name__).joinpath("data/summary.ipynb")
        if len(glob.glob(f"{book_dir}/notebooks/*summary.ipynb")) == 0:
            copyfile(file1, f"{book_dir}/notebooks/{i_pad}_summary.ipynb")

        # change domain_title to "Full domain"

        with open(f"{book_dir}/notebooks/{i_pad}_summary.ipynb", "r") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("domain_title", "Full domain")
        filedata = filedata.replace("data_dir_value", data_dir)
        filedata = filedata.replace("out_dir_value", out_dir)

        # Write the file out again
        with open(f"{book_dir}/notebooks/{i_pad}_summary.ipynb", "w") as file:
            file.write(filedata)

        # pair the notebooks using jupyter text

        os.system(
            f"jupytext --set-formats ipynb,py:percent {book_dir}/notebooks/*.ipynb"
        )

        # add the chunks
        add_chunks(out_dir)

        # loop through the notebooks and set r warnings options
        for ff in glob.glob(f"{book_dir}/notebooks/*.py"):
            with open(ff, "r") as file:
                filedata = file.read()

            # loop through line by line, and rewrite the original file
            lines = filedata.split("\n")
            new_lines = []
            for line in lines:
                if "%%R" in line:
                    new_lines.append(line)
                    new_lines.append("options(warn=-1)")
                else:
                    new_lines.append(line)
            # loop through all lines in lines and replace the_test_status with True
            for i in range(len(new_lines)):
                new_lines[i] = new_lines[i].replace("latexpagebreak", "")
                if "the_test_status" in new_lines[i]:
                    if test:
                        new_lines[i] = new_lines[i].replace("the_test_status", "True")
                    else:
                        new_lines[i] = new_lines[i].replace("the_test_status", "False")
                if '"gam"' in new_lines[i]:
                    new_lines[i] = new_lines[i].replace('"gam"', '"lm"')

                new_lines[i] = new_lines[i].replace("the_lon_lim", str(lon_lim))
                new_lines[i] = new_lines[i].replace("the_lat_lim", str(lat_lim))
                new_lines[i] = new_lines[i].replace(
                    "fixed_scale_value", str(fixed_scale)
                )
                # replace concice_value with concice
                if "concise_value" in new_lines[i]:
                    if concise:
                        new_lines[i] = new_lines[i].replace("concise_value", "True")
                    else:
                        new_lines[i] = new_lines[i].replace("concise_value", "False")

            # write the new lines to the file
            with open(ff, "w") as file:
                for line in new_lines:
                    file.write(line + "\n")

        # sync the notebooks
        #
        os.system(f"jupytext --sync {book_dir}/notebooks/*.ipynb")

    # loop through notebooks and change fast_plot_value to fast_plot

    for ff in glob.glob(f"{book_dir}/notebooks/*.ipynb"):
        with open(ff, "r") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("fast_plot_value", str(fast_plot))
        filedata = filedata.replace("data_dir_value", data_dir)
        filedata = filedata.replace("out_dir_value", out_dir)

        # Write the file out again
        with open(ff, "w") as file:
            file.write(filedata)

    # fix the toc using the function

    fix_toc(concise=concise, data_dir=data_dir, out_dir=out_dir)

    for ff in glob.glob(f"{book_dir}/notebooks/*.ipynb"):
        ff_clean = ff.replace(".ipynb", ".py")
        if os.path.exists(ff_clean):
            os.remove(ff_clean)

    # move pml_logo to book directory

    shutil.copyfile(
        importlib.resources.files(__name__).joinpath("data/pml_logo.jpg"),
        f"{book_dir}/pml_logo.jpg",
    )

    _build_book(book_dir)

    stamps = [
        os.path.basename(x) for x in glob.glob(f"{book_dir}/notebooks/.trackers/*")
    ]
    stamps.append("nctoolkit_rwi_uhosarcenctoolkittmp")

    delete = []
    for x in stamps:
        delete += glob.glob("/tmp/*" + x + "*")

    for ff in delete:
        if os.path.exists(ff):
            if "nctoolkit" in x:
                os.remove(ff)

    out_ff = f"{book_dir}/_build/html/index.html"

    # create a symlink to the html file
    if os.path.exists(f"{out_dir}/oceanval_report.html"):
        os.remove(f"{out_dir}/oceanval_report.html")
    # os.symlink(f"{book_dir}/_build/html/index.html", f"{out_dir}/oceanval_report.html")
    # create a symlink with relative directory
    os.symlink(os.path.relpath(out_ff, out_dir), f"{out_dir}/oceanval_report.html")
    if test is False:
        webbrowser.open(
            "file://" + os.path.abspath(f"{book_dir}/_build/html/index.html")
        )


def rebuild(data_dir="."):
    """
    Rebuild the validation report after modifying notebooks.
    Use this if you have modified the notebooks generated and want to create a new validation report.

    Parameters
    ----------
    data_dir : str
        The directory where the oceanval_report directory is located. Default is current directory.
    """
    # check data_dir exists
    if not os.path.exists(data_dir):
        raise ValueError(f"data_dir {data_dir} does not exist")
    # add a deprecation notice
    data_dir = os.path.expanduser(data_dir)
    data_dir = os.path.abspath(data_dir)

    _build_book(f"{data_dir}/oceanval_report")

    webbrowser.open(
        "file://"
        + os.path.abspath(f"{data_dir}/oceanval_report/_build/html/index.html")
    )


def compare(model_dict=None, view=True, ask=True):
    """
    Compare pre-validated simulations.
    This function will compare the validation output from multiple simulations.

    Parameters
    ----------
    model_dict : dict
        A dictionary mapping model names to the paths of their validation outputs.
    view : bool
        Open the comparison report in a web browser after it is generated.
    ask : bool
        If the comparison directory already exists, ask before replacing it.
    """
    if model_dict is None:
        raise AttributeError("model_dict must be provided")
    if not isinstance(model_dict, dict):
        raise AttributeError("model_dict must be a dictionary")

    for key in model_dict.keys():
        if not os.path.exists(model_dict[key]):
            raise ValueError(f"Path {model_dict[key]} does not exist")
        model_dict[key] = os.path.abspath(model_dict[key])

    if os.path.exists("oceanval_comparison"):
        if ask:
            user_input = input(
                "oceanval_comparison directory already exists. This will be emptied and replaced. Do you want to proceed? (y/n): "
            )
            if user_input.lower() != "y":
                print("Exiting")
                return None

        while True:
            files = glob.glob("oceanval_comparison/**/**/**", recursive=True)
            for ff in files:
                if ff.startswith("oceanval_comparison"):
                    try:
                        os.remove(ff)
                    except Exception:
                        pass
            files = glob.glob("oceanval_comparison/**/**/**", recursive=True)
            files = [x for x in files if os.path.isfile(x)]
            if len(files) == 0:
                break

    if not os.path.exists("oceanval_comparison/compare"):
        os.makedirs("oceanval_comparison/compare")
    if not os.path.exists("oceanval_comparison/compare/notebooks"):
        os.makedirs("oceanval_comparison/compare/notebooks")

    shutil.copyfile(
        os.path.join(os.path.dirname(__file__), "data", "pml_logo.jpg"),
        "oceanval_comparison/compare/pml_logo.jpg",
    )

    comparison_notebooks = [
        "comparison_seasonal.ipynb",
        "comparison_spatial.ipynb",
        "comparison_regional.ipynb",
        "comparison_bias.ipynb",
    ]
    for notebook_name in comparison_notebooks:
        data_path = importlib.resources.files(__name__).joinpath(f"data/{notebook_name}")
        dest_path = os.path.join("oceanval_comparison", "compare", "notebooks", notebook_name)
        shutil.copyfile(data_path, dest_path)

    # book scaffold: needed for the classic jupyter-book<2 build, harmless for >=2
    with open("oceanval_comparison/compare/_config.yml", "w") as file:
        file.write(
            "title:\n"
            "author:   \"Robert Wilson | Plymouth Marine Laboratory\"\n"
            "logo: \"pml_logo.jpg\"\n"
            "copyright:  Plymouth Marine Laboratory\n"
            "execute:\n"
            "  execute_notebooks: force\n"
            "  timeout: 500\n"
            "  allow_errors: true\n"
            "sphinx:\n"
            "  config:\n"
            "    html_static_path: ['_static']\n"
            "    html_css_files: ['custom.css']\n"
        )
    with open("oceanval_comparison/compare/_toc.yml", "w") as file:
        file.write("format: jb-book\nroot: intro\nchapters:\n- glob: notebooks/*\n")
    with open("oceanval_comparison/compare/intro.md", "w") as file:
        file.write(
            "# Comparison of ocean model simulations\n\n"
            "This report compares the validation results of multiple simulations using **oceanval**.\n"
        )

    static_src = importlib.resources.files(__name__).joinpath("data/_static")
    static_out = "oceanval_comparison/compare/_static"
    if not os.path.exists(static_out):
        os.makedirs(static_out)
    shutil.copyfile(f"{static_src}/custom.css", f"{static_out}/custom.css")

    model_dict_str = str(model_dict)
    for notebook_name in comparison_notebooks:
        path = os.path.join("oceanval_comparison", "compare", "notebooks", notebook_name)
        with open(path, "r") as file:
            filedata = file.read()
        filedata = filedata.replace("model_dict_str", model_dict_str)
        with open(path, "w") as file:
            file.write(filedata)

    os.system("jupytext --set-formats ipynb,py:percent oceanval_comparison/compare/notebooks/*.ipynb")
    add_chunks(None)
    for book in glob.glob("oceanval_comparison/compare/notebooks/*.py"):
        with open(book, "r") as file:
            filedata = file.read()
        filedata = filedata.replace("the_test_status", "False")
        filedata = filedata.replace("the_lon_lim", "None")
        filedata = filedata.replace("the_lat_lim", "None")
        filedata = filedata.replace("concise_value", "False")
        filedata = filedata.replace("fast_plot_value", "False")
        with open(book, "w") as file:
            file.write(filedata)
    os.system("jupytext --sync oceanval_comparison/compare/notebooks/*.ipynb")
    validation_links = [
        (key, os.path.join(model_dict[key], "oceanval_report", "_build", "html", "index.html"))
        for key in model_dict
    ]
    _build_book("oceanval_comparison/compare", validation_links=validation_links)

    if view:
        webbrowser.open(
            "file://" + os.path.abspath("oceanval_comparison/compare/_build/html/index.html")
        )


try:
    from importlib.metadata import version as _version
except ImportError:
    from importlib_metadata import version as _version

try:
    __version__ = _version("oceanval")
except Exception:
    __version__ = "999"


import tempfile


def temp_check():
    """
    Function to check temp files
    """

    mylist = [f for f in glob.glob("/tmp/*")]
    mylist = mylist + [f for f in glob.glob("/var/tmp/*")]
    mylist = mylist + [f for f in glob.glob("/usr/tmp/*")]
    mylist = [f for f in mylist if "nctoolkit" in f]

    mylist = [x for x in mylist if "ecoval_output" in x]

    session_info["old_files"] = mylist

    if len(mylist) > 0:
        if len(mylist) == 1:
            print(
                f"{len(mylist)} temporary file was created by oceanval in prior or current "
                f"sessions. Consider running oceanval.deep_clean!"
            )
        else:
            print(
                f"{len(mylist)} temporary files were created by oceanval in prior or current"
                f" sessions. Consider running oceanval.deep_clean!"
            )


temp_check()


def deep_clean():
    """
    Deep temp file cleaner.
    Remove all temporary files ever created by oceanval
    across all previous and current sesions
    """

    candidates = session_info["old_files"]

    mylist = [f for f in candidates if "nctoolkit" in f and "ecoval_output" in f]
    for ff in mylist:
        if ff in session_info["old_files"]:
            if "nctoolkit" in ff and "ecoval_output" in ff:
                os.remove(ff)
