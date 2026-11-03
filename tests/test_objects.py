from pctimelogger import objects

ROOT = r"D:\AAA aktiivsed objektid"


def test_project_folder_by_marker_and_root():
    p = r"D:\AAA aktiivsed objektid\Audentes pikk koridor\joonised\plaan.dwg"
    assert objects.project_folder(p) == "Audentes pikk koridor"
    assert objects.project_folder(p, ROOT) == "Audentes pikk koridor"
    assert objects.project_folder(r"C:\Users\m\Desktop\x.xlsx") is None
    assert objects.project_folder(r"D:\AAA aktiivsed objektid\x.xlsx") is None


def test_split_names_one_and_two_word_objects():
    names = objects.split_names({
        "Audentes pikk koridor", "Audentes naiste duširuum",
        "Tallinna Ülikool saal", "Tallinna Ülikool fuajee", "Tondi 84a",
    })
    assert names["Audentes pikk koridor"] == ("Audentes", "pikk koridor")
    assert names["Audentes naiste duširuum"] == ("Audentes", "naiste duširuum")
    assert names["Tallinna Ülikool saal"] == ("Tallinna Ülikool", "saal")
    assert names["Tondi 84a"] == ("Tondi 84a", "")
