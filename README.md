
# JAMLO Hotel Analytics — structured app (GM & INV)

Two roles:
- **GM** — edycja: plan roczny, prognozy dzienne, wykonanie; analizy i VAR.
- **INV** — tylko podgląd dashboardów, raportów i kowenantów.

## Uruchomienie lokalne
```bash
pip install -r requirements.txt
streamlit run src/Operacje.py
```

## Dane wejściowe
- **Projekt aplikacji (Excel)** — arkusz `Zakładki` definiuje dostępne strony per rola.
- **Dane operacyjne (Excel)** — opcjonalne: arkusze `insights`, `raw_matrix`/`raw`, `kpi`, oraz `cost*`.

W trybie demo, jeśli nie wgrasz plików, aplikacja użyje danych przykładowych.
