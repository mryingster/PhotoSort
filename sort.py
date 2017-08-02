#!/usr/bin/env python
import sys, os, time

supportedSortingExt = ["jpg", "png", "cr2", "raw", "aae", "xmp", "avi", "mov", "mp4"]
supportedArchiveExt = ["jpg", "png", "cr2", "raw",               "avi", "mov", "mp4"]

def help(name, version):
    #     0        10        20        30        40        50        60        70        80
    #     |---------|---------|---------|---------|---------|---------|---------|---------|
    print("PhotoSort v%s" % version)
    print("")
    print("PhotoSort is a small utility that will sort supported filetypes by their ")
    print("metadata or their OS specified creation date, and put them into hierarchal")
    print("folders organized by year, month, and day.")
    print("")
    print("Usage")
    print("    %s (options) (files/directories)" % name)
    print("")
    print("Options")
    print("    -h   Show the help message")
    print("    -r   Add files and folders recursively")
    print("    -a   Archive media using Par2 after sorting")
    print("    -t   Test. Process files but don't do anything")
    print("")

def error(msg):
    print("ERROR: %s" % msg)
    quit(1)

def warning(msg):
    print("WARNING: %s" % msg)
    return

## Filename Functions ##

def getExtension(path):
    return path.split(".")[-1].lower()

def getBaseName(path):
    return os.path.basename(path)

def getFilenameWithoutExtension(path):
    return os.path.splitext(os.path.basename(path))[0]

def getPathWithoutFilename(path):
    return os.path.dirname(path)

## Date & EXIF Functions ##

def getDateFromEXIF(image):
    try:
        import exifread
    except:
        error("Please install exifread using the command: pip install exifread")
    date = 0

    # Open image
    f = open(image, 'rb')

    # Parse EXIF
    exif = exifread.process_file(f)
    for tag in ["DateTimeOriginal", "EXIF DateTimeOriginal"]:
        if tag in exif:
            date = str(exif[tag])

    return date

def getDateFromSystem(image):
    return time.strftime("%Y:%m:%d %H:%M:%S", time.strptime(time.ctime(os.path.getmtime(image))))

def destinationFromDate(date):
    dateArray = date.split(" ")[0].split(":")
    return "%s/%s/%s" % (int(dateArray[0]), int(dateArray[1]), int(dateArray[2]))

## Filename Manipulation Functions ##

def incrementName(filename):
    import re
    newName = getFilenameWithoutExtension(filename)
    if re.match('.*_\([0-9]+\)', newName):
        oldName = re.compile('(.*)_\([0-9]+\)').sub(r'\1', newName)
        number = int(re.compile('.*_\(([0-9]+)\)').sub(r'\1', newName))
        newName = "%s_(%d)" % (oldName, number + 1)
    else:
        newName += "_(1)"

    return newName

def determineNewPath(file):
    newPath = os.path.join(file["new_dir"], file["new_name"]+"."+file["ext"])
    return newPath

def determineNewNameAndPath(file, files):
    filename = file["filename"]
    basename = file["basename"]
    newPath = ""
    validPathFound = False

    while validPathFound == False:
        validPathFound = True

        # New path based on new directory and base name
        newPath = os.path.join(file["new_dir"], basename)

        # Create array of paths to compare against
        pathsToCheck = []

        # Add current file's destination path if there is a conflict
        if os.path.exists(newPath):
            pathsToCheck.append(newPath)

        # Add all pending files who have same destination name
        for fileToCheck in files:
            if fileToCheck["new_path"] in ["SKIP", ""]: continue
            if fileToCheck["old_path"] == file["old_path"]: break
            if fileToCheck["new_path"] == newPath:
                pathsToCheck.append(fileToCheck["old_path"])

        # Check all paths in array
        for pathToCheck in pathsToCheck:

            # If checksums are same, skip file
            if compareChecksum(file["old_path"], pathToCheck):
                warning("Duplicate file, '%s'. Skipping..." % filename)
                return filename, "SKIP"

            # If checksums are different, rename file
            filename = incrementName(filename)
            basename = filename + "." + file["ext"]
            validPathFound = False
            break

    # See if we had to rename, and give warning
    if filename != file["filename"]:
        warning("Duplicate filename, '%s'. Renaming to '%s'." % (file["basename"], basename))

    return filename, newPath

## Checksumming ##

def checksumSha1(path):
    import hashlib
    BUF_SIZE = 65536  # Read 64kb chunks to reduce memory usage
    sha1 = hashlib.sha1()

    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break

            sha1.update(data)

    return sha1.hexdigest()

def compareChecksum(path1, path2):
    if checksumSha1(path1) == checksumSha1(path2):
        return True
    return False

## PAR2 Functions ##

