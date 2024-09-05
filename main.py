import requests
from skyfield.api import Topos, load, EarthSatellite
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Paramètres d'entrée
observer_lat = 48.25
observer_lon = -1.66667
observer_alt = 0
altitude_min = 0  # Altitude minimale en degrés pour simuler le relief
observation_time = datetime(2024, 9, 5, 0, 0, 0, tzinfo=timezone.utc)
current_date = observation_time.strftime("%Y_%m_%d")  # Format de la date pour le fichier CSV

# Spécifier l'heure de début et l'heure de fin
start_time = datetime(2024, 9, 5, 0, 0, 1, tzinfo=timezone.utc)  # Par exemple, 6h00
end_time = datetime(2024, 9, 5, 23, 59, 59, tzinfo=timezone.utc)   # Par exemple, 18h00

# Liste des satellites avec leurs IDs NORAD et leurs noms
satellites_info = {
    44876: 'ANGELS',
    38771: 'METOP-B',
    28654: 'NOAA-18',
    39086: 'SARAL',
    54023: 'CS-HOPS',
    43689: 'METOP-C',
    33591: 'NOAA-19',
    25338: 'NOAA-15',
    54361: 'OCEANSAT-3'
}

# Couleurs pour chaque satellite
satellite_colors = {
    44876: 'r',  # Rouge
    38771: 'g',  # Vert
    28654: 'b',  # Bleu
    39086: 'c',  # Cyan
    54023: 'm',  # Magenta
    43689: 'y',  # Jaune
    33591: 'orange',  # Orange
    25338: 'purple',  # Violet
    54361: 'brown'   # Marron
}

# Fonction pour obtenir les TLE depuis Celestrak
def get_tle_from_celestrak(satellite_id):
    url = f'https://celestrak.com/NORAD/elements/gp.php?CATNR={satellite_id}'
    response = requests.get(url)
    if response.status_code == 200:
        tle_data = response.text.splitlines()
        if len(tle_data) >= 3:
            return tle_data[1], tle_data[2]
        else:
            print("Erreur : les TLE sont incomplets.")
    else:
        print(f"Erreur lors de la requête : {response.status_code}")
    return None, None

# Fonction pour obtenir la position du satellite à une date donnée
def get_satellite_position(tle_line1, tle_line2, observation_time, observer_lat, observer_lon, observer_alt):
    ts = load.timescale()
    satellite = EarthSatellite(tle_line1, tle_line2, 'Satellite', ts)
    observer_location = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon, elevation_m=observer_alt)
    observation_time = ts.utc(observation_time)
    difference = satellite - observer_location
    topocentric = difference.at(observation_time)
    alt, az, distance = topocentric.altaz()
    return alt.degrees, az.degrees, distance.km

# Fonction pour enregistrer les données des passages dans un fichier CSV
def save_passages_to_csv(passage_infos, date):
    # Transformer les informations des passages en DataFrame
    df = pd.DataFrame(passage_infos)

    # Nom du fichier avec la date incluse
    filename = f"satellite_passages_{date}.csv"

    # Enregistrer les données dans un fichier CSV
    df.to_csv(filename, index=False)
    print(f"Données enregistrées dans le fichier : {filename}")

# Fonction pour tracer la trajectoire du satellite sur un graphique polaire avec survol
def plot_satellite_trajectories_with_hover(satellite_segments, passage_infos):
    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)
    lines = []
    annotations = []
    labels_added = set()  # Pour suivre les labels déjà ajoutés à la légende

    # Tracer chaque segment de trajectoire pour chaque satellite avec une couleur différente
    for satellite_id, segments in satellite_segments.items():
        color = satellite_colors.get(satellite_id, 'k')  # Utiliser 'k' (noir) par défaut si aucune couleur spécifiée
        satellite_name = satellites_info[satellite_id]

        for i, positions in enumerate(segments):
            if i >= len(passage_infos[satellite_id]):  # Vérifie que l'index ne dépasse pas le nombre de passages
                continue

            azimuts_rad = [np.radians(azimut) for _, azimut in positions]
            elevations = [90 - altitude for altitude, _ in positions]  # Inverser l'altitude pour le graphique

            # Ajouter le label uniquement si ce n'est pas déjà fait pour ce satellite
            if satellite_name not in labels_added:
                line, = ax.plot(azimuts_rad, elevations, c=color, label=satellite_name)
                labels_added.add(satellite_name)
            else:
                line, = ax.plot(azimuts_rad, elevations, c=color)  # Pas de label pour les autres segments

            lines.append(line)

            # Ajouter les informations du passage correspondant
            passage_info = passage_infos[satellite_id][i]
            annotation_text = (
                f"{satellite_name}\n"
                f"Début: {passage_info['Heure début']}\n"
                f"Fin: {passage_info['Heure fin']}"
            )
            annotation = ax.annotate(
                annotation_text, xy=(0, 0), xytext=(10, 10),
                textcoords="offset points", bbox=dict(boxstyle="round", fc="w"),
                arrowprops=dict(arrowstyle="->"), ha='center'
            )
            annotation.set_visible(False)
            annotations.append(annotation)

    ax.set_theta_zero_location('N')  # Le 0° azimut correspond au nord
    ax.set_theta_direction(-1)       # Les angles augmentent dans le sens des aiguilles d'une montre
    ax.set_rmax(90)                  # L'altitude maximale est de 90° (le zénith)

    # Masquer les étiquettes d'élévation (altitude)
    ax.set_yticklabels([])

    plt.title("Trajectoires des Satellites Argos")

    # Positionner la légende en dehors du graphique, à droite
    plt.legend(loc='upper right', bbox_to_anchor=(1.5, 1))

    # Fonction pour détecter le survol de la souris
    def on_hover(event):
        # Vérifier que les coordonnées xdata et ydata sont valides (non None)
        if event.xdata is None or event.ydata is None:
            return  # Ne rien faire si la souris est en dehors de la zone de tracé

        for line, annotation in zip(lines, annotations):
            if line.contains(event)[0]:  # Vérifier si la souris survole une trajectoire
                annotation.xy = (event.xdata, event.ydata)  # Mettre à jour la position de l'annotation
                annotation.set_visible(True)
            else:
                annotation.set_visible(False)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_hover)
    plt.show()

