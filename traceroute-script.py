#!/bin/python3
# =============================================================
#
#   █████████   █████████
#  ███░░░░░███ ███░░░░░███  Suchith Sridhar
# ░███    ░░░ ░███    ░░░
# ░░█████████ ░░█████████   https://suchicodes.com
#  ░░░░░░░░███ ░░░░░░░░███  https://github.com/suchithsridhar
#  ███    ░███ ███    ░███
# ░░█████████ ░░█████████
#  ░░░░░░░░░   ░░░░░░░░░
#
# =============================================================
# A python script to perform `traceroute` on multiple server
# in the world and generate graphs for One way time and number
# of hops to each of the servers.
#
# Required files:
# - $IPSTACK_API_KEYFILE: A file that contains your API key to ipstack.
# - $SOURCE_LOC_FILE: A file that contains the coords of your source machine.
# - $ARCH_MIRRORS: A file that contains a list of Arch Linux mirrors.
#
# Generates files:
# - $OUTPUT_CSV: A CSV file with all collected data.
# - $OUTPUT_GRAPH_1: An image with the scatter plot time vs distance.
# - $OUTPUT_GRAPH_2: An image with the scatter plot hops vs distance.
#
# Valid call:
# $ python traceroute-script.py 10
# =============================================================

import re
import sys
import math
import random
import requests
import subprocess
import logging as log
import matplotlib.pyplot as plt
from urllib.parse import urlparse

# Required files
ARCH_MIRRORS = 'arch-mirror-list.txt'
SOURCE_LOC_FILE = 'source-location.txt'
IPSTACK_API_KEYFILE = 'ipstack-api-key.txt'

# Generated files
OUTPUT_CSV = "output-table.csv"
OUTPUT_GRAPH_1 = "graph1.png"
OUTPUT_GRAPH_2 = "graph2.png"

# Internal variables (Do not change)
IPSTACK_URL = "http://api.ipstack.com/{}?access_key={}"
HOME_LAT, HOME_LON = 0.0, 0.0
IPSTACK_API_KEY = ""

LOG_LEVEL = log.INFO

log_format = '%(asctime)s - %(levelname)s: %(message)s'
log.basicConfig(format=log_format, level=LOG_LEVEL)


def get_source_coords() -> tuple[float, float]:
    """
    Get the coordinates of the source machine.
    This is expected to be stored in the $SOURCE_LOC_FILE
    as comma separated values with the latitude first and then
    the longitude.

    Returns:
    float, float
    The latitude and longitude of the source machine as floats.
    """

    try:
        lat, lon = map(float, open(SOURCE_LOC_FILE).read().strip().split(","))
        return lat, lon

    except (ValueError, FileNotFoundError) as e:
        print(e)
        log.error(f"Source coords file not found: {SOURCE_LOC_FILE}\n"
                  "Please set your source machine coordinates in file:\n"
                  f"{SOURCE_LOC_FILE}\n"
                  "It should be 2 values that are comma separated. The first\n"
                  "is the latitude and the second the longitude.")
        exit(1)


def get_ipstack_api_key() -> str:
    """
    Get the API key for https://ipstack.com/
    that is expected to be stored in the $IPSTACK_API_KEYFILE.

    Returns:
    API key (str)
    """

    try:
        key = open(IPSTACK_API_KEYFILE).read().strip()
        return key

    except FileNotFoundError:
        log.error(f"Unable to read file {IPSTACK_API_KEYFILE}.\n"
                  "Please register for a key at: https://ipstack.com/\n"
                  "Once registered, save your key in the "
                  "above mentioned filename.")
        exit(1)


def plot_graph_and_save(x_name: str, x_values: list,
                        y_name: str, y_values: list,
                        filename: str):
    """
    Plot a graph based on the provided x and y values and save it to a file.

    Parameters:
    - x_name (str): Name of the x-axis.
    - x_values (list): Values for the x-axis.
    - y_name (str): Name of the y-axis.
    - y_values (list): Values for the y-axis.
    - filename (str): Filename to save the plotted graph.

    Returns:
    None
    """

    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have the same length.")

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, marker='o')
    plt.title(f'{y_name} vs. {x_name}')
    plt.xlabel(x_name)
    plt.ylabel(y_name)
    plt.grid(True)

    # Save the plot to a file
    plt.savefig(filename, format='png')


