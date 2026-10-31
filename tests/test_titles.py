from pctimelogger import titles


def test_autocad_full_path_in_brackets():
    t = r"Autodesk AutoCAD 2024 - [C:\Objektid\Audentes pikk koridor\plaan.dwg]"
    assert titles.find_path(t) == r"C:\Objektid\Audentes pikk koridor\plaan.dwg"
    assert titles.find_filename(t) == "plaan.dwg"


def test_autocad_name_only():
    assert titles.find_filename("Autodesk AutoCAD 2024  Lõige A-A.dwg") == "Lõige A-A.dwg"
    assert titles.find_path("Autodesk AutoCAD 2024  plaan.dwg") is None


def test_office_titles():
    assert titles.find_filename("Eelarve 2026.xlsx - Excel") == "Eelarve 2026.xlsx"
    assert titles.find_filename("Seletuskiri.docx [Compatibility Mode] - Word") == "Seletuskiri.docx"


def test_unc_path():
    t = r"\\server\objektid\Audentes naiste duširuum\tabel.xlsx - Excel"
    assert titles.find_path(t) == r"\\server\objektid\Audentes naiste duširuum\tabel.xlsx"


def test_no_file():
    assert titles.find_filename("Google Chrome") is None
    assert titles.find_filename("") is None
