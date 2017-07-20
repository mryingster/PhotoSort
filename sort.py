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
    print("")

def error(msg):
    print("ERROR: %s" % msg)
    quit(1)

def warning(msg):
    print("WARNING: %s" % msg)

def getExtension(path):
    return path.split(".")[-1].lower()

def getBaseName(path):
    return os.path.basename(path)

def getFilenameWithoutExtension(path):
    return os.path.splitext(os.path.basename(path))[0]

def getPathWithoutFilename(path):
    return os.path.dirname(path)

def getDateFromEXIF(image):
    import PIL.ExifTags
    import PIL.Image

    try:
        img = PIL.Image.open(image)
        exif_data = img._getexif()

    except:
        return 0

    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in img._getexif().items()
        if k in PIL.ExifTags.TAGS
    }

    return exif["DateTimeOriginal"]

def getDateFromSystem(image):
    return time.strftime("%Y:%m:%d %H:%M:%S", time.strptime(time.ctime(os.path.getmtime(image))))

def destinationFromDate(date):
    dateArray = date.split(" ")[0].split(":")
    return "%s/%s/%s" % (int(dateArray[0]), int(dateArray[1]), int(dateArray[2]))

def incrementName(file):
    import re
    newName = file["filename"]
    if re.match('.*_\([0-9]+\)', newName):
        oldName = re.compile('(.*)_\([0-9]+\)').sub(r'\1', newName)
        number = int(re.compile('.*_\(([0-9]+)\)').sub(r'\1', newName))
        newName = "%s_(%d)" % (oldName, number + 1)
    else:
        newName += "_(1)"

    newName += "."+file["ext"]
    return newName

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
        return 1

    # Move file
    try:
        os.rename(oldPath, newPath)
    except:
        return -1

    return 0

def main(argv):
    version = 0.1
    files = []
    recurse = False
    archive = False

    # Process options
    if "-h" in argv:
        help(argv[0], version)
        quit()

    if "-r" in argv:
        recurse = True

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

                "new_path" : "",                             # 2017/7/19/file.JPG
                "new_dir"  : ""                              # 2017/7/19/
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

    # Process Files - If no EXIF available, use system date
    for file in files:
        if file["date"] == 0:
            file.update({"date" : getDateFromSystem(file["old_path"])})

    # Process Files - Determine destination, Move files
    for file in files:
        file.update({"new_dir" : destinationFromDate(file["date"])})
        makeDirectory(file["new_dir"])
        status = -1
        while status != 0:

            file.update({"new_path" : os.path.join(file["new_dir"], file['basename'])})
            status = moveFile(file["old_path"], file["new_path"])

            # General error
            if status == -1:
                warning("Unable to move file '%s' to '%s'." % (file["basename"], file["new_dir"]))
                status = 0 # Skip to next file

            # Success
            if status == 0:
                if archive == True and file["ext"] in supportedArchiveExt:
                    createPar2File(file["new_path"])
                print("%s --> %s" % (file["old_path"], file["new_path"]))

            # Name collision.
            if status == 1:
                # Check checksum
                checksumA = checksumSha1(file["old_path"])
                checksumB = checksumSha1(file["new_path"])
                # If checksums are same, skip file
                if checksumA == checksumB:
                    warning("Duplicate file, '%s'. Skipping..." % file["basename"])
                    status = 0 # Skip to next file
                # If checksums are different, rename file
                else:
                    newName = incrementName(file)
                    warning("Duplicate filename, '%s'. Renaming to '%s'." % (file["basename"], newName))
                    file.update({"basename" : newName})

if __name__ == "__main__":
    main(sys.argv)
