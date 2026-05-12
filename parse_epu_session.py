#!/usr/bin/python3

import os
from pathlib import Path
import csv
import math
import argparse
import xml.etree.ElementTree as ET

DEBUG = False
UNKNOWN = "UNKNOWN"
nspace = {
    'so': '{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}',
    'ar': '{http://schemas.microsoft.com/2003/10/Serialization/Arrays}',
    'fr': '{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Omp.Interface}',
    'tp': '{http://schemas.datacontract.org/2004/07/Fei.Types}',
    'dr': '{http://schemas.datacontract.org/2004/07/System.Drawing}',
    'app': '{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}',
    'gen': '{http://schemas.datacontract.org/2004/07/System.Collections.Generic}',
    'coser': '{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Services}',
    'ser': '{http://schemas.microsoft.com/2003/10/Serialization/}',
    'co': '{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}',
}


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
        if session_path.name != "EpuSession.dm":
            continue

        session_dir = session_path.parent

        # Find first matching movie XML
        movie_files = session_dir.glob("Images-Disc*/GridSquare*/Data/FoilHole_*_Data_*.xml")
        movie_path = next(movie_files, None)

        if DEBUG:
            print(f"Parsing session XML: {session_path}")

        output_dict = parseSessionXml(session_path)

        if movie_path:
            if DEBUG:
                print(f"Parsing movie XML: {movie_path}")

            movie_dict = parseMovieXml(movie_path, output_dict)
            output_dict.update(movie_dict)

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
    output_dict = dict()

    # Defocus list & number of exposures
    numExpPath = "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}DataAcquisitionAreas/{ar}m_serializationArray"
    defocusPath = numExpPath + "/*[1]/{gen}value/{app}ImageAcquisitionSettingXml/{app}Defocus/{ar}_items"
    defocus = root.find(defocusPath.format(**nspace))

    if defocus is None:
        defocusPath = (numExpPath + "/*[1]/{gen}value/{app}ImageAcquisitionSettingXml/{app}Defocus")
        defocus = root.find(defocusPath.format(**nspace))

    if defocus is not None:
        defocusList = [round(float(str(i.text)) * 1e6, 2) for i in defocus]
        output_dict["Defocus list"] = sorted(defocusList)

    numExp = root.find(numExpPath.format(**nspace))

    if numExp is not None:
        output_dict["Number of exposures"] = numExp.attrib.get('{ser}Size'.format(**nspace), UNKNOWN)
    else:
        output_dict["Number of exposures"] = UNKNOWN

    # Simple (direct-root) items
    root_items = {
        'AfisMode': "./{app}AfisMode",
        'AutoZeroLossEnabled': "./{app}AutoZeroLossEnabled",
        'AutoZeroLossPeriodicity': "./{app}AutoZeroLossPeriodicity",
        'AutoloaderSlot': "./{app}AutoloaderSlot",
        'ClusteringMode': "./{app}ClusteringMode",
        'ClusteringRadius': "./{app}ClusteringRadius",
        'DoseFractionsOutputFormat': "./{app}DoseFractionsOutputFormat",
        'Name': "./{app}Name",
        'PhasePlateEnabled': "./{app}PhasePlateEnabled",
        'HoleSize': "./{app}Samples/{app}_items/{app}SampleXml/{app}FilterHolesSettings/{app}HoleSize",
        'HoleSpacing': "./{app}Samples/{app}_items/{app}SampleXml/{app}FilterHolesSettings/{app}HoleSpacing",
        'GridType': "./{app}Samples/{app}_items/{app}SampleXml/{app}GridType",
        'GridGeometry': "./{app}Samples/{app}_items/{app}SampleXml/{app}GridGeometry",
        'TiltAngle': "./{app}TiltAngle",
        'TiltedAcquisitionEnabled': "./{app}TiltedAcquisitionEnabled",
        'StartDateTime': "./{app}StartDateTime",
        'Autofocus recurrence': "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}AutoFocusArea/{app}Recurrence",
        'Autofocus distance': "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}AutoFocusArea/{app}RecurrenceDistance",
        'Drift recurrence': "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}DriftStabilizationArea/{app}Recurrence",
        'Drift threshold': "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}DriftStabilizationArea/{app}Threshold",
        'DelayAfterImageShift': "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}DelayAfterImageShift",
        'DelayAfterStageShift': "./{app}Samples/{app}_items/{app}SampleXml/{app}TargetAreaTemplate/{app}DelayAfterStageShift",
    }

    for key, path in root_items.items():
        try:
            node = root.find(path.format(**nspace))
            output_dict[key] = node.text if node is not None else UNKNOWN
        except Exception:
            output_dict[key] = UNKNOWN

    # Acquisition‑specific items (relative to acquisition_value)
    acquisition_items = {
        'Detector': "{coser}Acquisition/{so}camera/{so}Name",
        'Binning': "{coser}Acquisition/{so}camera/{so}Binning/{dr}x",
        'ProbeMode': "{coser}Optics/{so}ProbeMode",
        'SpotSize': "{coser}Optics/{so}SpotIndex",
        'BeamSize': "{coser}Optics/{so}BeamDiameter",
        'EnergySelectionSlitWidth': "{coser}Optics/{so}EnergyFilter/{so}EnergySelectionSlitWidth",
        'C2Aperture': "{coser}Optics/{so}Apertures/{so}C2Aperture/{so}Diameter",
    }

    # find Acquisition settings VALUE by dictionary key
    acquisition_value = None
    kvps = root.findall("./{app}Samples/{app}_items/{app}SampleXml/{app}MicroscopeSettings/KeyValuePairs/*".format(**nspace))

    for kvp in kvps:
        key = kvp.find("{gen}key".format(**nspace))
        if key is not None and key.text == "Acquisition":
            acquisition_value = kvp.find("{gen}value".format(**nspace))
            break

    for key, path in acquisition_items.items():
        try:
            if acquisition_value is not None:
                node = acquisition_value.find(path.format(**nspace))
                output_dict[key] = node.text if node is not None else UNKNOWN
            else:
                output_dict[key] = UNKNOWN
        except Exception:
            output_dict[key] = UNKNOWN

    # Unit conversions
    if output_dict.get('BeamSize') not in [UNKNOWN, None]:
        output_dict['BeamSize'] = round(float(output_dict['BeamSize']) * 1e6, 2)

    if output_dict.get('Binning') not in [UNKNOWN, None]:
        output_dict['Binning'] = int(output_dict['Binning'])

    if output_dict.get('HoleSize') not in [UNKNOWN, None]:
        output_dict['HoleSize'] = round(float(output_dict['HoleSize']) * 1e6, 2)

    if output_dict.get('HoleSpacing') not in [UNKNOWN, None]:
        output_dict['HoleSpacing'] = round(float(output_dict['HoleSpacing']) * 1e6, 2)

    if output_dict.get('Autofocus distance') not in [UNKNOWN, None]:
        output_dict['Autofocus distance'] = float(output_dict['Autofocus distance']) * 1e6

    if output_dict.get('ClusteringRadius') not in [UNKNOWN, None]:
        output_dict['ClusteringRadius'] = float(output_dict['ClusteringRadius']) * 1e6

    output_dict['ObjAperture'] = UNKNOWN

    if DEBUG:
        for k, v in sorted(output_dict.items()):
            print(f"{k} = {v}")

    return output_dict


