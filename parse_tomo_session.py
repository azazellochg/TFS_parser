#!/usr/bin/python3

import os
from pathlib import Path
import re
import csv
import math
import argparse
import xml.etree.ElementTree as ET
import mdocfile as md
import pandas as pd
import numpy as np

DEBUG = False
ns = {'app': 'Applications.Tomography.Version.2'}


def parse_files(list_file: Path):
    rows = []

    # Read session file paths
    session_files = [
        Path(line.strip())
        for line in list_file.read_text().splitlines()
        if line.strip()
    ]

    # Output file
    output_file = list_file.with_suffix(".csv")
    if output_file.exists():
        output_file.unlink()

    for session_path in session_files:
        if session_path.name != "Session.dm":
            continue

        session_dir = session_path.parent

        # Find first matching TS mdoc
        ts_path = next(session_dir.glob("*.mdoc"), None)

        if DEBUG:
            print(f"Parsing session XML: {session_path}")

        output_dict = parseSessionXml(session_path)

        if ts_path:
            if DEBUG:
                print(f"Parsing tilt series MDOC: {ts_path}")

            ts_dict = parseTSMdoc(ts_path, output_dict)
            output_dict.update(ts_dict)

        rows.append(output_dict)

    if not rows:
        print("No data found")
        return

    fieldnames = sorted({key for row in rows for key in row})

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=> Output saved to {output_file}")


def parseSessionXml(session_fn: Path):
    root = ET.parse(session_fn).getroot()
    session_info = {
        "SpecimenType": root.findtext("app:SpecimenType", namespaces=ns),
        "Lamella": root.findtext("app:LamellaWorkflow", namespaces=ns) == "true",
        "DoseFractionsOutputFormat": root.findtext("app:DoseFractionsFormat", namespaces=ns),
        "Name": root.findtext("app:Name", namespaces=ns),
    }

    if DEBUG:
        for k, v in sorted(session_info.items()):
            print(f"{k} = {v}")

    return session_info


def parseTSMdoc(ts_fn: Path, acqDict):
    df = md.read(ts_fn)
    first_row = df.iloc[0]

    keys = [
        "Binning",
        "SpotSize",
        "Voltage",
        "NumSubFrames",
        "PixelSpacing",
        "RotationAngle",
        "Magnification",
        "TargetDefocus",
        "ExposureTime"
    ]

    for key in keys:
        acqDict[key] = first_row[key]

    acqDict["Magnification"] = int(acqDict["Magnification"])
    acqDict["Binning"] = int(acqDict["Binning"])
    acqDict["Voltage"] = int(acqDict["Voltage"])
    acqDict["SpotSize"] = int(acqDict["SpotSize"])

    # movies are never binned
    acqDict["PixelSpacing"] = float(acqDict['PixelSpacing']) / acqDict['Binning']

    acqDict["EnergySelectionSlitWidth"] = int(first_row["FilterSlitAndLoss"][0])
    acqDict["DosePerFrame"] = first_row["FrameDosesAndNumber"][0][0]
    acqDict["DosePerTilt"] = first_row["ExposureDose"] if "ExposureDose" in first_row.index else 0.0
    acqDict["DoseTotal"] = acqDict["DosePerTilt"] * len(df)

    ext = Path(first_row["SubFramePath"]).suffix
    if ext.lower() in [".tiff", ".tif"]:
        acqDict["DoseFractionsOutputFormat"] = "Tiff Lzw Non-Gain normalized"
    elif ext.lower() == ".eer":
        acqDict["DoseFractionsOutputFormat"] = "EER"

    dt = pd.to_datetime(df["DateTime"], format="%d-%b-%Y %H:%M:%S")
    acqDict["StartDateTime"] = dt.min()
    row = df.loc[dt.idxmin()]
    acqDict["TiltAngleStart"] = row["TiltAngle"]

    vals = df["TiltAngle"].dropna().sort_values().to_numpy()
    diffs = np.diff(vals)
    acqDict["TiltAngleStep"] = np.median(diffs) if len(diffs) else None
    acqDict["TiltAngleMin"] = round(vals[0], 2)
    acqDict["TiltAngleMax"] = round(vals[-1], 2)
    df.loc[df["DateTime"].idxmin(), "TiltAngle"]

    desc = first_row["titles"]
    acqDict["TiltAxisAngle"] = None

    for line in desc:
        m = re.search(r"TiltAxisAngle\s*=\s*([-0-9.]+)", line)
        if m:
            acqDict["TiltAxisAngle"] = float(m.group(1))

        m = re.search(r"Tomography_([\d.]+):\s+(\S+)", line)
        if m:
            acqDict["TomographyVersion"] = m.group(1)
            acqDict["MicroscopeID"] = m.group(2)

    calcDose(acqDict)

    if DEBUG:
        for k, v in sorted(acqDict.items()):
            print(f"{k} = {v}")

    return acqDict


def calcDose(acqDict):
    """ Calculate dose rate per unbinned px per s. """
    dose_total = float(acqDict['DosePerTilt'])  # e/A^2
    exp = float(acqDict['ExposureTime'])  # s
    pix = acqDict['PixelSpacing'] # binning is already accounted for

    dose_on_camera = dose_total * math.pow(pix, 2) / exp  # e/unbinned_px/s
    acqDict['DoseOnCamera'] = round(dose_on_camera, 2)


def main():
    parser = argparse.ArgumentParser(
        prog="parse_tomo_session.py",
        description=f"TFS Tomo parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(dest="filename", help="File containing a list of Session.dm files")
    args = parser.parse_args()
    parse_files(Path(args.filename))

if __name__ == "__main__":
    main()
