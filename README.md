# Benchmark-massiveGCP
https://massive-gcp-473713.ew.r.appspot.com/

## Description
Benchmark de l'application Massive GCP : génération de fichiers CSV et visualisation des performances.

## Arborescence importante
- `/old` — CSV produits par les anciens scripts séquentiels (ab).
- `/out` — CSV produits par les scripts multithread actuels.

## Génération des CSV
- `old` : résultats des scripts séquentiel. 
- `out` : résultats des scripts multithread.

## Changements apportés aux scripts
- Remplacement d’Apache Bench (ab) par la bibliothèque Python `requests` avec exécution multithread pour :
    - `bench_fanout`
    - `bench_post`
- Raison : `ab` produisait fréquemment des erreurs de type "run failed" en cas de forte concurrence.

## Visualisation / Plots
- Les CSV dans `/out` sont ceux générés par les versions les plus récentes des scripts.
- `boxplot.py` permet de sélectionner depuis le terminal le dossier à analyser et d’afficher des boxplots à partir des CSV pour comparer les performances entre scénarios.
- Conseil : utiliser `/out` pour les plots avec les scripts fonctionnel `/old` pour afficher ce que j'ai obtenu avec la mauvaise méthode.