def parseMovieXml(movie_fn: Path, acqDict):
    root = ET.parse(movie_fn).getroot()
    items = {
        'GunLens': "./{so}microscopeData/{so}gun/{so}GunLens",
        'Voltage': "./{so}microscopeData/{so}gun/{so}AccelerationVoltage",
        'ExtractorVoltage': "./{so}microscopeData/{so}gun/{so}ExtractorVoltage",
        'MicroscopeID': "./{so}microscopeData/{so}instrument/{so}InstrumentID",
        'PixelSpacing': "./{so}SpatialScale/{so}pixelSize/{so}x/{so}numericValue",
        'EPUversion': "./{so}microscopeData/{so}core/{so}ApplicationSoftwareVersion",
        'Magnification': "./{so}microscopeData/{so}optics/{so}TemMagnification/{so}NominalMagnification",
        'ExposureTime': "./{so}microscopeData/{so}acquisition/{so}camera/{so}ExposureTime",
    }

    for key in items:
        try:
            acqDict[key] = root.find(items[key].format(**nspace)).text
        except:
            pass

    acqDict['Mode'] = 'Linear'
    acqDict['NumSubFrames'] = 0
    acqDict['PhasePlateUsed'] = 'false'
    acqDict['Dose'] = 0
    acqDict['Voltage'] = int(acqDict['Voltage']) // 1000
    acqDict['ExtractorVoltage'] = int(float(acqDict['ExtractorVoltage']))

    # get cameraSpecificInput: ElectronCountingEnabled, SuperResolutionFactor etc. from the Acquisition preset
    customDict = dict()
    keys = "./{so}microscopeData/{so}acquisition/{so}camera/{so}CameraSpecificInput/{ar}KeyValueOfstringanyType/{ar}Key"
    values = "./{so}microscopeData/{so}acquisition/{so}camera/{so}CameraSpecificInput/{ar}KeyValueOfstringanyType/{ar}Value"

    for k, v in zip(root.findall(keys.format(**nspace)), root.findall(values.format(**nspace))):
        if k.text == "FractionationSettings":
            num = v.find("{fr}NumberOffractions".format(**nspace))
            acqDict["NumSubFrames"] = int(num.text) if num is not None else 0
        else:
            customDict[k.text] = v.text

    # check if counting/super-res is enabled
    sr = 1.0
    if customDict.get('ElectronCountingEnabled', "false") == 'true':
        sr = float(customDict['SuperResolutionFactor'])  # 1 - counting, 2 - super-res
        acqDict['Mode'] = 'Counting' if sr == 1.0 else 'Super-resolution'

    # EPU's pixel size refers to a physical pixel, which is already multiplied by Binning factor
    acqDict['PixelSpacing'] = round(float(acqDict.get('PixelSpacing', 0)) * math.pow(10, 10) / sr, 3)

    if acqDict.get('Detector', None) == 'EF-CCD':
        elem = "./{so}microscopeData/{so}acquisition/{so}camera/{so}CameraSpecificInput/{ar}KeyValueOfstringanyType/{ar}Value/{fr}NumberOffractions"
        acqDict['NumSubFrames'] = root.find(elem.format(**nspace)).text
    else:
        # count number of DoseFractions for Falcon
        elem = "./{so}microscopeData/{so}acquisition/{so}camera/{so}CameraSpecificInput/{ar}KeyValueOfstringanyType/{ar}Value/{fr}DoseFractions"
        try:
            acqDict['NumSubFrames'] = len(root.find(elem.format(**nspace)))
        except:
            pass

    if 'EnableCompression' in customDict:
        acqDict['EnableCompression'] = customDict['EnableCompression']

    # get customData: Dose, DoseOnCamera, PhasePlateUsed, AppliedDefocus from the top of xml
    customDict2 = dict()
    keys = "./{so}CustomData/{ar}KeyValueOfstringanyType/{ar}Key"
    values = "./{so}CustomData/{ar}KeyValueOfstringanyType/{ar}Value"
    for k, v in zip(root.findall(keys.format(**nspace)), root.findall(values.format(**nspace))):
        customDict2[k.text] = v.text

    detectors = ['BM-Falcon', 'EF-Falcon']
    for detector in detectors:
        for suffix in ['EerGainReference', 'GainReference']:
            key = f'Detectors[{detector}].{suffix}'
            if key in customDict2:
                acqDict['GainReference'] = os.path.basename(customDict2[key])

                if customDict.get('EnableCompression', "false") == "true":
                    acqDict['DoseFractionsOutputFormat'] = "Tiff Lzw Non-Gain normalized"
                else:
                    acqDict['DoseFractionsOutputFormat'] = "EER"
                    frame_rate = float(customDict2.get(f'Detectors[{detector}].FrameRate', 0))
                    acqDict['NumSubFrames'] = int(int(float(acqDict['ExposureTime']) * frame_rate) * 31 / 32)
                break
        else:
            continue
        break

    #if 'AppliedDefocus' in customDict:
    #    acqDict['AppliedDefocus'] = float(customDict['AppliedDefocus']) * math.pow(10, 6)
    if 'Dose' in customDict2:
        acqDict['Dose'] = float(customDict2['Dose']) * math.pow(10, -20)
    if 'PhasePlateUsed' in customDict2:
        acqDict['PhasePlateUsed'] = customDict2['PhasePlateUsed']
    if 'Aperture[C2].Name' in customDict2:
        acqDict['C2Aperture'] = customDict2['Aperture[C2].Name']
    if 'Aperture[OBJ].Name' in customDict2:
        acqDict['ObjAperture'] = customDict2['Aperture[OBJ].Name']

        if customDict2['PhasePlateUsed'] == 'true':
            acqDict['PhasePlateNumber'] = customDict2['PhasePlateApertureName'].split(" ")[-1]
            acqDict['PhasePlatePosition'] = customDict2['PhasePlatePosition']

    if 'DoseOnCamera' in customDict2:
        acqDict['DoseOnCamera'] = customDict2['DoseOnCamera']

    calcDose(acqDict)

    if DEBUG:
        for k, v in sorted(acqDict.items()):
            print(f"{k} = {v}")

    return acqDict


