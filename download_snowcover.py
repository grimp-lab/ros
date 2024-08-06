import os
import requests
from bs4 import BeautifulSoup

folder_project = 'D:/JALANGLOIS/'
start_year = 2004
end_year = 2015
years = range(start_year, end_year+1)

for year in years:

    # URL de base
    base_url = "https://noaadata.apps.nsidc.org/NOAA/G02156/netcdf/4km/%s/"%(str(year))


    # Créer un dossier pour les fichiers téléchargés
    output_dir = os.path.join(folder_project, "SNOW_COVER", 'NOAA-IMS-4km', str(year))
    print(output_dir)
    os.makedirs(output_dir, exist_ok=True)



    # Obtenir la liste des fichiers à télécharger
    response = requests.get(base_url, verify=False)
    soup = BeautifulSoup(response.content, "html.parser")

    # Télécharger chaque fichier trouvé
    for link in soup.find_all("a"):
        file_name = link.get("href")
        if file_name and file_name != "../" and not file_name.startswith("index.html"):
            #print(file_name)
            file_url = base_url + file_name
            file_path = os.path.join(output_dir, file_name)
            #print(file_path)
            
            with requests.get(file_url, stream=True, verify=False) as r:
                r.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print(f"Téléchargé: {file_name}")
    print(" tous les fichiers de l'année %s ont été téléchargés."%(str(year)))


print("Tous les fichiers ont été téléchargés.")