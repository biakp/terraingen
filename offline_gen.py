#!/usr/bin/env python3
'''
Generation of all dat files at 100m spacing.
Preprocessing so the website doesn't have to

This will take a long time to process!
'''
import os
#from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
import argparse
import time
import gzip
import shutil

from MAVProxy.modules.mavproxy_map import srtm
from terrain_gen import create_degree

def worker(downloader, lat, long, targetFolder, startedTiles, totTiles):
    # only create if the output file does not exists
    if os.path.exists(datafile(lat, long, targetFolder) + '.gz'):
        print("Skipping existing compressed tile {0} of {1} ({2:.3f}%)".format(startedTiles, totTiles, ((startedTiles)/totTiles)*100))
        return

    if not os.path.exists(datafile(lat, long, targetFolder)):
        create_degree(downloader, lat, long, targetFolder, 100)
        print("Created tile {0} of {1}".format(startedTiles, totTiles))
    else:
        print("Skipping existing tile {0} of {1} ({2:.3f}%)".format(startedTiles, totTiles, ((startedTiles)/totTiles)*100))

    # and compress
    with open(datafile(lat, long, targetFolder), 'rb') as f_in:
        with gzip.open(datafile(lat, long, targetFolder) + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(datafile(lat, long, targetFolder))

    print("Done tile {0} of {1} ({2:.3f}%)".format(startedTiles, totTiles, ((startedTiles)/totTiles)*100))
    print("Folder is {0:.0f}Mb in size".format(get_size(targetFolder)/(1024*1024)))

def datafile(lat, lon, folder):
    if lat < 0:
        NS = 'S'
    else:
        NS = 'N'
    if lon < 0:
        EW = 'W'
    else:
        EW = 'E'
    name = folder + "/%c%02u%c%03u.DAT" % (NS, min(abs(int(lat)), 99),
                                    EW, min(abs(int(lon)), 999))

    return name

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                # other threads may be moving files whilst we're getting folder
                # size here
                try:
                    total_size += os.path.getsize(fp)
                except FileNotFoundError:
                    pass

    return total_size

if __name__ == '__main__':
    global filelistDownloadActive
    # Create the parser
    parser = argparse.ArgumentParser(description='ArduPilot Terrain DAT file generator')

    # Add the arguments
    # Folder to store processed DAT files
    parser.add_argument('-folder', action="store", dest="folder", default="processedTerrain")
    # Number of threads to use
    parser.add_argument('-processes', action="store", dest="processes", type=int, default=4)
    # Latitude range
    parser.add_argument('-latitude', action="store", dest="latitude", type=int, default=60)
    
    args = parser.parse_args()

    downloader = srtm.SRTMDownloader(debug=False, cachedir='srtmcache')
    downloader.loadFileList()

    targetFolder = os.path.join(os.getcwd(), args.folder)
    #create folder if required
    try:
        os.mkdir(targetFolder)
    except FileExistsError:
        pass

    print("Storing in " + targetFolder)

    # store the threads
    processes = []

    # make tileID's
    tileID = []
    i = 0
    for long in range(-180, 180):
        for lat in range (-(args.latitude+1), args.latitude+1):
            tileID.append([lat, long, i]) 
            i += 1

    # total number of tiles
    totTiles = len(tileID)
    startedTiles = 0

    # Use a pool of workers to process
    with ThreadPool(args.processes-1) as p:
        reslist = [p.apply_async(worker, args=(downloader, td[0], td[1], targetFolder, td[2], len(tileID))) for td in tileID]
        for result in reslist:
            result.get()

    print("--------------------------")
    print("All tiles generated!")
    print("--------------------------")

