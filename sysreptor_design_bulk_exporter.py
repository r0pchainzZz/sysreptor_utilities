#!/usr/bin/python3

# name: sysreptor_design_bulk_exporter.py 
# 
# version: 1.0
# 
# author: r0pchainzZz
# 
# description:  This script will export all report designs from an 
#               instance of Sysreptor to aid users migrating between
#               installs or wishing to back up their designs. The reptor
#               cli already provides similar functionality for exporting 
#               finding templates or reports, but not for report designs.
#               This script is meant to fill that gap.
#  
# disclaimer:   This is not an official project of Syslifters and not in 
#               any way affiliated with the company. 
 
 

from getpass import getpass
import requests, json, click, re, sys, os, subprocess
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# asks for username and password, then returns session
def get_session(server, verbose, debug, proxies):
    username = input("Please enter your username: ")
    password = getpass()

    url = f"{server}/api/v1/auth/login/"

    headers = {
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json",
        }
    my_json = json.dumps({"username": username, "password": password})
    if verbose >= 2:
        print(my_json)

    session = requests.session()
    
    if debug == 1:
        res = session.post(url, data=my_json, headers=headers, verify=False, proxies=proxies)
    else:  
        res = session.post(url, data=my_json, headers=headers, verify=False)

    if verbose >= 2:
        print(res.text)

    if res.status_code != 200:  
        print(f"[-] Received unexpected reponse code: {res.status_code}")
        print("[-] Exiting.")
        sys.exit(1)

    if not re.search("success", res.text):
        print("[-] There was some sort of error logging in. Exiting.")
        sys.exit(1)

    print("[+] Login successful!")

    return session


# Calls the API to find the ids and names of all designs. Returns a list of ids and names.
def get_design_info(server, verbose, debug, proxies, session):
    print("[+] Getting list of report design IDs and names.")

    design_list = list()

    url = f"{server}/api/v1/projecttypes/?scope=global&ordering=name"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        }
    
    if debug == 1:
        res = session.get(url, proxies=proxies, verify=False)
    else:
        res = session.get(url, verify=False)

    if res.status_code != 200:  
        print(f"[-] Received unexpected reponse code: {res.status_code}")
        print("[-] Exiting.")
        sys.exit(1)

    if verbose >= 2:
        print(res.text)

    my_json = json.loads(res.text)

    for result in my_json["results"]:
        if verbose >= 1:
            print(f"[+] Identified design: {result['id']} - {result['name']}")
        design_list.append({"id":result['id'],"name":result['name']})

    if verbose >= 2:
        print(design_list)

    print("[+] Design information retrieved successfully.")

    return design_list


# Loops through the list of design ids and exports them all to a folder. 
def export_designs(server, verbose, debug, proxies, session, design_list, output_dir):

    error_count = 0
    print(f"[+] Checking to make sure the output directory does not already exist.")
    # First, make sure that we have a unique directory name to write to.
    increment = 1
    output_dir_base = output_dir
    while os.path.exists(os.path.join(os.getcwd(), output_dir)):
        print(f"[!] Directory already exists. Incrementing name.")
        output_dir = output_dir_base + f"_{increment}"
        increment += 1

    print(f"[+] Success!. Designs will be exported to '{output_dir}'.")
    os.mkdir(output_dir)
    os.mkdir(f"{output_dir}/all_designs")
    
    # Now export
    print(f"[+] Exporting designs...")

    for design in design_list:
        id = design["id"]
        name = design["name"]


        url = f"{server}/api/v1/projecttypes/{id}/export"

        headers = {
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept": "application/json",
            }
        my_json = json.dumps({})

        if debug == 1:
            res = session.post(url, data=my_json, headers=headers, verify=False, proxies=proxies)
        else:  
            res = session.post(url, data=my_json, headers=headers, verify=False)

        if res.status_code != 200:  
            print(f"[!] Received unexpected reponse code from export endpoint for id {id}: {res.status_code}")
            print(f"[!] Continuing to try next id...")
            error_count += 1
            continue

        # replace spaces in the design names with hyphens
        name = re.sub("\s","-", name)

        try:
            save_name = f'{output_dir}/{name}-.tar.gz'   
            if verbose >= 1:
                print(f"[!] Trying to save to '{save_name}'.")
            with open(save_name,'wb') as f:
                f.write(res.content)
        except:
            print(f"[!] There was an error saving the design '{id} - {name}' to file. Trying the next one.") 
            error_count += 1
            continue

        # now unarchive the design contents to the all_designs subdirectory so that we can also create an 
        # additional archive that contains all of the designs together for easy movement or sharing
        try:
            subprocess.run(["tar","-xzf", save_name, "--directory", f"{output_dir}/all_designs/"])
        except:
            print(f"[!] There was an error unarchivng the design '{id} - {name}' for combination with the others. Trying the next one.") 
            error_count += 1
            continue
            

        print(f"[+] Design saved successfully to '{name}.tar.gz'")
    
    # now compress the all_designs directory and remove it 
    print("[+] Trying to combine all designs into single all_designs.tar.gz for easy use...")
    try:
        subprocess.run(["tar","czf", f"{output_dir}/all_designs.tar.gz","-C",f"{output_dir}/all_designs","."])
    except:
        print(f"[!] There was an error creating an archive of all the designs!")
        error_count += 1
    
    print("[+] Removing intermediate folder for combining designs...")
    try:
        subprocess.run(["rm","-rf",f"{output_dir}/all_designs"])
    except:
        print(f"[!] There was an error removing the folder with unarchived content from many designs!")
        error_count += 1
    
    print("[+] Designs successfully combined into single archive.")
            
    if error_count == 0:
        success = True
    else:
        success = False

    return [success, error_count]

@click.command()
@click.option('--server','-s',default="http://127.0.0.1:8000",show_default=True,help="The server you want to target, including the port if needed.")
@click.option('--verbose','-v',default=0,count=True,help="Verbosity level. Supports -v and -vv.")
@click.option('--output-dir','-o',default="exported_designs",show_default=True,help="The directory where the designs will be exported.")
@click.option('--debug','-d',is_flag=True,default=False,show_default=True,help="Activate debugging mode. This will send program traffic through the proxy specifed by the '--proxy' option, which is 127.0.0.1:8080 by default.")
@click.option('--proxy','-p',default="127.0.0.1:8080",show_default=True,help="Proxy for traffic during debugging.")
def main(server, verbose, output_dir, debug, proxy):
    
    proxies={"http":proxy,"https":proxy}

    print(f"[+] Targeting server: {server}")

    session = get_session(server, verbose, debug, proxies)
    design_list = get_design_info(server, verbose, debug, proxies, session)
    exported = export_designs(server, verbose, debug, proxies, session, design_list, output_dir)

    if exported[0] == True:
        print("[+] All designs successfully exported!")
    else:
        print(f"[!] There were {exported[1]} errors! You should check the output.")

if __name__=="__main__":
    main()
