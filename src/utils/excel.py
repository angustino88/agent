"""Excel workbook utilities powered by openpyxl."""
from __future__ import annotations

import openpyxl
from openpyxl.utils.cell import (
    column_index_from_string,
    coordinate_from_string,
    get_column_letter,
)


class ExcelUtil:
    """Read / write / format Excel workbooks."""

    def __init__(self, excel_path: str, data_only: bool = True):
        self._workbook = openpyxl.load_workbook(excel_path, data_only=data_only)
        self._worksheet: openpyxl.worksheet.worksheet.Worksheet | None = None

    @classmethod
    def create(cls, excel_path: str) -> ExcelUtil:
        """Create a new empty workbook and return an :class:`ExcelUtil` instance."""
        wb = openpyxl.Workbook()
        wb.save(excel_path)
        return cls(excel_path, data_only=False)

    def select_sheet(self, sheet_name: str):
        """Select a worksheet by name."""
        self._worksheet = self._workbook[sheet_name]

    def save_as(self, excel_path: str):
        """Save the workbook to the specified path."""
        self._workbook.save(excel_path)

    def sheet_names(self) -> list[str]:
        """Return all sheet names in the workbook."""
        return self._workbook.sheetnames

    def max_row(self) -> int:
        """Return the maximum row number of the current worksheet."""
        return self._worksheet.max_row

    def max_column(self) -> int:
        """Return the maximum column number of the current worksheet."""
        return self._worksheet.max_column

    @staticmethod
    def split_cell(cell: str) -> tuple[str, int]:
        """Split a cell name into column letter and row number."""
        return coordinate_from_string(str(cell))

    def cell_to_indices(self, cell: str) -> tuple[int, int]:
        """Convert a cell name to (column_index, row_index)."""
        col_letter, row_num = self.split_cell(cell)
        col_num = column_index_from_string(col_letter)
        return col_num, int(row_num)

    def get_cell(self, cell: str = None, row: int = None, column: int = None) -> str | None:
        """
        Get a cell value by cell name or by row and column number.
        Returns None if the cell is empty.
        """
        if cell is not None:
            value = self._worksheet[cell].value
        elif row is not None and column is not None:
            value = self._worksheet.cell(row=row, column=column).value
        else:
            raise ValueError("Provide either cell or both row and column.")
        return str(value).strip() if value is not None and str(value).strip() else None

    def get_range(self, start_cell: str = None, end_cell: str = None,
                    start_row: int = None, start_col: int = None,
                    end_row: int = None, end_col: int = None) -> list[list[str | None]]:
        """
        Get a range of cells by cell names or by row/col indices.
        Returns a 2D list of cell values.
        """
        if start_cell and end_cell:
            start_col, start_row = self.cell_to_indices(start_cell)
            end_col, end_row = self.cell_to_indices(end_cell)
        elif None not in (start_row, start_col, end_row, end_col):
            pass
        else:
            raise ValueError("Provide either start_cell and end_cell or all row/col indices.")

        result = []
        for row in range(start_row, end_row + 1):
            row_vals = []
            for col in range(start_col, end_col + 1):
                row_vals.append(self.get_cell(row=row, column=col))
            result.append(row_vals)
        return result

    def set_cell(self, value, cell: str = None, row: int = None, column: int = None):
        """
        Set a value to a cell by cell name or by row and column number.
        """
        if cell is not None:
            self._worksheet[cell].value = value
        elif row is not None and column is not None:
            self._worksheet.cell(row=row, column=column).value = value
        else:
            raise ValueError("Provide either cell or both row and column.")

    def set_range(self, values: list[list], start_cell: str = None,
                    start_row: int = None, start_col: int = None):
        """
        Set a 2D list of values to a range starting at start_cell or (start_row, start_col).
        """
        if start_cell:
            start_col, start_row = self.cell_to_indices(start_cell)
        if start_row is None or start_col is None:
            raise ValueError("Provide start_cell or both start_row and start_col.")

        for i, row_vals in enumerate(values):
            for j, val in enumerate(row_vals):
                self.set_cell(val, row=start_row + i, column=start_col + j)

    def insert_column(self, column: int | str):
        """Insert a column by index or letter."""
        col_num = column_index_from_string(column) if isinstance(column, str) else int(column)
        self._worksheet.insert_cols(col_num)

    def insert_row(self, row: int):
        """Insert a row at the given index."""
        self._worksheet.insert_rows(int(row))

    def set_row_height(self, row: int, height: int):
        """Set the height of a specific row."""
        self._worksheet.row_dimensions[int(row)].height = int(height)

    def set_row_heights(self, height: int, start_row: int, end_row: int):
        """Set the height for a range of rows."""
        for row in range(start_row, end_row + 1):
            self.set_row_height(row, height)

    def set_column_width(self, column: str, width: int):
        """Set the width of a specific column."""
        self._worksheet.column_dimensions[str(column)].width = int(width)

    def set_column_widths(self, width: int, start_col: str = None, end_col: str = None,
                            start_col_num: int = None, end_col_num: int = None):
        """
        Set the width for a range of columns, by letter or by index.
        """
        if start_col and end_col:
            start_col_num = column_index_from_string(start_col)
            end_col_num = column_index_from_string(end_col)
        if start_col_num is None or end_col_num is None:
            raise ValueError("Provide start_col and end_col or start_col_num and end_col_num.")

        for col_num in range(start_col_num, end_col_num + 1):
            col_letter = get_column_letter(col_num)
            self.set_column_width(col_letter, width)

    def merge_cells(self, start_cell: str = None, end_cell: str = None,
                    start_row: int = None, start_col: int = None,
                    end_row: int = None, end_col: int = None):
        """
        Merge a range of cells by cell names or by row/col indices.
        """
        if start_cell and end_cell:
            self._worksheet.merge_cells(f"{start_cell}:{end_cell}")
        elif None not in (start_row, start_col, end_row, end_col):
            self._worksheet.merge_cells(
                start_row=start_row, start_column=start_col,
                end_row=end_row, end_column=end_col
            )
        else:
            raise ValueError("Provide start_cell and end_cell or all row/col indices.")

    def format_cells(self, formats: dict, start_cell: str = None, end_cell: str = None,
                        start_row: int = None, start_col: int = None,
                        end_row: int = None, end_col: int = None):
        """
        Apply formatting to a range of cells.
        :param formats: Dict of format attributes (e.g., font, fill, alignment).
        """
        if start_cell and end_cell:
            start_col, start_row = self.cell_to_indices(start_cell)
            end_col, end_row = self.cell_to_indices(end_cell)
        elif None in (start_row, start_col, end_row, end_col):
            raise ValueError("Provide start_cell and end_cell or all row/col indices.")

        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = self._worksheet.cell(row=row, column=col)
                for key, value in formats.items():
                    setattr(cell, key, value)
