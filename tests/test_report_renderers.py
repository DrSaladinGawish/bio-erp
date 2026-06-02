from pathlib import Path
import pytest

from app.services.report_renderers import ExcelRenderer, PDFRenderer, CSVRenderer


class TestExcelRenderer:
    def test_generate_with_rows(self, tmp_path: Path):
        data = {"rows": [{"item": "A", "cost": 100}, {"item": "B", "cost": 200}]}
        path = str(tmp_path / "test.xlsx")
        result = ExcelRenderer.generate("test", data, path)
        assert Path(result).exists()
        assert result.endswith(".xlsx")

    def test_generate_empty(self, tmp_path: Path):
        path = str(tmp_path / "empty.xlsx")
        result = ExcelRenderer.generate("test", {"rows": []}, path)
        assert Path(result).exists()


class TestPDFRenderer:
    def test_generate_pdf(self, tmp_path: Path):
        data = {"rows": [{"metric": "ROI", "value": 0.15}]}
        path = str(tmp_path / "test.pdf")
        result = PDFRenderer.generate("or_analysis", data, path)
        assert Path(result).exists()
        assert result.endswith(".pdf")


class TestCSVRenderer:
    def test_generate_csv(self, tmp_path: Path):
        data = {"data": [{"engine": "EOQ", "result": 250}]}
        path = str(tmp_path / "test.csv")
        result = CSVRenderer.generate("test", data, path)
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "engine" in content
        assert "EOQ" in content
