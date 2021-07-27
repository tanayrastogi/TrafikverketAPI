# Python Libraries
import requests
import argparse
import json
from datetime import datetime as dt
import csv
import os
import plotly.graph_objects as go
import pandas as pd
import re 
from collections import OrderedDict
from PIL import Image
from tqdm import tqdm

###################
# Argument Parser #
###################
def __parse_args():
    """
    Function to perform CLI operations. 
    """
    parser = argparse.ArgumentParser(
        description='Fetching data from Trafikverket API.')
    
    # Arguments
    parser.add_argument('--xml', type=str,
                        help='path to xml data input for API.', required=True)
    parser.add_argument('--to_json', type=str, default=None,
                        help='path to output json file.')
    parser.add_argument('--to_csv', type=str, default=None,
                        help='path to output csv file.')
    parser.add_argument('--to_plot', type=str, default=None,
                        help='path to output HTML-plot file.')
    parser.add_argument('--to_images', type=str, default=None,
                        help='path to output camera images.')
    parser.add_argument('--verbose', type=str, default="True",
                    help='print output from the request.')
    args = parser.parse_args()
    return args

############
# CSV file #
############
def __save_to_csv(data_to_csv, csv_filepath):
    # Get all the columns in the data
    csv_columns = list(data_to_csv[0].keys())
    for data in data_to_csv:
        if csv_columns != list(data.keys()):
            for col in data.keys():
                if col not in csv_columns:
                    csv_columns.append(col)
    csv_columns.sort()

    # Default data when they column is missing from the fetch data
    defaults = {key:'N/A' for key in csv_columns}

    # Save CSV
    try:
        with open(csv_filepath, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns, delimiter=';')
            writer.writeheader()
            for entry in data_to_csv:
                entry = OrderedDict(sorted(entry.items()))
                kv = defaults.copy()
                kv.update(entry)
                writer.writerow(kv)
        print("Done!")
    except IOError:
        print("I/O error")

####################
# TrafficFlow Plot #
####################
def __plot_TrafficFlow(plot_data, plot_filepath):
    api_type = "TrafficFlow"
    # Pandas Dataframe
    df = pd.DataFrame.from_dict(plot_data)

    # Fix index
    df.set_index("SiteId", inplace=True)
    df.sort_index(inplace=True)

    # Fix datetime 
    df["MeasurementTime"] = pd.to_datetime(df['MeasurementTime'], utc=True)
    df["MeasurementTime"] = df["MeasurementTime"].dt.tz_convert("Europe/Stockholm")
    df["ModifiedTime"] = pd.to_datetime(df['ModifiedTime'], utc=True)
    df["ModifiedTime"] = df["ModifiedTime"].dt.tz_convert("Europe/Stockholm")

    # Map coordinates
    df["lat"] = df["Geometry"].apply(lambda x: re.split('[( )]', x["WGS84"])[3])
    df["lng"] = df["Geometry"].apply(lambda x: re.split('[( )]', x["WGS84"])[2])
    df["lat"] = df["lat"].astype(float)
    df["lng"] = df["lng"].astype(float)

    # Plot
    plot_data = [go.Scattermapbox(
                    lat =df.lat.to_list(), lon = df.lng.to_list(),
                    mode = "markers",
                    name = "{}".format(api_type),
                    marker=dict(
                        size=7,
                        color=df["AverageVehicleSpeed"].to_list(),
                        cmin=min(df["AverageVehicleSpeed"]),
                        cmax=max(df["AverageVehicleSpeed"]),
                        opacity=0.8,
                        colorbar=dict(
                                    title="Avg. Vehicle Speed"),
                                ),
                    customdata = [(a, b, c, d, e, f) for a, b, c, d, e, f in zip(df.index.to_list(), 
                                      df["VehicleFlowRate"].to_list(),
                                      df["AverageVehicleSpeed"].to_list(),
                                      df["SpecificLane"].to_list(),
                                      df["MeasurementTime"].dt.strftime("%m-%d-%y %H:%M:%S").to_list(),
                                      df["ModifiedTime"].dt.strftime("%m-%d-%y %H:%M:%S").to_list())],
                    hovertemplate = 
                    'SiteID: %{customdata[0]}<br>' +
                    'Veh Flow Rate: %{customdata[1]}<br>' +
                    'Avg Speed: %{customdata[2]}<br>' +
                    'Lane: %{customdata[3]}<br>' +
                    'Measurement Time: %{customdata[4]}<br>' +
                    'Modified Time: %{customdata[5]}<br>',
                    showlegend=False)
            ]

    layout = go.Layout(mapbox=dict(
                            style="carto-positron",
                            center= dict(lat=59.3471, lon=18.06689),
                            zoom=10),
                       title=dict(
                           text="{}".format(api_type),
                           y=.98, x=0.5,
                           xanchor='center',
                           yanchor='top'),
                       margin={"r":0,"t":0,"l":0,"b":0})
    fig = go.Figure(data=plot_data, layout=layout)
    fig.write_html(plot_filepath)
    print("Done!")

