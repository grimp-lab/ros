import os
import requests
from bs4 import BeautifulSoup

folder_project = 'E:/'
resolution = '24km'
product_name = 'NOAA-IMS-%s'%(resolution)
start_year = 1997
end_year = 2003
years = range(start_year, end_year+1)
base_url = "https://noaadata.apps.nsidc.org/NOAA/G02156/"

for year in years:

    # URL de base
    if resolution == '4km':
        url = base_url + "/netcdf/%s/%s/"%(resolution, str(year))
    elif resolution == '24km':
        url = base_url + "/%s/%s/"%(resolution, str(year))


    # Créer un dossier pour les fichiers téléchargés
    output_dir = os.path.join(folder_project, "SNOW_COVER", product_name, str(year))
    print(output_dir)
    #create the directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)



    # Obtenir la liste des fichiers à télécharger
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.content, "html.parser")

    # Télécharger chaque fichier trouvé
    for link in soup.find_all("a"):
        file_name = link.get("href")
        if file_name and file_name != "../" and not file_name.startswith("index.html"):
            #print(file_name)
            file_url = url + file_name
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