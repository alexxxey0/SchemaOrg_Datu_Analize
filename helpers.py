import gzip
from collections import Counter
import matplotlib.pyplot as plt

# Funkcija, kas izveido RDF četrinieku sarakstu no .gz faila vai failiem
# Jāpadod faila vārds un Schema.org klases vārds, piemēram, School

def parse_gz_files(filenames, schema_org_class_name):
    current_subject_has_class = False
    quads = []
    
    for filename in filenames:
        with gzip.open(filename, 'rt', encoding='utf-8') as f:
            for line in f:

                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    s, p, o, g, _ = line.split()
                except ValueError:
                    continue

                # Datu kopā RDF četriniekiem ir šāda struktūra:
                # Sākumā nāk četrinieks, kas norāda aprakstamās entītijas tipu
                # Tam seko pārējie četrinieki, kas apraksta entītijas īpašības
                # Tātad, datu apstrāde notiek blokos: sākumā nolasām tipu, tad nolasām īpašības

                # Datu kopa satur ne tikai entītijas ar tipu X, bet arī citas
                # Mēs gribam analizēt tikai entītijas ar tipu X
                # Lai noskaidrotu tipu, mēs nolasām predikātu, kas apzīmē tipu, un pārbaudām, vai tā vērtība atbilst schema.org tipam X
                # Ja tips nav X, tad datu bloks tiek ignorēts

                if p == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>":
                    if o == f"<http://schema.org/{schema_org_class_name}>":
                        current_subject_has_class = True
                    else:
                        current_subject_has_class = False

                if current_subject_has_class:
                    quads.append((s, p, o, g))
    
    return quads

# quads_list ir jābūt formātā:
# {'2020': quads2020, '2024': quads2024}

def top_10_predicates(quads_list, class_name):
    
    for year, quads in quads_list.items():
        # Top 10 predikāti (predicates) entītijām ar tipu X
        
        predicate_counter = Counter()
        subj_pred_pairs = set()

        for s, p, o, graph in quads:
            # Tā kā vienai entītijai var būt vairākas īpašības ar vienādu nosaukumu,
            # ir jānodrošina, ka katrai entītijai katra īpašības tiek pieskatīta skaitītājam tieši vienu reizi
            if (s, p) not in subj_pred_pairs:
                predicate_counter[p] += 1
                subj_pred_pairs.add((s, p))

        top_predicates = predicate_counter.most_common(10)

        print(f"\nTop 10 predikāti {year}:")

        # Īpašība; entītiju skaits, kas izmanto; procents no kopējā entītiju skaita
        # Tā kā katra entītija sākas ar tipa predikātu, tipa predikātu skaitu var uzskatīt par entītiju skaitu
        entity_count = predicate_counter["<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"]
        for p, count in top_predicates:
            print(p, count, str(round(100 * (count / entity_count), 2)) + "%")
            
        predicates = [p for p, c in top_predicates]
        counts = [c for p, c in top_predicates]
        percentages = [round(100 * c / (predicate_counter["<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"]), 2) for c in counts]

        plt.figure(figsize=(12, 6))
        plt.barh(predicates, counts)
        plt.xlabel("Entītiju skaits")
        plt.title(f"Top 10 predikāti klasei {class_name} {year}. gada datu kopā")
        plt.gca().invert_yaxis()

        
        for i, (c, pct) in enumerate(zip(counts, percentages)):
            plt.text(c + entity_count * 0.01, i, f"{c} ({pct}%)", va="center")

        plt.tight_layout()
        plt.savefig(f"../diagrammas/{class_name}_{year}_top_10_predicates.png")
        plt.show()
    
