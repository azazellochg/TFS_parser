TFS parser
==========

Simple Python 3 scripts to parse EPU/Tomo session files. These scripts can be useful to analyze EPU/Tomo parameters from sessions of different facility users.

For EPU sessions, it will analyze **EpuSession.dm** (one per session) and a FoilHole data xml file (from a first found movie).
For Tomo sessions, it will analyze **Session.dm** (one per session) and amn mdoc file (from a first found tilt series). In the end, an output CSV table is created.

How to use
----------

1) Locate *EpuSession.dm* or *Session.dm* files. You can use **get_files.sh** as an example script to find all files modified in 2023. This script will output a list of file paths.
2) Install the package:

.. code-block:: bash

    conda create -yn tfs_parser python
    conda activate tfs_parser
    pip install .

3) Run the parser:

.. code-block:: bash

   parse_epu /path/to/filelist
   parse_tomo /path/to/filelist

It will generate **filelist.csv**

4) PROFIT!! You are done. You can analyse the output CSV in any way you like with downstream tools.
5) If you want to use the provided streamlit-based dashboard to display simple plots:

.. code-block:: bash

    pip install .[extra]
    streamlit run --browser.gatherUsageStats=false --browser.serverAddress=localhost dashboard.py


CSV columns (EPU)
-----------------

* Autofocus distance (um)
* Autofocus recurrence
* BeamSize (um)
* Binning
* C2Aperture (um)
* ClusteringMode
* ClusteringRadius (um)
* Defocus list (um)
* DelayAfterImageShift (s)
* DelayAfterStageShift (s)
* Detector
* Dose (e/A^2)
* DoseFractionsOutputFormat
* DoseOnCamera (e/unbinned_px/s)
* DosePerFrame (e/A^2/frame)
* Drift recurrence
* Drift threshold (m/s)
* EnergySelectionSlitWidth (eV)
* EPUversion
* ExposureTime (s)
* ExtractorVoltage (V)
* GunLens
* HoleSize (um)
* HoleSpacing (um)
* Magnification
* MicroscopeID
* Mode
* Name
* Number of exposures (per hole)
* NumSubFrames
* ObjAperture (um)
* PhasePlateEnabled
* PhasePlateUsed
* PixelSpacing (A)
* ProbeMode
* SpecimenCarrierType
* SpotSize
* StartDateTime
* Voltage (kV)

CSV columns (Tomo)
-----------------

tbd