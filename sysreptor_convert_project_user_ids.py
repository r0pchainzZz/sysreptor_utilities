#!/usr/bin/python3

# file: convert_project_user_ids.py 
# 
# version: 1.0
#
# author: r0pchainzZz 
# 
# description:  Takes two json files, one with the old Sysreptor usernames
#               and ids, and one with the new usernames and ids, and also   
#               requires a tar file name of a Sysreptor exported project 
#               or a directory name for a directory containing Sysreptor
#               projects. It then unarchives each project, converts any 
#               recognized user IDs in the project, and rearchives the project
#               into a new folder.
# 


import json, click, re, sys, os, random, string, tarfile, shutil, zipfile

def create_conv_list(old_json,new_json):
    # import the two jsons
    with open(old_json,'r') as file:
        old = json.load(file)
    with open(new_json,'r') as file:
        new = json.load(file)

    conv_list = []

    for user in old:
        username = user["username"]
        old_id = user["id"]

        for new_user in new:
            if new_user["username"] == username:
                new_id = new_user["id"]
                conv_list.append({"username":username,"ids":{"old_id":old_id,"new_id":new_id}})
                break
    
    return(conv_list)

def create_output_dir(output_dir):
    
    error_count = 0
    print(f"[+] Checking to make sure the output directory does not already exist.")
    # First, make sure that we have a unique directory name to write to.
    increment = 1
    output_dir_base = output_dir
    while os.path.exists(os.path.join(os.getcwd(), output_dir)):
        print(f"[!] Directory already exists. Incrementing name.")
        output_dir = output_dir_base + f"_{increment}"
        increment += 1

    print(f"[+] Success! Converted projects will be written to '{output_dir}'.")
    os.mkdir(output_dir)

    return output_dir

def convert_all_projects(verbose, conv_list, directory, output_dir):
    # get a list of all project files in the directory
    file_list = os.listdir(directory)

    # loop through the list and convert each project
    for file in file_list:
        convert_single_project(verbose, conv_list, directory, output_dir, file)
    
    return True

def convert_single_project(verbose, conv_list, directory, output_dir, filename):
    
    stripped_name = re.sub(r'\.tar.gz', "", filename)
    output_name = f"{stripped_name}updated-uids"

    # generate random name for temporary directory
    temp_dir = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    if verbose >= 2:
        print(filename)
        print(stripped_name)
        print(output_name)
        print(temp_dir)
    
    os.mkdir(temp_dir)

    with tarfile.open(f"{directory}/{filename}") as tf:
        tf.extractall(path=temp_dir)
    
    file_list = os.listdir(temp_dir)

    try:
        for file in file_list:
            if re.search(".json$", file):
                json_filename = file
                if verbose >= 2:
                    print(json_filename)
                break
    except: 
        print("Could not find a JSON file for that project. Removing temporary directory and moving on...")
        shutil.rmtree(temp_dir)
        return False

    try:
        with open(f"{temp_dir}/{json_filename}", "r") as f:
            project_json = json.load(f)
    except:
        print("Error loading JSON")

    
    # now go through the project json and replace the uids
    for i in range(0,len(project_json["members"])):
        member = project_json["members"][i]
        #print(member)
        found = 0
        username = member["username"]
        old_id = member["id"]

        for user in conv_list:
            if user["username"] == username:
                if user["ids"]["old_id"] == old_id:
                    #print(f"{username}: {user['ids']['old_id']} => {user['ids']['new_id']}")
                    project_json["members"][i]["id"] = user["ids"]["new_id"]
                    found = 1
                    break

        if found == 0:
            print(f"[!] User {username} has no ID in list of new user IDs")
    
    
    with open(f"{temp_dir}/{json_filename}", "w") as f:
        json.dump(project_json, f)

    try:
        archive_name = os.path.join(os.getcwd(),output_dir,f"{stripped_name}-updated-uids.tar.gz")
        with tarfile.open(archive_name, "w:gz") as tf:
            os.chdir(temp_dir)
            for dir_, _, files in os.walk("."):
                for file_name in files:
                    fullpath = os.path.join(dir_,file_name)
                    fullpath = re.sub(r'\./', "", fullpath)
                    #print(fullpath)
                    tf.add(fullpath)
            os.chdir("..")            

    except:
        print("something went wrong!")
        shutil.rmtree(temp_dir)
        sys.exit(1)
        pass

    shutil.rmtree(temp_dir)
    return True

@click.command()
@click.option('--old-json','-o',required=True,help="The name of the json file containing the names and old IDs")
@click.option('--new-json','-n',required=True,help="The name of the json file containing the names and new IDs")
@click.option('--directory','-d',required=True,help="The name of the directory containing exported sysreptor projects.")
@click.option('--output-dir','-O',default="projects_updated_user_ids",show_default=True,help="The directory where the projects will be exported after their user IDs are updated.")
@click.option('--verbose','-v',default=0,count=True,help="Verbosity level. Supports -v and -vv.")
def main(old_json, new_json, directory, output_dir, verbose):
    conv_list = create_conv_list(old_json,new_json)

    if verbose > 0:
        for user in conv_list:
            print(user["username"])

    try: 
        output_dir = create_output_dir(output_dir)
    except:
        print("[!] Error creating output directory. Exiting!")
        sys.exit(1)

    try:
        convert_all_projects(verbose, conv_list, directory, output_dir)
    except:
        print("[!] Error exporting projects. Exiting!")
        sys.exit(1)

if __name__ == "__main__":
    main()



