import json
import os

from syftbox.lib import Client

client = Client.load()

input_folder = client.appdata("adder/inputs")
output_folder = client.appdata("adder/done")
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

input_file_path = input_folder / "data.json"
output_file_path = output_folder / "data.json"

if os.path.exists(input_file_path):
    with open(input_file_path, "r") as f:
        data = json.load(f)

    data["datum"] += 1

    with open(output_file_path, "w") as f:
        json.dump(data, f)

    os.remove(input_file_path)
else:
    print(f"Input file {input_file_path} does not exist.")
