#!/usr/bin/env python
import sys, os, time

supportedExtensions = [
    "jpg",
    "png",
    "cr2",
    "raw",
    "aae",
    "xmp",
    "avi",
    "mov",
    "mp4"
]

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
    print("")

def error(msg):
    print("ERROR: %s" % msg)
    quit(1)

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

def getExtension(path):
    return path.split(".")[-1].lower()

def getBaseName(path):
    return os.path.basename(path)

def getFilenameWithoutExtension(path):
    return os.path.splitext(os.path.basename(path))[0]

def moveFile(file):
    # Create new folder if destination doesn't exist
    if not os.path.exists(file["dest"]):
        os.makedirs(file["dest"])

    newFilePath = os.path.join(file["dest"], file['basename'])

    # Check for name collision. Error for now
    if os.path.exists(newFilePath):
        print("'%s' already exists in '%s'" % (file["basename"], file["dest"]))
        return -1

    # Move file
    try:
        os.rename(file["path"], newFilePath)
        print("%s --> %s" % (file["path"], newFilePath))

    except:
        print("Unable to move file '%s' to '%s'." % (file["basename"], file["dest"]))
        return -1

    return 0

def main(argv):
    version = 0.1
    files = []
    recurse = False

    # Process options
    if "-h" in argv:
        help(argv[0], version)
        quit()
    if "-r" in argv:
        recurse = True

    # Process Files and Directories in Arguments
    for i in argv:
        if os.path.isfile(i) and getExtension(i) in supportedExtensions:
            files.append({
                "path" : i,
                "ext"  : getExtension(i),
                "filename" : getFilenameWithoutExtension(i),
                "basename" : getBaseName(i),
                "date" : "",
                "dest" : ""
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
        file.update({"date" : getDateFromEXIF(file["path"])})

    # Process Files - If no EXIF available, use system date
    for file in files:
        if file["date"] == 0:
            file.update({"date" : getDateFromSystem(file["path"])})

    # Process Files - Determine destination, Move files
    for file in files:
        file.update({"dest" : destinationFromDate(file["date"])})
        moveFile(file)

if __name__ == "__main__":
    main(sys.argv)
