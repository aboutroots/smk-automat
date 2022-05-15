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
   1. Potrzebne kolumny: `"Nazwisko pacjenta"`, `"Imię pacjenta"`, `"Usługa"`, `"Data"`. Jeśli dodatkowo w arkuszu jest kolumna `"Lekarz opisujący"`, oznacza to że twoje imię i nazwisko zostanie wpisane jako "Asysta", nazwisko lekarza opisującego jako "Operator", kod operacji "B - Asysta". W przeciwnym wypadku twoje imię i nazwisko -> "Operator", kod "A - Operator" a pole asysta zostanie puste.
2. Zmień nazwę `config.example.json` na `config.json` i wypełnij własnymi danymi. Tam gdzie w nazwie jest `pozycja_na_liscie` podaj która z kolei wartość z rozwijanego "drop-downu" Cię interesuje, licząc od 0.
3. Uruchom `python main.py` i postępuj zgodnie z instrukcjami w konsoli:

| komunikat |  opis | 
|---|---|
   | `With assist? Write 1 or 0 and press [Enter]:` | Jeśli masz w pliku kolumnę `"Lekarz opisujący"` i chcesz zostać wpisany/a jako asysta a nie operator, wpisz 1 | 
| `Make sure the proper procedure table is open!`| Rozwiń wybraną kategorię i tabelę, tak żebyś widział/a przycisk "Dodaj" |
| `Paste "Dodaj" button XPATH and click [Enter]`| Otwórz narzędzia developerskie, znajdż przycisk w kodzie HTML i skopiuj jego XPATH (prawy przycisk -> `Copy...` -> `Copy XPATH`). Wklej xpath w terminal i Enter |
| `Press [Enter] to continue. You may need to switch to next page in the table first` |  Po wpisaniu każdych kolejnych 100 wierszy manualnie przełącz stronę i kliknij enter w konsoli żeby kontynuować|
