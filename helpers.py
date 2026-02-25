import gzip
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import os
import time
import gc
import re
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError

# Funkcija, kas izveido RDF četrinieku sarakstu no .gz faila vai failiem
# Jāpadod faila vārds un Schema.org klases vārds, piemēram, School

def parse_gz_files(filenames, schema_org_class_name, keep_all_quads = False):
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
                
                if keep_all_quads:
                    quads.append((s, p, o, g))
                else:
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
# quads_list satur tikai dotās klases četriniekus

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


# Parsēšana un klašu skaitīšana vienā funkcija.
# Apstrāde notiek secīgi, rinda pēc rindas, tāpēc nav nepieciešams saglabāt visu datu kopu atmiņā.
# Šāda kombinēta funkcija tika izveidota, jo ar sākotnējo pieeju ar divām atsevišķām funkcijām
# nebija iespējams apstrādāt Movie datu kopu atmiņas trūkuma dēļ (nevarēja visu datu kopu paturēt atmiņā).

def parse_and_count_classes(filenames, schema_org_class_name, year):
    
    classes_frequency = {} # klašu biežumi
    classes_in_graphs = defaultdict(set) # defaultdict(set) automātiski piekārto atslēgai tukšu kopu (set), ja ievietojamās atslēgas nav vārdnīcā
    RDF_TYPE = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"

    for filename in filenames:
        with gzip.open(filename, "rt", encoding="utf-8") as f:
            for line in f:

                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    s, p, o, g, _ = line.split()
                except ValueError:
                    continue
                
                # Ja tekošais četrinieks ir entītijas klases deklarācija,
                # pievienojam to klasi pie attiecīgā grafa klašu kopas.
                if p == RDF_TYPE:
                    classes_in_graphs[g].add(o)

    # Saskaitām visu klašu biežumus vārdnīcā classes_frequency
    for cls_set in classes_in_graphs.values():
        for cls in cls_set:
            classes_frequency[cls] = classes_frequency.get(cls, 0) + 1

    # Izrēķināt top 10
    top_10 = sorted(classes_frequency.items(), key=lambda x: x[1], reverse=True)[:10]

    for name, number in top_10:
        print(f"{name}: {number}")

    class_names = [cls for cls, cnt in top_10]
    counts = [cnt for cls, cnt in top_10]
    percentages = [round(100 * count / top_10[0][1], 2) for count in counts]

    plt.figure(figsize=(12, 6))
    plt.barh(class_names, counts)
    plt.xlabel("Grafu skaits, kas izmanto klasi")
    plt.title(f"Top 10 klases, kas tiek izmantotas kopā ar klasi {schema_org_class_name} {year}. gada datu kopā")
    plt.gca().invert_yaxis()

    for i, (c, pct) in enumerate(zip(counts, percentages)):
        plt.text(c + top_10[0][1] * 0.01, i, f"{c} ({pct}%)", va="center")

    plt.tight_layout()
    plt.savefig(f"../diagrammas/{schema_org_class_name}_{year}_top_10_classes.png")
    
    classes_in_graphs = None
    classes_frequency = None
    gc.collect()
    # plt.show()
    
    
def parse_and_count_predicates(filenames, schema_org_class_name, year):
    predicate_counter = Counter()
    subj_pred_pairs = set()
    current_subject_has_class = False
    
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
                
                if p == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>":
                    if o == f"<http://schema.org/{schema_org_class_name}>":
                        current_subject_has_class = True
                    else:
                        current_subject_has_class = False
                
                if current_subject_has_class:
                    if (s, p) not in subj_pred_pairs:
                        predicate_counter[p] += 1
                        subj_pred_pairs.add((s ,p))
                        
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
    plt.title(f"Top 10 predikāti klasei {schema_org_class_name} {year}. gada datu kopā")
    plt.gca().invert_yaxis()

    
    for i, (c, pct) in enumerate(zip(counts, percentages)):
        plt.text(c + entity_count * 0.01, i, f"{c} ({pct}%)", va="center")

    plt.tight_layout()
    plt.savefig(f"../diagrammas/{schema_org_class_name}_{year}_top_10_predicates.png")
    
    predicate_counter = None
    subj_pred_pairs = None
    gc.collect()
    # plt.show()
                    
    
    
