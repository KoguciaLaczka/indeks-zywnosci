# Rejestr cen — metodologia v2.5

## Kolejność wyboru ceny

1. Aktywna i aktualna cena użytkownika.
2. Aktywna i aktualna cena referencyjna.
3. Brak kwalifikacji do rankingu ekonomicznego.

Brak ceny nigdy nie jest zamieniany na zero.

## Ważność

- cena użytkownika: 45 dni,
- cena referencyjna: 90 dni.

## Format ceny użytkownika

Plik `data/prices/user-prices.csv` zawiera jeden wiersz dla każdego
produktu. Cena podawana jest w PLN za kilogram jadalnego produktu
odpowiadającego stanowi opisanemu w rankingu.

Aby aktywować cenę, należy podać:

- `price_pln_per_kg`,
- `observed_at` w formacie `YYYY-MM-DD`,
- `source_label`,
- opcjonalnie `source_url`,
- `active` ustawione na `TAK`.

Cena użytkownika nie jest automatycznie uznawana za cenę rynkową.
Może oznaczać paragon, lokalny sklep albo koszt własnej produkcji,
jeżeli zostanie to jasno opisane w polu `source_label` i `note`.

## Wzory

- koszt 100 g = cena za kg / 10,
- koszt porcji = cena za kg × porcja w gramach / 1000,
- punkty bazowe za 1 zł = wynik bazowy / koszt 100 g,
- punkty porcji za 1 zł = wynik porcji / koszt porcji.

Wersja: `2.5.0-economy-pilot`.