###############
# Camera Plot #
###############
def __plot_Camera(plot_data, plot_filepath):
    api_type = "Camera"

    # Pandas Dataframe
    df = pd.DataFrame.from_dict(plot_data)

    # Fix index
    df.set_index("Id", inplace=True)
    df.sort_index(inplace=True)

    # Fix datetime 
    df["ModifiedTime"] = pd.to_datetime(df['ModifiedTime'], utc=True)
    df["ModifiedTime"] = df["ModifiedTime"].dt.tz_convert("Europe/Stockholm")
    df['PhotoTime'] = pd.to_datetime(df['PhotoTime'], utc=True)
    df["PhotoTime"] = df["PhotoTime"].dt.tz_convert("Europe/Stockholm")

    # Map coordinates
    df["lat"] = df["Geometry"].apply(lambda x: re.split('[( )]', x["WGS84"])[3])
    df["lng"] = df["Geometry"].apply(lambda x: re.split('[( )]', x["WGS84"])[2])
    df["lat"] = df["lat"].astype(float)
    df["lng"] = df["lng"].astype(float)

    # # Photo URL for full size images
    df["PhotoUrl"] = df["PhotoUrl"].apply(lambda x: x+"?type=fullsize")    

    # Plot
    plot_data = [go.Scattermapbox(
                    lat =df.lat.to_list(), lon = df.lng.to_list(),
                    mode = "markers",
                    name = "{}".format(api_type),
                    marker=dict(
                        size=7,
                        color='rgb(200, 0, 0)',
                        opacity=0.8),
                    text = ["""<a href="{}">Link</a>""".format(url) for url in df["PhotoUrl"]],
                    customdata = [(a, b, c, d, e) for a, b, c, d, e in zip(df.index.to_list(), 
                                      df["Name"].to_list(),
                                      df["ModifiedTime"].dt.strftime("%m-%d-%y %H:%M:%S").to_list(),
                                      df["PhotoTime"].dt.strftime("%m-%d-%y %H:%M:%S").to_list(),
                                      df["PhotoUrl"].to_list())],
                    hovertemplate = 
                    'ID: %{customdata[0]}<br>' + 
                    'Name: %{customdata[1]}<br>' +
                    'Link: <b>%{text}</b><br>'
                    'Modified Time: %{customdata[2]}<br>' +
                    'Photo Time: %{customdata[3]}<br>',
                    showlegend=False)
            ]

    layout = go.Layout(mapbox=dict(
                            style="carto-positron",
                            center= dict(lat=59.3471, lon=18.06689),
                            zoom=10),
                       title=dict(
                           text="{}".format(api_type),
                           y=.98, x=0.5,
                           xanchor='center',
                           yanchor='top'),
                       margin={"r":0,"t":0,"l":0,"b":0})
    fig = go.Figure(data=plot_data, layout=layout)
    fig.write_html(plot_filepath)
    print("Done!")


#################
# Camera Images #
#################
def __save_images(data, image_folder, time_now):
    # Pandas Dataframe
    df = pd.DataFrame.from_dict(data)
    # Fix index
    df.set_index("Id", inplace=True)
    df.sort_index(inplace=True)
    # Photo URL for full size images
    df["PhotoUrl"] = df["PhotoUrl"].apply(lambda x: x+"?type=fullsize&maxage=15")

    print("\n[INFO] Generating images ...", end=" ")
    start_time = dt.utcnow()
    for itr in tqdm(range(len(df.index))):
        image_id = df.index.to_list()[itr]

        # Image folder path
        folder_path = os.path.join(image_folder, image_id)

        # Check if the folder exits already. If not create one
        if not os.path.isdir(folder_path):
            os.makedirs(folder_path)
        
        # Read the image
        img = Image.open(requests.get(df.loc[image_id, "PhotoUrl"], stream=True).raw)
        img.save(os.path.join(folder_path, "{}.jpeg".format(time_now)))
    
    delta = dt.utcnow() - start_time
    print("Done in {} sec".format(delta.seconds))



