#!/usr/bin/python3

# name: sysreptor_project_bulk_deleter.py 
# 
# version: 1.0
# 
# author: r0pchainzZz
# 
# description:  Deletes all projects in a sysreptor instance. Useful 
#               when fixing bulk import mistakes. Note that this will
#               delete all projects that the user account can access,
#               and deletion is not recoverable. 
# 
#               Do NOT use this in a production environment without
#               having backups of anything you care about. When in doubt,
#               run the project bulk exporter before running this.
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


# Displays a warning. Shows one message the first time and another the second time 
# Note that this function will exit the program if the user does not choose to continue
# but as a failsafe, the function returns True unless there's explicity acceptance.
def show_warning(server, time, num_projects):
    
    if time == 1:
        print(f"""[!] This program will permanently delete all projects that you user can access in the instance of Sysreptor located at: {server}
[!] This operation is unrecoverable. Do you still wish to proceed? (Y/n): """, end="")
        choice = input()
        if choice != "Y":
            print("[!] You did not choose 'Y'. Exiting.")
            sys.exit(0)
        elif choice == "Y":
            return True


    elif time == 2:
        print(f"""
[!] Final warning! The program has detected {num_projects} projects on the server located at {server}. Are you absolutely certain that you wish to permanently delete all of these projects?

[!] If you wish to proceed, type the word 'DELETE': """, end="")
        
        choice = input()
        if choice != "DELETE":
            print("[!] You did not type 'DELETE'. Exiting.")
            sys.exit(0)
        elif choice == "DELETE":
            return True

    return False


# Loops through the list of project ids and exports them all to a folder. 
def delete_projects(server, verbose, debug, proxies, session, project_list):
    
    error_count = 0

    print(f"[+] Deleting projects...")

    for project in project_list:
        id = project["id"]
        name = project["name"]


        url = f"{server}/api/v1/pentestprojects/{id}/"

        headers = {
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept": "application/json",
            }
        my_json = json.dumps({})

        if debug == 1:
            res = session.delete(url, headers=headers, verify=False, proxies=proxies)
        else:  
            res = session.delete(url, headers=headers, verify=False)

        if res.status_code != 204:  
            print(f"[!] Received unexpected reponse code while deleting id {id}: {res.status_code}")
            print(f"[!] Continuing to try next id...")
            error_count += 1
            continue

    if error_count == 0:
        success = True
    else:
        success = False

    return [success, error_count]

@click.command()
@click.option('--server','-s',default="http://127.0.0.1:8000",show_default=True,help="The server you want to target, including the port if needed.")
@click.option('--verbose','-v',default=0,count=True,help="Verbosity level. Supports -v and -vv.")
@click.option('--debug','-d',is_flag=True,default=False,show_default=True,help="Activate debugging mode. This will send program traffic through the proxy specifed by the '--proxy' option, which is 127.0.0.1:8080 by default.")
@click.option('--proxy','-p',default="127.0.0.1:8080",show_default=True,help="Proxy for traffic during debugging.")
def main(server, verbose, debug, proxy):
    
    proxies={"http":proxy,"https":proxy}

    print(f"[+] Targeting server: {server}")

    time = 1
    warn = show_warning(server, time, 0)
    # warn will return True if the user accepts the warning and wishes to proceed
    if warn == True:
        time = 2
    else:
        print("User somehow managed to get out of the warn function without accepting. Exiting!")
        sys.exit(1)


    session, username, password = get_session(server, verbose, debug, proxies)
    project_list = get_project_info(server, verbose, debug, proxies, session, username, password)


    warn = show_warning(server, time, len(project_list))
    # show the warning again, because it's crucial the user understands this is unrecoverable
    if warn == True:
        pass
    else:
        print("User somehow managed to get out of the warn function without accepting. Exiting!")
        sys.exit(1)

    deleted = delete_projects(server, verbose, debug, proxies, session, project_list)

    if deleted[0] == True:
        print("[+] All projects successfully deleted!")
    else:
        print(f"[!] There were {deleted[1]} errors! You should check the output.")

if __name__=="__main__":
    main()