def dist_from_source(lat, lon) -> float:
    """
    Calculate the distance from my the source machine that's making the
    `traceroute` requests and the destination server. Note that this uses the
    $HOME_LAT and $HOME_LON global variables as the source machine coordinates.

    Parameters:
    - lat: The latitude of the destination server.
    - lon: The longitude of the destination server.

    Returns:
    float
    The distance in km between the source and the destination.
    """

    def getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2):
        """
        Formula used to calculate the distance between 2 coordinates.
        Taken from: https://www.movable-type.co.uk/scripts/latlong.html
        """
        R = 6371  # Radius of the earth in km
        dLat = deg2rad(lat2 - lat1)
        dLon = deg2rad(lon2 - lon1)

        a = (math.sin(dLat/2) * math.sin(dLat/2) +
             math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) *
             math.sin(dLon/2) * math.sin(dLon/2))

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c  # Distance in km

        return d

    def deg2rad(deg):
        return deg * (math.pi/180)

    return getDistanceFromLatLonInKm(lat, lon, HOME_LAT, HOME_LON)


def extract_urls_from_arch_linux_mirrors(filename) -> dict[str, list[str]]:
    """
    Creates a dict from a file containing URLs. This is a function intended
    to be used with an arch linux mirrors file. It expects a certain format
    for the URLs.

    Return
    dict
    The keys are the countries and the values are the list of URLs that each
    country has under it.
    """

    try:
        with open(filename, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        log.error(f"Unable to find file with URLs: {filename}. Exiting.")
        exit(1)

    countries = {}
    current_country = None
    for line in lines:
        if line.startswith("## "):
            current_country = line[3:].strip()
            countries[current_country] = []
        elif line.startswith("#Server = "):
            search = re.search(r"#Server = (.+)$", line)

            if search is None:
                continue

            url = search.group(1)

            if current_country:
                countries[current_country].append(url)

    return countries


def pick_urls(urls: dict, count: int) -> list[str]:
    """
    Function used to pick random URLs from a dict containing many URLS.
    Expected structure: { x: [...], y: [...]}. Will first randomly pick a key
    and then randomly pick an element from the value at that key.

    Parameters:
    - urls (dict): A dict containing URLs in the above mentioned format.
    - count (int): The number of URLs required to be picked.

    Returns:
    list[str]
    An array of picked URLs.
    """

    selection = [
        (random.choice(
            random.choice(list(urls.items()))[1])
         ) for _ in range(count)
    ]
    return selection


def extract_domains(urls: list[str]) -> list[str]:
    """
    Given a list of URLs, get a list of corresponding domain names.

    Parameters:
    - urls: The list of URLs to extract domain names.

    Returns:
    list[str]
    The list of domain names.
    """
    return [urlparse(url).netloc for url in urls]


def get_traceroute_result(domain: str) -> str:
    """
    This runs `traceroute` on the provided domain and returns the
    stdout output of the program.

    Parameter:
    - domain (str): The domain to perform traceroute on.

    Returns:
    str
    A string that contains the strout output of the traceroute.
    """
    result = subprocess.run(
        ['traceroute', domain],
        capture_output=True,
        text=True
    )

    return result.stdout


def parse_traceroute_output(output: str) -> tuple[int, str, float] | None:
    """
    Given a traceroute output, extract the number of hops, one way time and
    the IP address.

    Parameters:
    - output (str): The traceroute stdout to be parsed.

    Return:
    tuple[int, str, float]
    Returns the number of hops, IP address, one-way time if successful.

    None
    Returns None if the parsing fails.
    """

    items = reversed(output.split("\n"))

    for line in items:
        line_item = line.split(" ")
        # example:
        # ['15', '', '89.164.86.92', '(89.164.86.92)',
        # '', '124.342', 'ms', '89.164.87. 158',
        # '(89.164.87.158)', '', '121.881', 'ms',
        # '89.164.86.174', '(89.164.86.17 4)', '',
        # '124.635', 'ms']

        if (len(line_item) <= 12):
            continue

        else:
            try:
                hop_num = int(line_item[0])
            except ValueError:
                log.debug("--- DEBUG INFO START ---")
                log.debug(output)
                log.debug("--- DEBUG INFO END ---")
                # Failure Case
                return None

            ip_addr = line_item[3].strip("(").strip(")")
            index = 5
            hop_times = []
            for _ in range(3):
                try:
                    hop = float(line_item[index])
                    hop_times.append(hop)
                    index += 2
                except ValueError:
                    index += 1

            one_way_time = (sum(hop_times)/len(hop_times))/2

            return hop_num, ip_addr, one_way_time


def is_duplicate(domain, dataset) -> bool:
    """
    Check if domain is a duplicate in the dataset.

    Parameters:
    - domain (str): the domain to look for in dataset.
    - dataset (list): the list of dicts to look through for domain.

    Returns:
    bool
    True if domain present in dataset, False if not.
    """

    for item in dataset:
        if item['domain'] == domain:
            return True

    return False


def traceroute_analysis(urls: dict[str, list[str]], count: int) -> list[dict]:
    """
    Pick $count number of URLs from $urls and perform a `traceroute` analysis
    on those domains.

    Parameters:
    - urls (list[str]): The list of URL to pick from for performing traceroute.
    - count (int): The number of URLs to pick from list of URLs.

    Returns:
    list[dict]
    A list of results stored at dicts.
    """

    domain_count = 0
    final_dataset = []

    while (domain_count < count):

        # Select a URL
        select = pick_urls(urls, 1)

        # Extract the domain
        domain = extract_domains(select)[0]

        # Check if domain selected is a duplicate
        if (is_duplicate(domain, final_dataset)):
            continue

        log.info(f"Running traceroute for domain: {domain}")

        # Get the output of traceroute for said domain
        output = get_traceroute_result(domain)

        log.info("Traceroute complete.")

        # Extract required information from traceoute output
        output = parse_traceroute_output(output)

        # Check to see if traceroute failed
        if (output is None):
            log.error(f"Failed analysis for domain: {domain}")
            continue

        hops, ip_addr, time = output

        # Get details about geolocation of ip address
        result = requests.get(
            IPSTACK_URL.format(ip_addr, IPSTACK_API_KEY)
        ).json()

        if ("success" in result and not result["success"]):
            log.error(f"Failed to get geolocation of IP Address of: {ip_addr}")
            log.error(f"Exiting traceroute analysis for domain: {domain}")
            continue

        lat, lon, city, country = (result['latitude'],
                                   result['longitude'],
                                   result['city'],
                                   result['country_name']
                                   )

        # Get distance from home for geolocation of ip address
        distance = dist_from_source(lat, lon)

        # Append final information to data set
        final_dataset.append({
            "domain": domain,
            "hops": hops,
            "ipa": ip_addr,
            "time": time,
            "lat": lat,
            "lon": lon,
            "city": city,
            "dist": distance,
            "country": country
        })

        log.info(f"Complete analysis for domain: {domain}")

        domain_count += 1

    return final_dataset


def gen_csv(dataset: list[dict], filename: str):
    """
    Given a dataset, generate a CSV that corresponds to it.

    Parameters:
    - dataset (list[dict]): The data to include in the CSV file.
    - filename (str): The file to write the data to.

    Return:
    None
    """

    # This is a mapping for CSV column name to key name in dataset.
    fields = [
        ("Web Server", "domain"),
        ("IP Address", "ipa"),
        ("Number of hops", "hops"),
        ("One-Way transit time (ms)", "time"),
        ("Geo Distance (km)", "dist"),
        ("City", "city"),
        ("Country", "country"),
        ("Latitude", "lat"),
        ("Longitude", "lon"),
    ]

    string = ",".join(["No."] + [field[0] for field in fields]) + '\n'

    for count, item in enumerate(dataset, start=1):
        string += ",".join(
            [str(count)] + [str(item[f[1]]) for f in fields]
        ) + '\n'

    with open(filename, "w") as f:
        f.write(string)


def get_count_for_traceroute() -> int:
    """
    Get the count parameter from command line arguments. Handle any errors.

    Returns:
    int
    The count as specified by the command line argument.
    """

    try:
        count = int(sys.argv[1])
        return count

    except (ValueError, IndexError):
        log.error("Please provide a valid number of URLs to "
                  "perform operation.\n"
                  "A valid call: python3 <script.py> 10")
        exit(1)


def main():
    global IPSTACK_API_KEY
    global HOME_LAT, HOME_LON

    count = get_count_for_traceroute()
    HOME_LAT, HOME_LON = get_source_coords()
    IPSTACK_API_KEY = get_ipstack_api_key()
    urls: dict = extract_urls_from_arch_linux_mirrors(ARCH_MIRRORS)
    dataset = traceroute_analysis(urls, count)

    gen_csv(dataset, OUTPUT_CSV)
    plot_graph_and_save(
        "Geographical distance (km)", [item['dist'] for item in dataset],
        "One-way transit time (ms)", [item['time'] for item in dataset],
        OUTPUT_GRAPH_1
    )
    plot_graph_and_save(
        "Geographical distance (km)", [item['dist'] for item in dataset],
        "Number of hops", [item['hops'] for item in dataset],
        OUTPUT_GRAPH_2
    )


if __name__ == "__main__":
    main()
