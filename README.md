# [PL] Automat do wypełniania procedur w SMK 
bazujący na https://github.com/fegnomash/SMK-rozkurwiator

## Instalacja
potrzebujesz dostępu do konsoli, `python3` i `pip`

Sprawdź czy masz zainstalowane używając:
```bash
$ python --version
Python 3.6.0

$ pip --version
pip 21.0.1
```
Aby zainstalować:

`pip install -r requirements.txt`

## Sposób użycia
1. Stwórz folder `/arkusze` i umieść w nim pliki .xls / .xlsx (Excel) z danymi (patrz na plik `raport.example.xlsx` jako wzór)
2. Zmień nazwę `config.example.json` na `config.json` i wypełnij własnymi danymi. Tam gdzie w nazwie jest `wartosc_na_liscie` podaj która z kolei wartość z rozwijanego "drop-downu" Cię interesuje, licząc od 0.
3. Uruchom `python main.py` i postępuj zgodnie z instrukcjami w konsoli