def calcDose(acqDict):
    """ Calculate dose rate per unbinned px per s.
    Here we use Dose (e/A^2) to compute dose on camera in e/px/s
    """
    numFr = int(acqDict['NumSubFrames'])
    dose_total = float(acqDict['Dose'])  # e/A^2
    exp = float(acqDict['ExposureTime'])  # s

    if acqDict['Mode'] == 'Super-resolution':
        pix = 2 * float(acqDict['PixelSpacing']) / int(acqDict['Binning'])  # A
    else:
        pix = float(acqDict['PixelSpacing']) / int(acqDict['Binning'])  # A

    if numFr:  # not 0
        dose_per_frame = dose_total / numFr  # e/A^2/frame
    else:
        dose_per_frame = 0
    dose_on_camera = dose_total * math.pow(pix, 2) / exp  # e/unbinned_px/s

    acqDict['DosePerFrame'] = round(dose_per_frame, 4)
    acqDict['DoseOnCamera'] = round(dose_on_camera, 2)
    acqDict['ExposureTime'] = round(exp, 2)
    acqDict['Dose'] = round(dose_total, 2)


def main():
    parser = argparse.ArgumentParser(
        prog="parse_epu_session.py",
        description=f"TFS EPU parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(dest="filename", help="File containing a list of EpuSession.dm files")
    args = parser.parse_args()
    parse_files(Path(args.filename))

if __name__ == "__main__":
    main()