def checkPar2Install(prg="par2create"):
    import subprocess
    process = subprocess.Popen(["which", prg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output != ''

def createPar2File(path):
    import subprocess
    process = subprocess.Popen(["par2create", "-n1", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return error

## File Functions ##

def makeDirectory(path):
    try:
        # Create new folder if destination doesn't exist
        if not os.path.exists(path):
            os.makedirs(path)
    except:
        return 0
    return 1

def moveFile(oldPath, newPath):
    # Check for name collision. Error for now
    if os.path.exists(newPath):
        return 0

    # Move file
    try:
        os.rename(oldPath, newPath)
    except:
        return 0

    return 1

## Main Function ##

def main(argv):
    version = 0.1
    files = []
    recurse = False
    archive = False
    debug = False

    # Process options
    if "-h" in argv:
        help(argv[0], version)
        quit()

    if "-r" in argv:
        recurse = True

    if "-t" in argv:
        debug = True

    if "-a" in argv:
        if checkPar2Install():
            archive = True
        else:
            warning("Unable to locate 'par2' executable. Please ensure it is installed correctly.")

    # Process Files and Directories in Arguments
    for i in argv:
        if os.path.isfile(i) and getExtension(i) in supportedSortingExt:
            files.append({
                "old_path" : i,                              # sample/path/file.JPG
                "old_dir"  : getPathWithoutFilename(i),      # sample/path/

                "filename" : getFilenameWithoutExtension(i), # file
                "basename" : getBaseName(i),                 # file.jpg
                "ext"      : getExtension(i),                # jpg
                "date"     : "",                             # 2000:12:21 22:56:17

                "new_name" : "",                             # New name if renamed because of naming conflict
                "new_path" : "",                             # 2017/7/19/file.JPG
                "new_dir"  : "",                             # 2017/7/19/

                "associated" : []                            # List of indices of associated files
            })

        # Add all subdirectories to files list
        if os.path.isdir(i):
            for file in os.listdir(i):
                path = os.path.join(i, file)
                # If we find a file, add to queue, if we are recursing, add directories too
                if os.path.isfile(path) or os.path.isdir(path) and recurse == True:
                    argv.append(path)

    # If no files specified, exit
    if len(files) == 0:
        error("Please specify files to sort!")

    # Process Files - Try getting date from EXIF data
    for file in files:
        file.update({"date" : getDateFromEXIF(file["old_path"])})

    # If we got date from EXIF (more reliable) look for associated files and assign same date
    # Assuming associated file IF same name (minus extension) and same directory
    for file1 in files:
        if file1["date"] != 0:
            for file2 in files:
                if file1["old_dir"]  == file2["old_dir"]  and \
                   file1["filename"] == file2["filename"] and \
                   file1["ext"]      != file2["ext"]      and \
                                        file2["date"] == 0:

                    # Add index of associated file to main file
                    file1.update({"associated" : file1["associated"] + [files.index(file2)]})

                    # Mark associated file so it doesn't get processed otherwise
                    file2.update({"date" : file1["date"]})
                    file2.update({"new_path" : "SKIP"})

    # Process Files - If no EXIF available, use system date
    for file in files:
        if file["date"] == 0:
            file.update({"date" : getDateFromSystem(file["old_path"])})

    # Process Files - Determine destination
    for file in files:
        # Skip certain files
        if file["new_path"] == "SKIP" or file["new_name"] != "": continue

        # New directory based on date
        file.update({"new_dir" : destinationFromDate(file["date"])})

        # Look for naming conflicts and assign new path
        newFilename, newPath = determineNewNameAndPath(file, files)
        file.update({"new_name" : newFilename,
                     "new_path" : newPath})

        # If there are file associates, rename them accordingly
        for associatedFileIndex in file["associated"]:
            files[associatedFileIndex].update({"new_name" : file["new_name"],
                                               "new_dir"  : file["new_dir"]})
            files[associatedFileIndex].update({"new_path" : determineNewPath(files[associatedFileIndex])})

    # Process files - Archive and Move files
    for file in files:
        status = 1

        # Skip files
        if file["new_path"] == "SKIP": continue

        # Only create archvies and move files if we are not in test/debug mode
        if debug == False:
            makeDirectory(file["new_dir"])
            status = moveFile(file["old_path"], file["new_path"])
            if archive == True and file["ext"] in supportedArchiveExt:
                    createPar2File(file["new_path"])

        # If we are good, print output
        if status == 1:
            print("%s --> %s" % (file["old_path"], file["new_path"]))

        # Otherwise, error message
        if status == 0:
            warning("Unable to move file '%s' to '%s'." % (file["basename"], file["new_dir"]))

if __name__ == "__main__":
    main(sys.argv)
