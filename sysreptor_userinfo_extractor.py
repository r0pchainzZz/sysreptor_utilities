#!/usr/bin/python3

# name: sysreptor_userinfo_extractor.py 
# 
# version: 1.0
# 
# author: r0pchainzZz
# 
# description:  This script takes a saved HTTP request that containing Sysreptor user
#               data and then extracts the usernames and IDs. The files this produces can
#               be used along with sysreptor_convert_project_users_ids.py to convert the 
#               IDs associated with usernames in exported Sysreptor projects. 


import json, click

@click.command()
@click.option('--filename','-f',required=True,help="The file of sysreptor user information from which to extract names and IDs.")
def main(filename):
    with open(filename,"r") as f:
        my_json = json.load(f)

    output = []

    for result in my_json["results"]:
        data = {"username": result["username"], "id": result["id"]}
        output.append(data)

    print(json.dumps(output))

if __name__ == "__main__":
    main()