def get_data(xml,
             save_json=None,
             save_csv=None,
             save_plot=None,
             save_images=None,
             verbose=True,
             URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"):
  
    # Send POST Request
    print("\n[INFO] Fetching data from Trafikverket ....", end=" ")
    response = requests.post(
                        URL,
                        headers={"Content-Type": "application/xml"},
                        data=xml)
    print("Done!")

    # Make sure that the data is correctly recieved
    assert response.status_code == 200, \
        "Error!!\n{}".format(response.json()["RESPONSE"]["RESULT"][0]["ERROR"])
    assert "application/json" in response.headers["Content-Type"], \
        "Error!!\nExpected JSON. Returned {}".format(response.headers["Content-Type"])

    # Data fetched on time
    time_now = dt.now().strftime("%y%m%d_%H%M%S")
    data = response.json()["RESPONSE"]["RESULT"][0]
    api_type = list(data.keys())[0]

    ################
    # Print output #
    ################
    if verbose:
        text = "\nAPI: {}".format(api_type) + "\tNumber of entries: {}".format( len(data[list(data.keys())[0]]) ) 
        print(text)
        print("Fetched on: ", time_now)
        print("\nSample Entry: ")
        print( data[list(data.keys())[0]][0] )
        print("\n")

    #############
    # JSON file #
    #############
    if save_json is not None:
        # Check if dir exit otherwise make dir
        if not os.path.isdir(save_json):
            os.makedirs(save_json)

        print("[INFO] Saving JSON at ", save_json,"....", end=" ")
        filepath = os.path.join(save_json, '{}-{}.json'.format(api_type, time_now))
        with open(filepath, 'w') as outfile:
            json.dump(response.json(), outfile)
        print("Done!")
    
    ############
    # CSV file #
    ############
    if save_csv is not None:
        # Check if dir exit otherwise make dir
        if not os.path.isdir(save_csv):
            os.makedirs(save_csv)
        print("[INFO] Saving CSV at ", save_csv,"....", end=" ")
        filepath = os.path.join(save_csv, "{}-{}.csv".format(api_type, time_now))

        # Saving to CSV
        __save_to_csv(data[api_type], filepath)

    #############
    # Plot file #
    #############
    if save_plot is not None:
        # Check if dir exit otherwise make dir
        if not os.path.isdir(save_plot):
            os.makedirs(save_plot)
        print("[INFO] Saving Plot at ", save_plot,"....", end=" ")
        filepath = os.path.join(save_plot, "{}-{}.html".format(api_type, time_now))

        if api_type == "TrafficFlow":
            __plot_TrafficFlow(data[api_type], filepath)
        elif api_type == "Camera":
            __plot_Camera(data[api_type], filepath)
    
    ###############
    # Images file #
    ###############
    if save_images is not None:
        if api_type == "Camera":
            # Check if dir exit otherwise make dir
            if not os.path.isdir(save_images):
                os.makedirs(save_images)
            print("[INFO] Saving Plot at ", save_images,"....", end=" ")

            __save_images(data[api_type], save_images, time_now)
        
        else:
            print("[ERROR] API {} has no images to save... ".format(api_type))



    return response.json()


if __name__ == "__main__":
    # Parse input arguments
    args = __parse_args()

    # Read the XML file
    with open(args.xml, mode='r') as f:
        xml = f.read()

    # Get Data
    data = get_data(xml,
                    save_json=args.to_json,
                    save_csv=args.to_csv,
                    save_plot=args.to_plot,
                    save_images=args.to_images,
                    verbose=False if args.verbose=="False" else True)

    

    # ###########
    # # Testing #
    # ###########
    # filepath = "Camera.xml"
    # # Read the XML file
    # with open(filepath, mode='r') as f:
    #     xml = f.read()
    # URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

    # # Send POST Request
    # print("\n[INFO] Fetching data from Trafikverket ....", end=" ")
    # response = requests.post(
    #                     URL,
    #                     headers={"Content-Type": "application/xml"},
    #                     data=xml)
    # print("Done!")

    # # Make sure that the data is correctly recieved
    # assert response.status_code == 200, \
    #     "Error!!\n{}".format(response.json()["RESPONSE"]["RESULT"][0]["ERROR"])
    # assert "application/json" in response.headers["Content-Type"], \
    #     "Error!!\nExpected JSON. Returned {}".format(response.headers["Content-Type"])

    # # Data fetched on time
    # time_now = dt.now().strftime("%y%m%d_%H%M%S")
    # data = response.json()["RESPONSE"]["RESULT"][0]
    # api_type = list(data.keys())[0]


    # image_folder = "images/"
    # plot_data = data[api_type]

    # # Pandas Dataframe
    # df = pd.DataFrame.from_dict(plot_data)
    # # Fix index
    # df.set_index("Id", inplace=True)
    # df.sort_index(inplace=True)
    # # Photo URL for full size images
    # df["PhotoUrl"] = df["PhotoUrl"].apply(lambda x: x+"?type=fullsize&maxage=15")

    # start_time = dt.utcnow()
    # for image_id in df.index:

    #     # Image folder path
    #     folder_path = os.path.join(image_folder, image_id)

    #     # Check if the folder exits already. If not create one
    #     if not os.path.isdir(folder_path):
    #         os.makedirs(folder_path)
        
    #     # Read the image
    #     img = Image.open(requests.get(df.loc[image_id, "PhotoUrl"], stream=True).raw)
    #     img.save(os.path.join(folder_path, "{}.jpeg".format(time_now)))
    # delta = dt.utcnow() - start_time


