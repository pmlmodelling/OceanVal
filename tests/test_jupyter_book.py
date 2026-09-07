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
    ), patch("oceanval.os.makedirs"), patch(
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
    )

    index = (output_dir / "index.html").read_text()
    report_page = pages[-1].read_text()
    for document in (index, report_page):
        assert "OceanVal by" in document
        assert "Plymouth Marine Laboratory" in document
        assert "Validation metrics summary" in document
        assert "Full domain summary statistics of model performance" in document
        assert "Temperature" in document
        assert "Sea surface temperature validation using gridded observations from FOO" in document
    assert 'href="notebooks/003_foo_temperature.html"' in index
    assert 'href="003_foo_temperature.html"' in report_page
    assert 'href="index.html"' in index
    assert 'href="../index.html"' in report_page
    assert 'src="../../pml_logo.jpg"' in index
    assert 'src="../../../pml_logo.jpg"' in report_page
    assert index.index('class="oceanval-nav-sections"') < index.index('class="oceanval-brand-link"')
    assert 'class="oceanval-brand-block"' in index
    assert 'class="oceanval-logo-box"' in index
    assert ".jp-Notebook{margin-left:340px!important;margin-right:300px!important}" in index
    assert ".oceanval-nav-sections{flex:1 1 auto;overflow-y:auto;min-height:0" in index
    assert ".oceanval-brand-link{display:block;flex:0 0 auto" in index
    assert ".oceanval-index{max-width:calc(100% - 600px);margin-left:300px;margin-right:300px" in index
    assert '<div class="oceanval-actions">' in index
    assert "Robert Wilson" in index
    assert 'href="mailto:rwi@pml.ac.uk"' in index