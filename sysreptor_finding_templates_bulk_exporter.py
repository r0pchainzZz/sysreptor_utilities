#!/usr/bin/python3

# name: sysreptor_finding_templates_bulk_exporter.py 
# 
# version: 1.0
# 
# author: r0pchainzZz
# 
# description:  This script will export all finding templates from a Sysreptor
#               instance. It saves them into both individual files for each template
#               and a combined file for easy transfer. This should make it easier to
#               develop findings across teams.
#  
# disclaimer:   This is not an official project of Syslifters GmbH and not in 
#               any way affiliated with the company. 
 
 

from getpass import getpass
import requests, json, click, re, sys, os, subprocess
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# Asks for username and password, then returns session.
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


# Calls the API to find the ids and names of all templates. Returns a list of ids and names.
def get_template_info(server, verbose, debug, proxies, session):
    print("[+] Getting list of finding template IDs and names.")

    template_list = list()

    url = f"{server}/api/v1/findingtemplates/?ordering=-risk"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        }
    
    if debug == 1:
        res = session.get(url, verify=False, proxies=proxies)
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
        # names are more complicated for finding templates than report designs,
        # so the name needs to be extracted. The name also needs to have unicode arrow
        # characters converted to the word "to" for the sake of cleaner filenames.
        name = ""
        for translation in result["translations"]:
            if translation["language"] == "en-US": 
                name = translation["data"]["title"]

        name = re.sub("(\u2192|\u21fe|\u2265|\u21c9|\u21d2)","to", name)            

        if verbose >= 1:
            print(f"[+] Identified finding template: {result['id']} - {name}")
        template_list.append({"id":result['id'],"name":name})

    if verbose >= 2:
        print(template_list)

    print("[+] Template information retrieved successfully.")

    return template_list


# Loops through the list of template ids and exports them all to a folder. 
def export_templates(server, verbose, debug, proxies, session, username, password, template_list, output_dir):

    error_count = 0
    print(f"[+] Checking to make sure the output directory does not already exist.")
    # First, make sure that we have a unique directory name to write to.
    increment = 1
    output_dir_base = output_dir
    while os.path.exists(os.path.join(os.getcwd(), output_dir)):
        print(f"[!] Directory already exists. Incrementing name.")
        output_dir = output_dir_base + f"_{increment}"
        increment += 1

    print(f"[+] Success!. Templates will be exported to '{output_dir}'.")
    os.mkdir(output_dir)
    os.mkdir(f"{output_dir}/all_templates")
    
    # Now export
    print(f"[+] Exporting templates...")

    # make sure the right permissions are there
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


    # At this point either the script has permission to access templates or will have exited with an error.    
    for template in template_list:
        id = template["id"]
        name = template["name"]


        url = f"{server}/api/v1/findingtemplates/{id}/export"

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

        # replace spaces in the template names with underscores 
        name = re.sub("\s","_", name)

        try:
            save_name = f'{output_dir}/{name}_.tar.gz'   
            if verbose >= 1:
                print(f"[!] Trying to save to '{save_name}'.")
            with open(save_name,'wb') as f:
                f.write(res.content)
        except:
            print(f"[!] There was an error saving the template '{id} - {name}' to file. Trying the next one.") 
            error_count += 1
            continue

        # Unarchive the template contents to the all_templates subdirectory so that we can also create an 
        # additional archive that contains all of the templates together for easy moving or sharing.
        try:
            subprocess.run(["tar","-xzf", save_name, "--directory", f"{output_dir}/all_templates/"])
        except:
            print(f"[!] There was an error unarchivng the template '{id} - {name}' for combination with the others. Trying the next one.") 
            error_count += 1
            continue
            

        print(f"[+] Template saved successfully to '{name}.tar.gz'")
    
    # Compress the all_templates directory and remove it. 
    print("[+] Trying to combine all templates into single all_templates.tar.gz for easy use...")
    try:
        subprocess.run(["tar","czf",f"{output_dir}/all_templates.tar.gz","-C",f"{output_dir}/all_templates","."])
    except:
        print(f"[!] There was an error creating an archive of all the templates!")
        error_count += 1
    
    print("[+] Removing intermediate folder for combining templates...")
    try:
        subprocess.run(["rm","-rf",f"{output_dir}/all_templates"])
    except:
        print(f"[!] There was an error removing the folder with unarchived content from many templates!")
        error_count += 1
    
    print("[+] Templates successfully combined into single archive.")
            
    if error_count == 0:
        success = True
    else:
        success = False

    return [success, error_count]

@click.command()
@click.option('--server','-s',default="http://127.0.0.1:8000",show_default=True,help="The server you want to target, including the port if needed.")
@click.option('--verbose','-v',default=0,count=True,help="Verbosity level. Supports -v and -vv.")
@click.option('--output-dir','-o',default="exported_templates",show_default=True,help="The directory where the templates will be exported.")
@click.option('--debug','-d',is_flag=True,default=False,show_default=True,help="Activate debugging mode. This will send program traffic through the proxy specifed by the '--proxy' option, which is 127.0.0.1:8080 by default.")
@click.option('--proxy','-p',default="127.0.0.1:8080",show_default=True,help="Proxy for traffic during debugging.")
def main(server, verbose, output_dir, debug, proxy):
    
    proxies={"http":proxy,"https":proxy}

    print(f"[+] Targeting server: {server}")

    session, username, password = get_session(server, verbose, debug, proxies)
    template_list = get_template_info(server, verbose, debug, proxies, session)
    exported = export_templates(server, verbose, debug, proxies, session, username, password, template_list, output_dir)

    if exported[0] == True:
        print("[+] All templates successfully exported!")
    else:
        print(f"[!] There were {exported[1]} errors! You should check the output.")

if __name__=="__main__":
    main()
