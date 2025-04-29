#!/usr/bin/python3

# name: sysreptor_project_bulk_exporter.py 
# 
# version: 1.0
# 
# author: r0pchainzZz
# 
# description:  This script will export all report projects from an 
#               instance of Sysreptor to aid users migrating between
#               installs or wishing to back up their projects. 
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

    return [session,username,password]


# Calls the API to find the ids and names of all projects. Returns a list of ids and names.
def get_project_info(server, verbose, debug, proxies, session,username,password):

    # make sure the right permissions are there for seeing every single project
    url = f"{server}/api/v1/pentestusers/self/admin/enable/"
    headers = {
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json",
        }
    if debug == 1:
        res = session.post(url, data="{}", headers=headers, verify=False, proxies=proxies)
    else:  
        res = session.post(url, data="{}", headers=headers, verify=False)

    if res.status_code != 200:  
        print(f"[!] Received unexpected reponse code while trying to establish template admin permissions: {res.status_code}")
        
        if res.status_code != 403:
            print("[!] This response is fatal. Exiting.")
            sys.exit(1)
        
    print("[+] Reauthenticating...")        
    url = f"{server}/api/v1/auth/login/"

    headers = {
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json",
        }
    my_json = json.dumps({"username": username, "password": password})
    
    if debug == 1:
        res = session.post(url, data=my_json, headers=headers, verify=False, proxies=proxies)
    else:  
        res = session.post(url, data=my_json, headers=headers, verify=False)
    
    if res.status_code != 200:  
        print(f"[-] Received unexpected reponse code: {res.status_code}")
        print("[-] Exiting.")
        sys.exit(1)
    
    url = f"{server}/api/v1/pentestusers/self/admin/enable/"
    headers = {
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json",
        }
    if debug == 1:
        res = session.post(url, data="{}", headers=headers, verify=False, proxies=proxies)
    else:  
        res = session.post(url, data="{}", headers=headers, verify=False)


    # at this point we should have superuser permissions activated if they weren't before
    print("[+] Getting list of project IDs and names.")

    project_list = list()

    url = f"{server}/api/v1/pentestprojects/?ordering=-created"
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
            print(f"[+] Identified project: {result['id']} - {result['name']}")
        project_list.append({"id":result['id'],"name":result['name']})

    if verbose >= 2:
        print(project_list)

    print("[+] Project information retrieved successfully.")

    return project_list


# Loops through the list of project ids and exports them all to a folder. 
def export_projects(server, verbose, debug, proxies, session, project_list, output_dir):

    error_count = 0
    print(f"[+] Checking to make sure the output directory does not already exist.")
    # First, make sure that we have a unique directory name to write to.
    increment = 1
    output_dir_base = output_dir
    while os.path.exists(os.path.join(os.getcwd(), output_dir)):
        print(f"[!] Directory already exists. Incrementing name.")
        output_dir = output_dir_base + f"_{increment}"
        increment += 1

    print(f"[+] Success!. Projects will be exported to '{output_dir}'.")
    os.mkdir(output_dir)
#    os.mkdir(os.path.join(output_dir/"all_projects")
    
    # Now export
    print(f"[+] Exporting projects...")

    for project in project_list:
        id = project["id"]
        name = project["name"]


        url = f"{server}/api/v1/pentestprojects/{id}/export/all"

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

        # replace spaces in the project names with hyphens
        name = re.sub("\s","-", name)

        # if the filename already exists (can happen if projects share names) then increment the filename
        try:
            save_name = os.path.join(output_dir,f"{name}")   

            increment = 1
            save_name_base = save_name
            while os.path.exists(os.path.join(os.getcwd(), f"{save_name}.tar.gz")):
                save_name = save_name_base + f"-{increment}"
                increment += 1

            save_name = f"{save_name}.tar.gz"

            if verbose >= 1:
                print(f"[!] Trying to save to '{save_name}'.")
            with open(save_name,'wb') as f:
                f.write(res.content)
        except:
            print(f"[!] There was an error saving the project '{id} - {name}' to file. Trying the next one.") 
            error_count += 1
            continue


        print(f"[+] Project saved successfully to '{name}.tar.gz'")
    
    if error_count == 0:
        success = True
    else:
        success = False

    return [success, error_count]

@click.command()
@click.option('--server','-s',default="http://127.0.0.1:8000",show_default=True,help="The server you want to target, including the port if needed.")
@click.option('--verbose','-v',default=0,count=True,help="Verbosity level. Supports -v and -vv.")
@click.option('--output-dir','-o',default="exported_projects",show_default=True,help="The directory where the projects will be exported.")
@click.option('--debug','-d',is_flag=True,default=False,show_default=True,help="Activate debugging mode. This will send program traffic through the proxy specifed by the '--proxy' option, which is 127.0.0.1:8080 by default.")
@click.option('--proxy','-p',default="127.0.0.1:8080",show_default=True,help="Proxy for traffic during debugging.")
def main(server, verbose, output_dir, debug, proxy):
    
    proxies={"http":proxy,"https":proxy}

    print(f"[+] Targeting server: {server}")

    session, username, password = get_session(server, verbose, debug, proxies)
    project_list = get_project_info(server, verbose, debug, proxies, session, username, password)
    exported = export_projects(server, verbose, debug, proxies, session, project_list, output_dir)

    if exported[0] == True:
        print("[+] All projects successfully exported!")
    else:
        print(f"[!] There were {exported[1]} errors! You should check the output.")

if __name__=="__main__":
    main()
