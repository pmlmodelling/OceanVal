import re
from unittest.mock import call, patch

import nbformat
import oceanval


def test_build_book_uses_legacy_command_for_jupyter_book_1():
    with patch.object(oceanval, "_version", return_value="1.0.4"), patch(
        "oceanval.subprocess.run"
    ) as run:
        oceanval._build_book("report")

    run.assert_called_once_with(["jupyter-book", "build", "report"], check=True)


def test_build_book_uses_offline_html_for_jupyter_book_2():
    with patch.object(oceanval, "_version", return_value="2.1.6"), patch(
        "oceanval.glob.glob",
        return_value=[
            "report/notebooks/summary.ipynb",
            "report/notebooks/example.ipynb",
        ],
    ), patch("oceanval.os.makedirs"), patch("oceanval.shutil.copyfile"), patch(
        "oceanval._remove_diagnostic_outputs"
    ) as remove_diagnostics, patch(
        "oceanval._write_offline_report_pages"
    ) as write_pages, patch("oceanval.subprocess.run") as run:
        oceanval._build_book("report")

    assert run.call_args_list == [
        call(
            [
                "jupyter",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                "--inplace",
                "--allow-errors",
                "--ExecutePreprocessor.timeout=500",
                "report/notebooks/example.ipynb",
                "report/notebooks/summary.ipynb",
            ],
            check=True,
        ),
        call(
            [
                "jupyter",
                "nbconvert",
                "--to",
                "html",
                "--no-input",
                "--output-dir",
                "report/_build/html/notebooks",
                "report/notebooks/example.ipynb",
                "report/notebooks/summary.ipynb",
            ],
            check=True,
        ),
    ]
    write_pages.assert_called_once_with(
        "report/_build/html",
        ["report/notebooks/example.ipynb", "report/notebooks/summary.ipynb"],
        validation_links=None,
        pdf=False,
    )
    remove_diagnostics.assert_called_once_with(
        ["report/notebooks/example.ipynb", "report/notebooks/summary.ipynb"]
    )


def test_remove_diagnostic_outputs_preserves_formatted_content(tmp_path):
    notebook_path = tmp_path / "report.ipynb"
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                outputs=[
                    nbformat.v4.new_output("stream", text="warning"),
                    nbformat.v4.new_output("error", ename="Error", evalue="failure"),
                        nbformat.v4.new_output(
                            "error", ename="RInterpreterError", evalue="R plot failed"
                        ),
                    nbformat.v4.new_output("execute_result", data={"text/plain": "0"}),
                    nbformat.v4.new_output("execute_result", data={"text/html": "<table>"}),
                    nbformat.v4.new_output("display_data", data={"image/png": "data"}),
                ]
            )
        ]
    )
    nbformat.write(notebook, notebook_path)

    oceanval._remove_diagnostic_outputs([str(notebook_path)])

    outputs = nbformat.read(notebook_path, as_version=4).cells[0].outputs
    assert [output.output_type for output in outputs] == [
        "error",
        "execute_result",
        "display_data",
    ]
    assert outputs[0].ename == "RInterpreterError"


def test_remove_diagnostic_outputs_preserves_remove_cell_tags(tmp_path):
    notebook_path = tmp_path / "report.ipynb"
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(
                "## Read in the data",
                metadata={"tags": ["remove-cell"]},
            ),
            nbformat.v4.new_markdown_cell("Visible content"),
        ]
    )
    nbformat.write(notebook, notebook_path)

    oceanval._remove_diagnostic_outputs([str(notebook_path)])

    written_notebook = nbformat.read(notebook_path, as_version=4)
    assert len(written_notebook.cells) == 2
    assert written_notebook.cells[0].source == "## Read in the data"
    assert written_notebook.cells[0].metadata["tags"] == ["remove-cell"]
    assert written_notebook.cells[1].source == "Visible content"


def test_remove_diagnostic_outputs_drops_warning_streams(tmp_path):
    notebook_path = tmp_path / "report.ipynb"
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                outputs=[
                    nbformat.v4.new_output("stream", name="stdout", text="normal output"),
                    nbformat.v4.new_output(
                        "stream",
                        name="stderr",
                        text="Warning: plotting code produced a warning",
                    ),
                    nbformat.v4.new_output("display_data", data={"text/plain": "plot"}),
                ]
            )
        ]
    )
    nbformat.write(notebook, notebook_path)

    oceanval._remove_diagnostic_outputs([str(notebook_path)])

    written_notebook = nbformat.read(notebook_path, as_version=4)
    outputs = written_notebook.cells[0].outputs
    assert outputs == []


def test_remove_diagnostic_outputs_keeps_real_plot_outputs(tmp_path):
    notebook_path = tmp_path / "report.ipynb"
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                outputs=[
                    nbformat.v4.new_output(
                        "display_data",
                        data={"text/plain": "<Figure size 640x480 with 0 Axes>"},
                    ),
                    nbformat.v4.new_output(
                        "display_data",
                        data={"image/png": "data:image/png;base64,abc123"},
                    ),
                ]
            )
        ]
    )
    nbformat.write(notebook, notebook_path)

    oceanval._remove_diagnostic_outputs([str(notebook_path)])

    written_notebook = nbformat.read(notebook_path, as_version=4)
    outputs = written_notebook.cells[0].outputs
    assert len(outputs) == 1
    assert outputs[0].data == {"image/png": "data:image/png;base64,abc123"}


