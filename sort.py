#!/usr/bin/env python
import sys, os, time

supportedExtensions = [
    "jpg",
    "png",
    "cr2",
    "raw",
    "aae",
    "avi",
    "mov",
    "mp4"
]

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

def moveFile(file, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)

    try:
        os.rename(file, os.path.join(destination, file))
        print("%s --> %s" % (file, destination))

    except:
        print("Unable to move file '%s' to '%s'." % (file, destination))
        return -1

    return 0

def main(argv):
    files = []

    # Process Arguments
    for i in argv:
        if os.path.isfile(i) and getExtension(i) in supportedExtensions:
            files.append(i)
        # TODO if os.path.isdir(i): add all subdirectories to files list

    # Process Files
    for file in files:
        # Try getting date from EXIF data
        date = getDateFromEXIF(file)

        # If no EXIF available, use system date
        if date == 0:
            date = getDateFromSystem(file)

        # Use date to determine destination
        destinationFolder = destinationFromDate(date)

        # Move file
        moveFile(file, destinationFolder)

if __name__ == "__main__":
    main(sys.argv[1:])
