<!--
*** This readme is based on the 'BLANK_README template 
*** from https://github.com/othneildrew/Best-README-Template
-->
<a id="readme-top"></a>



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/awcrusius/CMPT353-Translink-data-analysis">
    <img src="images/logo.svg" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Transit Data Analyzer</h3>

  <p align="center">
    Collect and analyze GTFS data over time

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#data-collection">Data Collection</a></li>
      </ul>
    </li>
    <li><a href="#generating-visuals">Generating Visuals</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>
  </p>
</div>

<!-- ABOUT THE PROJECT -->
## About The Project

This project is meant to gather data from a real-time general transit feed specification (<a href="https://gtfs.org/">GTFS</a>) API. The data is ingested as a set of protocol buffer objects whose data is moved into a DUCKDB database. 

Once real-time data is ingested, the user can do the following:
* Ingest <a href="https://gtfs.org/documentation/schedule/reference/">Static GTFS data</a>
* Clean Data to add missing realtime values from Static data
* produce graphs of the GTFS data:
  * Speed maps
  * Comparitive delays
  * Usage pi charts
  * and more!

To get started running the code, see  <a href="#getting-started">Getting Started</a>


<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

[![Python][Python.org]][Python-url]
[![Duck DB][Duck.db]][Duckdb-url]
[![Pandas][Pandas.org]][Pandas-url]
[![Docker][Docker.com]][Docker-url]
[![Plotly][plotly.icon]][plotly-url]
[![Numpy][numpy.icon]][numpy-url]


<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- COLLECTED DATA -->
## COLLECTED DATA

<a href="https://mega.nz/folder/vc9lCbiD#6yG6-qpfd8ODDX-359gtDQ">Collected data linked here</a>

Our current dataset is 9 months long from December 17th to May 23rd and is 23.66gb uncompressed.

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

To install prerequesites please run the following
  ```sh
  pip install duckdb 
  pip install requests
  pip install PyYAML
  pip install gtfs-realtime-bindings
  pip install numpy
  pip install pandas
  pip install seaborn
  pip install matplotlib
  pip install gtfs_functions
  pip install plotly
  pip install kaleido
  pip install dash
  ```

## Data Collection



<details >
  <summary >Start from here to collect data yourself before generating visualizations</summary>

1. Download your relevant docker installation from [Docker](https://www.docker.com/get-started/)
2. Run the downloaded docker installation file and install docker fully
3. Download the dockerfile from releases:dockerfile 
4. Load the dockerfile into docker
    ```sh
    docker load < translink_ingest.tar.gz
    ```
5. Run the container the repo, where <destination_dir> is the desired destination for your data
   ```sh
   docker run \
    --restart on-failure \
    -v <destination_dir>:/app/output_database \
    cmpt353translinkdataanalysis

   ```
6. Confirm the docker container is running by checking the logs with
   ```sh
   docker logs -f cmpt353translinkdataanalysis
   ```
7. If you see the logs similar to below, the collector is running as expected and realtime data will be collected until the program is stopped.  If the colletor is not running as expected, please skip to <a href="#generating-visuals">Generating Visuals</a> 
   ```
   rt_position inserted, total length is ###
   rt_trip inserted, total length is ###
   rt_position inserted, total length is ###
   rt_trip inserted, total length is ###
   rt_position inserted, total length is ###
   ```

8. When you have successfully collected enough data using translink_ingest, Download [gtfs_static_add.py](gtfs_static_add.py)
9. Download the most recent translink static data from [Translink](https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/gtfs/gtfs-data)
10. To run gtfs_static_add.py, run the following exchanging `google_transit.zip` and  `transit.db` for your respective dowloaded gtfs static and database files.
   ```sh
   python3 gtfs_static_add.py google_transit.zip transit.db
   ```
11. If any of the following steps do not work locally, skip to Generating Visuals to download a pre built dataset.
</details>

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Generating Visuals

<details>
<summary >Start here if you just want to generate visualizations on pre built data.</summary>

1. If you could not generate your own database, please download the pre built database from [releases:Transit_Data](https://github.com/awcrusius/CMPT353-Translink-data-analysis/releases/tag/Transit_Data)
2. To generate the route map, we recommend downloading the kepler.gl.json and uploading that to [kepler.gl/demo](https://kepler.gl/demo). This will generate a map configured exactly as shown
3. Alternatively, you can use the transit_cleaned.zip file (don't unzip it!) from Data_for_analysis.zip. You will then run it through Map_data.py, and use the shape_info.csv and feeds_stops.csv files it produces. However, you will have to configure all the settings manually when uploading these to kepler.gl, so we don't recommend this method
4. To create the visualizations, you will need 2024-boardings-by-servic.csv, routes_speeds.csv, stop_frequency.csv, and trips_ridership.csv from Data_for_analysis.zip. You will then run these through Creating_visualizations.py
5. You can also manually create the files in Data_for_analysis.zip using Analysis_data.py, though this doesn't include google_transit.zip

</details>


<p align="right">(<a href="#readme-top">back to top</a>)</p>











<!-- LICENSE -->
## License

Distributed under the GNUv3 License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Adrian Cruisus -  acrusius@sfu.ca

Anthony Fesenko - anthonyfesenko02@gmail.com

<p align="right">(<a href="#readme-top">back to top</a>)</p>




<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/awcrusius/CMPT353-Translink-data-analysis.svg?style=for-the-badge
[contributors-url]: https://github.com/othneildrew/Best-README-Template/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/othneildrew/Best-README-Template.svg?style=for-the-badge
[forks-url]: https://github.com/othneildrew/Best-README-Template/network/members
[stars-shield]: https://img.shields.io/github/stars/othneildrew/Best-README-Template.svg?style=for-the-badge
[stars-url]: https://github.com/othneildrew/Best-README-Template/stargazers
[issues-shield]: https://img.shields.io/github/issues/othneildrew/Best-README-Template.svg?style=for-the-badge
[issues-url]: https://github.com/othneildrew/Best-README-Template/issues
[license-shield]: https://img.shields.io/github/license/othneildrew/Best-README-Template.svg?style=for-the-badge
[license-url]: https://github.com/othneildrew/Best-README-Template/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/othneildrew
[product-screenshot]: images/screenshot.png
[Python.org]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[Python-url]: https://www.python.org/
[duck.db]: https://img.shields.io/badge/-DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=white
[duckdb-url]: https://duckdb.org/
[Docker.com]: https://img.shields.io/badge/-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/
[Pandas.org]: https://img.shields.io/badge/-pandas-150458?style=for-the-badge&logo=pandas&logoColor=white
[Pandas-url]: https://pandas.pydata.org/
[plotly.icon]: https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white
[plotly-url]: https://plotly.com/
[numpy.icon]: https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white
[numpy-url]: https://numpy.org/
