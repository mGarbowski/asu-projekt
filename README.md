# Projekt ASU
Administrowanie Systemem Unix i sieciami TCP/IP (2025L) - projekt

Mikołaj Garbowski

## Opis projektu
Projekt polega na przygotowaniu skryptu porządkującego pliki w katalogach.
Treść zadania znajduje się w pliku [zadanie.pdf](./docs/zadanie.pdf)

## Uruchomienie

Skrypt wymaga pliku konfiguracyjnego, domyślnie pod ścieżką `./clean_files.ini`.
Opcjonalnie, ścieżkę do pliku można podać przez parametr `--config` linii poleceń.
Przykładowy plik znajduje się w repozytorium [clean_files.ini](./clean_files.ini).

Przy domyślnej konfiguracji skrypt działa w trybie nieinteraktywnym.

Do uruchamiania wymagany jest Python w wersji co najmniej 3.8.
Skrypt nie wymaga instalacji zewnętrznych bibliotek.

```shell
python3 main.py main_dir other_dir_1 other_dir_2
```

Repozytorium zawiera przykładowe drzewo katalogów na potrzeby testowania.
Kopia znajduje się w katalogu `sandbox-bak`. Skrypt [`restore.sh`](./restore.sh) tworzy jego kopię w katalogu sandbox.

Wtedy bez utraty plików (skrypt kasuje pliki) można przetestować działanie przez

```shell
./restore.sh
python3 main.py sandbox/a sandbox/b sandbox/c
```