def download_files(urls, output_dir, filenames=None, delay_seconds=5):
    """
    Download files one by one with a safety delay between downloads.

    :param urls: List of file URLs to download
    :param output_dir: Directory where files will be saved
    :param filenames: Optional list of filenames (same length as urls)
    :param delay_seconds: Delay between downloads in seconds
    """
    os.makedirs(output_dir, exist_ok=True)

    if filenames and len(filenames) != len(urls):
        raise ValueError("filenames list must be the same length as urls")

    for index, url in enumerate(urls):
        filename = (
            filenames[index]
            if filenames
            else os.path.basename(url)
        )
        file_path = os.path.join(output_dir, filename)

        print(f"Downloading {url} → {file_path}")

        try:
            urlretrieve(url, file_path)
            print("✔ Download complete")
        except (HTTPError, URLError) as e:
            print(f"✖ Failed to download {url}: {e}")

        if index < len(urls) - 1:
            print(f"Waiting {delay_seconds} seconds before next download...\n")
            time.sleep(delay_seconds)

def properties_above_threshold(entity_props: dict, threshold: float):
    items = list(entity_props.items())
    total = items[0][1]  # value of the first property (entity count)

    return {
        prop
        for prop, count in items[1:]
        if count / total >= threshold
    }

            
def parse_and_count_well_described_entities(schema_org_class_name, filenames, threshold):
    
    predicate_count = {
        "Answer": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 59240980,
            '<http://schema.org/url>': 7715197,
            '<http://schema.org/upvoteCount>': 7229612,
            '<http://schema.org/author>': 7056452,
            '<http://schema.org/dateCreated>': 5706923,
            '<http://schema.org/text>': 2435975,
            '<http://schema.org/inLanguage>': 1790894,
            '<http://schema.org/comment>': 658525,
            '<http://schema.org/encodingFormat>': 644119,
            '<http://schema.org/position>': 634753,
        },
        "Book": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 10051016,
            '<http://schema.org/image>': 4582533,
            '<http://schema.org/author>': 2581545,
            '<http://schema.org/name>': 2506811,
            '<http://schema.org/isbn>': 2484745,
            '<http://schema.org/offers>': 2450124,
            '<http://schema.org/url>': 2284848,
            '<http://schema.org/bookFormat>': 2051932,
            '<http://schema.org/datePublished>': 1985268,
            '<http://schema.org/publisher>': 1698348,
        },
        "Dataset": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 1480364,
            '<http://schema.org/name>': 636704,
            '<http://schema.org/creator>': 421027,
            '<http://schema.org/url>': 386383,
            '<http://schema.org/license>': 323953,
            '<http://schema.org/distribution>': 248520,
            '<http://schema.org/includedInDataCatalog>': 210987,
            '<http://schema.org/spatialCoverage>': 171630,
            '<http://schema.org/temporalCoverage>': 158497,
            '<http://www.w3.org/1999/xhtml/microdata#item>': 138227,
        },
        "Hospital": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 314241,
            '<http://schema.org/address>': 212298,
            '<http://schema.org/image>': 207164,
            '<http://schema.org/telephone>': 116951,
            '<http://schema.org/url>': 113623,
            '<http://schema.org/name>': 85532,
            '<http://schema.org/location>': 43235,
            '<http://schema.org/priceRange>': 41778,
            '<http://schema.org/geo>': 39818,
            '<http://schema.org/hasMap>': 29945,
        },
        "Movie": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 3733115,
            '<http://schema.org/image>': 3186455,
            '<http://schema.org/url>': 2450073,
            '<http://schema.org/dateCreated>': 1860800,
            '<http://schema.org/director>': 1633797,
            '<http://schema.org/aggregateRating>': 1294902,
            '<http://schema.org/datePublished>': 612552,
            '<http://schema.org/actor>': 566084,
            '<http://schema.org/genre>': 560894,
            '<http://schema.org/name>': 430020,
        },
        "MusicAlbum": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 1936996,
            '<http://schema.org/url>': 1611554,
            '<http://schema.org/image>': 1543534,
            '<http://schema.org/byArtist>': 738904,
            '<http://schema.org/datePublished>': 300327,
            '<http://schema.org/name>': 249876,
            '<http://schema.org/albumProductionType>': 212937,
            '<http://schema.org/offers>': 204729,
            '<http://schema.org/albumReleaseType>': 182902,
            '<http://schema.org/publisher>': 177005,
        },
        "QAPage": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 1986634,
            '<http://schema.org/mainEntity>': 1926441,
            '<http://schema.org/url>': 317462,
            '<http://schema.org/image>': 218626,
            '<http://schema.org/publisher>': 159258,
            '<http://schema.org/datePublished>': 147476,
            '<http://schema.org/dateModified>': 109176,
            '<http://schema.org/interactionStatistic>': 80561,
            '<http://schema.org/author>': 78769,
            '<http://schema.org/dateCreated>': 77160,
        },
        "Recipe": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 2874812,
            '<http://schema.org/image>': 2692018,
            '<http://schema.org/author>': 2136441,
            '<http://schema.org/datePublished>': 1686970,
            '<http://schema.org/totalTime>': 1650804,
            '<http://schema.org/prepTime>': 1597685,
            '<http://schema.org/cookTime>': 1497305,
            '<http://schema.org/recipeInstructions>': 1431101,
            '<http://schema.org/recipeYield>': 1398641,
            '<http://schema.org/aggregateRating>': 1229242,
        },
        "School": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 270931,
            '<http://schema.org/url>': 149566,
            '<http://schema.org/address>': 119650,
            '<http://schema.org/logo>': 81333,
            '<http://schema.org/contactPoint>': 67313,
            '<http://schema.org/location>': 52611,
            '<http://schema.org/image>': 44006,
            '<http://schema.org/telephone>': 37546,
            '<http://schema.org/sameAs>': 31648,
            '<http://schema.org/geo>': 22362,
        },
        "ShoppingCenter": {
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>': 111608,
            '<http://schema.org/address>': 99934,
            '<http://schema.org/url>': 97323,
            '<http://schema.org/image>': 92893,
            '<http://schema.org/name>': 61935,
            '<http://schema.org/geo>': 20049,
            '<http://schema.org/telephone>': 19027,
            '<http://schema.org/openingHoursSpecification>': 18504,
            '<http://schema.org/aggregateRating>': 13863,
            '<http://schema.org/sameAs>': 11546,
        }
    }
    
    current_subject_predicates = set()
    commonly_used_predicates = properties_above_threshold(predicate_count[schema_org_class_name], threshold)
    well_described_entity_count = 0
    current_subject_has_class = False
    
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
                
                if p == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>":
                    if o == f"<http://schema.org/{schema_org_class_name}>":
                        current_subject_has_class = True
                    else:
                        current_subject_has_class = False
                        
                    # Check if the previous subject has all the needed properties
                    if current_subject_predicates == commonly_used_predicates:
                        well_described_entity_count += 1
                    
                    current_subject_predicates = set()
                        
                if current_subject_has_class:
                    if (p in commonly_used_predicates) and (p not in current_subject_predicates):
                        current_subject_predicates.add(p) 
    
    total_entity_count = predicate_count[schema_org_class_name]['<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>']
    
    print(schema_org_class_name)
    print(f"Well-described entity count: {well_described_entity_count} out of {total_entity_count}, {round(well_described_entity_count / total_entity_count * 100, 2)}%")
    
    
def parse_and_count_predicates_all_classes(filenames, schema_org_class_name, year):
    classes_with_predicates = {}
    current_class = ""
    subj_pred_pairs = set()
    
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
                
                if p == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>":
                    # print(o)
                    class_name = re.search(r'/([^/>]+)>$', o)
                    current_class = class_name.group(1) if class_name else None
                    
                    if current_class not in classes_with_predicates:
                        classes_with_predicates[current_class] = Counter()
                
                if (s, p) not in subj_pred_pairs:
                    classes_with_predicates[current_class][p] += 1
                    subj_pred_pairs.add((s ,p))
                    
    
    for cls, predicate_counter in classes_with_predicates.items():         
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
        plt.title(f"Top 10 predikāti klasei {cls} datu kopā {schema_org_class_name} ({year})")
        plt.gca().invert_yaxis()

        
        for i, (c, pct) in enumerate(zip(counts, percentages)):
            plt.text(c + entity_count * 0.01, i, f"{c} ({pct}%)", va="center")

        plt.tight_layout()
        plt.savefig(f"../diagrammas/{schema_org_class_name}/{cls}_{year}_top_10_predicates.png")
        # plt.show()
        
    predicate_counter = None
    subj_pred_pairs = None
    gc.collect()
                    