# Fonction pour calculer les positions du satellite dans une plage horaire donnée
def calculate_positions_in_time_range(tle_line1, tle_line2, observer_lat, observer_lon, observer_alt, start_time, end_time, altitude_min):
    positions = []
    segments = []
    passage_info = []  # Liste pour stocker les infos des passages
    visible = False
    ts = load.timescale()

    # Calculer la durée totale en minutes entre l'heure de début et l'heure de fin
    total_minutes = int((end_time - start_time).total_seconds() / 60)

    for minute_offset in range(total_minutes):
        current_time = start_time + timedelta(minutes=minute_offset)
        altitude, azimut, _ = get_satellite_position(tle_line1, tle_line2, current_time, observer_lat, observer_lon, observer_alt)

        # Appliquer le masque d'altitude minimum
        if altitude > altitude_min:  # Satellite visible au-dessus de l'altitude minimale
            if not visible:
                if positions:
                    segments.append(positions)
                positions = []
                visible = True
                start_time_passage = current_time
            positions.append((altitude, azimut))
        else:
            if visible:
                visible = False
                if positions:
                    end_time_passage = current_time
                    mid_index = len(positions) // 2
                    mid_time = start_time_passage + (end_time_passage - start_time_passage) / 2
                    mid_alt, mid_az = positions[mid_index]
                    duration = (end_time_passage - start_time_passage).total_seconds() / 60
                    passage_info.append({
                        'Heure début': start_time_passage.strftime("%H:%M"),
                        'Heure milieu': mid_time.strftime("%H:%M"),
                        'Heure fin': end_time_passage.strftime("%H:%M"),
                        'Durée (min)': duration,
                        'Élévation milieu': mid_alt,
                        'Azimut début': positions[0][1],
                        'Azimut milieu': mid_az,
                        'Azimut fin': positions[-1][1]
                    })
                    segments.append(positions)
    if positions:
        end_time_passage = start_time + timedelta(minutes=total_minutes)
        mid_index = len(positions) // 2
        mid_time = start_time + (end_time_passage - start_time) / 2
        mid_alt, mid_az = positions[mid_index]
        duration = (end_time_passage - start_time).total_seconds() / 60
        passage_info.append({
            'Heure début': start_time.strftime("%H:%M"),
            'Heure milieu': mid_time.strftime("%H:%M"),
            'Heure fin': end_time_passage.strftime("%H:%M"),
            'Durée (min)': duration,
            'Élévation milieu': mid_alt,
            'Azimut début': positions[0][1],
            'Azimut milieu': mid_az,
            'Azimut fin': positions[-1][1]
        })
        segments.append(positions)

    return segments, passage_info

# Calculer et stocker les segments de trajectoire pour chaque satellite dans la plage horaire
satellite_segments = {}
passage_infos = {}

for satellite_id, satellite_name in satellites_info.items():
    tle_line1, tle_line2 = get_tle_from_celestrak(satellite_id)
    if tle_line1 and tle_line2:
        segments, passage_info = calculate_positions_in_time_range(tle_line1, tle_line2, observer_lat, observer_lon, observer_alt, start_time, end_time, altitude_min)
        satellite_segments[satellite_id] = segments
        passage_infos[satellite_id] = passage_info  # Stocker les infos par satellite
        print(f"Segments calculés pour {satellite_name} ({satellite_id}) de {start_time.strftime('%H:%M')} à {end_time.strftime('%H:%M')}: {len(segments)} passages.")
    else:
        print(f"Impossible de récupérer les TLE pour {satellite_name} ({satellite_id}).")

# Enregistrer les données dans un fichier CSV
# Créer une seule liste de tous les passages pour le CSV
all_passages = []
for satellite_id, passages in passage_infos.items():
    all_passages += passages
save_passages_to_csv(all_passages, current_date)

# Afficher les trajectoires des satellites avec les annotations au survol
plot_satellite_trajectories_with_hover(satellite_segments, passage_infos)
