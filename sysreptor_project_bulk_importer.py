#!/usr/bin/python3

# name: sysreptor_project_bulk_importer.py
# 
# version: 1.0
# 
# author: r0pchainzZz
# 
# description:  Opens a directory and uploads all the exported
#               sysreptor projects within it to the targeted
#               instance of sysreptor.


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


def import_projects(server, verbose, debug, proxies, session, directory, finished):
    error_count = 0

    project_list = os.listdir(directory)

    for project in project_list:

        url = f"{server}/api/v1/pentestprojects/import/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept": "*/*",
            }


        with open(os.path.join(directory, project), "rb") as tar:
            if debug == 1:
                res = session.post(url, headers=headers, verify=False, files={"file":(project, tar)}, proxies=proxies)
            else:  
                res = session.post(url, headers=headers, verify=False, files={"file":(project, tar)})

        if res.status_code != 201:  
            print(f"[!] Received unexpected reponse code from import endpoint for {project}: {res.status_code}")
            print(f"[!] Continuing to try next project...")
            error_count += 1
            continue

        print(f"[+] Project imported from file: {project}")

        # if the "--finished" or "-F" flag is there, mark the project as readonly
        if finished:
            my_json = json.loads(res.content)
            new_id = my_json[0]["id"]

            url = f"{server}/api/v1/pentestprojects/{new_id}/readonly/" 
                
            if debug == 1:
                res = session.patch(url, headers=headers, verify=False, json={"readonly":"true"}, proxies=proxies)
            else:  
                res = session.patch(url, headers=headers, verify=False, json={"readonly":"true"})

            if res.status_code != 200:  
                print(f"[!] Received unexpected reponse code finishing {project}: {res.status_code}")
                print(f"[!] Continuing to try next project...")
                error_count += 1
                continue

            print("[+] Project successfully moved to 'finished' state.")
    
    if error_count == 0:
        success = True
    else:
        success = False

    return [success, error_count]

@click.command()
@click.option('--server','-s',default="http://127.0.0.1:8000",show_default=True,help="The server you want to target, including the port if needed.")
@click.option('--verbose','-v',default=0,count=True,help="Verbosity level. Supports -v and -vv.")
@click.option('--directory','-d',required=True,show_default=True,help="The directory where the projects are.")
@click.option('--debug','-D',is_flag=True,default=False,show_default=True,help="Activate debugging mode. This will send program traffic through the proxy specifed by the '--proxy' option, which is 127.0.0.1:8080 by default.")
@click.option('--proxy','-p',default="127.0.0.1:8080",show_default=True,help="Proxy for traffic during debugging.")
@click.option('--finished','-F',is_flag=True,default=False,show_default=True,help="Should all projects be marked as finished?")
def main(server, verbose, directory, debug, proxy, finished):
    
    proxies={"http":proxy,"https":proxy}

    print(f"[+] Targeting server: {server}")

    session = get_session(server, verbose, debug, proxies)
    imported = import_projects(server, verbose, debug, proxies, session, directory, finished)

    if imported[0] == True:
        print("[+] All projects successfully imported!")
    else:
        print(f"[!] There were {imported[1]} errors! You should check the output.")

if __name__=="__main__":
    main()