def test_offline_report_pages_group_navigation_and_hide_code(tmp_path):
    output_dir = tmp_path / "_build" / "html"
    notebook_dir = output_dir / "notebooks"
    notebook_dir.mkdir(parents=True)
    source_notebook_dir = tmp_path / "notebooks"
    source_notebook_dir.mkdir()
    (tmp_path / "_toc.yml").write_text(
        "format: jb-book\nroot: intro\nparts:\n"
        "- caption: Summaries\n  chapters:\n"
        "  - file: notebooks/001_methods.ipynb\n"
        "  - file: notebooks/002_summary.ipynb\n"
        "- caption: Temperature\n  chapters:\n"
        "  - file: notebooks/003_foo_temperature.ipynb\n"
    )
    pages = [
        notebook_dir / "001_methods.html",
        notebook_dir / "002_summary.html",
        notebook_dir / "003_foo_temperature.html",
    ]
    for page in pages:
        page.write_text(
            '<html><head></head><body class="jp-Notebook"><main>Report</main></body></html>'
        )
    notebook_titles = {
        "001_methods": "Validation metrics summary",
        "002_summary": "Full domain summary statistics of model performance",
        "003_foo_temperature": "Sea surface temperature validation using gridded observations from FOO",
    }
    for stem, title in notebook_titles.items():
        notebook = nbformat.v4.new_notebook(
            cells=[nbformat.v4.new_markdown_cell(f"# {title}")]
        )
        nbformat.write(notebook, source_notebook_dir / f"{stem}.ipynb")

    oceanval._write_offline_report_pages(
        str(output_dir),
        [
            str(source_notebook_dir / "001_methods.ipynb"),
            str(source_notebook_dir / "002_summary.ipynb"),
            str(source_notebook_dir / "003_foo_temperature.ipynb"),
        ],
        pdf=True,
    )

    # there is no index.html: reports land straight on a notebook page
    assert not (output_dir / "index.html").exists()

    report_page = pages[-1].read_text()
    assert "Validation metrics summary" in report_page
    assert "Full domain summary statistics of model performance" in report_page
    assert "Temperature" in report_page
    assert "Sea surface temperature validation using gridded observations from FOO" in report_page
    assert 'href="003_foo_temperature.html"' in report_page
    assert ".jp-Notebook{margin-left:340px!important;margin-right:300px!important;font-size:1.15rem}" in report_page
    assert ".oceanval-nav-sections{flex:1 1 auto;overflow-y:auto;min-height:0" in report_page
    assert ".oceanval-sidebar{position:fixed!important" in report_page
    assert "sessionStorage" in report_page
    assert report_page.index('class="oceanval-nav-sections"') < report_page.index('class="oceanval-viewpdf-btn"')


def test_offline_report_pages_pdf_off_by_default(tmp_path):
    output_dir = tmp_path / "_build" / "html"
    notebook_dir = output_dir / "notebooks"
    notebook_dir.mkdir(parents=True)
    source_notebook_dir = tmp_path / "notebooks"
    source_notebook_dir.mkdir()

    page = notebook_dir / "001_methods.html"
    page.write_text(
        '<html><head></head><body class="jp-Notebook"><main>Report</main></body></html>'
    )
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_markdown_cell("# Validation metrics summary")]
    )
    notebook_path = source_notebook_dir / "001_methods.ipynb"
    nbformat.write(notebook, notebook_path)

    oceanval._write_offline_report_pages(str(output_dir), [str(notebook_path)])

    report_page = page.read_text()
    # the CSS rules for these classes are always embedded in the stylesheet;
    # what must be absent is the actual element using them
    assert 'class="oceanval-viewpdf-btn"' not in report_page
    assert 'class="oceanval-download-btn"' not in report_page
    assert list(output_dir.rglob("*.pdf")) == []


def test_pdf_latex_is_embedded_as_svg():
    body = '<p>Inline \\(x^2\\) and $m$</p><div class="math">\\[E=mc^2\\]</div>'

    rendered = oceanval._render_latex_for_pdf(body)

    assert rendered.count("data:image/svg+xml;base64,") == 3
    assert "\\(" not in rendered
    assert "\\[" not in rendered
    assert "$m$" not in rendered


def test_pdf_latex_is_sized_relative_to_the_text():
    rendered = oceanval._render_latex_for_pdf(
        '<p>Inline $m$</p><div class="math">\\[E=mc^2\\]</div>'
    )

    inline = re.search(r'class="oceanval-math-inline" style="([^"]*)"', rendered)
    display = re.search(r'class="oceanval-math-display" style="([^"]*)"', rendered)

    # sized in em so the maths scales with the body text, and sat on the
    # baseline rather than being forced to a fixed height
    assert re.fullmatch(
        r"width:[\d.]+em;height:[\d.]+em;vertical-align:-[\d.]+em", inline.group(1)
    )
    # no height, so an over-wide equation scales instead of being squashed
    assert re.fullmatch(r"width:[\d.]+em", display.group(1))


def test_pdf_pages_are_numbered_and_carry_a_linked_wordmark():
    style = oceanval._offline_report_pdf_style()
    footer = oceanval._offline_report_pdf_footer()

    assert "@bottom-left{content:'Page ' counter(page) ' of ' counter(pages)" in style
    assert "@bottom-right{content:element(oceanvalfooter)}" in style
    assert ".oceanval-pdf-footer{position:running(oceanvalfooter)}" in style
    assert 'href="https://pmlmodelling.github.io/OceanVal/"' in footer
    assert "data:image/svg+xml;base64," in footer