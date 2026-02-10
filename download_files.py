from helpers import download_files
import os

# Lejupielādēt datu kopas Answer, Book, QAPage, MusicAlbum, Recipe (2024. gada versijas)

urls = {}
filenames = {}
classes = ['Answer', 'Book', 'QAPage', 'MusicAlbum', 'Recipe']
file_count = {'Answer': 118, 'Book': 19, 'QAPage': 12, 'MusicAlbum': 5, 'Recipe': 21}

for cls in classes:
    urls[cls] = []
    filenames[cls] = []

for key, value in urls.items():
    urls[key] = [f"https://data.dws.informatik.uni-mannheim.de/structureddata/2024-12/quads/classspecific/{key}/part_{x}.gz" for x in range(file_count[key])]
    
for key, value in filenames.items():
    filenames[key] = [f"{key}_part_{x}.gz" for x in range(file_count[key])]
    
base_dir = r"E:\schema_org_datasets"

for cls in classes:
    download_files(urls[cls], os.path.join(base_dir, cls), filenames[cls], 1)